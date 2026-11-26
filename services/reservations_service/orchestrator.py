"""Orquestador SOA del proceso de negocio completo de reservación de espacios."""

from __future__ import annotations

from typing import Any

from services.reservations_service.models import (
    ReservationCreate,
    ReservationResponse,
    ReservationUpdate,
    SoaStepTrace,
)
from services.reservations_service.repository import ReservationRepository
from shared.errors import (
    BusinessValidationError,
    ConflictError,
    NotFoundError,
    UpstreamServiceError,
)
from shared.http_client import ServiceHttpClient


class ReservationOrchestrator:
    """Coordina la integración HTTP entre users, spaces, reservations y notifications."""

    def __init__(
        self,
        repo: ReservationRepository,
        users_client: ServiceHttpClient,
        spaces_client: ServiceHttpClient,
        notifications_client: ServiceHttpClient,
    ) -> None:
        self.repo = repo
        self.users_client = users_client
        self.spaces_client = spaces_client
        self.notifications_client = notifications_client

    async def _fetch_active_user(self, user_id: int) -> dict[str, Any]:
        resp = await self.users_client.get(f"/users/{user_id}")
        if resp.status_code == 404:
            raise NotFoundError(f"El usuario {user_id} no existe en users-service.")
        if resp.status_code >= 400:
            raise UpstreamServiceError(
                message="Error al consultar el servicio de usuarios.",
                status_code=502,
                error_code="USERS_SERVICE_ERROR",
                details={"upstream_status": resp.status_code},
            )
        user = resp.json()
        if not user.get("is_active", False):
            raise BusinessValidationError(
                f"El usuario '{user.get('full_name')}' se encuentra inactivo y no puede reservar."
            )
        return user

    async def _validate_space(self, space_id: int, attendees: int) -> dict[str, Any]:
        resp = await self.spaces_client.get(
            f"/spaces/{space_id}/validate",
            params={"attendees": attendees},
        )
        if resp.status_code == 404:
            raise NotFoundError(f"El espacio {space_id} no existe en spaces-service.")
        if resp.status_code >= 400:
            raise UpstreamServiceError(
                message="Error al validar el espacio en spaces-service.",
                status_code=502,
                error_code="SPACES_SERVICE_ERROR",
                details={"upstream_status": resp.status_code},
            )
        data = resp.json()
        if not data.get("valid", False):
            raise BusinessValidationError(data.get("reason", "El espacio no cumple las reglas."))
        return data["space"]

    async def _send_notification(
        self,
        *,
        reservation: ReservationResponse,
        event_type: str,
        subject: str,
        message: str,
    ) -> tuple[str, SoaStepTrace]:
        payload = {
            "reservation_id": reservation.id,
            "user_id": reservation.user_id,
            "recipient_email": reservation.user_email,
            "recipient_name": reservation.user_name,
            "event_type": event_type,
            "subject": subject,
            "message": message,
            "channel": "EMAIL",
        }
        try:
            resp = await self.notifications_client.post("/notifications", json_body=payload)
            if resp.status_code in (200, 201):
                body = resp.json()
                code = body.get("confirmation_code", "")
                return code, SoaStepTrace(
                    service="notifications-service",
                    operation="POST /notifications",
                    status="OK",
                    detail=f"Confirmación emitida con folio {code}",
                )
            return "PENDING-RETRY", SoaStepTrace(
                service="notifications-service",
                operation="POST /notifications",
                status="DEGRADED",
                detail=f"Respuesta inesperada ({resp.status_code}); confirmación pendiente.",
            )
        except UpstreamServiceError as exc:
            return "PENDING-RETRY", SoaStepTrace(
                service="notifications-service",
                operation="POST /notifications",
                status="DEGRADED",
                detail=f"Servicio temporalmente no disponible: {exc.message}",
            )

    async def create_reservation(
        self, payload: ReservationCreate, effective_user_id: int
    ) -> ReservationResponse:
        """Ejecuta el flujo E2E completo de creación de reservación."""
        trace: list[SoaStepTrace] = []

        # Paso 1: Validar existencia y estado activo del usuario en users-service
        user = await self._fetch_active_user(effective_user_id)
        trace.append(
            SoaStepTrace(
                service="users-service",
                operation=f"GET /users/{effective_user_id}",
                status="OK",
                detail=f"Usuario activo validado: {user['full_name']} ({user['department']})",
            )
        )

        # Paso 2: Validar existencia, disponibilidad operativa y capacidad en spaces-service
        space = await self._validate_space(payload.space_id, payload.attendees)
        trace.append(
            SoaStepTrace(
                service="spaces-service",
                operation=f"GET /spaces/{payload.space_id}/validate?attendees={payload.attendees}",
                status="OK",
                detail=(
                    f"Sala '{space['name']}' ({space['code']}) disponible "
                    f"(capacidad {space['capacity']})"
                ),
            )
        )

        # Paso 3: Validar ausencia de traslape de horario en reservations.db
        if self.repo.has_time_conflict(
            space_id=payload.space_id,
            reservation_date=payload.reservation_date,
            start_time=payload.start_time,
            end_time=payload.end_time,
        ):
            raise ConflictError(
                f"La sala '{space['name']}' ya cuenta con una reservación confirmada "
                f"el {payload.reservation_date} entre {payload.start_time} y {payload.end_time}."
            )

        # Paso 4: Persistir la reservación
        created = self.repo.create(
            user_id=int(user["id"]),
            user_name=user["full_name"],
            user_email=user["email"],
            space_id=int(space["id"]),
            space_code=space["code"],
            space_name=space["name"],
            title=payload.title,
            reservation_date=payload.reservation_date,
            start_time=payload.start_time,
            end_time=payload.end_time,
            attendees=payload.attendees,
            notes=payload.notes,
        )
        trace.append(
            SoaStepTrace(
                service="reservations-service",
                operation="SQLite INSERT reservations",
                status="OK",
                detail=f"Reservación #{created.id} registrada localmente.",
            )
        )

        # Paso 5: Emitir confirmación en notifications-service
        code, notif_trace = await self._send_notification(
            reservation=created,
            event_type="RESERVATION_CONFIRMED",
            subject=f"Confirmación de reserva: {created.space_name} ({created.reservation_date})",
            message=(
                f"Hola {created.user_name}, tu reservación '{created.title}' en "
                f"{created.space_name} ({created.space_code}) fue confirmada para el "
                f"{created.reservation_date} de {created.start_time} a {created.end_time} "
                f"({created.attendees} asistentes)."
            ),
        )
        trace.append(notif_trace)

        final_reservation = self.repo.set_confirmation_code(created.id, code)
        final_reservation.soa_trace = trace
        return final_reservation

    async def update_reservation(
        self, reservation_id: int, payload: ReservationUpdate
    ) -> ReservationResponse:
        """Actualiza horario o asistentes revalidando capacidad y conflictos."""
        existing = self.repo.get_by_id(reservation_id)
        if existing.status == "CANCELLED":
            raise BusinessValidationError("No se puede modificar una reservación cancelada.")

        new_title = payload.title if payload.title is not None else existing.title
        new_date = (
            payload.reservation_date
            if payload.reservation_date is not None
            else existing.reservation_date
        )
        new_start = payload.start_time if payload.start_time is not None else existing.start_time
        new_end = payload.end_time if payload.end_time is not None else existing.end_time
        new_attendees = payload.attendees if payload.attendees is not None else existing.attendees
        new_notes = payload.notes if payload.notes is not None else existing.notes

        if new_end <= new_start:
            raise BusinessValidationError("La hora de fin debe ser posterior a la hora de inicio.")

        trace: list[SoaStepTrace] = []
        await self._validate_space(existing.space_id, new_attendees)
        trace.append(
            SoaStepTrace(
                service="spaces-service",
                operation=f"GET /spaces/{existing.space_id}/validate?attendees={new_attendees}",
                status="OK",
                detail="Capacidad y estado operativo revalidados.",
            )
        )

        if self.repo.has_time_conflict(
            space_id=existing.space_id,
            reservation_date=new_date,
            start_time=new_start,
            end_time=new_end,
            exclude_reservation_id=reservation_id,
        ):
            raise ConflictError(
                f"El nuevo horario ({new_date} {new_start}-{new_end}) se traslapa con otra reserva."
            )

        updated = self.repo.update(
            reservation_id,
            title=new_title,
            reservation_date=new_date,
            start_time=new_start,
            end_time=new_end,
            attendees=new_attendees,
            notes=new_notes,
        )
        _, notif_trace = await self._send_notification(
            reservation=updated,
            event_type="RESERVATION_UPDATED",
            subject=f"Actualización de reserva #{updated.id}: {updated.space_name}",
            message=(
                f"Tu reservación '{updated.title}' fue actualizada para el "
                f"{updated.reservation_date} de {updated.start_time} a {updated.end_time}."
            ),
        )
        trace.append(notif_trace)
        updated.soa_trace = trace
        return updated

    async def cancel_reservation(self, reservation_id: int) -> ReservationResponse:
        """Cancela una reservación y dispara la notificación de cancelación."""
        existing = self.repo.get_by_id(reservation_id)
        if existing.status == "CANCELLED":
            raise ConflictError(f"La reservación #{reservation_id} ya se encuentra cancelada.")

        cancelled = self.repo.cancel(reservation_id)
        _, notif_trace = await self._send_notification(
            reservation=cancelled,
            event_type="RESERVATION_CANCELLED",
            subject=f"Cancelación de reserva #{cancelled.id}: {cancelled.space_name}",
            message=(
                f"La reservación '{cancelled.title}' en {cancelled.space_name} del "
                f"{cancelled.reservation_date} ({cancelled.start_time}-{cancelled.end_time}) "
                "ha sido cancelada."
            ),
        )
        cancelled.soa_trace = [notif_trace]
        return cancelled
