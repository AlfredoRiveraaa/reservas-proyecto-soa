const state = {
  token: localStorage.getItem("reservasoa_token") || null,
  user: JSON.parse(localStorage.getItem("reservasoa_user") || "null"),
};

const alertBanner = document.getElementById("alert-banner");
const authSection = document.getElementById("auth-section");
const dashboardSection = document.getElementById("dashboard-section");
const userSession = document.getElementById("user-session");
const adminSpaceCard = document.getElementById("admin-space-card");

function showAlert(message, type = "success") {
  alertBanner.textContent = message;
  alertBanner.className = `alert alert-${type}`;
  setTimeout(() => {
    alertBanner.classList.add("hidden");
  }, 6000);
}

async function apiFetch(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) {
    headers["Authorization"] = `Bearer ${state.token}`;
  }
  const response = await fetch(path, { ...options, headers });
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { message: text };
  }
  if (!response.ok) {
    const msg = (data && (data.message || data.detail)) || `Error HTTP ${response.status}`;
    throw new Error(msg);
  }
  return data;
}

function renderSession() {
  if (state.token && state.user) {
    authSection.classList.add("hidden");
    dashboardSection.classList.remove("hidden");
    userSession.classList.remove("hidden");
    document.getElementById("session-name").textContent = `${state.user.full_name} (${state.user.department})`;
    document.getElementById("session-role").textContent = state.user.role;
    if (state.user.role === "admin") {
      adminSpaceCard.classList.remove("hidden");
    } else {
      adminSpaceCard.classList.add("hidden");
    }
    loadAllData();
  } else {
    authSection.classList.remove("hidden");
    dashboardSection.classList.add("hidden");
    userSession.classList.add("hidden");
  }
}

function renderTrace(steps, confirmationCode = "") {
  const box = document.getElementById("soa-trace-box");
  if (!steps || steps.length === 0) {
    box.innerHTML = '<p class="muted">Sin traza registrada.</p>';
    return;
  }
  const header = confirmationCode
    ? `<div class="trace-step"><strong>Folio de confirmación emitido:</strong> <code>${confirmationCode}</code></div>`
    : "";
  box.innerHTML =
    header +
    steps
      .map(
        (s, idx) => `
      <div class="trace-step ${s.status !== "OK" ? "degraded" : ""}">
        <strong>Paso ${idx + 1} • ${s.service}</strong> (${s.status})<br />
        <code>${s.operation}</code><br />
        <span class="muted">${s.detail}</span>
      </div>`
      )
      .join("");
}

async function loadSpaces() {
  const spaces = await apiFetch("/api/spaces");
  const select = document.getElementById("res-space");
  select.innerHTML = spaces
    .map(
      (s) =>
        `<option value="${s.id}">${s.code} — ${s.name} (Cap. ${s.capacity}, ${s.status})</option>`
    )
    .join("");

  const grid = document.getElementById("spaces-grid");
  grid.innerHTML = spaces
    .map(
      (s) => `
      <div class="mini-card">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <strong>${s.name}</strong>
          <span class="pill pill-${s.status}">${s.status}</span>
        </div>
        <div class="muted">${s.code} • ${s.building}, Piso ${s.floor} • Cap: ${s.capacity}</div>
        <div>${s.resources.map((r) => `<span class="tag">${r}</span>`).join("")}</div>
      </div>`
    )
    .join("");
}

async function loadReservations() {
  const items = await apiFetch("/api/reservations");
  const tbody = document.getElementById("reservations-tbody");
  if (!items.length) {
    tbody.innerHTML = '<tr><td colspan="9" class="muted">No hay reservaciones registradas.</td></tr>';
    return;
  }
  tbody.innerHTML = items
    .map(
      (r) => `
      <tr>
        <td>#${r.id}</td>
        <td><code>${r.confirmation_code || "-"}</code></td>
        <td>${r.space_name}</td>
        <td>${r.title}</td>
        <td>${r.user_name}</td>
        <td>${r.reservation_date} ${r.start_time}-${r.end_time}</td>
        <td>${r.attendees}</td>
        <td><span class="pill pill-${r.status.toLowerCase()}">${r.status}</span></td>
        <td>
          ${
            r.status === "CONFIRMED"
              ? `<button class="btn btn-danger" onclick="cancelReservation(${r.id})">Cancelar</button>`
              : "-"
          }
        </td>
      </tr>`
    )
    .join("");
}

async function loadNotifications() {
  const items = await apiFetch("/api/notifications");
  const tbody = document.getElementById("notifications-tbody");
  if (!items.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="muted">Sin notificaciones registradas.</td></tr>';
    return;
  }
  tbody.innerHTML = items
    .map(
      (n) => `
      <tr>
        <td><code>${n.confirmation_code}</code></td>
        <td>#${n.reservation_id}</td>
        <td>${n.event_type}</td>
        <td>${n.recipient_name}<br/><span class="muted">${n.recipient_email}</span></td>
        <td>${n.subject}</td>
        <td>${n.channel}</td>
        <td><span class="pill pill-${n.status.toLowerCase()}">${n.status}</span></td>
      </tr>`
    )
    .join("");
}

