"use strict";
/* InnoCalc Manager - front end.
   The front end holds no engineering knowledge. Every calculation form is built
   from the schema its module publishes, so a new design module needs no change
   here. */

const $ = id => document.getElementById(id);
const state = {
  token: "", user: null, people: [],
  projects: [], project: null,
  modules: [], module: null, schema: null,
  inputs: {}, fields: [], checks: {}, cells: [],
  calculationId: "", dirty: false, view: "library",
  library: null, qa: [], qaTemplate: null,
  packageEntries: [], packageSelection: new Set(),
  timer: 0, request: 0
};

/* ---------------------------------------------------------------- utilities */
async function api(path, payload, method = "POST") {
  const options = method === "GET" ? {} : {
    method, headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token: state.token, ...(payload || {}) })
  };
  const response = await fetch(path, options);
  let data;
  try { data = await response.json(); } catch { throw new Error(`Server error (${response.status})`); }
  if (!response.ok || !data.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}
function get(path, params) {
  const query = new URLSearchParams({ token: state.token, ...(params || {}) });
  return api(`${path}?${query}`, null, "GET");
}
function toast(message, bad = false) {
  const node = $("toast");
  node.textContent = message;
  node.className = bad ? "show bad" : "show";
  clearTimeout(node._timer);
  node._timer = setTimeout(() => { node.className = ""; }, 4000);
}
function esc(value) {
  const node = document.createElement("span");
  node.textContent = value === undefined || value === null ? "" : String(value);
  return node.innerHTML;
}
function fileUrl(path) {
  return `/api/file?${new URLSearchParams({ token: state.token, path })}`;
}
function percent(value) { return `${(Number(value || 0) * 100).toFixed(1)}%`; }
function statusPill(status) {
  const key = String(status || "").toLowerCase();
  return status ? `<span class="pill ${key}">${esc(status)}</span>` : "";
}
function stamp(value) { return String(value || "").replace("T", " ").slice(0, 16); }

function setDirty(value) {
  state.dirty = Boolean(value);
  document.body.classList.toggle("dirty", state.dirty);
}

/* Ask before losing work. Returns a promise resolving to true when it is safe. */
function guard() {
  if (!state.dirty || !state.module) return Promise.resolve(true);
  return new Promise(resolve => {
    const dialog = $("unsavedDialog");
    const identity = `${$("idMemberType").value} ${$("idMemberNumber").value}`.trim();
    $("unsavedMessage").textContent =
      `You have unsaved changes to ${identity || "this calculation"}.`;
    const finish = async choice => {
      dialog.close();
      if (choice === "save") {
        try { await saveCalculation(); resolve(true); } catch { resolve(false); }
        return;
      }
      if (choice === "discard") setDirty(false);
      resolve(choice === "discard");
    };
    $("unsavedSave").onclick = () => finish("save");
    $("unsavedDiscard").onclick = () => finish("discard");
    $("unsavedCancel").onclick = () => finish("cancel");
    dialog.showModal();
  });
}
window.addEventListener("beforeunload", event => {
  if (!state.dirty) return;
  event.preventDefault();
  event.returnValue = "";
});

/* --------------------------------------------------------------- sign in */
async function loadAuthConfig() {
  const data = await fetch("/api/auth/config").then(response => response.json());
  state.people = data.people || [];
  $("versionTag").textContent = data.version;
  const sso = data.sso || {};
  $("signInMode").textContent = sso.note || "";
  $("devSignIn").hidden = Boolean(sso.enabled);
  $("ssoSignIn").hidden = !sso.enabled;
  $("signInDialog").showModal();
}
async function signIn(event) {
  event.preventDefault();
  try {
    const data = await api("/api/auth/signin", {
      email: $("signInEmail").value, fullName: $("signInName").value,
      initials: $("signInInitials").value
    });
    state.token = data.token;
    state.user = data.user;
    state.people = data.people;
    $("currentUser").textContent = `${data.user.displayName} (${data.user.initials})`;
    $("signInDialog").close();
    await Promise.all([loadModules(), loadProjects()]);
    showView("library");
  } catch (error) { $("signInError").textContent = error.message; }
}
async function startSso() {
  try {
    const data = await get("/auth/sso/start");
    location.href = data.url;
  } catch (error) { $("ssoError").textContent = error.message; }
}

