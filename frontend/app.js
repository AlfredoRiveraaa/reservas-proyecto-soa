const state = {
  token: localStorage.getItem("reservasoa_token") || null,
  user: JSON.parse(localStorage.getItem("reservasoa_user") || "null"),
  activeView: "view-reservations",
  spaces: [],
  reservations: [],
  resFilter: "ALL",
  selectedSpaceId: null,
  loadedViews: new Set(),
};

const VIEW_META = {
  "view-reservations": {
    title: "Agenda y reservas",
    subtitle: "Selecciona una sala, elige horario y genera una confirmación orquestada.",
  },
  "view-spaces": {
    title: "Salas y recursos",
    subtitle: "Consulta disponibilidad operativa, capacidad y equipamiento de cada espacio.",
  },
  "view-notifications": {
    title: "Comprobantes",
    subtitle: "Historial de folios de confirmación y cancelación emitidos por notifications-service.",
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

function showToast(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast ${type === "error" ? "toast-error" : ""}`;
  toast.textContent = message;
  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4500);
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

async function apiFetch(path, options = {}) {
  const started = performance.now();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) {
    headers["Authorization"] = `Bearer ${state.token}`;
  }
  const response = await fetch(path, { ...options, headers });
  const elapsed = Math.round(performance.now() - started);
  if (latencyPill) {
    latencyPill.textContent = `${elapsed} ms`;
  }

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

function getInitials(name = "") {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("") || "EH";
}

function statusBadge(status) {
  const map = {
    CONFIRMED: ["Confirmada", "status-ok"],
    CANCELLED: ["Cancelada", "status-err"],
    available: ["Disponible", "status-ok"],
    maintenance: ["Mantenimiento", "status-warn"],
    UP: ["Activo", "status-ok"],
    DOWN: ["Sin respuesta", "status-err"],
    SENT: ["Enviado", "status-ok"],
    READ: ["Leído", "status-ok"],
    FAILED: ["Error", "status-err"],
  };
  const [label, cls] = map[status] || [status, "status-ok"];
  return `<span class="status-badge ${cls}">${label}</span>`;
}

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

  if (!state.selectedSpaceId) {
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
      </article>`
    )
    .join("");
}

function renderReservations() {
  const container = document.getElementById("reservations-list");
  const filtered = state.reservations.filter((r) =>
    state.resFilter === "ALL" ? true : r.status === state.resFilter
  );

  if (!filtered.length) {
    container.innerHTML = '<p class="empty-hint">No hay reservaciones en esta vista. Usa el formulario lateral para crear una.</p>';
    return;
  }

  container.innerHTML = filtered
    .map(
      (r) => `
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
            r.status === "CONFIRMED"
              ? `<button type="button" class="btn btn-danger-subtle" data-cancel-id="${r.id}">Cancelar</button>`
              : ""
          }
        </div>
      </article>`
    )
    .join("");

  container.querySelectorAll("[data-cancel-id]").forEach((btn) => {
    btn.addEventListener("click", () => handleCancelReservation(Number(btn.dataset.cancelId), btn));
  });
}

function renderTrace(steps, confirmationCode = "", elapsedMs = null) {
  const box = document.getElementById("soa-trace-box");
  const durationEl = document.getElementById("trace-duration");
  if (elapsedMs !== null) {
    durationEl.textContent = `${elapsedMs} ms`;
  }
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

async function loadNotifications() {
  const { data } = await apiFetch("/api/notifications");
  document.getElementById("notifs-count-label").textContent = `${data.length} registros`;
  const tbody = document.getElementById("notifications-tbody");
  if (!data.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-hint">Aún no se han emitido comprobantes.</td></tr>';
    return;
  }
  const eventLabels = {
    RESERVATION_CONFIRMED: "Confirmación",
    RESERVATION_UPDATED: "Actualización",
    RESERVATION_CANCELLED: "Cancelación",
  };
  tbody.innerHTML = data
    .map(
      (n) => `
      <tr>
        <td><span class="mono-inline">${n.confirmation_code}</span></td>
        <td>#${n.reservation_id}</td>
        <td>${eventLabels[n.event_type] || n.event_type}</td>
        <td>${n.recipient_name}<br /><span class="muted-text">${n.recipient_email}</span></td>
        <td>${n.subject}</td>
        <td>${statusBadge(n.status)}</td>
      </tr>`
    )
    .join("");
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
      await Promise.all([loadSpaces(), loadReservations()]);
    } else if (state.activeView === "view-spaces") {
      await loadSpaces();
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

    const adminPanel = document.getElementById("admin-space-panel");
    adminPanel.classList.toggle("hidden", state.user.role !== "admin");
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

/* ---------- Eventos ---------- */
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
  document.getElementById("login-email").value = "admin@espaciohub.com";
  document.getElementById("login-password").value = "Admin123!";
});

document.getElementById("btn-demo-emp").addEventListener("click", () => {
  document.getElementById("login-email").value = "ana.lopez@espaciohub.com";
  document.getElementById("login-password").value = "Ana12345";
});

document.getElementById("btn-logout").addEventListener("click", () => logoutUser());

document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => switchView(btn.dataset.view));
});

document.getElementById("btn-refresh-active").addEventListener("click", refreshActiveView);

document.getElementById("res-space").addEventListener("change", (e) => {
  state.selectedSpaceId = Number(e.target.value);
  renderRoomPicker();
});

document.querySelectorAll("[data-res-filter]").forEach((btn) => {
  btn.addEventListener("click", () => {
    state.resFilter = btn.dataset.resFilter;
    document.querySelectorAll("[data-res-filter]").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    renderReservations();
  });
});

document.getElementById("space-search").addEventListener("input", (e) => {
  renderSpacesCatalog(e.target.value);
});

document.getElementById("reservation-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("btn-reserve-submit");
  setButtonLoading(btn, true, "Validando servicios...");
  try {
    const { data, elapsed } = await apiFetch("/api/reservations", {
      method: "POST",
      body: JSON.stringify({
        space_id: Number(document.getElementById("res-space").value),
        title: document.getElementById("res-title").value.trim(),
        reservation_date: document.getElementById("res-date").value,
        start_time: document.getElementById("res-start").value,
        end_time: document.getElementById("res-end").value,
        attendees: Number(document.getElementById("res-attendees").value),
        notes: document.getElementById("res-notes").value.trim(),
      }),
    });
    renderTrace(data.soa_trace, data.confirmation_code, elapsed);
    showToast(`Reservación confirmada (${data.confirmation_code}).`);
    document.getElementById("res-title").value = "";
    document.getElementById("res-notes").value = "";
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

const tomorrow = new Date();
tomorrow.setDate(tomorrow.getDate() + 1);
document.getElementById("res-date").value = tomorrow.toISOString().split("T")[0];

renderSession();
