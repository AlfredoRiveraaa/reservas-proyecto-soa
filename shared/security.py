"""Seguridad básica: hash de contraseñas, tokens JWT (HS256) y llaves internas SOA."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from shared.config import get_settings
from shared.errors import ForbiddenError, UnauthorizedError

bearer_scheme = HTTPBearer(auto_error=False)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def hash_password(password: str) -> str:
    """Genera un hash PBKDF2-HMAC-SHA256 con sal aleatoria."""
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256${salt}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verifica una contraseña contra su hash almacenado en tiempo constante."""
    try:
        algorithm, salt, expected_hex = stored_hash.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        derived = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000
        )
        return hmac.compare_digest(derived.hex(), expected_hex)
    except ValueError:
        return False


def create_access_token(payload: dict[str, Any], expires_minutes: int | None = None) -> str:
    """Crea un token JWT estándar firmado con HMAC-SHA256."""
    settings = get_settings()
    ttl_minutes = expires_minutes if expires_minutes is not None else settings.jwt_expire_minutes
    now = int(time.time())

    header = {"alg": "HS256", "typ": "JWT"}
    claims = {**payload, "iat": now, "exp": now + ttl_minutes * 60}

    encoded_header = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _b64url_encode(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")

    signature = hmac.new(
        settings.jwt_secret_key.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    return f"{encoded_header}.{encoded_payload}.{_b64url_encode(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodifica y valida la firma y vigencia de un token JWT."""
    settings = get_settings()
    parts = token.split(".")
    if len(parts) != 3:
        raise UnauthorizedError("Formato de token JWT inválido.")

    encoded_header, encoded_payload, encoded_sig = parts
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    expected_sig = hmac.new(
        settings.jwt_secret_key.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()

    try:
        provided_sig = _b64url_decode(encoded_sig)
    except Exception as exc:
        raise UnauthorizedError("Firma de token JWT malformada.") from exc

    if not hmac.compare_digest(expected_sig, provided_sig):
        raise UnauthorizedError("Firma de token JWT inválida.")

    try:
        claims = json.loads(_b64url_decode(encoded_payload).decode("utf-8"))
    except Exception as exc:
        raise UnauthorizedError("Contenido de token JWT ilegible.") from exc

    if int(claims.get("exp", 0)) < int(time.time()):
        raise UnauthorizedError("El token JWT ha expirado.")

    return claims


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    """Dependencia FastAPI que exige un Bearer JWT válido."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Se requiere cabecera Authorization: Bearer <token>.")
    return decode_access_token(credentials.credentials)


def require_admin(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Dependencia FastAPI que restringe la operación a usuarios con rol admin."""
    if user.get("role") != "admin":
        raise ForbiddenError("Esta operación requiere rol de administrador.")
    return user


def verify_service_key(x_service_key: str | None = Header(default=None)) -> bool:
    """Valida la llave compartida para llamadas internas servicio-a-servicio."""
    settings = get_settings()
    if not x_service_key or not hmac.compare_digest(x_service_key, settings.internal_service_key):
        raise UnauthorizedError("Llave interna X-Service-Key inválida o ausente.")
    return True


def get_user_or_internal_service(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_service_key: str | None = Header(default=None),
) -> dict[str, Any]:
    """Permite acceso tanto a un usuario autenticado (JWT) como a otro servicio SOA."""
    settings = get_settings()
    if x_service_key and hmac.compare_digest(x_service_key, settings.internal_service_key):
        return {"sub": "internal-service", "role": "service"}
    if credentials is not None and credentials.scheme.lower() == "bearer":
        return decode_access_token(credentials.credentials)
    raise UnauthorizedError("Se requiere token Bearer JWT o cabecera X-Service-Key válida.")
