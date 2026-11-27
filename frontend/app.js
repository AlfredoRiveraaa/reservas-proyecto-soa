const state = {
  token: localStorage.getItem("reservasoa_token") || null,
  user: JSON.parse(localStorage.getItem("reservasoa_user") || "null"),
  activeView: "view-reservations",
  spaces: [],
  reservations: [],
  users: [],
  notifications: [],
  resFilter: "ALL",
  notifFilter: "ALL",
  selectedSpaceId: null,
  loadedViews: new Set(),
};

const VIEW_META = {
  "view-reservations": {
    title: "Agenda y reservas",
    subtitle: "Selecciona una sala, valida capacidad y genera una confirmación orquestada.",
  },
  "view-spaces": {
    title: "Salas y recursos",
    subtitle: "Administra disponibilidad operativa, capacidad y equipamiento de cada espacio.",
  },
  "view-users": {
    title: "Usuarios y perfil",
    subtitle: "Consulta tu perfil y administra el directorio de colaboradores.",
  },
  "view-notifications": {
    title: "Comprobantes",
    subtitle: "Historial de folios de confirmación, actualización y cancelación.",
  },
  "view-catalog": {
    title: "Servicios SOA",
    subtitle: "Monitoreo en vivo de los cuatro servicios independientes y sus contratos OpenAPI.",
  },
};

const toastContainer = document.getElementById("toast-container");
const authShell = document.getElementById("auth-shell");
const appShell = document.getElementById("app-shell");
const latencyPill = document.getElementById("gateway-latency-pill");
const modalBackdrop = document.getElementById("modal-backdrop");
const modalTitle = document.getElementById("modal-title");
const modalBody = document.getElementById("modal-body");