/* --------------------------------------------------------------- projects */
function projectLabel(item) {
  const name = [item.code, item.clientRef, item.projectName].filter(Boolean).join(" - ");
  return name || item.folderName || item.folderPath;
}
function renderProjectSelect() {
  const group = (label, list) => list.length
    ? `<optgroup label="${label}">${list.map(item =>
        `<option value="${esc(item.id)}">${esc(projectLabel(item))}${item.role ? ` (${esc(item.role)})` : ""}</option>`
      ).join("")}</optgroup>` : "";
  const active = state.projects.filter(item => !item.archived);
  const archived = state.projects.filter(item => item.archived);
  $("projectSelect").innerHTML =
    `<option value="">${state.project ? "Switch project..." : "No project open"}</option>`
    + group("Active", active) + group("Archived", archived);
  $("projectSelect").value = state.project ? state.project.id : "";
}
function renderProjectList() {
  const rows = state.projects.map(item => `
    <tr data-project="${esc(item.id)}">
      <td>${esc(projectLabel(item))}${item.exists ? "" : ' <span class="pill fail">missing</span>'}</td>
      <td class="muted">${esc(item.folderPath)}</td>
      <td class="nowrap">${esc(item.role || "")}</td>
      <td class="nowrap">${esc(stamp(item.lastOpened))}</td>
      <td class="row-actions">
        <button data-open="${esc(item.id)}">Open</button>
        <button data-archive="${esc(item.id)}">${item.archived ? "Restore" : "Archive"}</button>
        <button data-forget="${esc(item.id)}" class="danger" title="Remove from your list only">Remove</button>
      </td>
    </tr>`).join("");
  $("projectList").innerHTML = rows
    ? `<table class="data"><thead><tr><th>Project</th><th>Folder</th><th>Role</th><th>Last opened</th><th></th></tr></thead><tbody>${rows}</tbody></table>`
    : '<p class="empty-state">No projects yet. Add one below.</p>';
  $("projectList").querySelectorAll("[data-open]").forEach(button =>
    button.onclick = () => openProject(button.dataset.open).then(() => $("projectsDialog").close()));
  $("projectList").querySelectorAll("[data-archive]").forEach(button =>
    button.onclick = () => archiveProject(button.dataset.archive));
  $("projectList").querySelectorAll("[data-forget]").forEach(button =>
    button.onclick = () => forgetProject(button.dataset.forget));
}
async function loadProjects() {
  const data = await get("/api/projects");
  state.projects = data.projects || [];
  state.people = data.people || state.people;
  renderProjectSelect();
  renderProjectList();
  showDiscovery(data.discovery);
}
function showDiscovery(discovery) {
  if (!discovery) return;
  const parts = [`${discovery.folders} folder(s) indexed`];
  if (discovery.scanning) parts.push("scanning the drive...");
  else if (discovery.scannedAt) parts.push(`last scan ${stamp(discovery.scannedAt)}`);
  if (!discovery.rootExists) parts.push(`root not reachable: ${discovery.root}`);
  $("discoveryStatus").textContent = parts.join(" | ");
}
async function openProject(projectId) {
  if (!await guard()) return;
  try {
    const data = await api("/api/projects/open", { projectId });
    state.project = data.project;
    state.projects = data.projects;
    state.library = data.library;
    state.qa = data.qa || [];
    state.meta = data.meta;
    setDirty(false);
    state.calculationId = "";
    renderProjectSelect();
    renderProjectList();
    renderLibrary();
    renderTree();
    applyProjectMeta();
    toast(`Opened ${projectLabel(data.project)}`);
  } catch (error) { toast(error.message, true); }
}
function applyProjectMeta() {
  if (!state.meta) return;
  if ($("idDesigner")) $("idDesigner").value = state.meta.designer || "";
}
async function archiveProject(projectId) {
  const project = state.projects.find(item => item.id === projectId);
  try {
    const data = await api("/api/projects/archive", { projectId, archived: !project.archived });
    state.projects = data.projects;
    renderProjectSelect();
    renderProjectList();
  } catch (error) { toast(error.message, true); }
}
async function forgetProject(projectId) {
  if (!confirm("Remove this project from your list? The folder and its calculations are not touched.")) return;
  try {
    const data = await api("/api/projects/forget", { projectId });
    state.projects = data.projects;
    if (state.project && state.project.id === projectId) state.project = null;
    renderProjectSelect();
    renderProjectList();
  } catch (error) { toast(error.message, true); }
}
async function findProject() {
  const code = $("findCode").value.trim();
  if (!code) return;
  $("findResults").innerHTML = '<p class="muted">Looking&hellip;</p>';
  try {
    const data = await api("/api/projects/find", { code });
    if (!data.matches.length) {
      $("findResults").innerHTML = data.scanning
        ? '<p class="notice">Not in the index yet. A background scan has started - try again shortly, or add the folder below.</p>'
        : '<p class="notice">No folder found for that number. Add it below.</p>';
      return;
    }
    $("findResults").innerHTML = `<table class="data"><tbody>${data.matches.map(item => `
      <tr><td>${esc(projectLabel(item))}</td><td class="muted">${esc(item.folderPath)}</td>
      <td><button data-add="${esc(item.folderPath)}">Add and open</button></td></tr>`).join("")}</tbody></table>`;
    $("findResults").querySelectorAll("[data-add]").forEach(button =>
      button.onclick = () => addProject(button.dataset.add, true));
  } catch (error) { $("findResults").innerHTML = `<p class="error">${esc(error.message)}</p>`; }
}
async function addProject(path, openAfter) {
  $("projectsError").textContent = "";
  try {
    const data = await api("/api/projects/create", {
      path: path || $("newProjectPath").value.trim(),
      code: $("newProjectCode").value.trim(),
      clientRef: $("newProjectClient").value.trim(),
      projectName: $("newProjectName").value.trim(),
      createFolders: $("newProjectCreate").checked
    });
    state.projects = data.projects;
    renderProjectSelect();
    renderProjectList();
    toast(`Added ${projectLabel(data.project)}`);
    if (openAfter !== false) {
      await openProject(data.project.id);
      $("projectsDialog").close();
    }
  } catch (error) { $("projectsError").textContent = error.message; }
}
async function pickFolder(target, mode) {
  try {
    const data = await get("/api/pick", mode === "file"
      ? { mode: "file", title: "Select a PDF" } : { title: "Select project folder" });
    if (!data.path) return;
    $(target).value = data.path;
    if (target === "newProjectPath") {
      const parts = (data.path.split(/[\\/]/).pop() || "").split(" - ");
      $("newProjectCode").value = parts[0] || "";
      $("newProjectClient").value = parts[1] || "";
      $("newProjectName").value = parts.slice(2).join(" - ");
    }
  } catch (error) { toast(error.message, true); }
}

/* ---------------------------------------------------------------- modules */
async function loadModules() {
  const data = await api("/api/modules", null, "GET");
  state.modules = data.modules || [];
  (data.problems || []).forEach(problem =>
    toast(`Module ${problem.entry} did not load: ${problem.error}`, true));
  $("libraryModule").innerHTML = '<option value="">All</option>'
    + state.modules.map(item => `<option value="${esc(item.id)}">${esc(item.name)}</option>`).join("");
  $("moduleCards").innerHTML = state.modules.map(item => `
    <button class="module-card" data-module="${esc(item.id)}" type="button">
      <b>${esc(item.name)}</b><small>${esc(item.standard)} &middot; ${esc(item.version)}</small>
      <p>${esc(item.description)}</p></button>`).join("");
  $("moduleCards").querySelectorAll("[data-module]").forEach(card =>
    card.onclick = () => { $("moduleDialog").close(); newCalculation(card.dataset.module); });
}

/* ------------------------------------------------- schema driven input form */
function fieldVisible(field) {
  if (!field.showWhen) return true;
  return Object.entries(field.showWhen).every(([key, values]) => {
    const control = state.fields.find(item => item.id === key);
    return control && values.includes(String(control.el.value));
  });
}
function syncVisibility() {
  state.fields.forEach(field => {
    if (!field.wrapper) return;
    field.wrapper.hidden = !fieldVisible(field.definition);
  });
}
function optionsHtml(list, current) {
  return (list || []).map(option => {
    const value = typeof option === "string" ? option : option.value;
    const label = typeof option === "string" ? option : option.label;
    return `<option value="${esc(value)}"${String(value) === String(current) ? " selected" : ""}>${esc(label)}</option>`;
  }).join("");
}
function buildField(field, value) {
  const wrapper = document.createElement("label");
  wrapper.className = field.width === "full" || field.type === "checkbox" ? "wide" : "";
  const unit = field.unit ? ` <small class="muted">${esc(field.unit)}</small>` : "";
  if (field.type === "checkbox") {
    wrapper.className = "check wide";
    wrapper.innerHTML = `<input type="checkbox" id="f_${esc(field.id)}"${value ? " checked" : ""}> ${esc(field.label)}`;
  } else if (field.type === "select" || field.type === "catalogue") {
    wrapper.innerHTML = `<span>${esc(field.label)}${unit}</span><select id="f_${esc(field.id)}"></select>`;
  } else if (field.type === "textarea") {
    wrapper.innerHTML = `<span>${esc(field.label)}${unit}</span><textarea id="f_${esc(field.id)}" rows="3">${esc(value)}</textarea>`;
  } else {
    const type = field.type === "number" ? "number" : "text";
    const step = field.type === "number" ? ' step="any"' : "";
    wrapper.innerHTML = `<span>${esc(field.label)}${unit}</span><input id="f_${esc(field.id)}" type="${type}"${step} value="${esc(value)}">`;
  }
  const el = wrapper.querySelector("input,select,textarea");
  if (field.type === "select") el.innerHTML = optionsHtml(field.options, value);
  if (field.type === "catalogue") el.dataset.catalogue = field.catalogue;
  if (field.help) wrapper.title = field.help;
  // Catalogue options arrive after the dependent field exists, so remember the
  // value the calculation was saved with until the list can be built.
  state.fields.push({ id: field.id, definition: field, el, wrapper, pending: String(value ?? "") });
  el.addEventListener("input", onInputChanged);
  el.addEventListener("change", onInputChanged);
  return wrapper;
}
function refreshCatalogues() {
  state.fields.filter(field => field.definition.type === "catalogue").forEach(field => {
    const source = (state.schema.catalogues || {})[field.definition.catalogue] || {};
    const keyField = state.fields.find(item => item.id === field.definition.optionsBy);
    const list = Array.isArray(source) ? source : (source[keyField ? keyField.el.value : ""] || []);
    const wanted = field.el.value || field.pending;
    field.el.innerHTML = optionsHtml(list, wanted);
    if (list.includes(wanted)) field.el.value = wanted;
    else if (list.length) field.el.value = list[0];
    field.pending = "";
  });
}
function renderSchemaForm(schema, values) {
  state.fields = [];
  state.schema = schema;
  const groups = $("schemaGroups");
  const optional = $("schemaOptional");
  groups.innerHTML = "";
  optional.innerHTML = "";
  (schema.groups || []).forEach(group => {
    const details = document.createElement("details");
    details.open = true;
    details.innerHTML = `<summary>${esc(group.title)}</summary>`;
    const grid = document.createElement("div");
    grid.className = "field-grid";
    group.fields.forEach(field => grid.appendChild(buildField(field, values[field.id] ?? field.default ?? "")));
    details.appendChild(grid);
    groups.appendChild(details);
  });
  (schema.optional || []).forEach(option => {
    const section = document.createElement("section");
    section.className = "optional";
    const enabled = Boolean((values.checks || {})[option.id]);
    section.innerHTML = `<label><input type="checkbox" data-check="${esc(option.id)}"${enabled ? " checked" : ""}> ${esc(option.label)}</label>`;
    const details = document.createElement("details");
    details.dataset.panel = option.id;
    details.open = enabled;
    const grid = document.createElement("div");
    grid.className = "field-grid";
    option.fields.forEach(field => grid.appendChild(buildField(field, values[field.id] ?? field.default ?? "")));
    details.appendChild(grid);
    section.appendChild(details);
    optional.appendChild(section);
  });
  optional.querySelectorAll("[data-check]").forEach(box => {
    box.onchange = () => {
      const panel = optional.querySelector(`[data-panel="${box.dataset.check}"]`);
      if (panel) panel.open = box.checked;
      onInputChanged();
    };
  });
  $("moduleActions").innerHTML = (schema.actions || []).map(action =>
    `<button type="button" data-action="${esc(action.id)}">${esc(action.label)}</button>`).join("")
    + (schema.learning ? '<button type="button" id="showLearning">Jupyter &amp; handcalcs guide</button>' : "");
  $("moduleActions").querySelectorAll("[data-action]").forEach(button =>
    button.onclick = () => runModuleAction(button.dataset.action));
  if ($("showLearning")) $("showLearning").onclick = showLearning;
  refreshCatalogues();
  syncVisibility();
  renderCellEditor(values.cells || []);
}

