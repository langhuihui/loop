const API = '';

let templates = {};
let hubState = null;

function linesToArray(text) {
  return text.split('\n').map((s) => s.trim()).filter(Boolean);
}

function arrayToLines(arr) {
  return (arr || []).join('\n');
}

function showToast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 2000);
}

function setError(msg) {
  const el = document.getElementById('formError');
  if (!msg) {
    el.hidden = true;
    el.textContent = '';
    return;
  }
  el.hidden = false;
  el.textContent = msg;
}

function updateEmptyPromptPlaceholders() {
  document.querySelectorAll('[data-placeholder-key]').forEach((el) => {
    if (el.classList.contains('empty')) {
      el.textContent = t(el.dataset.placeholderKey);
    }
  });
}

function renderTemplateOptions() {
  const select = document.getElementById('templateSelect');
  const current = select.value || Object.keys(templates)[0];
  select.innerHTML = '';
  Object.keys(templates).forEach((id) => {
    const opt = document.createElement('option');
    opt.value = id;
    opt.textContent = t(`tpl.${id}`) || id;
    select.appendChild(opt);
  });
  if (templates[current]) select.value = current;
}

async function api(path, options = {}) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 10000);
  try {
    const res = await fetch(`${API}${path}`, { ...options, signal: ctrl.signal });
    clearTimeout(timer);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
  } catch (err) {
    clearTimeout(timer);
    throw err;
  }
}

function buildProfile() {
  return {
    template: document.getElementById('templateSelect').value,
    roles: {
      A: {
        name: document.getElementById('roleAName').value.trim(),
        goal: document.getElementById('roleAGoal').value.trim(),
        responsibilities: linesToArray(document.getElementById('roleAResp').value),
        forbidden: linesToArray(document.getElementById('roleAForbidden').value),
        wakeSentinel: 'AGENT_LOOP_WAKE_A',
      },
      B: {
        name: document.getElementById('roleBName').value.trim(),
        goal: document.getElementById('roleBGoal').value.trim(),
        responsibilities: linesToArray(document.getElementById('roleBResp').value),
        forbidden: linesToArray(document.getElementById('roleBForbidden').value),
        wakeSentinel: 'AGENT_LOOP_WAKE_B',
      },
    },
    workflow: templates[document.getElementById('templateSelect').value].workflow,
    task: {
      title: document.getElementById('taskTitle').value.trim(),
      branch: document.getElementById('taskBranch').value.trim() || 'main',
      constraints: linesToArray(document.getElementById('taskConstraints').value),
    },
    maxEpochs: parseInt(document.getElementById('maxEpochs').value, 10) || 20,
    lang: window.currentLang || 'en',
  };
}

function applyTemplateToForm(templateId) {
  const tpl = getLocalizedTemplate(templateId, templates);
  if (!tpl) return;

  document.getElementById('roleAName').value = tpl.roles.A.name;
  document.getElementById('roleAGoal').value = tpl.roles.A.goal;
  document.getElementById('roleAResp').value = arrayToLines(tpl.roles.A.responsibilities);
  document.getElementById('roleAForbidden').value = arrayToLines(tpl.roles.A.forbidden);

  document.getElementById('roleBName').value = tpl.roles.B.name;
  document.getElementById('roleBGoal').value = tpl.roles.B.goal;
  document.getElementById('roleBResp').value = arrayToLines(tpl.roles.B.responsibilities);
  document.getElementById('roleBForbidden').value = arrayToLines(tpl.roles.B.forbidden);

  document.getElementById('taskTitle').value = tpl.task.title;
  document.getElementById('taskConstraints').value = arrayToLines(tpl.task.constraints);
}

function showPrompts(prompts, profile) {
  const elA = document.getElementById('promptA');
  const elB = document.getElementById('promptB');
  elA.textContent = prompts.A;
  elB.textContent = prompts.B;
  elA.classList.remove('empty');
  elB.classList.remove('empty');
  document.getElementById('promptAName').textContent = profile.roles.A.name;
  document.getElementById('promptBName').textContent = profile.roles.B.name;
}

