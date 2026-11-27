# Guía de Ejecución Reproducible — ReservaSOA

Esta guía describe paso a paso cómo instalar, configurar, ejecutar y probar el ecosistema completo de **ReservaSOA** en un entorno local Windows, macOS o Linux.

---

## 1. Requisitos Previos

- **Python 3.11 o superior** (probado con Python 3.12)
- **Git**
- (Opcional) **Postman** o **Insomnia** para importar la colección `tests/postman/ReservaSOA.postman_collection.json`

---

## 2. Instalación

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/AlfredoRiveraaa/reservas-proyecto-soa.git
   cd reservas-proyecto-soa
   ```

2. Crear y activar el entorno virtual:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Configurar variables de entorno:
   ```powershell
   Copy-Item .env.example .env
   ```
   > **Seguridad:** Edite `.env` con sus propias llaves locales (`JWT_SECRET_KEY`, `INTERNAL_SERVICE_KEY`). El archivo `.env` está listado en `.gitignore` y nunca se sube al repositorio.

---

## 3. Ejecución del Sistema Completo

Ejecute el lanzador unificado para iniciar los **4 servicios SOA independientes** y el **API Gateway**:

```bash
python scripts/start_all.py
```

Servicios levantados automáticamente:

| Servicio | URL Base | Contrato OpenAPI (Swagger UI) | Base de Datos |
|---|---|---|---|
| **API Gateway + Cliente Web** | `http://127.0.0.1:8000` | `http://127.0.0.1:8000/docs` | N/A |
| **users-service** | `http://127.0.0.1:8001` | `http://127.0.0.1:8001/docs` | `data/users.db` |
| **spaces-service** | `http://127.0.0.1:8002` | `http://127.0.0.1:8002/docs` | `data/spaces.db` |
| **reservations-service** | `http://127.0.0.1:8003` | `http://127.0.0.1:8003/docs` | `data/reservations.db` |
| **notifications-service** | `http://127.0.0.1:8004` | `http://127.0.0.1:8004/docs` | `data/notifications.db` |

---

## 4. Carga de Datos Semilla de Demostración

En una segunda terminal (con el entorno virtual activo y los servicios corriendo), ejecute:

```bash
python scripts/seed_data.py
```

Esto creará:
- **Administrador**: `admin@nexosalas.com` / `Admin123!`
- **Colaboradores**: `ana.lopez@nexosalas.com` / `Ana12345` y `carlos.mendez@nexosalas.com` / `Carlos123`
- **5 salas corporativas** (4 disponibles y 1 en mantenimiento)
- **1 reservación inicial** orquestada de extremo a extremo con folio `CONF-...`

---

## 5. Demostración en Vivo (Guión para Exposición)

1. Abrir el cliente web en `http://127.0.0.1:8000`.
2. Iniciar sesión con el botón **Demo Admin** o **Demo Empleado**.
3. Ir a la pestaña **Catálogo SOA en Vivo** (`GET /registry/services`) para demostrar que los 4 servicios responden de forma independiente en puertos distintos con su propia BD y Swagger UI.
4. En **Reservaciones (Flujo E2E)**, crear una reserva y mostrar el panel **Trazabilidad SOA**, que evidencia las 4 llamadas encadenadas (`users-service` -> `spaces-service` -> `reservations-service` -> `notifications-service`) y el folio generado.
5. Intentar reservar la misma sala en el mismo horario para demostrar el rechazo controlado (`409 Conflict`).
6. Intentar reservar la sala en mantenimiento o exceder su capacidad para demostrar la validación remota desde `spaces-service` (`422`).
7. Cancelar la reserva y verificar en la pestaña **Confirmaciones** el evento `RESERVATION_CANCELLED`.

---

## 6. Ejecución de Pruebas Automatizadas y Regeneración de Artefactos

- Ejecutar toda la suite de pruebas CRUD e integración E2E:
  ```bash
  pytest -v
  ```
- Exportar contratos OpenAPI 3.0 en YAML (`contracts/*.openapi.yaml`):
  ```bash
  python scripts/export_contracts.py
  ```
- Regenerar diagramas PNG (`docs/diagrams/*.png`):
  ```bash
  python scripts/generate_diagrams.py
  ```
- Regenerar el documento técnico en Word (`docs/Documento_Tecnico_SOA_ReservaEspacios.docx`):
  ```bash
  python scripts/generate_docx.py
  ```