/* --------------------------------------------------- calculation pad editor */
function renderCellEditor(cells) {
  const host = $("schemaGroups");
  const existing = document.getElementById("padEditor");
  if (existing) existing.remove();
  if (!state.schema || state.schema.editor !== "cells") { state.cells = []; return; }
  state.cells = cells.map((cell, index) => ({ id: cell.id || `c${index + 1}`, ...cell }));
  const details = document.createElement("details");
  details.id = "padEditor";
  details.open = true;
  details.innerHTML = "<summary>Calculation cells</summary>";
  const list = document.createElement("div");
  list.className = "pad-cells";
  details.appendChild(list);
  const adder = document.createElement("div");
  adder.className = "pad-add";
  adder.innerHTML = (state.schema.cellTypes || []).map(type =>
    `<button type="button" data-add-cell="${esc(type.id)}">+ ${esc(type.label)}</button>`).join("");
  details.appendChild(adder);
  host.appendChild(details);
  adder.querySelectorAll("[data-add-cell]").forEach(button =>
    button.onclick = () => {
      state.cells.push({ id: `c${Date.now().toString(36)}`, type: button.dataset.addCell, title: "", source: "" });
      renderCellEditor(state.cells);
      onInputChanged();
    });
  drawCells(list);
}
function drawCells(list) {
  list.innerHTML = "";
  state.cells.forEach((cell, index) => {
    const node = document.createElement("div");
    node.className = "pad-cell";
    const types = (state.schema.cellTypes || []).map(type =>
      `<option value="${esc(type.id)}"${type.id === cell.type ? " selected" : ""}>${esc(type.label)}</option>`).join("");
    node.innerHTML = `
      <header>
        <select data-cell-type>${types}</select>
        <input data-cell-title placeholder="Title" value="${esc(cell.title || "")}">
        <button type="button" data-cell-up title="Move up">&uarr;</button>
        <button type="button" data-cell-down title="Move down">&darr;</button>
        <button type="button" data-cell-remove title="Delete">&times;</button>
      </header>`;
    if (cell.type === "calc" || cell.type === "text") {
      const area = document.createElement("textarea");
      area.value = cell.source || "";
      area.placeholder = cell.type === "calc"
        ? "w = 5.0    # kN/m\nL = 6.0    # m\nM = w * L^2 / 8   # kNm"
        : "Design intent, assumptions and references";
      area.addEventListener("input", () => { cell.source = area.value; onInputChanged(); });
      node.appendChild(area);
    } else if (cell.type === "pdf") {
      const meta = document.createElement("div");
      meta.className = "pad-meta";
      meta.innerHTML = `<input data-cell-path placeholder="PDF path" value="${esc(cell.path || "")}" style="flex:1">
        <input data-cell-pages placeholder="pages e.g. 1,3-5" value="${esc(cell.pages || "")}" style="width:130px">
        <button type="button" data-cell-browse>Browse</button>`;
      node.appendChild(meta);
      meta.querySelector("[data-cell-path]").addEventListener("input", event => { cell.path = event.target.value; onInputChanged(); });
      meta.querySelector("[data-cell-pages]").addEventListener("input", event => { cell.pages = event.target.value; onInputChanged(); });
      meta.querySelector("[data-cell-browse]").onclick = async () => {
        const data = await get("/api/pick", { mode: "file", title: "Select a PDF drawing or markup" });
        if (data.path) { cell.path = data.path; renderCellEditor(state.cells); onInputChanged(); }
      };
    } else if (cell.type === "blank") {
      const meta = document.createElement("div");
      meta.className = "pad-meta";
      meta.innerHTML = `<select data-cell-size>
        <option value="A4"${cell.size === "A3" ? "" : " selected"}>A4</option>
        <option value="A3"${cell.size === "A3" ? " selected" : ""}>A3</option></select>`;
      node.appendChild(meta);
      meta.querySelector("[data-cell-size]").addEventListener("change", event => { cell.size = event.target.value; onInputChanged(); });
    } else if (cell.type === "image") {
      const meta = document.createElement("div");
      meta.className = "pad-meta";
      meta.innerHTML = '<input type="file" accept="image/*" data-cell-image>';
      node.appendChild(meta);
      meta.querySelector("[data-cell-image]").addEventListener("change", event => {
        const file = event.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = () => { cell.data = reader.result; onInputChanged(); };
        reader.readAsDataURL(file);
      });
    }
    node.querySelector("[data-cell-type]").onchange = event => {
      cell.type = event.target.value; renderCellEditor(state.cells); onInputChanged();
    };
    node.querySelector("[data-cell-title]").addEventListener("input", event => { cell.title = event.target.value; onInputChanged(); });
    node.querySelector("[data-cell-up]").onclick = () => moveCell(index, -1);
    node.querySelector("[data-cell-down]").onclick = () => moveCell(index, 1);
    node.querySelector("[data-cell-remove]").onclick = () => {
      state.cells.splice(index, 1); renderCellEditor(state.cells); onInputChanged();
    };
    list.appendChild(node);
  });
}
function moveCell(index, delta) {
  const target = index + delta;
  if (target < 0 || target >= state.cells.length) return;
  const [cell] = state.cells.splice(index, 1);
  state.cells.splice(target, 0, cell);
  renderCellEditor(state.cells);
  onInputChanged();
}
function showLearning() {
  const items = (state.schema.learning || []).map(item =>
    `<li><a href="${esc(item.url)}" target="_blank" rel="noopener">${esc(item.title)}</a><span>${esc(item.note)}</span></li>`).join("");
  $("learningBody").innerHTML = `
    <p>The pad evaluates a restricted arithmetic subset of Python and prints each line the way a
    hand calculation reads: the symbolic expression, the substituted values, then the result.
    Use <code>^</code> or <code>**</code> for powers, <code>_</code> for subscripts
    (<code>M_x</code>), and a trailing <code>#&nbsp;kNm</code> comment for units.</p>
    <p>Available functions: <code>${esc((state.schema.functions || []).join(", "))}</code></p>
    <h3>Learning and reference</h3><ul class="learning">${items}</ul>`;
  $("learningDialog").showModal();
}

