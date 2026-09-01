"use strict";
/* InnoCalc Manager - front end.
   The front end holds no engineering knowledge. Every calculation form is built
   from the schema its module publishes, so a new design module needs no change
   here. */

const $ = id => document.getElementById(id);
const state = {
  token: "", user: null, people: [],
  projects: [], project: null,
  modules: [], module: null, schema: null, categories: [], moduleCategory: "", favourites: [],
  inputs: {}, fields: [], checks: {}, cells: [],
  calculationId: "", dirty: false, view: "library",
  library: null, qa: [], qaTemplate: null, filters: {}, issues: [],
  packageEntries: [], packageSelection: new Set(),
  timer: 0, request: 0
};

/* Small line icons; a PDF link and a folder link are recognised at a glance. */
const ICON = {
  pdf: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M9.5 0H3.5A1.5 1.5 0 0 0 2 1.5v13A1.5 1.5 0 0 0 3.5 16h9a1.5 1.5 0 0 0 1.5-1.5V4.5L9.5 0zm0 1.5L12.5 4.5H10a.5.5 0 0 1-.5-.5V1.5zM4.6 12.6V8.9h1.3c.9 0 1.4.4 1.4 1.2s-.5 1.2-1.4 1.2h-.5v1.3H4.6zm.8-2h.4c.3 0 .5-.2.5-.5s-.2-.5-.5-.5h-.4v1zm2.6 2V8.9h1.3c1.1 0 1.7.6 1.7 1.8s-.6 1.9-1.7 1.9H8zm.8-.7h.4c.5 0 .8-.4.8-1.2s-.3-1.1-.8-1.1h-.4v2.3zm3-3h2.1v.7h-1.3v.8h1.2v.7h-1.2v1.5h-.8V8.9z"/></svg>',
  folder: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M1.5 2.5h4.2l1.3 1.5h7.5a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H1.5a1 1 0 0 1-1-1v-9.5a1 1 0 0 1 1-1z"/></svg>'
};
const REASONS = ["Internal Review", "Verification", "Certification",
  "Preliminary Check", "Status Print"];

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
  const query = new URLSearchParams({ token: state.token });
  Object.entries(params || {}).forEach(([key, value]) => {
    if (Array.isArray(value)) value.forEach(item => query.append(key, item));
    else query.set(key, value);
  });
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
function openFile(path) {
  if (path) window.open(fileUrl(path), "_blank");
}
async function revealFolder(path) {
  try { await get("/api/reveal", { path }); }
  catch (error) { toast(error.message, true); }
}
function linkButtons(record) {
  const pdf = record.pdfPath
    ? `<button class="icon-link pdf" data-pdf-path="${esc(record.pdfPath)}" title="Open the PDF">${ICON.pdf}</button>` : "";
  const folder = record.folder
    ? `<button class="icon-link folder" data-folder="${esc(record.folder)}" title="Open the folder">${ICON.folder}</button>` : "";
  return pdf + folder;
}
function wireLinks(host) {
  host.querySelectorAll("[data-pdf-path]").forEach(button =>
    button.onclick = () => openFile(button.dataset.pdfPath));
  host.querySelectorAll("[data-folder]").forEach(button =>
    button.onclick = () => revealFolder(button.dataset.folder));
}
/* Saving prints a PDF with headless Chromium, which takes a few seconds, so the
   state of both the save and the print is always on screen. */