function showToast(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast ${type === "error" ? "toast-error" : ""}`;
  toast.textContent = message;
  toastContainer.appendChild(toast);
  setTimeout(() => toast.remove(), 4500);
}

function setButtonLoading(button, isLoading, loadingText) {
  if (!button) return;
  if (isLoading) {
    button.dataset.originalText = button.textContent;
    button.textContent = loadingText;
    button.disabled = true;
  } else {
    button.textContent = button.dataset.originalText || button.textContent;
    button.disabled = false;
  }
}

function openModal(title, htmlContent) {
  modalTitle.textContent = title;
  modalBody.innerHTML = htmlContent;
  modalBackdrop.classList.remove("hidden");
}

function closeModal() {
  modalBackdrop.classList.add("hidden");
  modalBody.innerHTML = "";
}

document.getElementById("btn-modal-close").addEventListener("click", closeModal);
modalBackdrop.addEventListener("click", (e) => {
  if (e.target === modalBackdrop) closeModal();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !modalBackdrop.classList.contains("hidden")) closeModal();
});

async function apiFetch(path, options = {}) {
  const started = performance.now();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) {
    headers["Authorization"] = `Bearer ${state.token}`;
  }
  const response = await fetch(path, { ...options, headers });
  const elapsed = Math.round(performance.now() - started);
  if (latencyPill) latencyPill.textContent = `${elapsed} ms`;

  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { message: text };
  }
  if (!response.ok) {
    if (response.status === 401 && state.token && !path.includes("/auth/login")) {
      logoutUser("Tu sesión expiró. Inicia sesión nuevamente.");
    }
    const msg = (data && (data.message || data.detail)) || `Error HTTP ${response.status}`;
    throw new Error(msg);
  }
  return { data, elapsed };
}

function isAdmin() {
  return state.user && state.user.role === "admin";
}

function getInitials(name = "") {
  return (
    name
      .split(" ")
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0].toUpperCase())
      .join("") || "NS"
  );
}

function statusBadge(status) {
  const map = {
    CONFIRMED: ["Confirmada", "status-ok"],
    CANCELLED: ["Cancelada", "status-err"],
    available: ["Disponible", "status-ok"],
    maintenance: ["Mantenimiento", "status-warn"],
    UP: ["Activo", "status-ok"],
    DOWN: ["Sin respuesta", "status-err"],
    SENT: ["Enviado", "status-warn"],
    READ: ["Leído", "status-ok"],
    FAILED: ["Error", "status-err"],
    active: ["Activo", "status-ok"],
    inactive: ["Inactivo", "status-err"],
  };
  const [label, cls] = map[status] || [status, "status-ok"];
  return `<span class="status-badge ${cls}">${label}</span>`;
}

/* ==================== ESPACIOS ==================== */
function renderRoomPicker() {
  const grid = document.getElementById("room-picker-grid");
  const select = document.getElementById("res-space");
  const countLabel = document.getElementById("spaces-count-label");

  if (!state.spaces.length) {
    grid.innerHTML = '<p class="empty-hint">Aún no hay espacios registrados.</p>';
    select.innerHTML = "";
    countLabel.textContent = "0 espacios";
    return;
  }

  const availableCount = state.spaces.filter((s) => s.status === "available").length;
  countLabel.textContent = `${availableCount} de ${state.spaces.length} disponibles`;

  if (!state.selectedSpaceId || !state.spaces.some((s) => s.id === state.selectedSpaceId)) {
    const firstAvailable = state.spaces.find((s) => s.status === "available") || state.spaces[0];
    state.selectedSpaceId = firstAvailable.id;
  }

  select.innerHTML = state.spaces
    .map(
      (s) =>
        `<option value="${s.id}" ${s.id === state.selectedSpaceId ? "selected" : ""}>${s.code} — ${s.name} (Cap. ${s.capacity})</option>`
    )
    .join("");

  grid.innerHTML = state.spaces
    .map(
      (s) => `
      <button type="button" class="room-tile ${s.id === state.selectedSpaceId ? "selected" : ""} ${s.status === "maintenance" ? "maintenance" : ""}" data-pick-space="${s.id}">
        <div class="room-tile-top">
          <span class="room-code">${s.code}</span>
          ${statusBadge(s.status)}
        </div>
        <strong>${s.name}</strong>
        <span class="room-tile-meta">${s.building}, piso ${s.floor} · Cap. ${s.capacity}</span>
      </button>`
    )
    .join("");

  grid.querySelectorAll("[data-pick-space]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.selectedSpaceId = Number(btn.dataset.pickSpace);
      select.value = String(state.selectedSpaceId);
      document.getElementById("space-validation-box").classList.add("hidden");
      renderRoomPicker();
    });
  });
}

function renderSpacesCatalog(filterText = "") {
  const grid = document.getElementById("spaces-grid");
  const needle = filterText.trim().toLowerCase();
  const filtered = state.spaces.filter((s) => {
    if (!needle) return true;
    return (
      s.name.toLowerCase().includes(needle) ||
      s.code.toLowerCase().includes(needle) ||
      s.building.toLowerCase().includes(needle) ||
      s.resources.some((r) => r.toLowerCase().includes(needle))
    );
  });

  if (!filtered.length) {
    grid.innerHTML = '<p class="empty-hint">No se encontraron espacios con ese criterio.</p>';
    return;
  }

  const admin = isAdmin();
  grid.innerHTML = filtered
    .map(
      (s) => `
      <article class="info-card">
        <div class="info-card-top">
          <div>
            <span class="room-code">${s.code}</span>
            <h3>${s.name}</h3>
          </div>
          ${statusBadge(s.status)}
        </div>
        <p class="muted-text">${s.building}, piso ${s.floor} · Capacidad para ${s.capacity} personas</p>
        ${s.description ? `<p class="muted-text">${s.description}</p>` : ""}
        <div class="chip-list">
          ${s.resources.map((r) => `<span class="chip">${r}</span>`).join("")}
        </div>
        ${
          admin
            ? `<div class="card-actions">
                <button type="button" class="btn btn-outline btn-sm" data-edit-space="${s.id}">Editar</button>
                <button type="button" class="btn btn-ghost btn-sm" data-toggle-space="${s.id}" data-next-status="${s.status === "available" ? "maintenance" : "available"}">
                  ${s.status === "available" ? "Mantenimiento" : "Habilitar"}
                </button>
                <button type="button" class="btn btn-danger-subtle" data-delete-space="${s.id}">Eliminar</button>
              </div>`
            : ""
        }
      </article>`
    )
    .join("");

  if (admin) {
    grid.querySelectorAll("[data-edit-space]").forEach((btn) => {
      btn.addEventListener("click", () => openEditSpaceModal(Number(btn.dataset.editSpace)));
    });
    grid.querySelectorAll("[data-toggle-space]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = Number(btn.dataset.toggleSpace);
        const nextStatus = btn.dataset.nextStatus;
        setButtonLoading(btn, true, "Actualizando...");
        try {
          await apiFetch(`/api/spaces/${id}`, {
            method: "PUT",
            body: JSON.stringify({ status: nextStatus }),
          });
          showToast(`Estado actualizado a ${nextStatus === "available" ? "disponible" : "mantenimiento"}.`);
          await loadSpaces();
        } catch (err) {
          showToast(err.message, "error");
          setButtonLoading(btn, false);
        }
      });
    });
    grid.querySelectorAll("[data-delete-space]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = Number(btn.dataset.deleteSpace);
        if (!confirm("¿Eliminar este espacio del catálogo?")) return;
        setButtonLoading(btn, true, "Eliminando...");
        try {
          await apiFetch(`/api/spaces/${id}`, { method: "DELETE" });
          showToast("Espacio eliminado.");
          await loadSpaces();
        } catch (err) {
          showToast(err.message, "error");
          setButtonLoading(btn, false);
        }
      });
    });
  }
}

async function openEditSpaceModal(spaceId) {
  try {
    const { data: space } = await apiFetch(`/api/spaces/${spaceId}`);
    openModal(
      `Editar espacio ${space.code}`,
      `<form id="edit-space-form" class="stack-form">
        <div class="field">
          <label for="es-name">Nombre</label>
          <input type="text" id="es-name" required value="${space.name}" />
        </div>
        <div class="field-row">
          <div class="field">
            <label for="es-building">Edificio</label>
            <input type="text" id="es-building" required value="${space.building}" />
          </div>
          <div class="field">
            <label for="es-floor">Piso</label>
            <input type="number" id="es-floor" min="0" required value="${space.floor}" />
          </div>
        </div>
        <div class="field-row">
          <div class="field">
            <label for="es-capacity">Capacidad</label>
            <input type="number" id="es-capacity" min="1" required value="${space.capacity}" />
          </div>
          <div class="field">
            <label for="es-status">Estado</label>
            <select id="es-status">
              <option value="available" ${space.status === "available" ? "selected" : ""}>Disponible</option>
              <option value="maintenance" ${space.status === "maintenance" ? "selected" : ""}>Mantenimiento</option>
            </select>
          </div>
        </div>
        <div class="field">
          <label for="es-resources">Equipamiento (separado por comas)</label>
          <input type="text" id="es-resources" value="${space.resources.join(", ")}" />
        </div>
        <div class="field">
          <label for="es-desc">Descripción</label>
          <input type="text" id="es-desc" value="${space.description || ""}" />
        </div>
        <button type="submit" class="btn btn-primary btn-full">Guardar cambios</button>
      </form>`
    );

    document.getElementById("edit-space-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await apiFetch(`/api/spaces/${spaceId}`, {
          method: "PUT",
          body: JSON.stringify({
            name: document.getElementById("es-name").value.trim(),
            building: document.getElementById("es-building").value.trim(),
            floor: Number(document.getElementById("es-floor").value),
            capacity: Number(document.getElementById("es-capacity").value),
            status: document.getElementById("es-status").value,
            resources: document
              .getElementById("es-resources")
              .value.split(",")
              .map((r) => r.trim())
              .filter(Boolean),
            description: document.getElementById("es-desc").value.trim(),
          }),
        });
        closeModal();
        showToast("Espacio actualizado.");
        await loadSpaces();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ==================== RESERVACIONES ==================== */
function renderReservations() {
  const container = document.getElementById("reservations-list");
  const filtered = state.reservations.filter((r) =>
    state.resFilter === "ALL" ? true : r.status === state.resFilter
  );

  if (!filtered.length) {
    container.innerHTML =
      '<p class="empty-hint">No hay reservaciones en esta vista. Usa el formulario lateral para crear una.</p>';
    return;
  }

  const admin = isAdmin();
  const currentUserId = state.user ? state.user.id : null;

  container.innerHTML = filtered
    .map((r) => {
      const canManage = admin || r.user_id === currentUserId;
      return `
      <article class="res-row">
        <div class="res-row-main">
          <div class="res-row-title">
            <strong>${r.title}</strong>
            ${statusBadge(r.status)}
            ${r.confirmation_code ? `<span class="mono-inline">${r.confirmation_code}</span>` : ""}
          </div>
          <div class="res-row-meta">
            ${r.space_name} (${r.space_code}) · ${r.reservation_date}, ${r.start_time} a ${r.end_time} · ${r.attendees} asistentes · ${r.user_name}
          </div>
        </div>
        <div class="res-row-actions">
          ${
            r.status === "CONFIRMED" && canManage
              ? `<button type="button" class="btn btn-outline btn-sm" data-edit-res="${r.id}">Editar</button>
                 <button type="button" class="btn btn-danger-subtle" data-cancel-id="${r.id}">Cancelar</button>`
              : ""
          }
          ${
            admin
              ? `<button type="button" class="btn btn-ghost btn-sm" data-delete-res="${r.id}">Eliminar</button>`
              : ""
          }
        </div>
      </article>`;
    })
    .join("");

  container.querySelectorAll("[data-edit-res]").forEach((btn) => {
    btn.addEventListener("click", () => openEditReservationModal(Number(btn.dataset.editRes)));
  });
  container.querySelectorAll("[data-cancel-id]").forEach((btn) => {
    btn.addEventListener("click", () => handleCancelReservation(Number(btn.dataset.cancelId), btn));
  });
  container.querySelectorAll("[data-delete-res]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = Number(btn.dataset.deleteRes);
      if (!confirm(`¿Eliminar permanentemente la reservación #${id}?`)) return;
      setButtonLoading(btn, true, "...");
      try {
        await apiFetch(`/api/reservations/${id}`, { method: "DELETE" });
        showToast(`Reservación #${id} eliminada.`);
        await loadReservations();
      } catch (err) {
        showToast(err.message, "error");
        setButtonLoading(btn, false);
      }
    });
  });
}

