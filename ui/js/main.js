const API = '';

let templates = {};
let hubState = null;
let isBusy = false;
let isRestoringProfile = false;
let currentPrompts = null;
let currentProfile = null;
let currentLessons = [];

function linesToArray(text) {
  return text.split('\n').map((s) => s.trim()).filter(Boolean);
}

function arrayToLines(arr) {
  return (arr || []).join('\n');
}

function readMaxEpochs() {
  const raw = document.getElementById('maxEpochs').value.trim();
  const value = Number(raw);
  if (!raw || !Number.isInteger(value) || value < 1) {
    throw new Error(t('error.maxEpochsInteger'));
  }
  return value;
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

function setControlsEnabled(enabled) {
  document.getElementById('generateBtn').disabled = !enabled;
  document.getElementById('clearStateBtn').disabled = !enabled;
  document.getElementById('refreshSnapshotBtn').disabled = !enabled;
  document.getElementById('refreshHistoryBtn').disabled = !enabled;
  document.getElementById('refreshLessonsBtn').disabled = !enabled;
  document.getElementById('addLessonBtn').disabled = !enabled;
}

function setBusy(busy) {
  isBusy = busy;
  setControlsEnabled(Boolean(hubState) && !busy);
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
    if (!res.ok) {
      const details = Array.isArray(data.errors) ? `: ${data.errors.join('; ')}` : '';
      throw new Error(`${data.error || `HTTP ${res.status}`}${details}`);
    }
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
    maxEpochs: readMaxEpochs(),
    lang: window.currentLang || 'en',
  };
}

