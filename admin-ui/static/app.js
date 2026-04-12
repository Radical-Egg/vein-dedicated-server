const boot = window.__VEIN_ADMIN_BOOT__ || { configFiles: [], composeAvailable: false };
const THEME_KEY = "vein-admin-theme";

const elements = {
  themeToggle: document.getElementById("theme-toggle"),
  configSelect: document.getElementById("config-select"),
  configPath: document.getElementById("config-path"),
  managedInfo: document.getElementById("managed-info"),
  managedTooltip: document.getElementById("managed-tooltip"),
  configEditor: document.getElementById("config-editor"),
  saveConfig: document.getElementById("save-config"),
  reloadConfig: document.getElementById("reload-config"),
  startupSyncInfo: document.getElementById("startup-sync-info"),
  startupSyncTooltip: document.getElementById("startup-sync-tooltip"),
  syncStateLabel: document.getElementById("sync-state-label"),
  syncStateMeta: document.getElementById("sync-state-meta"),
  syncStateBadge: document.getElementById("sync-state-badge"),
  enableSync: document.getElementById("enable-sync"),
  disableSync: document.getElementById("disable-sync"),
  refreshContainers: document.getElementById("refresh-containers"),
  containerList: document.getElementById("container-list"),
  flash: document.getElementById("flash"),
};

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || `Request failed with status ${response.status}`);
  }
  return data;
}

function showFlash(message, type = "info") {
  elements.flash.hidden = false;
  elements.flash.textContent = message;
  elements.flash.dataset.type = type;
}

function clearFlash() {
  elements.flash.hidden = true;
  elements.flash.textContent = "";
  delete elements.flash.dataset.type;
}

function formatStatus(item) {
  const health = item.health && item.health !== "none" ? ` / ${item.health}` : "";
  return `${item.status}${health}`;
}

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem(THEME_KEY, theme);
  elements.themeToggle.setAttribute(
    "aria-label",
    theme === "dark" ? "Switch to light mode" : "Switch to dark mode",
  );
}

function loadTheme() {
  const savedTheme = localStorage.getItem(THEME_KEY) || "dark";
  setTheme(savedTheme);
}

function renderManagedFields(fields) {
  if (!fields.length) {
    elements.managedInfo.hidden = true;
    elements.managedTooltip.hidden = true;
    elements.managedTooltip.innerHTML = "";
    return;
  }

  elements.managedInfo.hidden = false;
  elements.managedTooltip.innerHTML = `
    <p class="tooltip-title">Startup-managed values</p>
    <p class="tooltip-copy">If you edit one of these values, the UI will also update <code>docker-compose.yml</code> so the change survives restart.</p>
    <div class="tooltip-list">
      ${fields
    .map(
      (field) => `
        <div class="tooltip-item">
          <code>[${field.section}] ${field.option}</code>
          <span>Controlled by <code>${field.env_var}</code></span>
        </div>
      `,
    )
    .join("")}
    </div>
  `;
}

function renderContainers(items) {
  elements.containerList.innerHTML = "";

  items.forEach((item) => {
    const card = document.createElement("article");
    card.className = "container-card";

    const badgeClass = `badge badge-${item.status}`;
    card.innerHTML = `
      <div class="card-top">
        <div>
          <p class="section-label">${item.label}</p>
          <h3>${item.name}</h3>
          <p class="meta">${item.image || "No image metadata available"}</p>
        </div>
        <span class="${badgeClass}">${formatStatus(item)}</span>
      </div>
      <div class="actions">
        <button class="button" data-action="start" data-key="${item.key}">Start</button>
        <button class="button button-secondary" data-action="restart" data-key="${item.key}">Restart</button>
        <button class="button button-danger" data-action="stop" data-key="${item.key}">Stop</button>
      </div>
    `;

    elements.containerList.appendChild(card);
  });
}

async function loadConfig(key) {
  clearFlash();
  elements.configEditor.value = "";
  elements.configEditor.disabled = true;
  const data = await requestJson(`/api/configs/${key}`);
  elements.configPath.textContent = data.path;
  elements.configEditor.value = data.content;
  elements.configEditor.disabled = false;
  renderManagedFields(data.managed_fields || []);
}