async function openEditReservationModal(resId) {
  try {
    const { data: r } = await apiFetch(`/api/reservations/${resId}`);
    openModal(
      `Editar reservación #${r.id}`,
      `<form id="edit-res-form" class="stack-form">
        <div class="field">
          <label for="er-title">Título</label>
          <input type="text" id="er-title" required minlength="3" value="${r.title}" />
        </div>
        <div class="field-row">
          <div class="field">
            <label for="er-date">Fecha</label>
            <input type="date" id="er-date" required value="${r.reservation_date}" />
          </div>
          <div class="field">
            <label for="er-attendees">Asistentes</label>
            <input type="number" id="er-attendees" min="1" max="500" required value="${r.attendees}" />
          </div>
        </div>
        <div class="field-row">
          <div class="field">
            <label for="er-start">Inicio</label>
            <input type="time" id="er-start" required value="${r.start_time}" />
          </div>
          <div class="field">
            <label for="er-end">Fin</label>
            <input type="time" id="er-end" required value="${r.end_time}" />
          </div>
        </div>
        <div class="field">
          <label for="er-notes">Notas</label>
          <input type="text" id="er-notes" value="${r.notes || ""}" />
        </div>
        <button type="submit" class="btn btn-primary btn-full">Guardar cambios</button>
      </form>`
    );

    document.getElementById("edit-res-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const { data: updated, elapsed } = await apiFetch(`/api/reservations/${resId}`, {
          method: "PUT",
          body: JSON.stringify({
            title: document.getElementById("er-title").value.trim(),
            reservation_date: document.getElementById("er-date").value,
            start_time: document.getElementById("er-start").value,
            end_time: document.getElementById("er-end").value,
            attendees: Number(document.getElementById("er-attendees").value),
            notes: document.getElementById("er-notes").value.trim(),
          }),
        });
        closeModal();
        renderTrace(updated.soa_trace, updated.confirmation_code, elapsed);
        showToast(`Reservación #${resId} actualizada.`);
        state.loadedViews.delete("view-notifications");
        await loadReservations();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderTrace(steps, confirmationCode = "", elapsedMs = null) {
  const box = document.getElementById("soa-trace-box");
  const durationEl = document.getElementById("trace-duration");
  if (elapsedMs !== null) durationEl.textContent = `${elapsedMs} ms`;
  if (!steps || !steps.length) {
    box.innerHTML = '<p class="empty-hint">Sin pasos registrados.</p>';
    return;
  }
  const folioHtml = confirmationCode
    ? `<div class="folio-banner"><span>Folio emitido</span><code>${confirmationCode}</code></div>`
    : "";
  box.innerHTML =
    folioHtml +
    steps
      .map(
        (step) => `
      <div class="pipeline-step ${step.status !== "OK" ? "degraded" : ""}">
        <div class="pipeline-step-head">
          <span>${step.service}</span>
          <span class="mono-meta">${step.status}</span>
        </div>
        <code>${step.operation}</code>
        <p>${step.detail}</p>
      </div>`
      )
      .join("");
}

/* ==================== USUARIOS Y PERFIL ==================== */
function renderMyProfile(profile) {
  const box = document.getElementById("my-profile-box");
  box.innerHTML = `
    <div class="profile-stat"><span>Nombre completo</span><strong>${profile.full_name}</strong></div>
    <div class="profile-stat"><span>Correo corporativo</span><strong>${profile.email}</strong></div>
    <div class="profile-stat"><span>Departamento</span><strong>${profile.department}</strong></div>
    <div class="profile-stat"><span>Rol asignado</span><strong>${profile.role}</strong></div>
    <div class="profile-stat"><span>Estado de cuenta</span><div>${statusBadge(profile.is_active ? "active" : "inactive")}</div></div>
  `;
}

function populateAdminBookingUsers() {
  const field = document.getElementById("admin-res-user-field");
  const select = document.getElementById("res-user-id");
  if (!isAdmin() || !state.users.length) {
    field.classList.add("hidden");
    return;
  }
  field.classList.remove("hidden");
  const activeUsers = state.users.filter((u) => u.is_active);
  select.innerHTML = activeUsers
    .map(
      (u) =>
        `<option value="${u.id}" ${u.id === state.user.id ? "selected" : ""}>${u.full_name} (${u.department})</option>`
    )
    .join("");
}

function renderUsersTable() {
  const tbody = document.getElementById("users-tbody");
  if (!state.users.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-hint">No hay usuarios registrados.</td></tr>';
    return;
  }
  const admin = isAdmin();
  const myId = state.user ? state.user.id : null;

  tbody.innerHTML = state.users
    .map(
      (u) => `
      <tr>
        <td>#${u.id}</td>
        <td><strong>${u.full_name}</strong><br /><span class="muted-text">${u.email}</span></td>
        <td>${u.department}</td>
        <td><span class="role-chip">${u.role}</span></td>
        <td>${statusBadge(u.is_active ? "active" : "inactive")}</td>
        <td>
          <div class="table-actions">
            <button type="button" class="btn btn-ghost btn-sm" data-view-user="${u.id}">Ver</button>
            ${
              admin
                ? `<button type="button" class="btn btn-outline btn-sm" data-edit-user="${u.id}">Editar</button>
                   ${
                     u.id !== myId
                       ? `<button type="button" class="btn btn-danger-subtle" data-delete-user="${u.id}">Eliminar</button>`
                       : ""
                   }`
                : ""
            }
          </div>
        </td>
      </tr>`
    )
    .join("");

  tbody.querySelectorAll("[data-view-user]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        const { data: u } = await apiFetch(`/api/users/${btn.dataset.viewUser}`);
        openModal(
          `Perfil de ${u.full_name}`,
          `<div class="receipt-box">
            <div><strong>ID:</strong> #${u.id}</div>
            <div><strong>Correo:</strong> ${u.email}</div>
            <div><strong>Departamento:</strong> ${u.department}</div>
            <div><strong>Rol:</strong> ${u.role}</div>
            <div><strong>Estado:</strong> ${u.is_active ? "Activo" : "Inactivo"}</div>
            <div class="muted-text">Registrado: ${u.created_at}</div>
          </div>`
        );
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  });

  if (admin) {
    tbody.querySelectorAll("[data-edit-user]").forEach((btn) => {
      btn.addEventListener("click", () => openEditUserModal(Number(btn.dataset.editUser)));
    });
    tbody.querySelectorAll("[data-delete-user]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = Number(btn.dataset.deleteUser);
        if (!confirm(`¿Eliminar permanentemente al usuario #${id}?`)) return;
        setButtonLoading(btn, true, "...");
        try {
          await apiFetch(`/api/users/${id}`, { method: "DELETE" });
          showToast(`Usuario #${id} eliminado.`);
          await loadUsers();
        } catch (err) {
          showToast(err.message, "error");
          setButtonLoading(btn, false);
        }
      });
    });
  }
}