/* -------------------------------------------------------- inputs and report */
function readInputs() {
  const values = { ...state.inputs, ...(state.meta || {}) };
  state.fields.forEach(field => {
    const el = field.el;
    if (field.definition.type === "checkbox") values[field.id] = el.checked;
    else if (field.definition.type === "number") values[field.id] = Number(el.value || 0);
    else values[field.id] = el.value;
  });
  values.checks = {};
  document.querySelectorAll("#schemaOptional [data-check]").forEach(box => {
    values.checks[box.dataset.check] = box.checked;
  });
  Object.assign(values.checks, (state.schema && state.schema.alwaysOn) || {});
  values.memberType = $("idMemberType").value.trim();
  values.memberNumber = $("idMemberNumber").value.trim();
  values.package = $("idPackage").value.trim() || "Unallocated";
  values.level = $("idLevel").value.trim();
  values.subject = $("idSubject").value.trim();
  values.checker = $("idChecker").value.trim();
  values.designer = $("idDesigner").value.trim();
  if (state.schema && state.schema.editor === "cells") values.cells = state.cells;
  return values;
}
function applyIdentity(values, schema) {
  $("identityTypeLabel").firstChild.textContent = (schema.identity && schema.identity.typeLabel) || "Type";
  $("identityNumberLabel").firstChild.textContent = (schema.identity && schema.identity.numberLabel) || "Number";
  $("idMemberTypes").innerHTML = ((schema.identity && schema.identity.typeOptions) || [])
    .map(item => `<option value="${esc(item)}">`).join("");
  $("idMemberType").value = values.memberType || "";
  $("idMemberNumber").value = values.memberNumber || "";
  $("idPackage").value = values.package || "Unallocated";
  $("idLevel").value = values.level || "";
  $("idSubject").value = values.subject || schema.defaultSubject || "";
  $("idChecker").value = values.checker || "";
  $("idDesigner").value = values.designer || (state.user ? state.user.initials : "");
  const library = state.library || {};
  $("idPackages").innerHTML = (library.packages || []).map(item => `<option value="${esc(item)}">`).join("");
  $("idLevels").innerHTML = (library.levels || []).map(item => `<option value="${esc(item)}">`).join("");
}
function onInputChanged() {
  setDirty(true);
  syncVisibility();
  refreshCatalogues();
  scheduleCalculation();
}
function scheduleCalculation() {
  clearTimeout(state.timer);
  $("calcState").textContent = "Pending";
  state.timer = setTimeout(calculate, 220);
}
async function calculate() {
  if (!state.module) return;
  const request = ++state.request;
  $("calcState").textContent = "Calculating...";
  try {
    const data = await api("/api/calculate", { module: state.module.id, inputs: readInputs() });
    if (request !== state.request) return;
    $("reportPane").innerHTML = data.reportHtml;
    $("calcState").textContent = data.summary.headline || "Current";
    $("moduleBadge").textContent = `${state.module.name} ${state.module.version} | ${data.summary.headline || ""}`;
  } catch (error) {
    $("calcState").textContent = "Error";
    $("reportPane").innerHTML = `<div class="empty">${esc(error.message)}</div>`;
  }
}
async function newCalculation(moduleId) {
  if (!await guard()) return;
  try {
    const data = await get("/api/module/schema", { module: moduleId });
    state.module = state.modules.find(item => item.id === moduleId);
    state.calculationId = "";
    state.inputs = {};
    const values = { ...data.defaults, designer: state.user.initials };
    renderSchemaForm(data.schema, values);
    applyIdentity(values, data.schema);
    $("inputTitle").textContent = data.schema.name;
    setDirty(false);
    showView("calculation");
    calculate();
  } catch (error) { toast(error.message, true); }
}
async function openCalculation(calculationId) {
  if (!state.project) return toast("Open a project first", true);
  if (!await guard()) return;
  try {
    const record = (await get("/api/calculation", { project: state.project.id, id: calculationId })).calculation;
    const data = await get("/api/module/schema", { module: record.module });
    state.module = state.modules.find(item => item.id === record.module);
    state.calculationId = record.id;
    state.inputs = { ...record.inputs };
    renderSchemaForm(data.schema, record.inputs);
    applyIdentity(record.inputs, data.schema);
    $("inputTitle").textContent = `${data.schema.name} - rev ${record.revisions.length}`;
    setDirty(false);
    showView("calculation");
    renderTree();
    calculate();
  } catch (error) { toast(error.message, true); }
}
async function saveCalculation(supersede = true) {
  if (!state.project) { toast("Open a project before saving", true); throw new Error("no project"); }
  if (!state.module) throw new Error("no module");
  const identity = `${$("idMemberType").value.trim()}`;
  if (!identity) { toast("Give the calculation a type", true); throw new Error("no type"); }
  $("saveCalculation").disabled = true;
  try {
    const data = await api("/api/calculation/save", {
      projectId: state.project.id, module: state.module.id, inputs: readInputs(),
      calculationId: state.calculationId, supersede, meta: { checker: $("idChecker").value }
    });
    if (data.conflict) {
      $("saveCalculation").disabled = false;
      if (confirm("A calculation with this type and number already exists. Supersede it?")) {
        return saveCalculation(true);
      }
      throw new Error("save cancelled");
    }
    state.calculationId = data.calculationId;
    state.library = data.library;
    setDirty(false);
    renderLibrary();
    renderTree();
    toast(data.pdf ? "Saved with PDF" : `Saved (PDF not produced: ${data.pdfError || "unknown"})`);
    return data;
  } catch (error) {
    toast(error.message, true);
    throw error;
  } finally { $("saveCalculation").disabled = false; }
}
async function runModuleAction(actionId) {
  try {
    const data = await api("/api/module/action", {
      module: state.module.id, action: actionId, inputs: readInputs()
    });
    if (data.inputs) {
      renderSchemaForm(state.schema, data.inputs);
      applyIdentity(data.inputs, state.schema);
      setDirty(true);
      calculate();
    }
    if (data.file) {
      const blob = new Blob([data.file.content], { type: data.file.type });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = data.file.name;
      link.click();
      URL.revokeObjectURL(link.href);
    }
    if (data.message) toast(data.message);
  } catch (error) { toast(error.message, true); }
}

