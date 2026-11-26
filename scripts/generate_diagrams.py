"""Genera los 3 diagramas profesionales en PNG de alta resolución para el documento Word."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT_DIR = Path(__file__).resolve().parent.parent
DIAGRAMS_DIR = ROOT_DIR / "docs" / "diagrams"


def _box(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    subtitle: str = "",
    facecolor: str = "#EFF6FF",
    edgecolor: str = "#1D4ED8",
    title_color: str = "#0F172A",
    fontsize: float = 9.5,
) -> None:
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.025",
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=1.6,
        zorder=3,
    )
    ax.add_patch(patch)
    if subtitle:
        ax.text(
            x + w / 2,
            y + h * 0.64,
            title,
            ha="center",
            va="center",
            fontsize=fontsize,
            fontweight="bold",
            color=title_color,
            zorder=4,
        )
        ax.text(
            x + w / 2,
            y + h * 0.28,
            subtitle,
            ha="center",
            va="center",
            fontsize=fontsize - 1.5,
            color="#334155",
            zorder=4,
        )
    else:
        ax.text(
            x + w / 2,
            y + h / 2,
            title,
            ha="center",
            va="center",
            fontsize=fontsize,
            fontweight="bold",
            color=title_color,
            zorder=4,
        )


def _arrow(
    ax,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    label: str = "",
    color: str = "#334155",
    linestyle: str = "-",
    rad: float = 0.0,
    label_offset: tuple[float, float] = (0.0, 0.018),
) -> None:
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops=dict(
            arrowstyle="-|>,head_length=0.6,head_width=0.35",
            color=color,
            lw=1.4,
            linestyle=linestyle,
            connectionstyle=f"arc3,rad={rad}",
        ),
        zorder=5,
    )
    if label:
        mx = (x1 + x2) / 2 + label_offset[0]
        my = (y1 + y2) / 2 + label_offset[1]
        ax.text(
            mx,
            my,
            label,
            ha="center",
            va="center",
            fontsize=7.6,
            color=color,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="none", alpha=0.88),
            zorder=6,
        )


def draw_architecture_soa(output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(13, 7.2), dpi=220)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5,
        0.955,
        "Diagrama 1 — Arquitectura Orientada a Servicios (SOA) de ReservaSOA",
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold",
        color="#0F172A",
    )
    ax.text(
        0.5,
        0.915,
        "Integración desacoplada mediante REST/HTTP + JSON, JWT, X-Service-Key y persistencia autónoma",
        ha="center",
        va="center",
        fontsize=9,
        color="#475569",
    )

    # Consumidores
    _box(ax, 0.03, 0.62, 0.19, 0.16, "Cliente Web SPA", "HTML5 / CSS3 / JS\nhttp://localhost:8000", "#EEF2FF", "#4338CA")
    _box(ax, 0.03, 0.34, 0.19, 0.16, "Postman / REST", "Pruebas de Contratos\ny Flujo E2E", "#EEF2FF", "#4338CA")

    # API Gateway
    _box(
        ax,
        0.28,
        0.44,
        0.19,
        0.24,
        "API Gateway &\nCatálogo SOA",
        "FastAPI (:8000)\n/api/* Proxy\n/registry/services",
        "#ECFDF5",
        "#047857",
    )

    # Servicios
    services = [
        (0.55, 0.74, "users-service (:8001)", "Auth JWT + CRUD Usuarios", "users.db"),
        (0.55, 0.54, "spaces-service (:8002)", "CRUD Salas + Validación", "spaces.db"),
        (0.55, 0.34, "reservations-service (:8003)", "CRUD + Orquestador E2E", "reservations.db"),
        (0.55, 0.14, "notifications-service (:8004)", "Folios CONF + Historial", "notifications.db"),
    ]
    for x, y, title, sub, db_name in services:
        fc = "#FEF3C7" if "Orquestador" in sub else "#EFF6FF"
        ec = "#B45309" if "Orquestador" in sub else "#1D4ED8"
        _box(ax, x, y, 0.24, 0.13, title, sub, fc, ec, fontsize=9)
        _box(ax, 0.84, y + 0.015, 0.13, 0.10, db_name, "SQLite", "#F1F5F9", "#475569", fontsize=8.5)
        _arrow(ax, x + 0.24, y + 0.065, 0.84, y + 0.065, "", "#475569")

    # Flechas consumidores -> gateway
    _arrow(ax, 0.22, 0.70, 0.28, 0.60, "HTTP/JSON\n+ JWT", "#4338CA", label_offset=(-0.005, 0.03))
    _arrow(ax, 0.22, 0.42, 0.28, 0.51, "HTTP/JSON", "#4338CA", label_offset=(-0.005, -0.03))

    # Flechas gateway -> servicios
    for _, y, _, _, _ in services:
        _arrow(ax, 0.47, 0.56, 0.55, y + 0.065, "", "#047857")

    # Comunicación inter-servicio (Orquestación)
    _arrow(ax, 0.64, 0.47, 0.64, 0.54, "GET /validate", "#B45309", linestyle="--", label_offset=(0.065, 0.0))
    _arrow(ax, 0.57, 0.47, 0.57, 0.74, "GET /users/{id}", "#B45309", linestyle="--", rad=-0.22, label_offset=(-0.06, 0.02))
    _arrow(ax, 0.67, 0.34, 0.67, 0.27, "POST /notifications", "#B45309", linestyle="--", label_offset=(0.075, 0.0))

    ax.text(
        0.5,
        0.04,
        "Línea punteada naranja: consumo directo inter-servicio (HTTP/JSON + cabecera X-Service-Key).",
        ha="center",
        va="center",
        fontsize=8.3,
        style="italic",
        color="#92400E",
    )

    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def draw_components_deployment(output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(13, 7.2), dpi=220)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5,
        0.955,
        "Diagrama 2 — Componentes y Despliegue (Procesos Uvicorn + Capas Internas)",
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold",
        color="#0F172A",
    )

    # Contenedor del nodo
    node = FancyBboxPatch(
        (0.03, 0.06),
        0.94,
        0.84,
        boxstyle="round,pad=0.015,rounding_size=0.02",
        facecolor="#F8FAFC",
        edgecolor="#64748B",
        linewidth=1.5,
        linestyle="--",
        zorder=1,
    )
    ax.add_patch(node)
    ax.text(0.05, 0.875, "Nodo de Ejecución Local — Python 3.12 / FastAPI / Uvicorn (scripts/start_all.py)", fontsize=9, fontweight="bold", color="#334155")

    # Gateway arriba
    _box(
        ax,
        0.24,
        0.71,
        0.52,
        0.13,
        "Proceso :8000 — api-gateway",
        "Reverse Proxy (/api/*)  |  ServiceRegistry (/registry/services)  |  Frontend Estático (/)",
        "#ECFDF5",
        "#047857",
        fontsize=9.5,
    )

    # 4 servicios en columnas
    cols = [
        (0.05, "Proceso :8001\nusers-service", "FastAPI + OpenAPI\nUserRepository\nAuth JWT / PBKDF2", "data/users.db", "#EFF6FF", "#1D4ED8"),
        (0.285, "Proceso :8002\nspaces-service", "FastAPI + OpenAPI\nSpaceRepository\nValidador Capacidad", "data/spaces.db", "#EFF6FF", "#1D4ED8"),
        (0.52, "Proceso :8003\nreservations-service", "FastAPI + OpenAPI\nOrchestrator (httpx)\nReservationRepository", "data/reservations.db", "#FEF3C7", "#B45309"),
        (0.755, "Proceso :8004\nnotifications-service", "FastAPI + OpenAPI\nNotificationRepository\nGenerador Folios CONF", "data/notifications.db", "#EFF6FF", "#1D4ED8"),
    ]
    for x, title, layers, db, fc, ec in cols:
        _box(ax, x, 0.42, 0.195, 0.21, title, layers, fc, ec, fontsize=8.8)
        _box(ax, x + 0.02, 0.25, 0.155, 0.10, db, "SQLite 3", "#F1F5F9", "#475569", fontsize=8.2)
        _arrow(ax, x + 0.0975, 0.42, x + 0.0975, 0.35, "", "#475569")
        _arrow(ax, 0.50, 0.71, x + 0.0975, 0.63, "", "#047857")

    # Módulo compartido abajo
    _box(
        ax,
        0.12,
        0.09,
        0.76,
        0.11,
        "Módulo Transversal Compartido — shared/",
        "config.py (.env)   |   security.py (JWT HS256, X-Service-Key)   |   errors.py (JSON uniforme)   |   http_client.py (httpx)",
        "#EEF2FF",
        "#4338CA",
        fontsize=9,
    )

    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def draw_sequence_e2e(output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(13, 7.6), dpi=220)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5,
        0.96,
        "Diagrama 3 — Secuencia del Proceso Integrado E2E: Creación de Reservación",
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold",
        color="#0F172A",
    )

    actors = [
        (0.09, "Cliente Web\n(Usuario)", "#EEF2FF", "#4338CA"),
        (0.25, "API Gateway\n(:8000)", "#ECFDF5", "#047857"),
        (0.43, "Reservations\n(:8003)", "#FEF3C7", "#B45309"),
        (0.61, "Users\n(:8001)", "#EFF6FF", "#1D4ED8"),
        (0.77, "Spaces\n(:8002)", "#EFF6FF", "#1D4ED8"),
        (0.92, "Notifications\n(:8004)", "#EFF6FF", "#1D4ED8"),
    ]

    for x, label, fc, ec in actors:
        _box(ax, x - 0.068, 0.84, 0.136, 0.08, label, "", fc, ec, fontsize=8.3)
        ax.plot([x, x], [0.06, 0.84], linestyle="--", color="#94A3B8", lw=1.1, zorder=1)

    steps = [
        (0.78, 0.09, 0.25, "1. POST /api/reservations (JWT)", "#4338CA", "-"),
        (0.72, 0.25, 0.43, "2. Reenvía POST /reservations", "#047857", "-"),
        (0.65, 0.43, 0.61, "3. GET /users/{id} (X-Service-Key)", "#B45309", "-"),
        (0.59, 0.61, 0.43, "4. 200 OK (usuario activo)", "#1D4ED8", "--"),
        (0.51, 0.43, 0.77, "5. GET /spaces/{id}/validate?attendees=N", "#B45309", "-"),
        (0.45, 0.77, 0.43, "6. 200 OK (valid=true, sala disponible)", "#1D4ED8", "--"),
        (0.37, 0.43, 0.43, "7. Valida traslapes + INSERT reservations.db", "#0F172A", "self"),
        (0.29, 0.43, 0.92, "8. POST /notifications (X-Service-Key)", "#B45309", "-"),
        (0.23, 0.92, 0.43, "9. 201 Created (folio CONF-2026-XXXXXX)", "#1D4ED8", "--"),
        (0.15, 0.43, 0.25, "10. 201 Created (reserva + folio + soa_trace)", "#B45309", "--"),
        (0.09, 0.25, 0.09, "11. Muestra comprobante y traza SOA", "#047857", "--"),
    ]

    for y, x1, x2, label, color, style in steps:
        if style == "self":
            _box(ax, x1 - 0.13, y - 0.025, 0.26, 0.05, label, "", "#FEF9C3", "#CA8A04", fontsize=7.6)
        else:
            _arrow(ax, x1, y, x2, y, label, color, linestyle=style, label_offset=(0.0, 0.017))

    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    DIAGRAMS_DIR.mkdir(parents=True, exist_ok=True)
    draw_architecture_soa(DIAGRAMS_DIR / "01_arquitectura_soa.png")
    draw_components_deployment(DIAGRAMS_DIR / "02_componentes_despliegue.png")
    draw_sequence_e2e(DIAGRAMS_DIR / "03_secuencia_reserva_e2e.png")
    print("Diagramas PNG generados exitosamente en docs/diagrams/.")


if __name__ == "__main__":
    main()