async function openEditUserModal(userId) {
  try {
    const { data: u } = await apiFetch(`/api/users/${userId}`);
    openModal(
      `Editar usuario #${u.id}`,
      `<form id="edit-user-form" class="stack-form">
        <div class="field">
          <label for="eu-name">Nombre completo</label>
          <input type="text" id="eu-name" required minlength="3" value="${u.full_name}" />
        </div>
        <div class="field">
          <label for="eu-dept">Departamento</label>
          <input type="text" id="eu-dept" required value="${u.department}" />
        </div>
        <div class="field-row">
          <div class="field">
            <label for="eu-role">Rol</label>
            <select id="eu-role">
              <option value="employee" ${u.role === "employee" ? "selected" : ""}>Empleado</option>
              <option value="admin" ${u.role === "admin" ? "selected" : ""}>Administrador</option>
            </select>
          </div>
          <div class="field">
            <label for="eu-active">Estado</label>
            <select id="eu-active">
              <option value="true" ${u.is_active ? "selected" : ""}>Activo</option>
              <option value="false" ${!u.is_active ? "selected" : ""}>Inactivo</option>
            </select>
          </div>
        </div>
        <button type="submit" class="btn btn-primary btn-full">Guardar cambios</button>
      </form>`
    );

    document.getElementById("edit-user-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await apiFetch(`/api/users/${userId}`, {
          method: "PUT",
          body: JSON.stringify({
            full_name: document.getElementById("eu-name").value.trim(),
            department: document.getElementById("eu-dept").value.trim(),
            role: document.getElementById("eu-role").value,
            is_active: document.getElementById("eu-active").value === "true",
          }),
        });
        closeModal();
        showToast("Usuario actualizado.");
        await loadUsers();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ==================== COMPROBANTES / NOTIFICACIONES ==================== */
function renderNotificationsTable() {
  const tbody = document.getElementById("notifications-tbody");
  const filtered = state.notifications.filter((n) =>
    state.notifFilter === "ALL" ? true : n.event_type === state.notifFilter
  );

  if (!filtered.length) {
    tbody.innerHTML =
      '<tr><td colspan="7" class="empty-hint">No hay comprobantes en esta categoría.</td></tr>';
    return;
  }

  const eventLabels = {
    RESERVATION_CONFIRMED: "Confirmación",
    RESERVATION_UPDATED: "Actualización",
    RESERVATION_CANCELLED: "Cancelación",
  };
  const admin = isAdmin();

  tbody.innerHTML = filtered
    .map(
      (n) => `
      <tr>
        <td><span class="mono-inline">${n.confirmation_code}</span></td>
        <td>#${n.reservation_id}</td>
        <td>${eventLabels[n.event_type] || n.event_type}</td>
        <td>${n.recipient_name}<br /><span class="muted-text">${n.recipient_email}</span></td>
        <td>${n.subject}</td>
        <td>${statusBadge(n.status)}</td>
        <td>
          <div class="table-actions">
            <button type="button" class="btn btn-ghost btn-sm" data-view-notif="${n.id}">Ver</button>
            ${
              n.status !== "READ"
                ? `<button type="button" class="btn btn-outline btn-sm" data-read-notif="${n.id}">Marcar leído</button>`
                : ""
            }
            ${
              admin
                ? `<button type="button" class="btn btn-danger-subtle" data-delete-notif="${n.id}">Eliminar</button>`
                : ""
            }
          </div>
        </td>
      </tr>`
    )
    .join("");

  tbody.querySelectorAll("[data-view-notif]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        const { data: n } = await apiFetch(`/api/notifications/${btn.dataset.viewNotif}`);
        openModal(
          `Comprobante ${n.confirmation_code}`,
          `<div class="receipt-box">
            <div><strong>Asunto:</strong> ${n.subject}</div>
            <div><strong>Destinatario:</strong> ${n.recipient_name} (${n.recipient_email})</div>
            <div><strong>Reserva asociada:</strong> #${n.reservation_id} · Canal: ${n.channel}</div>
            <div class="receipt-message">${n.message}</div>
            <div class="muted-text">Emitido: ${n.created_at}</div>
          </div>`
        );
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  });

  tbody.querySelectorAll("[data-read-notif]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      setButtonLoading(btn, true, "...");
      try {
        await apiFetch(`/api/notifications/${btn.dataset.readNotif}/status`, {
          method: "PATCH",
          body: JSON.stringify({ status: "READ" }),
        });
        showToast("Comprobante marcado como leído.");
        await loadNotifications();
      } catch (err) {
        showToast(err.message, "error");
        setButtonLoading(btn, false);
      }
    });
  });

  if (admin) {
    tbody.querySelectorAll("[data-delete-notif]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = Number(btn.dataset.deleteNotif);
        if (!confirm("¿Eliminar este comprobante del historial?")) return;
        setButtonLoading(btn, true, "...");
        try {
          await apiFetch(`/api/notifications/${id}`, { method: "DELETE" });
          showToast("Comprobante eliminado.");
          await loadNotifications();
        } catch (err) {
          showToast(err.message, "error");
          setButtonLoading(btn, false);
        }
      });
    });
  }
}