/* ---------------------------------------------------------------- library */
function moduleName(id) {
  const module = state.modules.find(item => item.id === id);
  return module ? module.short || module.name : id;
}
async function refreshLibrary() {
  if (!state.project) return;
  try {
    const data = await get("/api/library", {
      project: state.project.id,
      showSuperseded: $("libraryShowSuperseded").checked ? "1" : "0",
      search: $("librarySearch").value.trim(),
      package: $("libraryPackage").value,
      level: $("libraryLevel").value,
      module: $("libraryModule").value,
      calcType: $("libraryCalcType").value
    });
    state.library = data.library;
    renderLibrary(true);
  } catch (error) { toast(error.message, true); }
}
function fillFilter(select, values, keep) {
  const current = keep ? select.value : "";
  select.innerHTML = '<option value="">All</option>'
    + values.map(item => `<option value="${esc(item)}">${esc(item)}</option>`).join("");
  select.value = current;
}
function renderLibrary(keepFilters) {
  const library = state.library;
  if (!library) return;
  fillFilter($("libraryPackage"), library.packages || [], keepFilters);
  fillFilter($("libraryLevel"), library.levels || [], keepFilters);
  fillFilter($("libraryCalcType"), library.calcTypes || [], keepFilters);
  fillFilter($("pkgPackage"), library.packages || [], true);
  fillFilter($("pkgLevel"), library.levels || [], true);
  fillFilter($("pkgCalcType"), library.calcTypes || [], true);
  fillFilter($("pkgMemberType"), library.memberTypes || [], true);
  const rows = (library.calculations || []).map(record => {
    const latest = record.revisions[record.revisions.length - 1] || {};
    const over = Number(record.worstUtil || 0) > 1;
    return `<tr${latest.superseded ? ' class="superseded"' : ""}>
      <td>${esc(record.package)}</td>
      <td>${esc(record.level)}</td>
      <td>${esc(moduleName(record.module))}</td>
      <td>${esc(record.memberType)}</td>
      <td>${esc(record.memberNumber)}</td>
      <td>${esc(record.title)}</td>
      <td class="nowrap">${statusPill(record.status)} <span class="util${over ? " over" : ""}">${percent(record.worstUtil)}</span></td>
      <td>${esc(record.criticalCheck)}</td>
      <td class="nowrap">rev ${esc(latest.rev || record.revisions.length)} ${esc(stamp(latest.savedAt))} ${esc(latest.initials || "")}</td>
      <td class="nowrap"><input type="checkbox" data-final="${esc(record.id)}"${record.finalised ? " checked" : ""} title="Finalised"></td>
      <td class="row-actions">
        <button data-open-calc="${esc(record.id)}">Open</button>
        ${latest.relativePath ? `<button data-pdf="${esc(record.id)}">PDF</button>` : ""}
        <button data-link="${esc(record.id)}" title="Send these values into another calculation">Link</button>
        <button data-remove="${esc(record.id)}" class="danger" title="Remove from the library index">Remove</button>
      </td></tr>`;
  }).join("");
  $("libraryTable").innerHTML = rows
    ? `<table class="data"><thead><tr><th>Package</th><th>Level</th><th>Module</th><th>Type</th>
       <th>No.</th><th>Title</th><th>Status</th><th>Governing check</th><th>Latest revision</th>
       <th>Final</th><th></th></tr></thead><tbody>${rows}</tbody></table>`
    : '<p class="empty-state">No calculations yet. Choose <b>New calculation</b> to start one.</p>';
  $("libraryTable").querySelectorAll("[data-open-calc]").forEach(button =>
    button.onclick = () => openCalculation(button.dataset.openCalc));
  $("libraryTable").querySelectorAll("[data-pdf]").forEach(button =>
    button.onclick = () => openPdf(button.dataset.pdf));
  $("libraryTable").querySelectorAll("[data-final]").forEach(box =>
    box.onchange = () => updateCalculation(box.dataset.final, { finalised: box.checked }));
  $("libraryTable").querySelectorAll("[data-remove]").forEach(button =>
    button.onclick = () => removeCalculation(button.dataset.remove));
  $("libraryTable").querySelectorAll("[data-link]").forEach(button =>
    button.onclick = () => linkCalculation(button.dataset.link));
}
function openPdf(calculationId) {
  const record = (state.library.calculations || []).find(item => item.id === calculationId);
  const latest = record.revisions[record.revisions.length - 1];
  const path = `${state.library.toolFolder}\\${latest.relativePath}`.replace(/\.html$/i, ".pdf");
  window.open(fileUrl(path), "_blank");
}
async function updateCalculation(id, fields) {
  try {
    const data = await api("/api/calculation/update", { projectId: state.project.id, id, fields });
    state.library = data.library;
    renderLibrary(true);
  } catch (error) { toast(error.message, true); }
}
async function removeCalculation(id) {
  if (!confirm("Remove this calculation from the library index? The saved files stay on the drive.")) return;
  try {
    const data = await api("/api/calculation/delete", { projectId: state.project.id, id });
    state.library = data.library;
    renderLibrary(true);
    renderTree();
  } catch (error) { toast(error.message, true); }
}
async function linkCalculation(sourceId) {
  const choices = state.modules.map((item, index) => `${index + 1}. ${item.name}`).join("\n");
  const answer = prompt(`Send these values into which module?\n${choices}`, "1");
  const module = state.modules[Number(answer) - 1];
  if (!module) return;
  if (!await guard()) return;
  try {
    const schema = await get("/api/module/schema", { module: module.id });
    const data = await api("/api/calculation/exchange", {
      projectId: state.project.id, sourceId, targetModule: module.id, inputs: schema.defaults
    });
    state.module = module;
    state.calculationId = "";
    state.inputs = {};
    renderSchemaForm(schema.schema, data.inputs);
    applyIdentity(data.inputs, schema.schema);
    setDirty(true);
    showView("calculation");
    calculate();
    toast(`Values linked into ${module.name}`);
  } catch (error) { toast(error.message, true); }
}
function renderTree() {
  const library = state.library;
  if (!library) return;
  const grouped = {};
  (library.calculations || []).forEach(record => {
    ((grouped[record.package] ??= {})[record.memberType] ??= []).push(record);
  });
  const html = Object.entries(grouped).map(([pkg, types]) => `
    <details open><summary>${esc(pkg)}</summary>${Object.entries(types).map(([type, records]) => `
      <details open><summary>${esc(type)}</summary>${records.map(record =>
        `<button data-tree="${esc(record.id)}" class="${record.id === state.calculationId ? "selected" : ""}">
          ${esc(record.memberNumber || record.title)}</button>`).join("")}</details>`).join("")}</details>`).join("");
  $("calcTree").innerHTML = html || '<p class="muted">No calculations saved yet.</p>';
  $("calcTree").querySelectorAll("[data-tree]").forEach(button =>
    button.onclick = () => openCalculation(button.dataset.tree));
}