function applyTemplateToForm(templateId) {
  const tpl = templates[templateId];
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

function applyProfileToForm(profile) {
  document.getElementById('templateSelect').value = profile.template || 'dev-review';
  renderTemplateOptions();

  ['A', 'B'].forEach((role) => {
    const r = profile.roles?.[role] || {};
    const prefix = role === 'A' ? 'roleA' : 'roleB';
    document.getElementById(`${prefix}Name`).value = r.name || '';
    document.getElementById(`${prefix}Goal`).value = r.goal || '';
    document.getElementById(`${prefix}Resp`).value = arrayToLines(r.responsibilities);
    document.getElementById(`${prefix}Forbidden`).value = arrayToLines(r.forbidden);
  });

  document.getElementById('taskTitle').value = profile.task?.title || '';
  document.getElementById('taskBranch').value = profile.task?.branch || 'main';
  document.getElementById('taskConstraints').value = arrayToLines(profile.task?.constraints);
  document.getElementById('maxEpochs').value = profile.maxEpochs || 20;
}

function showPrompts(prompts, profile) {
  const elA = document.getElementById('promptA');
  const elB = document.getElementById('promptB');
  currentPrompts = prompts;
  currentProfile = profile;
  elA.textContent = prompts.A;
  elB.textContent = prompts.B;
  elA.classList.remove('empty');
  elB.classList.remove('empty');
  document.getElementById('promptAName').textContent = profile.roles.A.name;
  document.getElementById('promptBName').textContent = profile.roles.B.name;
  document.getElementById('copyAllBtn').disabled = false;
}

function resetPrompts() {
  currentPrompts = null;
  currentProfile = null;
  ['promptA', 'promptB'].forEach((id) => {
    const el = document.getElementById(id);
    el.classList.add('empty');
    el.textContent = t('prompts.placeholder');
  });
  document.getElementById('promptAName').textContent = '—';
  document.getElementById('promptBName').textContent = '—';
  document.getElementById('copyAllBtn').disabled = true;
}

function buildAllPromptsText() {
  if (!currentPrompts || !currentProfile) return '';
  const task = currentProfile.task || {};
  const roleB = currentProfile.roles?.B?.name || 'B';
  const roleA = currentProfile.roles?.A?.name || 'A';
  const constraints = task.constraints?.length
    ? task.constraints.map((item) => `- ${item}`).join('\n')
    : t('prompts.noConstraints');

  return [
    t('prompts.copyAllTitle'),
    '',
    `${t('field.taskTitle')}: ${task.title || ''}`,
    `${t('field.branch')}: ${task.branch || 'main'}`,
    `${t('field.constraints')}:`,
    constraints,
    '',
    t('prompts.copyAllOrder'),
    '',
    `===== Session B (${roleB}) =====`,
    currentPrompts.B,
    '',
    `===== Session A (${roleA}) =====`,
    currentPrompts.A,
  ].join('\n');
}

function renderHubStatus(state) {
  const dot = document.querySelector('.status-dot');
  const text = document.getElementById('statusText');
  if (!state) {
    dot.className = 'status-dot offline';
    text.textContent = t('status.offline');
    if (!isBusy) setControlsEnabled(false);
    return;
  }
  dot.className = 'status-dot online';
  text.textContent = t('status.online', { epoch: state.epoch, turn: state.turn });
  document.getElementById('stateJson').textContent = JSON.stringify(state, null, 2);
  if (!isBusy) setControlsEnabled(true);
}

function renderHealthWarnings(warnings) {
  const el = document.getElementById('healthWarnings');
  el.textContent = '';

  if (!warnings?.length) {
    el.classList.add('empty');
    el.textContent = t('health.ok');
    return;
  }

  el.classList.remove('empty');
  warnings.forEach((warning) => {
    const item = document.createElement('div');
    item.className = 'health-warning';
    item.textContent = warning;
    el.appendChild(item);
  });
}

function renderOutcomeCounts(counts = {}) {
  const el = document.getElementById('outcomeCounts');
  const parts = ['progress', 'blocked', 'no-op', 'done'].map(
    (key) => `${key}: ${counts[key] || 0}`,
  );
  el.textContent = `${t('outcomes.label')}: ${parts.join(' · ')}`;
}

function chip(label, value, cls = '') {
  return `<span class="summary-chip ${cls}"><span class="chip-key">${label}</span> ${value}</span>`;
}

function renderStatusSummary(state) {
  const el = document.getElementById('statusSummary');
  if (!state) {
    el.innerHTML = `<span class="summary-chip muted">${t('live.waiting')}</span>`;
    return;
  }
  const maxEpochs = state.max_epochs ?? state.maxEpochs;
  const epochVal = maxEpochs ? `${state.epoch} / ${maxEpochs}` : `${state.epoch}`;
  const chips = [
    chip(t('live.epoch'), epochVal),
    chip(t('field.branch'), state.branch || 'main'),
  ];
  if (state.recommended_action) {
    chips.push(chip(t('live.action'), state.recommended_action));
  }
  chips.push(
    state.stopped
      ? chip(t('live.stopped'), '✓', 'danger')
      : chip(t('live.running'), '●', 'ok'),
  );
  if (Number(state.stagnation_count) > 0) {
    chips.push(chip(t('live.stagnation'), state.stagnation_count, 'warn'));
  }
  if (state.verdict) {
    chips.push(chip(t('live.verdict'), state.verdict));
  }
  el.innerHTML = chips.join('');
}

function renderRoleStatus(role, state, runtime) {
  const waiters = runtime?.waiters?.[role] ?? 0;
  const pendingId = runtime?.pending?.[role];
  const lastWake = runtime?.last_wake_id?.[role];

  const turnPill = document.getElementById(`turnPill${role}`);
  turnPill.hidden = !(state && state.turn === role);
  document.getElementById(`statusCard${role}`).classList.toggle(
    'is-turn',
    Boolean(state && state.turn === role),
  );

  const watcherEl = document.getElementById(`watcher${role}`);
  watcherEl.textContent = waiters > 0 ? t('live.watcherOn', { n: waiters }) : t('live.watcherOff');
  watcherEl.className = `metric-val ${waiters > 0 ? 'ok' : 'bad'}`;

  const pendingEl = document.getElementById(`pending${role}`);
  if (pendingId != null) {
    pendingEl.textContent = `#${pendingId}`;
    pendingEl.className = 'metric-val warn';
  } else {
    pendingEl.textContent = t('live.none');
    pendingEl.className = 'metric-val muted';
  }

  const lastWakeEl = document.getElementById(`lastWake${role}`);
  lastWakeEl.textContent = lastWake != null ? `#${lastWake}` : '—';
  lastWakeEl.className = 'metric-val muted';
}

function renderRuntime(state, runtime) {
  renderStatusSummary(state);
  document.getElementById('statusNameA').textContent =
    currentProfile?.roles?.A?.name || t('role.a');
  document.getElementById('statusNameB').textContent =
    currentProfile?.roles?.B?.name || t('role.b');
  renderRoleStatus('A', state, runtime);
  renderRoleStatus('B', state, runtime);
}

function renderLiveHealth(warnings) {
  const el = document.getElementById('liveHealth');
  el.textContent = '';
  if (!warnings?.length) {
    el.classList.add('empty');
    el.textContent = t('health.ok');
    return;
  }
  el.classList.remove('empty');
  warnings.forEach((warning) => {
    const item = document.createElement('div');
    item.className = 'health-warning';
    item.textContent = warning;
    el.appendChild(item);
  });
}

function renderSnapshot(snapshot) {
  const state = snapshot?.state || null;
  const health = snapshot?.health || {};
  const runtime = snapshot?.runtime || null;
  hubState = state ? { ...state, health, runtime } : null;
  renderHubStatus(hubState);
  renderHealthWarnings(health.warnings || []);
  renderLiveHealth(health.warnings || []);
  renderOutcomeCounts(health.outcome_counts || {});
  renderRuntime(state, runtime);
  document.getElementById('historyJson').textContent = JSON.stringify(snapshot?.history || [], null, 2);
  renderLessons(snapshot?.lessons || []);
}

async function checkHub() {
  try {
    const snapshot = await api('/snapshot');
    renderSnapshot(snapshot);
    return hubState;
  } catch {
    hubState = null;
    renderHubStatus(null);
    renderHealthWarnings([]);
    renderLiveHealth([]);
    renderOutcomeCounts({});
    renderRuntime(null, null);
    document.getElementById('historyJson').textContent = '[]';
    renderLessons([]);
    return null;
  }
}

let liveRefreshTimer = null;

function startLiveRefresh() {
  stopLiveRefresh();
  liveRefreshTimer = setInterval(() => {
    if (isBusy) return;
    if (!document.getElementById('autoRefreshToggle')?.checked) return;
    if (document.hidden) return;
    checkHub();
  }, 3000);
}

function stopLiveRefresh() {
  if (liveRefreshTimer) {
    clearInterval(liveRefreshTimer);
    liveRefreshTimer = null;
  }
}

async function loadHistory() {
  try {
    const data = await api('/history?limit=10');
    document.getElementById('historyJson').textContent = JSON.stringify(data.history || [], null, 2);
  } catch {
    document.getElementById('historyJson').textContent = '[]';
  }
}

function renderLessons(items) {
  currentLessons = items || [];
  const list = document.getElementById('lessonsList');
  list.textContent = '';

  if (!currentLessons.length) {
    list.classList.add('empty');
    list.textContent = t('lessons.empty');
    return;
  }

  list.classList.remove('empty');
  currentLessons.forEach((lesson) => {
    const item = document.createElement('div');
    item.className = 'lesson-item';

    const meta = document.createElement('div');
    meta.className = 'lesson-meta';
    const epoch = lesson.epoch === null || lesson.epoch === undefined ? '-' : lesson.epoch;
    meta.textContent = `#${lesson.id} · ${lesson.role || '-'} · epoch ${epoch}`;

    const text = document.createElement('div');
    text.className = 'lesson-text';
    text.textContent = lesson.text || '';

    item.append(meta, text);
    list.appendChild(item);
  });
}

async function loadLessons() {
  try {
    const data = await api('/lessons?limit=20');
    renderLessons(data.lessons || []);
  } catch {
    renderLessons([]);
  }
}

async function loadTemplates() {
  const suffix = window.currentLang === 'zh' ? '?lang=zh' : '';
  templates = await api(`/templates${suffix}`);
  renderTemplateOptions();
  applyTemplateToForm(document.getElementById('templateSelect').value);
}

async function applySetup() {
  setError('');
  let profile;
  try {
    profile = buildProfile();
  } catch (err) {
    setError(err.message || t('error.setupFailed'));
    return;
  }
  if (!profile.task.title) {
    setError(t('error.taskRequired'));
    return;
  }

  setBusy(true);
  try {
    const result = await api('/setup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile),
    });
    showPrompts(result.prompts, profile);
    await checkHub();
    showToast(t('toast.applied'));
  } catch (err) {
    setError(err.message || t('error.setupFailed'));
  } finally {
    setBusy(false);
  }
}

