"""Genera el documento técnico completo en Word (.docx) para el proyecto final SOA."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor

ROOT_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT_DIR / "docs"
DIAGRAMS_DIR = DOCS_DIR / "diagrams"
EVIDENCE_FILE = DOCS_DIR / "evidencias" / "resultados_pruebas.md"
OUTPUT_DOCX = DOCS_DIR / "Documento_Tecnico_SOA_ReservaEspacios.docx"


def _set_cell_bg(cell, hex_color: str) -> None:
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shading)


def _set_table_borders(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        '<w:top w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/>'
        '<w:left w:val="none"/><w:right w:val="none"/><w:insideV w:val="none"/>'
        "</w:tblBorders>"
    )
    tbl_pr.append(borders)


def _add_styled_table(doc: Document, headers: list[str], rows: list[list[str]]) -> None:
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(table)

    hdr_cells = table.rows[0].cells
    for idx, text in enumerate(headers):
        hdr_cells[idx].text = text
        _set_cell_bg(hdr_cells[idx], "1E3A8A")
        p = hdr_cells[idx].paragraphs[0]
        run = p.runs[0]
        run.bold = True
        run.font.color.rgb = RGBColor(255, 255, 255)
        run.font.size = Pt(9.5)

    for r_idx, row_data in enumerate(rows):
        row_cells = table.rows[r_idx + 1].cells
        bg = "F8FAFC" if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, value in enumerate(row_data):
            row_cells[c_idx].text = value
            _set_cell_bg(row_cells[c_idx], bg)
            p = row_cells[c_idx].paragraphs[0]
            if p.runs:
                p.runs[0].font.size = Pt(9)

    doc.add_paragraph()


def _add_code_block(doc: Document, code_text: str) -> None:
    table = doc.add_table(rows=1, cols=1)
    cell = table.rows[0].cells[0]
    _set_cell_bg(cell, "F1F5F9")
    p = cell.paragraphs[0]
    run = p.add_run(code_text.strip())
    run.font.name = "Consolas"
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor(15, 23, 42)
    doc.add_paragraph()


def _add_heading_styled(doc: Document, text: str, level: int = 1) -> None:
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor(30, 58, 138) if level == 1 else RGBColor(15, 23, 42)


def _add_page_number_footer(section) -> None:
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run1 = p.add_run("ReservaSOA — Proyecto Final de Cómputo Orientado a Servicios   |   Página ")
    run1.font.size = Pt(8.5)
    run1.font.color.rgb = RGBColor(100, 116, 139)
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    p._p.append(fld)


def build_document() -> None:
    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(0.85)
        section.bottom_margin = Inches(0.85)
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)
        _add_page_number_footer(section)

    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Calibri"
    normal_style.font.size = Pt(10.5)
    normal_style.font.color.rgb = RGBColor(30, 41, 59)

    # ================= PORTADA (PLANTILLA EDITABLE) =================
    p_top = doc.add_paragraph()
    p_top.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_inst = p_top.add_run("[NOMBRE DE LA INSTITUCIÓN / UNIVERSIDAD]\n")
    r_inst.bold = True
    r_inst.font.size = Pt(15)
    r_inst.font.color.rgb = RGBColor(30, 58, 138)
    r_fac = p_top.add_run("[FACULTAD O DIVISIÓN ACADÉMICA]\n[CARRERA / PROGRAMA EDUCATIVO]")
    r_fac.font.size = Pt(11.5)
    r_fac.font.color.rgb = RGBColor(71, 85, 105)

    for _ in range(3):
        doc.add_paragraph()

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_title.add_run("PROYECTO INTEGRADOR FINAL\nCÓMPUTO ORIENTADO A SERVICIOS\n\n")
    r_sub.bold = True
    r_sub.font.size = Pt(12)
    r_sub.font.color.rgb = RGBColor(79, 70, 229)

    r_main = p_title.add_run("ReservaSOA\n")
    r_main.bold = True
    r_main.font.size = Pt(28)
    r_main.font.color.rgb = RGBColor(15, 23, 42)

    r_desc = p_title.add_run(
        "Plataforma de Reservación de Espacios y Recursos Corporativos\n"
        "basada en Arquitectura Orientada a Servicios (SOA)"
    )
    r_desc.font.size = Pt(13)
    r_desc.font.color.rgb = RGBColor(51, 65, 85)

    for _ in range(3):
        doc.add_paragraph()

    _add_styled_table(
        doc,
        ["Campo de Portada", "Información (Plantilla Editable)"],
        [
            ["Materia", "Cómputo Orientado a Servicios"],
            ["Docente", "[Nombre completo del docente]"],
            ["Integrante(s)", "[Nombre(s) y matrícula(s) del equipo]"],
            ["Grupo / Semestre", "[Grupo / Periodo escolar]"],
            ["Repositorio GitHub", "https://github.com/AlfredoRiveraaa/reservas-proyecto-soa"],
            ["Fecha de entrega", "[DD / MM / AAAA]"],
        ],
    )

    doc.add_page_break()

    # ================= 1. PROBLEMA Y CONTEXTO =================
    _add_heading_styled(doc, "1. Problema y Contexto Organizacional", level=1)
    doc.add_paragraph(
        "EspacioHub es un centro corporativo y de innovación que administra salas de juntas, "
        "auditorios, laboratorios de prototipos y equipamiento audiovisual compartido entre "
        "múltiples departamentos (Ingeniería, Operaciones, Diseño y Dirección). Actualmente, "
        "la operación se apoya en herramientas aisladas: Recursos Humanos mantiene el directorio "
        "de colaboradores en un archivo interno, Infraestructura controla el inventario y estado "
        "de mantenimiento de salas en hojas de cálculo, y Administración registra reservaciones "
        "manualmente por correo electrónico."
    )
    doc.add_paragraph(
        "Esta fragmentación provoca problemas recurrentes: empalmes de horario (doble reserva), "
        "asignación de salas en mantenimiento o con capacidad insuficiente para los asistentes, "
        "ausencia de comprobantes estandarizados y falta de trazabilidad cuando una reunión es "
        "reprogramada o cancelada."
    )

    # ================= 2. OBJETIVOS Y ALCANCE =================
    _add_heading_styled(doc, "2. Objetivos y Alcance", level=1)
    _add_heading_styled(doc, "2.1 Objetivo General", level=2)
    doc.add_paragraph(
        "Diseñar e implementar una plataforma de integración basada en Arquitectura Orientada a "
        "Servicios (SOA), denominada ReservaSOA, que coordine servicios independientes para la "
        "gestión de usuarios, espacios, reservaciones y confirmaciones, garantizando "
        "interoperabilidad, bajo acoplamiento, seguridad básica y ejecución reproducible."
    )
    _add_heading_styled(doc, "2.2 Objetivos Específicos", level=2)
    for item in [
        "Separar las responsabilidades del dominio en cuatro servicios autónomos con persistencia SQLite independiente.",
        "Documentar contratos formales de servicio mediante OpenAPI 3.0 (YAML y Swagger UI) con formato JSON.",
        "Implementar un proceso de negocio completo de extremo a extremo (E2E) que demuestre comunicación HTTP real entre servicios.",
        "Incorporar autenticación JWT, control de roles, llave interna servicio-a-servicio y manejo estandarizado de errores.",
        "Validar el sistema mediante pruebas automatizadas (pytest), colección Postman y una aplicación cliente web.",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    _add_heading_styled(doc, "2.3 Alcance", level=2)
    doc.add_paragraph(
        "El prototipo funcional cubre el ciclo completo de autenticación de usuarios, catálogo y "
        "validación operativa de espacios, creación/modificación/cancelación orquestada de "
        "reservaciones, emisión de folios de confirmación, descubrimiento de servicios vía API "
        "Gateway y visualización en interfaz web. Quedan fuera de alcance integraciones SMTP "
        "productivas externas y facturación."
    )

    # ================= 3. ACTORES =================
    _add_heading_styled(doc, "3. Actores del Sistema", level=1)
    _add_styled_table(
        doc,
        ["Actor", "Rol Técnico", "Responsabilidades Principales"],
        [
            [
                "Colaborador (Empleado)",
                "role = employee",
                "Registrarse, iniciar sesión, consultar salas disponibles, crear/modificar/cancelar sus reservaciones y consultar sus folios de confirmación.",
            ],
            [
                "Administrador de Espacios",
                "role = admin",
                "Gestionar el ciclo de vida CRUD de usuarios y salas (alta, edición, mantenimiento, baja), consultar la agenda global y supervisar el catálogo SOA.",
            ],
            [
                "Servicio Orquestador",
                "reservations-service",
                "Actúa como consumidor interno de users-service, spaces-service y notifications-service usando la credencial interna X-Service-Key.",
            ],
        ],
    )

    # ================= 4. REQUISITOS =================
    _add_heading_styled(doc, "4. Requisitos Funcionales y No Funcionales", level=1)
    _add_styled_table(
        doc,
        ["ID", "Tipo", "Descripción del Requisito"],
        [
            ["RF-01", "Funcional", "Permitir registro, inicio de sesión con JWT y operaciones CRUD de usuarios."],
            ["RF-02", "Funcional", "Administrar el catálogo CRUD de espacios, equipamiento, capacidad y estado operativo."],
            ["RF-03", "Funcional", "Orquestar reservaciones validando usuario activo, estado/capacidad de sala y ausencia de traslapes."],
            ["RF-04", "Funcional", "Emitir automáticamente un folio único de confirmación (CONF-AAAA-XXXXXX) al confirmar o cancelar."],
            ["RF-05", "Funcional", "Exponer un catálogo dinámico de servicios (/registry/services) con verificación de salud en vivo."],
            ["RNF-01", "No Funcional", "Autonomía de datos: cada servicio gestiona su propia base de datos SQLite."],
            ["RNF-02", "No Funcional", "Interoperabilidad: comunicación REST/HTTP con intercambio JSON y contratos OpenAPI 3.0."],
            ["RNF-03", "No Funcional", "Seguridad: contraseñas con PBKDF2-HMAC-SHA256, tokens JWT HS256 y secretos fuera del repositorio."],
            ["RNF-04", "No Funcional", "Resiliencia y errores claros: respuestas JSON uniformes (400/401/403/404/409/422/503/504)."],
        ],
    )

    # ================= 5. JUSTIFICACIÓN DE SOA =================
    _add_heading_styled(doc, "5. Justificación de la Arquitectura Orientada a Servicios (SOA)", level=1)
    doc.add_paragraph(
        "Se eligió una arquitectura SOA sobre un enfoque monolítico tradicional porque los procesos "
        "involucrados pertenecen a dominios organizacionales independientes (Identidad, "
        "Infraestructura, Agenda y Comunicaciones). Mediante SOA, cada dominio se encapsula en un "
        "servicio con contrato explícito, permitiendo reutilizar el servicio de usuarios o el de "
        "notificaciones en futuros sistemas de la organización (por ejemplo, incidencias de TI o "
        "préstamo de equipo) sin duplicar lógica ni acoplar bases de datos."
    )
    doc.add_paragraph(
        "Se optó por REST/HTTP con formato JSON y contratos OpenAPI 3.0 frente a SOAP/XML por su "
        "menor sobrecarga de serialización, adopción nativa en clientes web modernos, facilidad de "
        "prueba con Swagger UI/Postman y soporte directo de validación de esquemas en Python/FastAPI."
    )

    # ================= 6. ARQUITECTURA SOA Y DIAGRAMAS =================
    _add_heading_styled(doc, "6. Arquitectura SOA y Diagramas del Sistema", level=1)
    doc.add_paragraph(
        "ReservaSOA aplica los ocho principios clásicos de SOA: contrato estandarizado (OpenAPI), "
        "bajo acoplamiento (comunicación solo por HTTP), abstracción (ocultamiento de SQLite), "
        "reutilización (servicios de usuarios y notificaciones agnósticos), autonomía (procesos y "
        "bases de datos independientes), ausencia de estado (JWT), descubribilidad (Catálogo en el "
        "API Gateway) y composabilidad (orquestación E2E en reservations-service)."
    )

    img1 = DIAGRAMS_DIR / "01_arquitectura_soa.png"
    if img1.exists():
        doc.add_picture(str(img1), width=Inches(6.4))
        p_cap1 = doc.add_paragraph("Figura 1. Diagrama de Arquitectura SOA de ReservaSOA.")
        p_cap1.alignment = WD_ALIGN_PARAGRAPH.CENTER

    img2 = DIAGRAMS_DIR / "02_componentes_despliegue.png"
    if img2.exists():
        doc.add_picture(str(img2), width=Inches(6.4))
        p_cap2 = doc.add_paragraph("Figura 2. Diagrama de Componentes y Despliegue por procesos independientes.")
        p_cap2.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # ================= 7. DESCRIPCIÓN DE SERVICIOS =================
    _add_heading_styled(doc, "7. Descripción de Servicios Independientes", level=1)
    _add_styled_table(
        doc,
        ["Servicio", "Puerto", "Base de Datos", "Responsabilidad Delimitada"],
        [
            ["api-gateway", "8000", "Sin BD (Stateless)", "Punto de entrada único, proxy inverso (/api/*), catálogo SOA (/registry/services) y servidor del cliente web."],
            ["users-service", "8001", "data/users.db", "Registro, autenticación JWT, gestión CRUD de usuarios y control de estado activo/roles."],
            ["spaces-service", "8002", "data/spaces.db", "Catálogo CRUD de salas y equipamiento, filtros por capacidad/recurso y validación operativa (/validate)."],
            ["reservations-service", "8003", "data/reservations.db", "Gestión CRUD de agenda, control de traslapes y orquestación HTTP E2E entre los demás servicios."],
            ["notifications-service", "8004", "data/notifications.db", "Generación de folios CONF-AAAA-XXXXXX y trazabilidad CRUD de confirmaciones y cancelaciones."],
        ],
    )

    # ================= 8. CONTRATOS DE SERVICIO =================
    _add_heading_styled(doc, "8. Contratos de Servicio (OpenAPI 3.0)", level=1)
    doc.add_paragraph(
        "Cada servicio publica su contrato interactivo en /docs (Swagger UI) y cuenta con su "
        "especificación exportada en formato YAML dentro de la carpeta contracts/ del repositorio. "
        "A continuación se resumen las operaciones principales:"
    )
    _add_styled_table(
        doc,
        ["Servicio", "Operación", "Entrada / Parámetros", "Respuestas / Errores"],
        [
            ["users-service", "POST /auth/login", "JSON: email, password", "200 (JWT + user) | 401 | 403 | 422"],
            ["users-service", "GET /users/{id}", "Path id + JWT o X-Service-Key", "200 (UserResponse) | 401 | 404"],
            ["spaces-service", "POST /spaces", "JSON sala + JWT admin", "201 (SpaceResponse) | 403 | 409 | 422"],
            ["spaces-service", "GET /spaces/{id}/validate", "Query attendees + X-Service-Key", "200 ({valid, reason, space}) | 404"],
            ["reservations-service", "POST /reservations", "JSON reserva + JWT", "201 (reserva + folio + soa_trace) | 404 | 409 | 422 | 503"],
            ["reservations-service", "POST /reservations/{id}/cancel", "Path id + JWT propietario/admin", "200 (status=CANCELLED) | 403 | 404 | 409"],
            ["notifications-service", "POST /notifications", "JSON evento + X-Service-Key", "201 (confirmation_code) | 401 | 422"],
            ["api-gateway", "GET /registry/services", "Sin parámetros", "200 (catálogo SOA con estado UP/DOWN y latencia)"],
        ],
    )

    doc.add_paragraph("Formato estándar de respuesta de error en todos los servicios:")
    _add_code_block(
        doc,
        """{
  "error_code": "RESOURCE_CONFLICT",
  "message": "La sala 'Sala Innovación Norte' ya cuenta con una reservación confirmada...",
  "details": null,
  "service": "reservations-service",
  "timestamp": "2026-11-26T06:45:00.000000+00:00"
}""",
    )

    # ================= 9. MODELO DE DATOS =================
    _add_heading_styled(doc, "9. Modelo de Datos (Persistencia Autónoma)", level=1)
    doc.add_paragraph(
        "Siguiendo la mejor práctica SOA de autonomía de datos, cada servicio administra su propio "
        "archivo SQLite en el directorio data/ (excluido de Git para evitar versionar datos locales). "
        "No existen llaves foráneas físicas entre bases de datos; la integridad referencial se "
        "garantiza mediante validaciones de contrato vía HTTP en tiempo de ejecución."
    )
    _add_styled_table(
        doc,
        ["Base de Datos", "Tabla", "Columnas Principales"],
        [
            ["data/users.db", "users", "id (PK), full_name, email (UNIQUE), department, role, password_hash, is_active, created_at, updated_at"],
            ["data/spaces.db", "spaces", "id (PK), code (UNIQUE), name, building, floor, capacity, resources_json, status, description, created_at, updated_at"],
            ["data/reservations.db", "reservations", "id (PK), user_id, user_name, user_email, space_id, space_code, space_name, title, reservation_date, start_time, end_time, attendees, status, confirmation_code"],
            ["data/notifications.db", "notifications", "id (PK), confirmation_code (UNIQUE), reservation_id, user_id, recipient_email, recipient_name, event_type, subject, message, channel, status"],
        ],
    )

    # ================= 10. FLUJO DE NEGOCIO E2E =================
    _add_heading_styled(doc, "10. Flujo de Negocio Completo (End-to-End)", level=1)
    doc.add_paragraph(
        "El flujo principal del sistema es la creación orquestada de una reservación, la cual "
        "involucra activamente a los cuatro servicios independientes y al API Gateway:"
    )
    for step in [
        "1. El usuario autenticado envía la solicitud POST /api/reservations al API Gateway con su token Bearer JWT.",
        "2. El API Gateway enruta la petición a reservations-service (:8003).",
        "3. ReservationOrchestrator consulta a users-service (:8001) usando X-Service-Key para verificar que el usuario exista y esté activo.",
        "4. ReservationOrchestrator consulta a spaces-service (:8002) en /spaces/{id}/validate?attendees=N para verificar estado 'available' y capacidad suficiente.",
        "5. reservations-service verifica en reservations.db que no exista empalme de horario y persiste la reserva con estado CONFIRMED.",
        "6. Finalmente, invoca POST /notifications en notifications-service (:8004) para generar el folio único CONF-AAAA-XXXXXX y devuelve la respuesta junto con la traza SOA (soa_trace).",
    ]:
        doc.add_paragraph(step)

    img3 = DIAGRAMS_DIR / "03_secuencia_reserva_e2e.png"
    if img3.exists():
        doc.add_picture(str(img3), width=Inches(6.4))
        p_cap3 = doc.add_paragraph("Figura 3. Diagrama de secuencia del proceso integrado E2E de reservación.")
        p_cap3.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # ================= 11. SEGURIDAD Y MANEJO DE ERRORES =================
    _add_heading_styled(doc, "11. Seguridad Básica y Manejo de Errores", level=1)
    for item in [
        "Protección de credenciales: Las contraseñas nunca se almacenan en texto plano; se derivan con PBKDF2-HMAC-SHA256 (120,000 iteraciones y sal aleatoria de 16 bytes).",
        "Autenticación sin estado: Los tokens JWT firmados con HMAC-SHA256 (HS256) validan identidad, rol (admin/employee) y expiración.",
        "Seguridad inter-servicio: Las llamadas internas entre servicios utilizan la cabecera X-Service-Key configurada por variable de entorno.",
        "Gestión de secretos: Todas las llaves y puertos se configuran mediante .env (ignorado en .gitignore), entregando únicamente .env.example en el repositorio.",
        "Resiliencia ante fallas: Si spaces-service o users-service no responden, el orquestador retorna 503 UPSTREAM_UNAVAILABLE. Si notifications-service falla temporalmente, la reserva se completa en modo degradado controlado (confirmation_code = PENDING-RETRY) sin perder la transacción principal.",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    # ================= 12. PRUEBAS Y EVIDENCIAS =================
    _add_heading_styled(doc, "12. Pruebas y Evidencias de Funcionamiento", level=1)
    doc.add_paragraph(
        "Se implementó una suite automatizada con pytest (tests/) que valida las operaciones CRUD "
        "individuales de cada servicio, controles de seguridad, validaciones de negocio, flujo E2E "
        "completo y simulación de fallos de comunicación. Adicionalmente se incluye una colección "
        "Postman lista para importar en tests/postman/ReservaSOA.postman_collection.json."
    )
    _add_styled_table(
        doc,
        ["Caso de Prueba", "Servicio(s)", "Resultado Esperado", "Estado"],
        [
            ["CRUD completo de usuarios + Login JWT + bloqueo de usuario inactivo", "users-service", "201, 200, 403, 204, 404", "APROBADO"],
            ["Acceso sin token (401), sin rol admin (403), correo duplicado (409), datos inválidos (422)", "users-service", "Errores JSON estandarizados", "APROBADO"],
            ["CRUD de salas, filtros por recurso/capacidad y endpoint /validate", "spaces-service", "201, 200, 409, 204, 404", "APROBADO"],
            ["Emisión de folio CONF, consulta por reserva y cambio de estado READ", "notifications-service", "201, 200, 204", "APROBADO"],
            ["Flujo E2E: reservar (4 servicios) -> detectar traslape (409) -> editar -> cancelar -> re-reservar", "Todos (E2E)", "201, 409, 200, 201", "APROBADO"],
            ["Exceso de capacidad (422), sala en mantenimiento (422), horario invertido (422)", "reservations + spaces", "422 BusinessValidationError", "APROBADO"],
            ["Caída de spaces-service (503) y degradación controlada de notifications-service", "reservations + upstream", "503 y 201 DEGRADED", "APROBADO"],
        ],
    )

    if EVIDENCE_FILE.exists():
        doc.add_paragraph("Salida real capturada de la ejecución automatizada de pruebas (pytest -v):")
        raw_bytes = EVIDENCE_FILE.read_bytes()
        try:
            evidence_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            evidence_text = raw_bytes.decode("utf-16")
        _add_code_block(doc, evidence_text[:3500])

    # ================= 13. CONCLUSIONES =================
    _add_heading_styled(doc, "13. Conclusiones", level=1)
    doc.add_paragraph(
        "La implementación de ReservaSOA demuestra de forma práctica y verificable los beneficios "
        "de la Arquitectura Orientada a Servicios en un problema empresarial real. Al desacoplar "
        "usuarios, espacios, reservaciones y confirmaciones en servicios independientes con "
        "contratos OpenAPI explícitos y bases de datos autónomas, se logró eliminar el acoplamiento "
        "monolítico, facilitar pruebas aisladas e integradas, mejorar la tolerancia a fallos y "
        "construir una plataforma extensible para futuras necesidades corporativas."
    )

    # ================= 14. REFERENCIAS =================
    _add_heading_styled(doc, "14. Referencias", level=1)
    for ref in [
        "Erl, T. (2016). Service-Oriented Architecture: Analysis and Design for Services and Microservices (2nd ed.). Prentice Hall.",
        "OpenAPI Initiative. (2024). OpenAPI Specification v3.1.0. https://spec.openapis.org/",
        "Ramírez, S. (2024). FastAPI Framework Documentation. https://fastapi.tiangolo.com/",
        "Fielding, R. T. (2000). Architectural Styles and the Design of Network-based Software Architectures. University of California, Irvine.",
        "Jones, M., Bradley, J., & Sakimura, N. (2015). JSON Web Token (JWT) — RFC 7519. IETF.",
    ]:
        doc.add_paragraph(ref, style="List Bullet")

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUTPUT_DOCX))
    print(f"Documento técnico Word generado exitosamente: {OUTPUT_DOCX.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    build_document()