/* ==================== CARGA DE DATOS ==================== */
async function loadSpaces() {
  const { data } = await apiFetch("/api/spaces");
  state.spaces = data;
  renderRoomPicker();
  renderSpacesCatalog(document.getElementById("space-search")?.value || "");
}

async function loadReservations() {
  const { data } = await apiFetch("/api/reservations");
  state.reservations = data;
  renderReservations();
}

async function loadUsers() {
  const onlyActive = document.getElementById("users-only-active")?.checked || false;
  const [{ data: me }, { data: list }] = await Promise.all([
    apiFetch("/api/auth/me"),
    apiFetch(`/api/users?only_active=${onlyActive}`),
  ]);
  state.users = list;
  renderMyProfile(me);
  renderUsersTable();
  populateAdminBookingUsers();
}

async function loadNotifications() {
  const { data } = await apiFetch("/api/notifications");
  state.notifications = data;
  renderNotificationsTable();
}

async function loadCatalog() {
  const { data } = await apiFetch("/registry/services");
  const summary = document.getElementById("catalog-summary");
  summary.textContent = `${data.services_up} de ${data.total_services} servicios activos`;
  summary.className = `status-badge ${data.services_up === data.total_services ? "status-ok" : "status-warn"}`;

  const grid = document.getElementById("catalog-grid");
  grid.innerHTML = data.services
    .map(
      (svc) => `
      <article class="info-card">
        <div class="info-card-top">
          <div>
            <span class="room-code">:${svc.port}</span>
            <h3>${svc.name}</h3>
          </div>
          ${statusBadge(svc.status)}
        </div>
        <p class="muted-text">${svc.title}</p>
        <p class="muted-text">Base de datos: <span class="mono-inline">${svc.database}</span> · ${svc.latency_ms} ms</p>
        <div class="chip-list">
          ${svc.capabilities.map((c) => `<span class="chip">${c}</span>`).join("")}
        </div>
        <a class="docs-link" href="${svc.docs_url}" target="_blank" rel="noopener">Abrir contrato OpenAPI (Swagger)</a>
      </article>`
    )
    .join("");
}