function renderHubStatus(state) {
  const dot = document.querySelector('.status-dot');
  const text = document.getElementById('statusText');
  if (!state) {
    dot.className = 'status-dot offline';
    text.textContent = t('status.offline');
    return;
  }
  dot.className = 'status-dot online';
  text.textContent = t('status.online', { epoch: state.epoch, turn: state.turn });
  document.getElementById('stateJson').textContent = JSON.stringify(state, null, 2);
}

async function checkHub() {
  try {
    hubState = await api('/state');
    renderHubStatus(hubState);
    return hubState;
  } catch {
    hubState = null;
    renderHubStatus(null);
    return null;
  }
}

async function loadTemplates() {
  templates = await api('/templates');
  renderTemplateOptions();
  applyTemplateToForm(document.getElementById('templateSelect').value);
}

async function applySetup() {
  setError('');
  const profile = buildProfile();
  if (!profile.task.title) {
    setError(t('error.taskRequired'));
    return;
  }

  const btn = document.getElementById('generateBtn');
  btn.disabled = true;
  try {
    const result = await api('/setup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile),
    });
    showPrompts(result.prompts, profile);
    hubState = result.state;
    renderHubStatus(hubState);
    showToast(t('toast.applied'));
  } catch (err) {
    setError(err.message || t('error.setupFailed'));
  } finally {
    btn.disabled = false;
  }
}

async function loadExistingProfile() {
  const profile = await api('/profile');
  document.getElementById('templateSelect').value = profile.template || 'dev-review';
  renderTemplateOptions();

  ['A', 'B'].forEach((role) => {
    const r = profile.roles[role];
    const prefix = role === 'A' ? 'roleA' : 'roleB';
    document.getElementById(`${prefix}Name`).value = r.name;
    document.getElementById(`${prefix}Goal`).value = r.goal;
    document.getElementById(`${prefix}Resp`).value = arrayToLines(r.responsibilities);
    document.getElementById(`${prefix}Forbidden`).value = arrayToLines(r.forbidden);
  });

  document.getElementById('taskTitle').value = profile.task?.title || '';
  document.getElementById('taskBranch').value = profile.task?.branch || 'main';
  document.getElementById('taskConstraints').value = arrayToLines(profile.task?.constraints);
  document.getElementById('maxEpochs').value = profile.maxEpochs || 20;

  if (profile.lang && profile.lang !== window.currentLang) {
    applyLanguage(profile.lang);
  }

  const [pA, pB] = await Promise.all([api('/prompt/A'), api('/prompt/B')]);
  showPrompts({ A: pA.prompt, B: pB.prompt }, profile);
}

window.onLanguageChange = async () => {
  if (Object.keys(templates).length) {
    renderTemplateOptions();
    const templateId = document.getElementById('templateSelect').value;
    if (templateId && templates[templateId]) {
      applyTemplateToForm(templateId);
    }
  }
  updateEmptyPromptPlaceholders();
  renderHubStatus(hubState);

  const hasPrompts = !document.getElementById('promptA').classList.contains('empty');
  if (hasPrompts && hubState?.has_profile) {
    try {
      const profile = buildProfile();
      const result = await api('/setup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profile),
      });
      showPrompts(result.prompts, profile);
      hubState = result.state;
      renderHubStatus(hubState);
    } catch {
      // keep existing prompts if re-apply fails
    }
  }
};

document.addEventListener('DOMContentLoaded', async () => {
  updateEmptyPromptPlaceholders();

  const state = await checkHub();
  if (!state) {
    setError(t('error.hubOffline'));
    document.getElementById('generateBtn').disabled = true;
    return;
  }

  await loadTemplates();
  if (state.has_profile) {
    try {
      await loadExistingProfile();
    } catch {
      // no profile
    }
  }

  document.getElementById('templateSelect').addEventListener('change', (e) => {
    applyTemplateToForm(e.target.value);
  });

  document.getElementById('generateBtn').addEventListener('click', applySetup);

  document.querySelectorAll('.btn-copy').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const id = btn.dataset.target;
      const el = document.getElementById(id);
      if (el.classList.contains('empty')) return;
      await navigator.clipboard.writeText(el.textContent);
      showToast(t('toast.copied'));
    });
  });
});
