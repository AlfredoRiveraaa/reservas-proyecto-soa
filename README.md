# ReservaSOA — Plataforma de Reservación de Espacios con Arquitectura SOA

Proyecto final de la materia **Cómputo Orientado a Servicios**.  
Repositorio oficial: `https://github.com/AlfredoRiveraaa/reservas-proyecto-soa`

---

## Descripción General

**ReservaSOA** resuelve la fragmentación de procesos en la administración de espacios y recursos corporativos (*NexoSalas*) mediante una **Arquitectura Orientada a Servicios (SOA)** implementada en **Python + FastAPI**.  
El sistema divide sus responsabilidades en **4 servicios independientes** (cada uno con su propio proceso, puerto, contrato OpenAPI 3.0 y base de datos SQLite autónoma), integrados a través de un **API Gateway con Catálogo Dinámico de Servicios** y una **Aplicación Cliente Web**.

---

## Arquitectura de Servicios

| Servicio | Puerto | Base de Datos | Responsabilidad |
|---|---|---|---|
| **API Gateway & Catálogo** | `8000` | Stateless | Enrutamiento `/api/*`, catálogo en vivo `/registry/services` y cliente web (`/`) |
| **users-service** | `8001` | `data/users.db` | CRUD de usuarios, roles (`admin`/`employee`), contraseñas PBKDF2 y autenticación JWT |
| **spaces-service** | `8002` | `data/spaces.db` | CRUD de salas/recursos, filtros y validación operativa (`/spaces/{id}/validate`) |
| **reservations-service** | `8003` | `data/reservations.db` | CRUD de reservaciones, detección de traslapes y **orquestación HTTP E2E** |
| **notifications-service** | `8004` | `data/notifications.db` | Emisión de folios `CONF-AAAA-XXXXXX` e historial CRUD de confirmaciones |

### Flujo Integrado End-to-End (Comunicación Inter-Servicios)
Cuando un usuario crea una reservación (`POST /api/reservations`), `reservations-service` orquesta vía HTTP (`httpx` + `X-Service-Key`):
1. `GET /users/{id}` en **`users-service`** → valida existencia y estado activo.
2. `GET /spaces/{id}/validate?attendees=N` en **`spaces-service`** → valida estado `available` y capacidad suficiente.
3. Validación local de traslapes de horario y persistencia en `reservations.db`.
4. `POST /notifications` en **`notifications-service`** → emite el folio de confirmación `CONF-...` y registra el comprobante.

---

## Estructura del Repositorio

```text
reservas-proyecto-soa/
├── .env.example                                  # Variables de entorno de ejemplo (sin secretos)
├── requirements.txt                              # Dependencias Python
├── shared/                                       # Configuración, seguridad JWT, errores y cliente HTTP
├── services/
│   ├── users_service/                            # Servicio 1: Usuarios y Auth (:8001)
│   ├── spaces_service/                           # Servicio 2: Salas y Recursos (:8002)
│   ├── reservations_service/                     # Servicio 3: Reservaciones y Orquestación (:8003)
│   ├── notifications_service/                    # Servicio 4: Confirmaciones y Folios (:8004)
│   └── api_gateway/                              # API Gateway + Catálogo SOA (:8000)
├── frontend/                                     # Aplicación Cliente Web (HTML/CSS/JS)
├── contracts/                                    # Contratos OpenAPI 3.0 exportados (.yaml)
├── tests/                                        # Suite pytest (CRUD + E2E) + Colección Postman
├── scripts/                                      # Arranque, datos semilla, contratos, diagramas y Word
└── docs/
    ├── diagrams/                                 # Diagramas Mermaid (.mmd) e imágenes PNG
    ├── evidencias/                               # Resultados reales de ejecución de pruebas
    ├── GUIA_EJECUCION.md                         # Guía detallada paso a paso
    └── Documento_Tecnico_SOA_ReservaEspacios.docx # Documento técnico entregable en Word
```

---

## Inicio Rápido

```powershell
# 1. Crear entorno virtual e instalar dependencias
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Copiar variables de entorno de ejemplo
Copy-Item .env.example .env

# 3. Levantar los 4 servicios SOA + API Gateway
python scripts/start_all.py

# 4. (En otra terminal) Cargar datos de demostración
python scripts/seed_data.py
```

Luego abre **`http://127.0.0.1:8000`** en tu navegador.

Para ejecutar las pruebas automatizadas:
```powershell
pytest -v
```

Consulta la guía completa en [docs/GUIA_EJECUCION.md](docs/GUIA_EJECUCION.md).