async function refreshActiveView() {
  try {
    if (state.activeView === "view-reservations") {
      const jobs = [loadSpaces(), loadReservations()];
      if (isAdmin() && !state.users.length) {
        jobs.push(
          apiFetch("/api/users?only_active=true").then(({ data }) => {
            state.users = data;
            populateAdminBookingUsers();
          })
        );
      }
      await Promise.all(jobs);
    } else if (state.activeView === "view-spaces") {
      await loadSpaces();
    } else if (state.activeView === "view-users") {
      await loadUsers();
    } else if (state.activeView === "view-notifications") {
      await loadNotifications();
    } else if (state.activeView === "view-catalog") {
      await loadCatalog();
    }
    state.loadedViews.add(state.activeView);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function switchView(viewId) {
  state.activeView = viewId;
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === viewId);
  });
  document.querySelectorAll(".view-section").forEach((sec) => {
    sec.classList.toggle("active", sec.id === viewId);
  });
  const meta = VIEW_META[viewId];
  if (meta) {
    document.getElementById("view-title").textContent = meta.title;
    document.getElementById("view-subtitle").textContent = meta.subtitle;
  }
  if (!state.loadedViews.has(viewId)) {
    refreshActiveView();
  }
}

function logoutUser(notice = "") {
  state.token = null;
  state.user = null;
  state.users = [];
  state.loadedViews.clear();
  localStorage.removeItem("reservasoa_token");
  localStorage.removeItem("reservasoa_user");
  renderSession();
  if (notice) showToast(notice, "error");
}