function setSaveState(text, kind = "busy") {
  const node = $("saveState");
  node.textContent = text || "";
  node.className = `save-state${text ? ` ${kind}` : ""}`;
  clearTimeout(node._timer);
  if (text && kind !== "busy") node._timer = setTimeout(() => setSaveState(""), 6000);
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

/* ------------------------------------------------- multi-select filter menu */
/* The index will hold thousands of calculations, so each filter is a dropdown
   of tick boxes rather than a single-choice select. */
function multiSelect(hostId, label, onChange) {
  const host = $(hostId);
  host.innerHTML = `<span class="multi-label">${esc(label)}</span>
    <button type="button">All</button><div class="multi-panel" hidden></div>`;
  const button = host.querySelector("button");
  const panel = host.querySelector(".multi-panel");
  const control = { values: [], options: [] };
  const label_ = () => {
    button.textContent = control.values.length === 0 ? "All"
      : control.values.length === 1 ? control.values[0]
        : `${control.values.length} selected`;
    button.classList.toggle("on", control.values.length > 0);
  };
  const draw = () => {
    panel.innerHTML = control.options.map(item =>
      `<label><input type="checkbox" value="${esc(item)}"${control.values.includes(item) ? " checked" : ""}> ${esc(item)}</label>`).join("")
      + `<div class="multi-actions"><button type="button" data-all>All</button>
         <button type="button" data-none>None</button></div>`;
    panel.querySelectorAll("input").forEach(box => box.onchange = () => {
      control.values = [...panel.querySelectorAll("input:checked")].map(item => item.value);
      label_(); onChange();
    });
    panel.querySelector("[data-all]").onclick = () => { control.values = [...control.options]; draw(); label_(); onChange(); };
    panel.querySelector("[data-none]").onclick = () => { control.values = []; draw(); label_(); onChange(); };
  };
  button.onclick = () => {
    document.querySelectorAll(".multi-panel").forEach(item => { if (item !== panel) item.hidden = true; });
    panel.hidden = !panel.hidden;
    if (!panel.hidden) draw();
  };
  document.addEventListener("click", event => {
    if (!host.contains(event.target)) panel.hidden = true;
  });
  control.setOptions = options => {
    control.options = [...options];
    control.values = control.values.filter(item => control.options.includes(item));
    label_();
    if (!panel.hidden) draw();
  };
  control.clear = () => { control.values = []; label_(); if (!panel.hidden) draw(); };
  label_();
  return control;
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
      <td>${esc(projectLabel(item))}${item.exists ? "" : ' <span class="pill fail">missing</span>'}${item.archived ? ' <span class="pill noted">archived</span>' : ""}</td>
      <td class="muted">${esc(item.folderPath)}</td>
      <td class="nowrap">${esc(item.role || "")}</td>
      <td class="nowrap">${esc(stamp(item.lastOpened))}</td>
      <td class="row-actions">
        <button data-open="${esc(item.id)}">Open</button>
        <button data-relink="${esc(item.id)}" title="Point this project at a different folder">Relink</button>
        <button data-archive="${esc(item.id)}">${item.archived ? "Restore" : "Archive"}</button>
        <button data-forget="${esc(item.id)}" class="danger" title="Remove from your list only">Remove</button>
      </td>
    </tr>`).join("");
  $("projectList").innerHTML = rows
    ? `<table class="data"><thead><tr><th>Project</th><th>Folder</th><th>Role</th><th>Last opened</th><th></th></tr></thead><tbody>${rows}</tbody></table>`
    : '<p class="empty-state">No projects yet. Add one below.</p>';
  $("projectList").querySelectorAll("[data-open]").forEach(button =>
    button.onclick = () => openProject(button.dataset.open).then(() => $("projectsDialog").close()));
  $("projectList").querySelectorAll("[data-relink]").forEach(button =>
    button.onclick = () => relinkProject(button.dataset.relink));
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
    toast(project.archived ? "Project restored" : "Project archived");
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
    toast("Removed from your project list");
  } catch (error) { toast(error.message, true); }
}
/* A folder that has been moved or renamed leaves a dead link; re-address it
   here rather than adding the project again and losing its history. */
async function relinkProject(projectId) {
  const project = state.projects.find(item => item.id === projectId);
  try {
    const picked = await get("/api/pick", { title: `Folder for ${projectLabel(project)}`, scope: "project" });
    if (!picked.path) return;
    const data = await api("/api/projects/relink", { projectId, path: picked.path });
    state.projects = data.projects;
    if (state.project && state.project.id === projectId) state.project = data.project;
    renderProjectSelect();
    renderProjectList();
    toast(`Project folder now ${data.project.folderPath}`);
  } catch (error) { toast(error.message, true); }
}
async function findProject() {
  const query = $("findCode").value.trim();
  if (!query) return;
  $("findResults").innerHTML = '<p class="muted">Looking&hellip;</p>';
  try {
    const data = await api("/api/projects/search", { query });
    if (!data.matches.length) {
      $("findResults").innerHTML = data.scanning
        ? '<p class="notice">Not in the index yet. A background scan has started - try again shortly, or add the folder below.</p>'
        : '<p class="notice">Nothing found for that number or name. Add it below.</p>';
      return;
    }
    $("findResults").innerHTML = `<table class="data"><tbody>${data.matches.map(item => `
      <tr><td>${esc(projectLabel(item))}</td><td class="muted">${esc(item.folderPath)}</td>
      <td class="row-actions"><button data-use="${esc(item.folderPath)}">Use</button>
      <button data-add="${esc(item.folderPath)}" class="primary">Add and open</button></td></tr>`).join("")}</tbody></table>`;
    $("findResults").querySelectorAll("[data-add]").forEach(button =>
      button.onclick = () => addProject(button.dataset.add, true));
    $("findResults").querySelectorAll("[data-use]").forEach(button =>
      button.onclick = () => fillNewProject(button.dataset.use));
  } catch (error) { $("findResults").innerHTML = `<p class="error">${esc(error.message)}</p>`; }
}
/* Typing a project number is enough: the folder, client reference and project
   name are read from the matching folder on the drive. */
async function lookupProjectNumber() {
  const code = $("newProjectCode").value.trim();
  if (code.length < 3 || $("newProjectPath").value.trim()) return;
  try {
    const data = await api("/api/projects/search", { query: code });
    if (data.matches.length === 1) fillNewProject(data.matches[0].folderPath, data.matches[0]);
  } catch { /* the number may simply not exist yet */ }
}
function fillNewProject(path, described) {
  $("newProjectPath").value = path;
  const parts = described || {};
  const fallback = (path.split(/[\\/]/).pop() || "").split(" - ");
  $("newProjectCode").value = parts.code || fallback[0] || "";
  $("newProjectClient").value = parts.clientRef ?? (fallback[1] || "");
  $("newProjectName").value = parts.projectName ?? fallback.slice(2).join(" - ");
}
async function addProject(path, openAfter) {
  $("projectsError").textContent = "";
  try {
    const data = await api("/api/projects/create", {
      path: path || $("newProjectPath").value.trim(),
      code: $("newProjectCode").value.trim(),
      clientRef: $("newProjectClient").value.trim(),
      projectName: $("newProjectName").value.trim()
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
      ? { mode: "file", title: "Select a PDF" }
      : { title: "Select project folder", scope: "project" });
    if (!data.path) return;
    if (target === "newProjectPath") fillNewProject(data.path);
    else $(target).value = data.path;
  } catch (error) { toast(error.message, true); }
}

/* ---------------------------------------------------------------- modules */
/* Many more modules are coming, so the chooser is a discipline tree with a
   Favourites branch and a search, not one long list of cards. */
const FAVOURITES_KEY = "innocalc.favourites";
function loadFavourites() {
  try { state.favourites = JSON.parse(localStorage.getItem(FAVOURITES_KEY)) || []; }
  catch { state.favourites = []; }
}
function toggleFavourite(moduleId) {
  state.favourites = state.favourites.includes(moduleId)
    ? state.favourites.filter(item => item !== moduleId)
    : [...state.favourites, moduleId];
  localStorage.setItem(FAVOURITES_KEY, JSON.stringify(state.favourites));
  renderModuleBrowser();
}
async function loadModules() {
  const data = await api("/api/modules", null, "GET");
  state.modules = data.modules || [];
  state.categories = data.categories || [];
  (data.problems || []).forEach(problem =>
    toast(`Module ${problem.entry} did not load: ${problem.error}`, true));
  loadFavourites();
  renderModuleBrowser();
}
function moduleBranches() {
  // Every discipline branch is shown, including the ones still to be filled, so
  // the shape of the suite is visible as modules are commissioned.
  const used = new Set(state.modules.map(item => item.category || "General"));
  const extra = [...used].filter(item => !state.categories.includes(item)).sort();
  return ["Favourites", ...state.categories, ...extra];
}
function modulesIn(branch) {
  const search = $("moduleSearch").value.trim().toLowerCase();
  const pool = branch === "Favourites"
    ? state.modules.filter(item => state.favourites.includes(item.id))
    : state.modules.filter(item => (item.category || "General") === branch);
  if (!search) return pool;
  return pool.filter(item => [item.name, item.short, item.standard, item.description,
    item.category].join(" ").toLowerCase().includes(search));
}
function renderModuleBrowser() {
  const branches = moduleBranches();
  const search = $("moduleSearch").value.trim();
  const counts = Object.fromEntries(branches.map(item => [item, modulesIn(item).length]));
  // A search narrows the tree to the branches that still have something in it.
  const visible = search ? branches.filter(item => counts[item]) : branches;
  if (!visible.includes(state.moduleCategory)) state.moduleCategory = visible[0] || "";
  $("moduleTree").innerHTML = visible.map(branch =>
    `<button type="button" data-branch="${esc(branch)}" class="${branch === state.moduleCategory ? "selected" : ""}${counts[branch] ? "" : " empty"}">
      <span>${esc(branch)}</span><small>${counts[branch]}</small></button>`).join("")
    || '<p class="muted">No module matches.</p>';
  $("moduleTree").querySelectorAll("[data-branch]").forEach(button =>
    button.onclick = () => { state.moduleCategory = button.dataset.branch; renderModuleBrowser(); });
  const cards = modulesIn(state.moduleCategory);
  $("moduleCards").innerHTML = cards.map(item => `
    <button class="module-card" data-module="${esc(item.id)}" type="button">
      <span class="fav${state.favourites.includes(item.id) ? "" : " off"}"
            data-fav="${esc(item.id)}" title="Favourite">&#9733;</span>
      <b>${esc(item.name)}</b><small>${esc(item.standard)} &middot; ${esc(item.version)}</small>
      <p>${esc(item.description)}</p></button>`).join("")
    || `<p class="empty-state">${state.moduleCategory === "Favourites"
      ? "Star a module to keep it here."
      : `No ${state.moduleCategory.toLowerCase()} module yet.`}</p>`;
  $("moduleCards").querySelectorAll("[data-module]").forEach(card =>
    card.onclick = () => { $("moduleDialog").close(); newCalculation(card.dataset.module); });
  $("moduleCards").querySelectorAll("[data-fav]").forEach(star =>
    star.onclick = event => { event.stopPropagation(); toggleFavourite(star.dataset.fav); });
}
function openModuleDialog() {
  if (!state.project) return toast("Open a project first", true);
  $("moduleSearch").value = "";
  state.moduleCategory = state.favourites.length ? "Favourites" : "";
  renderModuleBrowser();
  $("moduleDialog").showModal();
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
  values.description = $("idDescription").value.trim();
  values.designer = $("idDesigner").value.trim();
  // 'Checked by' is the verifier's, written when they close the verification out.
  values.checker = $("idChecker").value.trim();
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
  $("idDescription").value = values.description || "";
  $("idChecker").value = values.checker || "";
  $("idChecker").placeholder = values.checker ? "" : "Set on verification";
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
    if (record.module === "imported-pdf") {
      openFile(record.pdfPath);
      return;
    }
    const data = await get("/api/module/schema", { module: record.module });
    state.module = state.modules.find(item => item.id === record.module);
    state.calculationId = record.id;
    state.inputs = { ...record.inputs };
    // The record carries what the verifier and the index own, not the form.
    const values = { ...record.inputs, checker: record.checker || "",
      description: record.description || "" };
    renderSchemaForm(data.schema, values);
    applyIdentity(values, data.schema);
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
  setSaveState("Saving\u2026");
  try {
    const data = await api("/api/calculation/save", {
      projectId: state.project.id, module: state.module.id, inputs: readInputs(),
      calculationId: state.calculationId, supersede
    });
    if (data.conflict) {
      $("saveCalculation").disabled = false;
      setSaveState("");
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
    toast(`Saved revision ${data.revision.rev}`);
    watchPdf(data.calculationId);
    return data;
  } catch (error) {
    setSaveState("Save failed", "bad");
    toast(error.message, true);
    throw error;
  } finally { $("saveCalculation").disabled = false; }
}
/* The sheet is printed on the server behind the save, so the indicator follows
   it until the PDF is on the drive. */
function watchPdf(calculationId) {
  clearTimeout(state.pdfTimer);
  setSaveState("Printing PDF\u2026");
  const poll = async () => {
    try {
      const data = await get("/api/calculation/pdf", { id: calculationId });
      if (data.status === "printing") { state.pdfTimer = setTimeout(poll, 900); return; }
      if (data.status === "ready") setSaveState("Saved with PDF", "done");
      else if (data.status === "failed") setSaveState(`PDF not produced: ${data.error}`, "bad");
      else setSaveState("Saved", "done");
    } catch { setSaveState("Saved", "done"); }
  };
  state.pdfTimer = setTimeout(poll, 900);
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

/* ------------------------------------------------------- calculation index */
function moduleName(id) {
  if (id === "imported-pdf") return "Imported PDF";
  const module = state.modules.find(item => item.id === id);
  return module ? module.short || module.name : id;
}
const INDEX_SORTS = [
  { id: "package", label: "Package, level, type" },
  { id: "level", label: "Level" },
  { id: "memberType", label: "Type" },
  { id: "memberNumber", label: "Number" },
  { id: "title", label: "Title" },
  { id: "status", label: "Status" },
  { id: "worstUtil", label: "Utilisation" },
  { id: "updatedAt", label: "Last saved" }
];
async function refreshLibrary() {
  if (!state.project) return;
  try {
    const data = await get("/api/library", {
      project: state.project.id,
      showSuperseded: $("libraryShowSuperseded").checked ? "1" : "0",
      search: $("librarySearch").value.trim(),
      package: state.filters.package.values,
      level: state.filters.level.values,
      module: state.filters.module.values.map(moduleIdFor),
      calcType: state.filters.calcType.values
    });
    state.library = data.library;
    state.issues = data.library.issues || [];
    renderLibrary(true);
  } catch (error) { toast(error.message, true); }
}
function moduleIdFor(name) {
  if (name === "Imported PDF") return "imported-pdf";
  const module = state.modules.find(item => (item.short || item.name) === name);
  return module ? module.id : name;
}
function fillFilter(select, values, keep) {
  const current = keep ? select.value : "";
  select.innerHTML = '<option value="">All</option>'
    + values.map(item => `<option value="${esc(item)}">${esc(item)}</option>`).join("");
  select.value = current;
}
function sortedCalculations(rows) {
  const key = $("librarySort").value || "package";
  const of = record => key === "worstUtil" ? Number(record.worstUtil || 0)
    : String(record[key] ?? "").toLowerCase();
  if (key === "package") return rows;   // the server already orders this way
  return [...rows].sort((a, b) => (of(a) > of(b) ? 1 : of(a) < of(b) ? -1 : 0));
}
function renderLibrary(keepFilters) {
  const library = state.library;
  if (!library) return;
  state.issues = library.issues || state.issues;
  state.filters.package.setOptions(library.packages || []);
  state.filters.level.setOptions(library.levels || []);
  state.filters.calcType.setOptions(library.calcTypes || []);
  state.filters.module.setOptions([...new Set((library.calculations || [])
    .map(item => moduleName(item.module)))].sort());
  fillFilter($("pkgPackage"), library.packages || [], true);
  fillFilter($("pkgLevel"), library.levels || [], true);
  fillFilter($("pkgCalcType"), library.calcTypes || [], true);
  fillFilter($("pkgMemberType"), library.memberTypes || [], true);
  $("idPackages").innerHTML = (library.packages || []).map(item => `<option value="${esc(item)}">`).join("");
  $("idLevels").innerHTML = (library.levels || []).map(item => `<option value="${esc(item)}">`).join("");
  const rows = sortedCalculations(library.calculations || []).map(record => {
    const latest = record.revisions[record.revisions.length - 1] || {};
    const over = Number(record.worstUtil || 0) > 1;
    return `<tr${record.superseded ? ' class="superseded"' : ""}>
      <td class="edit"><input data-edit="package" data-id="${esc(record.id)}" list="idPackages" value="${esc(record.package)}"></td>
      <td class="edit"><input data-edit="level" data-id="${esc(record.id)}" list="idLevels" value="${esc(record.level)}" size="6"></td>
      <td>${esc(moduleName(record.module))}</td>
      <td>${esc(record.memberType)}</td>
      <td>${esc(record.memberNumber)}</td>
      <td>${esc(record.title)}</td>
      <td class="edit"><input data-edit="description" data-id="${esc(record.id)}" value="${esc(record.description || "")}" placeholder="Description"></td>
      <td class="nowrap">${statusPill(record.status)} <span class="util${over ? " over" : ""}">${percent(record.worstUtil)}</span></td>
      <td>${esc(record.criticalCheck)}</td>
      <td class="nowrap">${esc(record.checker || "")}</td>
      <td class="nowrap">rev ${esc(latest.rev || record.revisions.length)} ${esc(stamp(latest.savedAt))} ${esc(latest.initials || "")}</td>
      <td class="nowrap"><input type="checkbox" data-final="${esc(record.id)}"${record.finalised ? " checked" : ""} title="Finalised"></td>
      <td class="row-actions">
        ${linkButtons(record)}
        <button data-open-calc="${esc(record.id)}">Open</button>
        <button data-link="${esc(record.id)}" title="Send these values into another calculation">Link</button>
        <button data-remove="${esc(record.id)}" class="danger" title="Remove from the library index">Remove</button>
      </td></tr>`;
  }).join("");
  $("libraryTable").innerHTML = rows
    ? `<table class="data"><thead><tr><th>Package</th><th>Level</th><th>Module</th><th>Type</th>
       <th>No.</th><th>Title</th><th>Description</th><th>Status</th><th>Governing check</th>
       <th>Checked by</th><th>Latest revision</th><th>Final</th><th></th></tr></thead>
       <tbody>${rows}</tbody></table>`
    : '<p class="empty-state">No calculations yet. Choose <b>New calculation</b> to start one.</p>';
  wireLinks($("libraryTable"));
  $("libraryTable").querySelectorAll("[data-open-calc]").forEach(button =>
    button.onclick = () => openCalculation(button.dataset.openCalc));
  $("libraryTable").querySelectorAll("[data-final]").forEach(box =>
    box.onchange = () => updateCalculation(box.dataset.final, { finalised: box.checked }));
  $("libraryTable").querySelectorAll("[data-edit]").forEach(input => {
    input.dataset.was = input.value;
    input.onchange = () => {
      if (input.value === input.dataset.was) return;
      updateCalculation(input.dataset.id, { [input.dataset.edit]: input.value });
    };
  });
  $("libraryTable").querySelectorAll("[data-remove]").forEach(button =>
    button.onclick = () => removeCalculation(button.dataset.remove));
  $("libraryTable").querySelectorAll("[data-link]").forEach(button =>
    button.onclick = () => linkCalculation(button.dataset.link));
}
async function updateCalculation(id, fields) {
  try {
    const data = await api("/api/calculation/update", { projectId: state.project.id, id, fields });
    state.library = data.library;
    renderLibrary(true);
    toast("Calculation index updated");
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
  const record = (state.library.calculations || []).find(item => item.id === sourceId);
  if (record && record.module === "imported-pdf") {
    return toast("An imported PDF has no values to link", true);
  }
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
    fillReviewers();
    renderPackage();
    renderIssues();
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
  const reviewer = $("pkgReviewer").selectedOptions[0];
  $("packageBuild").disabled = true;
  setSaveState("Building the package\u2026");
  try {
    const data = await api("/api/package/build", {
      projectId: state.project.id,
      selection: [...state.packageSelection],
      sort: sortOrder(),
      meta: {
        title: $("pkgTitle").value.trim() || "Calculation package",
        reason: $("pkgReason").value.trim() || "Internal Review",
        reviewerEmail: $("pkgReviewer").value,
        verifierInitials: reviewer ? (reviewer.textContent.match(/\(([^)]+)\)/) || [, ""])[1] : ""
      },
      drawings: $("pkgDrawings").value.trim() ? [{ path: $("pkgDrawings").value.trim() }] : []
    });
    state.issues = data.issues || [];
    renderIssues();
    setSaveState(`${data.issue.ref} issued`, "done");
    toast(`${data.sheets} sheet(s) exported as ${data.issue.ref}`
      + `${data.drawingsPath ? ", drawings issued separately" : ""}`
      + `${data.draft && data.draft.path ? ", draft email raised" : ""}`);
    openFile(data.pdfPath);
  } catch (error) { setSaveState("Export failed", "bad"); toast(error.message, true); }
  finally { $("packageBuild").disabled = false; }
}
/* Every issue is kept with the date it went out and a link back to the file. */
function renderIssues() {
  const rows = (state.issues || []).map(item => `
    <tr><td class="nowrap">${esc(item.ref)}</td><td>${esc(item.title)}</td>
      <td>${esc(item.reason)}</td><td class="nowrap">${esc(item.date)}</td>
      <td class="nowrap">${esc(item.issuedBy)}</td>
      <td class="nowrap">${esc(item.calculations)} calc / ${esc(item.sheets)} sheets</td>
      <td class="row-actions">
        ${linkButtons({ pdfPath: item.pdfPath, folder: item.folder })}
        ${item.drawingsPath ? `<button class="icon-link pdf" data-pdf-path="${esc(item.drawingsPath)}" title="Drawings">${ICON.pdf}</button>` : ""}
      </td></tr>`).join("");
  $("issueRegister").innerHTML = rows
    ? `<table class="data"><thead><tr><th>Ref</th><th>Title</th><th>Reason for issue</th>
       <th>Date of issue</th><th>By</th><th>Contents</th><th></th></tr></thead><tbody>${rows}</tbody></table>`
    : '<p class="empty-state">No packages issued from this project yet.</p>';
  wireLinks($("issueRegister"));
}
function fillReviewers() {
  const current = $("pkgReviewer").value;
  $("pkgReviewer").innerHTML = '<option value="">No one - do not raise an email</option>'
    + state.people.map(person =>
      `<option value="${esc(person.email)}">${esc(person.displayName)} (${esc(person.initials)})</option>`).join("");
  $("pkgReviewer").value = current;
  if (!$("pkgReason").value) $("pkgReason").value = REASONS[0];
}

/* ------------------------------------------------------------------ QA */
async function refreshQa() {
  if (!state.project) return;
  try {
    // The server reads any marked-up PDF the verifier has returned to the
    // package folder, so opening or refreshing this tab is enough to see it.
    const data = await get("/api/qa", { project: state.project.id, scan: "1" });
    state.qa = data.packages || [];
    state.qaTemplate = data.template;
    renderQa();
    if (data.imported) toast(`${data.imported} new verifier comment(s) found`);
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
    toast(`Verification package ${data.package.ref} created`
      + `${data.draft && data.draft.path ? ", draft email raised for the verifier" : ""}`);
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

/* ---------------------------------------------------------- PDF import */
function openImportDialog() {
  if (!state.project) return toast("Open a project first", true);
  ["importPath", "importType", "importNumber", "importLevel", "importCalcType",
    "importOrigin", "importTitle", "importDescription"].forEach(id => { $(id).value = ""; });
  $("importPackage").value = "Unallocated";
  $("importError").textContent = "";
  $("importPdfDialog").showModal();
}
async function importPdfCalculation() {
  $("importError").textContent = "";
  try {
    const data = await api("/api/calculation/import", {
      projectId: state.project.id,
      path: $("importPath").value.trim(),
      memberType: $("importType").value.trim(),
      memberNumber: $("importNumber").value.trim(),
      package: $("importPackage").value.trim(),
      level: $("importLevel").value.trim(),
      calcType: $("importCalcType").value.trim(),
      origin: $("importOrigin").value.trim(),
      title: $("importTitle").value.trim(),
      description: $("importDescription").value.trim()
    });
    state.library = data.library;
    $("importPdfDialog").close();
    renderLibrary(true);
    renderTree();
    toast("PDF calculation indexed");
  } catch (error) { $("importError").textContent = error.message; }
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
  $("newProjectCode").addEventListener("change", lookupProjectNumber);
  $("newProjectCode").addEventListener("blur", lookupProjectNumber);

  $("navLibrary").onclick = () => showView("library");
  $("navCalculation").onclick = () => showView("calculation");
  $("navPackage").onclick = () => showView("package");
  $("navQa").onclick = () => showView("qa");
  $("versionsButton").onclick = showVersions;
  $("saveCalculation").onclick = () => saveCalculation().catch(() => {});

  $("newCalculation").onclick = openModuleDialog;
  $("newCalculationCalc").onclick = openModuleDialog;
  $("moduleSearch").addEventListener("input", renderModuleBrowser);
  $("importPdf").onclick = openImportDialog;
  $("importPick").onclick = () => pickFolder("importPath", "file");
  $("importCreate").onclick = importPdfCalculation;
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
  ["package", "level", "module", "calcType"].forEach(key => {
    state.filters[key] = multiSelect(
      `library${key.charAt(0).toUpperCase()}${key.slice(1)}`,
      { package: "Package", level: "Level", module: "Module", calcType: "Calculation type" }[key],
      refreshLibrary);
  });
  $("librarySort").innerHTML = INDEX_SORTS.map(item =>
    `<option value="${esc(item.id)}">${esc(item.label)}</option>`).join("");
  $("librarySort").addEventListener("change", () => renderLibrary(true));
  $("libraryClear").onclick = () => {
    Object.values(state.filters).forEach(filter => filter.clear());
    $("librarySearch").value = "";
    $("libraryShowSuperseded").checked = false;
    refreshLibrary();
  };
  ["librarySearch", "libraryShowSuperseded"].forEach(id => {
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

  ["idMemberType", "idMemberNumber", "idPackage", "idLevel", "idSubject", "idDesigner",
    "idDescription"].forEach(id => $(id).addEventListener("input", () => setDirty(true)));
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