async function loadCatalog() {
  const data = await apiFetch("/registry/services");
  const grid = document.getElementById("catalog-grid");
  grid.innerHTML = data.services
    .map(
      (svc) => `
      <div class="mini-card">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <strong>${svc.name}</strong>
          <span class="pill pill-${svc.status.toLowerCase()}">${svc.status}</span>
        </div>
        <div class="muted">${svc.title}</div>
        <div class="muted">Puerto: <code>${svc.port}</code> • Latencia: ${svc.latency_ms} ms</div>
        <div class="muted">BD propia: <code>${svc.database}</code></div>
        <div>${svc.capabilities.map((c) => `<span class="tag">${c}</span>`).join("")}</div>
        <a href="${svc.docs_url}" target="_blank">Abrir contrato OpenAPI (Swagger) →</a>
      </div>`
    )
    .join("");
}

async function loadAllData() {
  try {
    await Promise.all([loadSpaces(), loadReservations(), loadNotifications(), loadCatalog()]);
  } catch (err) {
    showAlert(err.message, "error");
  }
}

window.cancelReservation = async function (id) {
  try {
    const res = await apiFetch(`/api/reservations/${id}/cancel`, { method: "POST" });
    renderTrace(res.soa_trace, res.confirmation_code);
    showAlert(`Reservación #${id} cancelada y notificación enviada.`, "success");
    await Promise.all([loadReservations(), loadNotifications()]);
  } catch (err) {
    showAlert(err.message, "error");
  }
};

document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const data = await apiFetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: document.getElementById("login-email").value,
        password: document.getElementById("login-password").value,
      }),
    });
    state.token = data.access_token;
    state.user = data.user;
    localStorage.setItem("reservasoa_token", state.token);
    localStorage.setItem("reservasoa_user", JSON.stringify(state.user));
    showAlert(`Bienvenido, ${state.user.full_name}.`, "success");
    renderSession();
  } catch (err) {
    showAlert(err.message, "error");
  }
});

document.getElementById("register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await apiFetch("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({
        full_name: document.getElementById("reg-name").value,
        email: document.getElementById("reg-email").value,
        department: document.getElementById("reg-dept").value,
        password: document.getElementById("reg-password").value,
      }),
    });
    showAlert("Cuenta creada con éxito. Ahora puedes iniciar sesión.", "success");
    e.target.reset();
  } catch (err) {
    showAlert(err.message, "error");
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

document.getElementById("btn-logout").addEventListener("click", () => {
  state.token = null;
  state.user = null;
  localStorage.removeItem("reservasoa_token");
  localStorage.removeItem("reservasoa_user");
  renderSession();
});

document.getElementById("reservation-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const res = await apiFetch("/api/reservations", {
      method: "POST",
      body: JSON.stringify({
        space_id: Number(document.getElementById("res-space").value),
        title: document.getElementById("res-title").value,
        reservation_date: document.getElementById("res-date").value,
        start_time: document.getElementById("res-start").value,
        end_time: document.getElementById("res-end").value,
        attendees: Number(document.getElementById("res-attendees").value),
        notes: document.getElementById("res-notes").value,
      }),
    });
    renderTrace(res.soa_trace, res.confirmation_code);
    showAlert(`Reservación #${res.id} confirmada con folio ${res.confirmation_code}.`, "success");
    e.target.reset();
    await Promise.all([loadReservations(), loadNotifications()]);
  } catch (err) {
    showAlert(err.message, "error");
  }
});

document.getElementById("space-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const rawResources = document.getElementById("sp-resources").value;
    const resources = rawResources
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    await apiFetch("/api/spaces", {
      method: "POST",
      body: JSON.stringify({
        code: document.getElementById("sp-code").value,
        name: document.getElementById("sp-name").value,
        building: document.getElementById("sp-building").value,
        floor: Number(document.getElementById("sp-floor").value),
        capacity: Number(document.getElementById("sp-capacity").value),
        resources,
      }),
    });
    showAlert("Espacio registrado en spaces-service.", "success");
    e.target.reset();
    await loadSpaces();
  } catch (err) {
    showAlert(err.message, "error");
  }
});

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(btn.dataset.tab).classList.add("active");
  });
});

document.getElementById("btn-refresh-res").addEventListener("click", loadReservations);
document.getElementById("btn-refresh-spaces").addEventListener("click", loadSpaces);
document.getElementById("btn-refresh-notifs").addEventListener("click", loadNotifications);
document.getElementById("btn-refresh-catalog").addEventListener("click", loadCatalog);

const defaultDate = new Date();
defaultDate.setDate(defaultDate.getDate() + 1);
document.getElementById("res-date").value = defaultDate.toISOString().split("T")[0];

renderSession();