function renderSession() {
  if (state.token && state.user) {
    authShell.classList.add("hidden");
    appShell.classList.remove("hidden");
    document.getElementById("session-name").textContent = state.user.full_name;
    document.getElementById("session-dept").textContent = state.user.department;
    document.getElementById("session-role").textContent = state.user.role;
    document.getElementById("user-avatar").textContent = getInitials(state.user.full_name);

    const admin = isAdmin();
    document.getElementById("admin-space-panel").classList.toggle("hidden", !admin);
    document.getElementById("admin-user-panel").classList.toggle("hidden", !admin);
    refreshActiveView();
  } else {
    authShell.classList.remove("hidden");
    appShell.classList.add("hidden");
    probeAuthHealth();
  }
}

async function probeAuthHealth() {
  const el = document.getElementById("auth-services-status");
  if (!el) return;
  try {
    const resp = await fetch("/registry/services");
    if (resp.ok) {
      const data = await resp.json();
      el.textContent = `${data.services_up} de ${data.total_services} en línea`;
      return;
    }
  } catch {
    // silencioso
  }
  el.textContent = "4 servicios independientes";
}

async function handleCancelReservation(id, btn) {
  setButtonLoading(btn, true, "Cancelando...");
  try {
    const { data, elapsed } = await apiFetch(`/api/reservations/${id}/cancel`, { method: "POST" });
    renderTrace(data.soa_trace, data.confirmation_code, elapsed);
    showToast(`Reservación #${id} cancelada.`);
    state.loadedViews.delete("view-notifications");
    await loadReservations();
  } catch (err) {
    showToast(err.message, "error");
    setButtonLoading(btn, false);
  }
}

/* ==================== EVENTOS ==================== */
document.querySelectorAll(".auth-switch").forEach((btn) => {
  btn.addEventListener("click", () => {
    const mode = btn.dataset.authMode;
    document.querySelectorAll(".auth-switch").forEach((b) => {
      const active = b.dataset.authMode === mode;
      b.classList.toggle("active", active);
      b.setAttribute("aria-selected", String(active));
    });
    document.getElementById("login-form").classList.toggle("hidden", mode !== "login");
    document.getElementById("register-form").classList.toggle("hidden", mode !== "register");
  });
});

document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("btn-login-submit");
  setButtonLoading(btn, true, "Verificando...");
  try {
    const { data } = await apiFetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: document.getElementById("login-email").value.trim(),
        password: document.getElementById("login-password").value,
      }),
    });
    state.token = data.access_token;
    state.user = data.user;
    localStorage.setItem("reservasoa_token", state.token);
    localStorage.setItem("reservasoa_user", JSON.stringify(state.user));
    showToast(`Sesión iniciada como ${state.user.full_name}.`);
    renderSession();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    setButtonLoading(btn, false);
  }
});

document.getElementById("register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("btn-register-submit");
  setButtonLoading(btn, true, "Creando cuenta...");
  try {
    await apiFetch("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({
        full_name: document.getElementById("reg-name").value.trim(),
        email: document.getElementById("reg-email").value.trim(),
        department: document.getElementById("reg-dept").value.trim(),
        password: document.getElementById("reg-password").value,
      }),
    });
    showToast("Cuenta creada. Ahora puedes iniciar sesión.");
    e.target.reset();
    document.querySelector('[data-auth-mode="login"]').click();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    setButtonLoading(btn, false);
  }
});

document.getElementById("btn-demo-admin").addEventListener("click", () => {
  document.getElementById("login-email").value = "admin@nexosalas.com";
  document.getElementById("login-password").value = "Admin123!";
});