async function clearState() {
  if (!window.confirm(t('config.clearConfirm'))) return;

  setError('');
  setBusy(true);
  try {
    await api('/clear', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirm: true }),
    });
    resetPrompts();
    applyTemplateToForm(document.getElementById('templateSelect').value);
    await checkHub();
    showToast(t('toast.cleared'));
  } catch (err) {
    setError(err.message || t('error.clearFailed'));
  } finally {
    setBusy(false);
  }
}

function downloadText(filename, text) {
  const blob = new Blob([text], { type: 'application/json;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function exportProfile() {
  let profile;
  try {
    profile = buildProfile();
  } catch (err) {
    setError(err.message || t('error.exportFailed'));
    return;
  }
  const safeTitle = (profile.task.title || 'coord-profile')
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60) || 'coord-profile';
  downloadText(`${safeTitle}.json`, `${JSON.stringify(profile, null, 2)}\n`);
  showToast(t('toast.exported'));
}

async function addLesson() {
  setError('');
  const textEl = document.getElementById('lessonText');
  const text = textEl.value.trim();
  if (!text) return;

  setBusy(true);
  try {
    await api('/lessons', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        role: document.getElementById('lessonRole').value,
        epoch: hubState?.epoch,
        text,
      }),
    });
    textEl.value = '';
    await checkHub();
    showToast(t('toast.lessonAdded'));
  } catch (err) {
    setError(err.message || t('error.setupFailed'));
  } finally {
    setBusy(false);
  }
}