/* --------------------------------------------------------- package export */
function fillSortSelects() {
  const fields = state.sortFields || [];
  ["pkgSort1", "pkgSort2", "pkgSort3"].forEach((id, index) => {
    const select = $(id);
    const current = select.value;
    select.innerHTML = '<option value="">-</option>'
      + fields.map(field => `<option value="${esc(field.id)}">${esc(field.label)}</option>`).join("");
    select.value = current || ["package", "level", "memberType"][index] || "";
  });
}
function sortOrder() {
  return ["pkgSort1", "pkgSort2", "pkgSort3"].map(id => $(id).value).filter(Boolean);
}
async function refreshPackage() {
  if (!state.project) return;
  try {
    const data = await api("/api/package/preview", {
      projectId: state.project.id,
      filters: {
        package: $("pkgPackage").value, level: $("pkgLevel").value,
        memberType: $("pkgMemberType").value, calcType: $("pkgCalcType").value,
        finalisedOnly: $("pkgFinalisedOnly").checked
      },
      sort: sortOrder()
    });
    state.sortFields = data.sortFields;
    state.packageEntries = data.entries;
    fillSortSelects();
    renderPackage();
  } catch (error) { toast(error.message, true); }
}
function renderPackage() {
  const rows = state.packageEntries.map(entry => `
    <tr><td><input type="checkbox" data-pick="${esc(entry.id)}"${state.packageSelection.has(entry.id) ? " checked" : ""}></td>
      <td>${esc(entry.package)}</td><td>${esc(entry.level)}</td>
      <td>${esc(entry.calcType)}</td><td>${esc(entry.memberType)}</td>
      <td>${esc(entry.memberNumber)}</td><td>${esc(entry.title)}</td>
      <td class="nowrap">${statusPill(entry.status)} ${percent(entry.worstUtil)}</td>
      <td>${entry.finalised ? "Yes" : ""}</td>
      <td class="nowrap">rev ${esc(entry.revision)} ${esc(stamp(entry.savedAt))}</td></tr>`).join("");
  $("packageTable").innerHTML = rows
    ? `<table class="data"><thead><tr><th></th><th>Package</th><th>Level</th><th>Type</th>
       <th>Member</th><th>No.</th><th>Title</th><th>Status</th><th>Final</th><th>Revision</th>
       </tr></thead><tbody>${rows}</tbody></table>`
    : '<p class="empty-state">Nothing matches these filters.</p>';
  $("packageTable").querySelectorAll("[data-pick]").forEach(box =>
    box.onchange = () => {
      if (box.checked) state.packageSelection.add(box.dataset.pick);
      else state.packageSelection.delete(box.dataset.pick);
      $("qaSelectionCount").textContent = `${state.packageSelection.size} selected.`;
    });
  $("qaSelectionCount").textContent = `${state.packageSelection.size} selected.`;
}
async function buildPackage() {
  if (!state.packageSelection.size) return toast("Select at least one calculation", true);
  $("packageBuild").disabled = true;
  toast("Building the package; this can take a moment.");
  try {
    const data = await api("/api/package/build", {
      projectId: state.project.id,
      selection: [...state.packageSelection],
      sort: sortOrder(),
      meta: { title: $("pkgTitle").value.trim() || "Calculation package" },
      drawings: $("pkgDrawings").value.trim() ? [{ path: $("pkgDrawings").value.trim() }] : []
    });
    toast(`${data.sheets} sheet(s) exported${data.attachments ? ` plus ${data.attachments} attachment(s)` : ""}`);
    window.open(data.url, "_blank");
  } catch (error) { toast(error.message, true); }
  finally { $("packageBuild").disabled = false; }
}

/* ------------------------------------------------------------------ QA */
async function refreshQa() {
  if (!state.project) return;
  try {
    const data = await get("/api/qa", { project: state.project.id });
    state.qa = data.packages || [];
    state.qaTemplate = data.template;
    renderQa();
  } catch (error) { toast(error.message, true); }
}
function renderQa() {
  const rows = state.qa.map(item => {
    const open = (item.comments || []).filter(comment => comment.status === "Open").length;
    const deferred = (item.comments || []).filter(comment => comment.status === "Deferred").length;
    return `<tr>
      <td>${esc(item.ref)}</td><td>${esc(item.title)}</td>
      <td>${esc(item.reviewer)}</td><td>${esc(item.date)}</td>
      <td>${esc(item.status)}</td>
      <td class="nowrap">${open} open / ${deferred} deferred / ${(item.comments || []).length} total</td>
      <td class="row-actions">
        <button data-qa-open="${esc(item.id)}">Register</button>
        <button data-qa-pdf="${esc(item.id)}">Calculations</button>
        <button data-qa-form="${esc(item.id)}">Form</button>
      </td></tr>`;
  }).join("");
  $("qaList").innerHTML = rows
    ? `<table class="data"><thead><tr><th>Ref</th><th>Title</th><th>Verifier</th><th>Date</th>
       <th>Status</th><th>Comments</th><th></th></tr></thead><tbody>${rows}</tbody></table>`
    : '<p class="empty-state">No verification packages yet.</p>';
  $("qaList").querySelectorAll("[data-qa-open]").forEach(button =>
    button.onclick = () => showQaPackage(button.dataset.qaOpen));
  $("qaList").querySelectorAll("[data-qa-pdf]").forEach(button => {
    const item = state.qa.find(entry => entry.id === button.dataset.qaPdf);
    button.onclick = () => window.open(fileUrl(item.calculationPdf), "_blank");
  });
  $("qaList").querySelectorAll("[data-qa-form]").forEach(button => {
    const item = state.qa.find(entry => entry.id === button.dataset.qaForm);
    button.onclick = () => window.open(fileUrl(`${item.folder}\\Verification Form.html`), "_blank");
  });
}
function showQaPackage(packageId) {
  const item = state.qa.find(entry => entry.id === packageId);
  if (!item) return;
  state.qaPackage = packageId;
  const statuses = (state.qaTemplate && state.qaTemplate.statuses) || ["Open", "Closed"];
  const rows = (item.comments || []).map(comment => `
    <tr data-comment="${esc(comment.id)}">
      <td class="nowrap">${esc(comment.ref)}${comment.carriedFrom ? `<br><small class="muted">from ${esc(comment.carriedFrom)}</small>` : ""}</td>
      <td class="nowrap">${esc(comment.source || "")}${comment.page ? ` p${esc(comment.page)}` : ""}<br><small class="muted">${esc(comment.author || "")}</small></td>
      <td><textarea data-field="comment" rows="2">${esc(comment.comment)}</textarea></td>
      <td><textarea data-field="response" rows="2">${esc(comment.response)}</textarea></td>
      <td><textarea data-field="agreedOutcome" rows="2">${esc(comment.agreedOutcome)}</textarea></td>
      <td class="nowrap"><select data-field="status">${statuses.map(status =>
        `<option${status === comment.status ? " selected" : ""}>${esc(status)}</option>`).join("")}</select>
        <input data-field="deferredTo" placeholder="deferred to" value="${esc(comment.deferredTo || "")}"></td>
      <td><button data-save-comment="${esc(comment.id)}">Save</button></td>
    </tr>`).join("");
  const endorsed = item.endorsed;
  const actions = (state.qaTemplate && state.qaTemplate.actions) || [];
  $("qaDetailTitle").textContent = `${item.ref} - ${item.title}`;
  $("qaDetail").innerHTML = `
    <div class="filters">
      <label>Import verifier markups (PDF)<span class="row-actions">
        <input id="qaMarkupPath" placeholder="Returned marked-up PDF"><button id="qaPickMarkup" type="button">Browse</button>
        <button id="qaImportMarkup" type="button">Import</button></span></label>
      <label>Add a comment<span class="row-actions">
        <input id="qaNewComment" placeholder="Comment text"><button id="qaAddComment" type="button">Add</button></span></label>
      <label>Endorsement<span class="row-actions">
        <select id="qaAction">${actions.map(action => `<option value="${esc(action.id)}">${esc(action.label)}</option>`).join("")}</select>
        <button id="qaEndorse" class="primary" type="button">Endorse</button>
        <button id="qaExport" type="button">Export form &amp; register</button></span></label>
    </div>
    ${endorsed ? `<p class="notice">Endorsed by ${esc(endorsed.by)} on ${esc(stamp(endorsed.at))}. Final register: ${esc(endorsed.registerFile)}</p>` : ""}
    <label>General comments<textarea id="qaGeneral" rows="2">${esc(item.generalComments || "")}</textarea></label>
    <div class="row-actions"><button id="qaSaveGeneral" type="button">Save general comments</button></div>
    <table class="data"><thead><tr><th>Ref</th><th>Source</th><th>Verifier comment</th>
      <th>Response</th><th>Agreed outcome</th><th>Status</th><th></th></tr></thead>
      <tbody>${rows || '<tr><td colspan="7" class="empty-state">No comments raised yet.</td></tr>'}</tbody></table>`;
  $("qaDetailCard").hidden = false;
  $("qaPickMarkup").onclick = () => pickFolder("qaMarkupPath", "file");
  $("qaImportMarkup").onclick = () => importMarkups(packageId);
  $("qaAddComment").onclick = () => addQaComment(packageId);
  $("qaEndorse").onclick = () => endorseQa(packageId);
  $("qaExport").onclick = () => exportQa(packageId);
  $("qaSaveGeneral").onclick = () => updateQaPackage(packageId, { generalComments: $("qaGeneral").value });
  $("qaDetail").querySelectorAll("[data-save-comment]").forEach(button =>
    button.onclick = () => {
      const row = button.closest("[data-comment]");
      const fields = {};
      row.querySelectorAll("[data-field]").forEach(control => { fields[control.dataset.field] = control.value; });
      updateQaComment(packageId, row.dataset.comment, fields);
    });
}
async function qaCall(path, payload, message) {
  try {
    const data = await api(path, { projectId: state.project.id, ...payload });
    state.qa = state.qa.map(item => item.id === data.package.id ? data.package : item);
    renderQa();
    showQaPackage(data.package.id);
    if (message) toast(typeof message === "function" ? message(data) : message);
  } catch (error) { toast(error.message, true); }
}
const updateQaPackage = (packageId, fields) => qaCall("/api/qa/update", { packageId, fields }, "Saved");
const updateQaComment = (packageId, commentId, fields) =>
  qaCall("/api/qa/comment/update", { packageId, commentId, fields }, "Comment updated");