async function saveConfig() {
  const key = elements.configSelect.value;
  const payload = { content: elements.configEditor.value };
  const response = await requestJson(`/api/configs/${key}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });

  if (response.compose_updates?.updated?.length) {
    const envVars = response.compose_updates.updated.map((change) => change.env_var).join(", ");
    showFlash(`Configuration saved and compose synced for ${envVars}.`, "success");
    await loadStartupSync();
    return;
  }

  showFlash("Configuration saved.", "success");
}

async function loadContainers() {
  const data = await requestJson("/api/containers");
  renderContainers(data.items);
}

function renderStartupSync(data) {
  if (!data.available) {
    elements.syncStateLabel.textContent = "Compose file unavailable";
    elements.syncStateMeta.textContent = "Mount docker-compose.yml into the admin container to enable sync controls.";
    elements.syncStateBadge.textContent = "Unavailable";
    elements.syncStateBadge.className = "badge badge-missing";
    elements.enableSync.disabled = true;
    elements.disableSync.disabled = true;
    return;
  }

  const enabled = Boolean(data.enabled);
  elements.syncStateLabel.textContent = enabled ? "Enabled on startup" : "Disabled on startup";
  elements.syncStateMeta.textContent = `Compose file: ${data.path}`;
  elements.syncStateBadge.textContent = enabled ? "Enabled" : "Disabled";
  elements.syncStateBadge.className = enabled ? "badge badge-running" : "badge badge-exited";
  elements.enableSync.disabled = enabled;
  elements.disableSync.disabled = !enabled;
}

async function loadStartupSync() {
  const data = await requestJson("/api/startup-sync");
  renderStartupSync(data);
}

async function updateStartupSync(enabled) {
  const response = await requestJson("/api/startup-sync", {
    method: "PUT",
    body: JSON.stringify({ enabled }),
  });
  renderStartupSync(response);
  showFlash(`Startup config sync ${enabled ? "enabled" : "disabled"}.`, "success");
}

async function runContainerAction(event) {
  const button = event.target.closest("button[data-action]");
  if (!button) {
    return;
  }

  const { key, action } = button.dataset;
  button.disabled = true;
  try {
    const result = await requestJson(`/api/containers/${key}/${action}`, {
      method: "POST",
    });
    showFlash(`${result.label} ${action} completed.`, "success");
    await loadContainers();
  } finally {
    button.disabled = false;
  }
}

async function bootstrap() {
  if (!boot.configFiles.length) {
    showFlash("No config files were registered.", "error");
    return;
  }

  loadTheme();

  elements.themeToggle.addEventListener("click", () => {
    const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
  });

  elements.managedInfo.addEventListener("click", () => {
    elements.managedTooltip.hidden = !elements.managedTooltip.hidden;
  });

  elements.startupSyncInfo.addEventListener("click", () => {
    elements.startupSyncTooltip.hidden = !elements.startupSyncTooltip.hidden;
  });

  elements.configSelect.addEventListener("change", () => {
    loadConfig(elements.configSelect.value).catch((error) => showFlash(error.message, "error"));
  });

  elements.saveConfig.addEventListener("click", () => {
    saveConfig().catch((error) => showFlash(error.message, "error"));
  });

  elements.reloadConfig.addEventListener("click", () => {
    loadConfig(elements.configSelect.value).catch((error) => showFlash(error.message, "error"));
  });

  elements.refreshContainers.addEventListener("click", () => {
    loadContainers().catch((error) => showFlash(error.message, "error"));
  });

  elements.enableSync.addEventListener("click", () => {
    updateStartupSync(true).catch((error) => showFlash(error.message, "error"));
  });

  elements.disableSync.addEventListener("click", () => {
    updateStartupSync(false).catch((error) => showFlash(error.message, "error"));
  });

  elements.containerList.addEventListener("click", (event) => {
    runContainerAction(event).catch((error) => showFlash(error.message, "error"));
  });

  await loadConfig(elements.configSelect.value);
  await loadStartupSync();
  await loadContainers();
}

bootstrap().catch((error) => showFlash(error.message, "error"));