async function importProfile(file) {
  setError('');
  try {
    const profile = JSON.parse(await file.text());
    await api('/validate-profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile),
    });
    if (profile.lang && profile.lang !== window.currentLang) {
      isRestoringProfile = true;
      applyLanguage(profile.lang);
      isRestoringProfile = false;
      await loadTemplates();
    }
    applyProfileToForm(profile);
    resetPrompts();
    showToast(t('toast.imported'));
  } catch (err) {
    setError(err.message || t('error.importFailed'));
  }
}

async function loadExistingProfile() {
  const profile = await api('/profile');

  if (profile.lang && profile.lang !== window.currentLang) {
    isRestoringProfile = true;
    applyLanguage(profile.lang);
    isRestoringProfile = false;
    await loadTemplates();
  }

  applyProfileToForm(profile);

  const [pA, pB] = await Promise.all([api('/prompt/A'), api('/prompt/B')]);
  showPrompts({ A: pA.prompt, B: pB.prompt }, profile);
}

window.onLanguageChange = async () => {
  if (isRestoringProfile) return;

  if (Object.keys(templates).length) {
    await loadTemplates();
  }
  updateEmptyPromptPlaceholders();
  renderLessons(currentLessons);
  renderHealthWarnings(hubState?.health?.warnings || []);
  renderLiveHealth(hubState?.health?.warnings || []);
  renderOutcomeCounts(hubState?.health?.outcome_counts || {});
  renderRuntime(hubState, hubState?.runtime || null);
  renderHubStatus(hubState);

  const hasPrompts = !document.getElementById('promptA').classList.contains('empty');
  if (hasPrompts && hubState?.has_profile) {
    try {
      const profile = buildProfile();
      await api('/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profile),
      });
      const [pA, pB] = await Promise.all([api('/prompt/A'), api('/prompt/B')]);
      showPrompts({ A: pA.prompt, B: pB.prompt }, profile);
      await checkHub();
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
    setControlsEnabled(false);
    return;
  }
  setControlsEnabled(true);

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
  document.getElementById('clearStateBtn').addEventListener('click', clearState);
  document.getElementById('refreshSnapshotBtn').addEventListener('click', checkHub);
  document.getElementById('refreshLiveBtn').addEventListener('click', checkHub);
  document.getElementById('autoRefreshToggle').addEventListener('change', (e) => {
    if (e.target.checked) {
      checkHub();
      startLiveRefresh();
    } else {
      stopLiveRefresh();
    }
  });
  startLiveRefresh();
  document.getElementById('refreshHistoryBtn').addEventListener('click', loadHistory);
  document.getElementById('refreshLessonsBtn').addEventListener('click', loadLessons);
  document.getElementById('addLessonBtn').addEventListener('click', addLesson);
  document.getElementById('lessonText').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addLesson();
    }
  });
  document.getElementById('exportProfileBtn').addEventListener('click', exportProfile);
  document.getElementById('importProfileBtn').addEventListener('click', () => {
    document.getElementById('profileFileInput').click();
  });
  document.getElementById('profileFileInput').addEventListener('change', async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (file) await importProfile(file);
  });
  document.getElementById('copyAllBtn').addEventListener('click', async () => {
    const text = buildAllPromptsText();
    if (!text) return;
    await navigator.clipboard.writeText(text);
    showToast(t('toast.copied'));
  });

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