const importMarkups = packageId =>
  qaCall("/api/qa/markups", { packageId, path: $("qaMarkupPath").value.trim() },
    data => `${data.added} markup comment(s) imported`);
function addQaComment(packageId) {
  const text = $("qaNewComment").value.trim();
  if (!text) return;
  qaCall("/api/qa/comment/add", { packageId, comment: { comment: text } }, "Comment added");
}
const endorseQa = packageId =>
  qaCall("/api/qa/endorse", { packageId, action: $("qaAction").value }, "Package endorsed");
async function exportQa(packageId) {
  try {
    const data = await api("/api/qa/export", { projectId: state.project.id, packageId });
    toast(`Exported ${Object.keys(data.files).join(", ")}`);
  } catch (error) { toast(error.message, true); }
}
function openQaDialog() {
  if (!state.project) return toast("Open a project first", true);
  if (!state.packageSelection.size) return toast("Select calculations in Package Export first", true);
  const template = state.qaTemplate || {};
  $("qaMethods").innerHTML = (template.methods || []).map(method =>
    `<label class="check"><input type="checkbox" data-method="${esc(method.id)}"${method.default ? " checked" : ""}> ${esc(method.label)}</label>`).join("");
  $("qaStatement").innerHTML = `<table class="data"><tbody>${(template.statementItems || []).map(item =>
    `<tr><td>${esc(item.label)}</td><td class="nowrap"><select data-statement="${esc(item.id)}">
      <option value="  "></option><option>Y</option><option>N</option><option>N/A</option></select></td></tr>`).join("")}</tbody></table>`;
  $("qaReviewer").innerHTML = '<option value="">Not in the directory</option>'
    + state.people.map(person => `<option value="${esc(person.email)}">${esc(person.displayName)} (${esc(person.initials)})</option>`).join("");
  $("qaSelectionCount").textContent = `${state.packageSelection.size} selected.`;
  $("qaError").textContent = "";
  updateQaFolderPreview();
  $("qaDialog").showModal();
}
function updateQaFolderPreview() {
  const now = new Date();
  const stampText = `${String(now.getFullYear()).slice(2)}${String(now.getMonth() + 1).padStart(2, "0")}${String(now.getDate()).padStart(2, "0")}`;
  const title = ($("qaTitle").value.trim() || "TITLE").toUpperCase();
  const reviewer = ($("qaReviewerInitials").value.trim() || "XX").toUpperCase();
  $("qaFolderPreview").textContent =
    `Will be filed in 06-QA\\03-Verification\\${stampText} - ${title} - ${reviewer}`;
}
async function createQaPackage() {
  $("qaError").textContent = "";
  const methods = {};
  $("qaMethods").querySelectorAll("[data-method]").forEach(box => { methods[box.dataset.method] = box.checked; });
  methods.other = $("qaMethodOther").value;
  const statement = {};
  $("qaStatement").querySelectorAll("[data-statement]").forEach(select => { statement[select.dataset.statement] = select.value; });
  const reviewerOption = $("qaReviewer").selectedOptions[0];
  try {
    const data = await api("/api/qa/create", {
      projectId: state.project.id,
      title: $("qaTitle").value.trim(),
      reviewer: reviewerOption && reviewerOption.value
        ? reviewerOption.textContent.replace(/\s*\(.*\)$/, "")
        : $("qaReviewerInitials").value.trim(),
      reviewerEmail: $("qaReviewer").value,
      reviewerInitials: $("qaReviewerInitials").value.trim(),
      selection: [...state.packageSelection],
      sort: sortOrder(),
      methods, statement,
      producerComments: $("qaProducerComments").value,
      drawingSet: $("qaDrawings").value.trim() ? { path: $("qaDrawings").value.trim() } : null,
      drawings: $("qaDrawings").value.trim() ? [{ path: $("qaDrawings").value.trim() }] : []
    });
    $("qaDialog").close();
    await refreshQa();
    showQaPackage(data.package.id);
    toast(`Verification package ${data.package.ref} created`);
  } catch (error) { $("qaError").textContent = error.message; }
}
async function showQaStatus() {
  try {
    const data = await get("/api/qa/status");
    $("qaStatusTable").innerHTML = `<table class="data"><thead><tr><th>Project</th><th>Name</th>
      <th>Packages</th><th>Endorsed</th><th>Open comments</th><th>Deferred</th><th>Latest status</th>
      </tr></thead><tbody>${data.projects.map(row => `<tr>
        <td>${esc(row.project)}</td><td>${esc(row.projectName)}</td>
        <td>${esc(row.packages)}</td><td>${esc(row.endorsed || 0)}</td>
        <td>${esc(row.openComments || 0)}</td><td>${esc(row.deferredComments || 0)}</td>
        <td>${esc(row.latestStatus)}</td></tr>`).join("")}</tbody></table>`;
    $("qaStatusDialog").showModal();
  } catch (error) { toast(error.message, true); }
}