document.getElementById("btn-demo-emp").addEventListener("click", () => {
  document.getElementById("login-email").value = "ana.lopez@nexosalas.com";
  document.getElementById("login-password").value = "Ana12345";
});

document.getElementById("btn-logout").addEventListener("click", () => logoutUser());
document.getElementById("btn-sidebar-profile").addEventListener("click", () => switchView("view-users"));

document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => switchView(btn.dataset.view));
});

document.getElementById("btn-refresh-active").addEventListener("click", refreshActiveView);

document.getElementById("res-space").addEventListener("change", (e) => {
  state.selectedSpaceId = Number(e.target.value);
  document.getElementById("space-validation-box").classList.add("hidden");
  renderRoomPicker();
});

document.getElementById("btn-validate-space").addEventListener("click", async () => {
  const spaceId = Number(document.getElementById("res-space").value);
  const attendees = Number(document.getElementById("res-attendees").value) || 1;
  const box = document.getElementById("space-validation-box");
  if (!spaceId) return;
  try {
    const { data } = await apiFetch(`/api/spaces/${spaceId}/validate?attendees=${attendees}`);
    box.textContent = data.reason;
    box.className = `validation-box ${data.valid ? "valid" : "invalid"}`;
  } catch (err) {
    box.textContent = err.message;
    box.className = "validation-box invalid";
  }
});

document.querySelectorAll("[data-res-filter]").forEach((btn) => {
  btn.addEventListener("click", () => {
    state.resFilter = btn.dataset.resFilter;
    document.querySelectorAll("[data-res-filter]").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    renderReservations();
  });
});

document.querySelectorAll("[data-notif-filter]").forEach((btn) => {
  btn.addEventListener("click", () => {
    state.notifFilter = btn.dataset.notifFilter;
    document.querySelectorAll("[data-notif-filter]").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    renderNotificationsTable();
  });
});

document.getElementById("space-search").addEventListener("input", (e) => {
  renderSpacesCatalog(e.target.value);
});

document.getElementById("users-only-active").addEventListener("change", () => {
  loadUsers().catch((err) => showToast(err.message, "error"));
});

document.getElementById("reservation-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("btn-reserve-submit");
  setButtonLoading(btn, true, "Validando servicios...");
  try {
    const body = {
      space_id: Number(document.getElementById("res-space").value),
      title: document.getElementById("res-title").value.trim(),
      reservation_date: document.getElementById("res-date").value,
      start_time: document.getElementById("res-start").value,
      end_time: document.getElementById("res-end").value,
      attendees: Number(document.getElementById("res-attendees").value),
      notes: document.getElementById("res-notes").value.trim(),
    };
    if (isAdmin()) {
      const selectedUserId = Number(document.getElementById("res-user-id").value);
      if (selectedUserId) body.user_id = selectedUserId;
    }
    const { data, elapsed } = await apiFetch("/api/reservations", {
      method: "POST",
      body: JSON.stringify(body),
    });
    renderTrace(data.soa_trace, data.confirmation_code, elapsed);
    showToast(`Reservación confirmada (${data.confirmation_code}).`);
    document.getElementById("res-title").value = "";
    document.getElementById("res-notes").value = "";
    document.getElementById("space-validation-box").classList.add("hidden");
    state.loadedViews.delete("view-notifications");
    await loadReservations();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    setButtonLoading(btn, false);
  }
});

document.getElementById("space-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("btn-space-submit");
  setButtonLoading(btn, true, "Guardando...");
  try {
    const resources = document
      .getElementById("sp-resources")
      .value.split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    await apiFetch("/api/spaces", {
      method: "POST",
      body: JSON.stringify({
        code: document.getElementById("sp-code").value.trim(),
        name: document.getElementById("sp-name").value.trim(),
        building: document.getElementById("sp-building").value.trim(),
        floor: Number(document.getElementById("sp-floor").value),
        capacity: Number(document.getElementById("sp-capacity").value),
        resources,
        description: document.getElementById("sp-description").value.trim(),
      }),
    });
    showToast("Espacio agregado al catálogo.");
    e.target.reset();
    await loadSpaces();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    setButtonLoading(btn, false);
  }
});

document.getElementById("admin-user-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("btn-user-submit");
  setButtonLoading(btn, true, "Creando...");
  try {
    await apiFetch("/api/users", {
      method: "POST",
      body: JSON.stringify({
        full_name: document.getElementById("u-name").value.trim(),
        email: document.getElementById("u-email").value.trim(),
        department: document.getElementById("u-dept").value.trim(),
        role: document.getElementById("u-role").value,
        password: document.getElementById("u-password").value,
      }),
    });
    showToast("Usuario creado correctamente.");
    e.target.reset();
    await loadUsers();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    setButtonLoading(btn, false);
  }
});

const tomorrow = new Date();
tomorrow.setDate(tomorrow.getDate() + 1);
document.getElementById("res-date").value = tomorrow.toISOString().split("T")[0];

renderSession();