/* ------------------------------------------------------------------ views */
const VIEWS = {
  library: "libraryView", calculation: "calculationView",
  package: "packageView", qa: "qaView"
};
async function showView(view) {
  if (state.view === "calculation" && view !== "calculation" && !await guard()) return;
  state.view = view;
  Object.entries(VIEWS).forEach(([key, id]) => { $(id).hidden = key !== view; });
  ["navLibrary", "navCalculation", "navPackage", "navQa"].forEach((id, index) =>
    $(id).classList.toggle("active", ["library", "calculation", "package", "qa"][index] === view));
  $("saveCalculation").hidden = view !== "calculation";
  if (view === "library") refreshLibrary();
  if (view === "package") refreshPackage();
  if (view === "qa") refreshQa();
}
function showVersions() {
  get("/api/versions").then(data => {
    $("versionHistory").innerHTML = data.history.map(item => `
      <article><h3>${esc(item.version)} <small class="muted">${esc(item.date)} &middot; ${esc(item.author)}</small></h3>
      <p>${esc(item.summary)}</p><ul>${item.changes.map(change => `<li>${esc(change)}</li>`).join("")}</ul></article>`).join("");
    $("versionsDialog").showModal();
  }).catch(error => toast(error.message, true));
}

/* ------------------------------------------------------------------ people */
function showPeople() {
  if (!state.project) return toast("Open a project first", true);
  const project = state.project;
  $("peopleList").innerHTML = `<table class="data"><thead><tr><th>Person</th><th>Designer</th><th>Verifier</th></tr></thead>
    <tbody>${state.people.map(person => `<tr>
      <td>${esc(person.displayName)} <span class="muted">${esc(person.email)}</span></td>
      <td><input type="checkbox" data-designer="${esc(person.email)}"${(project.designers || []).includes(person.email) ? " checked" : ""}></td>
      <td><input type="checkbox" data-verifier="${esc(person.email)}"${(project.verifiers || []).includes(person.email) ? " checked" : ""}></td>
      </tr>`).join("")}</tbody></table>`;
  $("peopleError").textContent = "";
  $("peopleDialog").showModal();
}
async function savePeople() {
  const designers = [...document.querySelectorAll("[data-designer]:checked")].map(box => box.dataset.designer);
  const verifiers = [...document.querySelectorAll("[data-verifier]:checked")].map(box => box.dataset.verifier);
  const extra = $("newPersonEmail").value.trim().toLowerCase();
  if (extra) ($("newPersonRole").value === "verifier" ? verifiers : designers).push(extra);
  try {
    const data = await api("/api/projects/people", { projectId: state.project.id, designers, verifiers });
    state.project = data.project;
    state.projects = data.projects;
    $("peopleDialog").close();
    toast("Project team updated");
  } catch (error) { $("peopleError").textContent = error.message; }
}

/* ------------------------------------------------------------------- wiring */
function wire() {
  $("signInForm").addEventListener("submit", signIn);
  $("ssoStart").onclick = startSso;
  $("signInEmail").oninput = () => {
    if (!$("signInName").value) {
      const local = $("signInEmail").value.split("@")[0] || "";
      $("signInName").value = local.split(/[._-]/).filter(Boolean)
        .map(part => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
    }
  };

  $("projectSelect").onchange = () => {
    const id = $("projectSelect").value;
    if (id) openProject(id); else renderProjectSelect();
  };
  $("projectsButton").onclick = () => { loadProjects(); $("projectsDialog").showModal(); };
  $("findButton").onclick = findProject;
  $("findCode").onkeydown = event => { if (event.key === "Enter") { event.preventDefault(); findProject(); } };
  $("rescanButton").onclick = async () => {
    const data = await api("/api/projects/refresh", {});
    showDiscovery(data.discovery);
    toast("Scanning the projects drive in the background");
    setTimeout(loadProjects, 8000);
  };
  $("pickFolder").onclick = () => pickFolder("newProjectPath");
  $("addProject").onclick = () => addProject();

  $("navLibrary").onclick = () => showView("library");
  $("navCalculation").onclick = () => showView("calculation");
  $("navPackage").onclick = () => showView("package");
  $("navQa").onclick = () => showView("qa");
  $("versionsButton").onclick = showVersions;
  $("saveCalculation").onclick = () => saveCalculation().catch(() => {});

  $("newCalculation").onclick = () => {
    if (!state.project) return toast("Open a project first", true);
    $("moduleDialog").showModal();
  };
  $("refreshLibrary").onclick = refreshLibrary;
  $("adoptExisting").onclick = async () => {
    try {
      const data = await api("/api/projects/adopt", { projectId: state.project.id });
      state.library = data.library;
      renderLibrary();
      renderTree();
      toast(`${data.adopted} existing calculation(s) indexed`);
    } catch (error) { toast(error.message, true); }
  };
  ["librarySearch", "libraryPackage", "libraryLevel", "libraryModule", "libraryCalcType",
    "libraryShowSuperseded"].forEach(id => {
      $(id).addEventListener("input", refreshLibrary);
      $(id).addEventListener("change", refreshLibrary);
    });
  $("refreshTree").onclick = refreshLibrary;

  ["pkgPackage", "pkgLevel", "pkgMemberType", "pkgCalcType", "pkgSort1", "pkgSort2", "pkgSort3",
    "pkgFinalisedOnly"].forEach(id => $(id).addEventListener("change", refreshPackage));
  $("packageRefresh").onclick = refreshPackage;
  $("packageBuild").onclick = buildPackage;
  $("pkgPickDrawings").onclick = () => pickFolder("pkgDrawings", "file");
  $("pkgSelectAll").onclick = () => {
    state.packageEntries.forEach(entry => state.packageSelection.add(entry.id));
    renderPackage();
  };
  $("pkgSelectNone").onclick = () => { state.packageSelection.clear(); renderPackage(); };

  $("qaNew").onclick = openQaDialog;
  $("qaRefresh").onclick = refreshQa;
  $("qaCreate").onclick = createQaPackage;
  $("qaStatusButton").onclick = showQaStatus;
  $("qaPickDrawings").onclick = () => pickFolder("qaDrawings", "file");
  $("qaTitle").addEventListener("input", updateQaFolderPreview);
  $("qaReviewerInitials").addEventListener("input", updateQaFolderPreview);
  $("qaReviewer").addEventListener("change", () => {
    const option = $("qaReviewer").selectedOptions[0];
    const match = option && option.textContent.match(/\(([^)]+)\)/);
    if (match) $("qaReviewerInitials").value = match[1];
    updateQaFolderPreview();
  });

  $("savePeople").onclick = savePeople;
  document.querySelectorAll("[data-close]").forEach(button =>
    button.onclick = () => button.closest("dialog").close());

  ["idMemberType", "idMemberNumber", "idPackage", "idLevel", "idSubject", "idChecker", "idDesigner"]
    .forEach(id => $(id).addEventListener("input", () => setDirty(true)));
  $("idSubject").addEventListener("input", scheduleCalculation);

  document.addEventListener("keydown", event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
      event.preventDefault();
      if (state.view === "calculation") saveCalculation().catch(() => {});
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  wire();
  loadAuthConfig().catch(error => toast(error.message, true));
});
