const TEMPLATES = {
  'dev-review': {
    roles: {
      A: {
        name: 'builder',
        goal: 'Implement the user task in small slices; hand off to reviewer when each slice is done.',
        responsibilities: [
          'Read current task and constraints from hub',
          'Implement the next small slice on state.branch',
          'Signal reviewer when a slice is complete',
        ],
        forbidden: [
          'Do not fix review feedback — that is B\'s job',
          'Do not push unless user asks',
        ],
        wakeSentinel: 'AGENT_LOOP_WAKE_A',
      },
      B: {
        name: 'reviewer',
        goal: 'Review builder changes; fix issues directly and commit when appropriate.',
        responsibilities: [
          'Review A\'s diff and commits',
          'Fix clear issues yourself',
          'Commit with English message, then signal A to continue',
        ],
        forbidden: [
          'Do not expand scope beyond the task',
          'Do not push unless user asks',
        ],
        wakeSentinel: 'AGENT_LOOP_WAKE_B',
      },
    },
    workflow: {
      initialTurn: 'A',
      transitions: [
        { from: 'A', to: 'B', action: 'review' },
        { from: 'B', to: 'A', action: 'continue_dev' },
        { from: 'B', to: 'A', action: 'blocked', stop: true },
      ],
    },
    task: {
      title: 'Implement feature X',
      constraints: ['Do not start test servers', 'Commit messages in English'],
    },
  },

  'test-fix': {
    roles: {
      A: {
        name: 'tester',
        goal: 'Write and run tests for the given scope; report failures to fixer.',
        responsibilities: [
          'Add or update test cases for the task',
          'Run tests and capture failures',
          'Signal fixer with failure summary',
        ],
        forbidden: ['Do not fix production code — that is B\'s job'],
        wakeSentinel: 'AGENT_LOOP_WAKE_A',
      },
      B: {
        name: 'fixer',
        goal: 'Fix code until tests pass; commit fixes and hand back to tester.',
        responsibilities: [
          'Read test failures from payload',
          'Fix code until tests pass',
          'Commit and signal tester for next round',
        ],
        forbidden: ['Do not weaken tests to make them pass'],
        wakeSentinel: 'AGENT_LOOP_WAKE_B',
      },
    },
    workflow: {
      initialTurn: 'A',
      transitions: [
        { from: 'A', to: 'B', action: 'review' },
        { from: 'B', to: 'A', action: 'continue_dev' },
      ],
    },
    task: {
      title: 'Add tests for module Y',
      constraints: ['Run tests with timeout', 'No flaky tests'],
    },
  },

  'plan-implement': {
    roles: {
      A: {
        name: 'architect',
        goal: 'Produce a concise technical plan for the task.',
        responsibilities: [
          'Break down requirements into implementation steps',
          'Define interfaces and file layout',
          'Signal implementer with plan',
        ],
        forbidden: ['Do not write implementation code'],
        wakeSentinel: 'AGENT_LOOP_WAKE_A',
      },
      B: {
        name: 'implementer',
        goal: 'Implement according to the plan; commit working code.',
        responsibilities: [
          'Follow architect plan from payload',
          'Implement and self-check',
          'Commit and signal architect for next slice if needed',
        ],
        forbidden: ['Do not change architecture without signaling blocked'],
        wakeSentinel: 'AGENT_LOOP_WAKE_B',
      },
    },
    workflow: {
      initialTurn: 'A',
      transitions: [
        { from: 'A', to: 'B', action: 'review' },
        { from: 'B', to: 'A', action: 'continue_dev' },
      ],
    },
    task: {
      title: 'Design and build API endpoint Z',
      constraints: ['Keep plan under 200 lines', 'Match existing code style'],
    },
  },

  'security-fix': {
    roles: {
      A: {
        name: 'auditor',
        goal: 'Security-review changes; flag vulnerabilities.',
        responsibilities: [
          'Scan diff for security issues',
          'Classify severity',
          'Signal developer with findings',
        ],
        forbidden: ['Do not fix code — report only'],
        wakeSentinel: 'AGENT_LOOP_WAKE_A',
      },
      B: {
        name: 'developer',
        goal: 'Fix reported security issues and commit.',
        responsibilities: [
          'Address auditor findings',
          'Add regression tests where needed',
          'Commit and signal auditor for re-check',
        ],
        forbidden: ['Do not ignore critical findings'],
        wakeSentinel: 'AGENT_LOOP_WAKE_B',
      },
    },
    workflow: {
      initialTurn: 'A',
      transitions: [
        { from: 'A', to: 'B', action: 'review' },
        { from: 'B', to: 'A', action: 'continue_dev' },
        { from: 'B', to: 'A', action: 'blocked', stop: true },
      ],
    },
    task: {
      title: 'Security audit recent auth changes',
      constraints: ['Follow OWASP top 10', 'No secrets in commits'],
    },
  },
};

function linesToArray(text) {
  return text
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean);
}

function arrayToLines(arr) {
  return (arr || []).join('\n');
}

function renderTemplateOptions() {
  const select = document.getElementById('templateSelect');
  if (!select) return;
  const current = select.value || Object.keys(TEMPLATES)[0];
  select.innerHTML = '';
  Object.keys(TEMPLATES).forEach((id) => {
    const opt = document.createElement('option');
    opt.value = id;
    opt.textContent = typeof t === 'function' ? (t(`tpl.${id}`) || id) : id;
    select.appendChild(opt);
  });
  if (TEMPLATES[current]) select.value = current;
}

function getFormProfile() {
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
    workflow: TEMPLATES[document.getElementById('templateSelect').value].workflow,
    task: {
      title: document.getElementById('taskTitle').value.trim(),
      branch: document.getElementById('taskBranch').value.trim(),
      constraints: linesToArray(document.getElementById('taskConstraints').value),
    },
    maxEpochs: parseInt(document.getElementById('maxEpochs').value, 10) || 20,
    lang: window.currentLang || 'en',
  };
}

function buildPrompt(role, profile, hubUrl) {
  const r = profile.roles[role];
  const lang = window.currentLang === 'zh' ? 'zh' : 'en';
  const roleLabel = role === 'A' ? (lang === 'zh' ? '角色 A' : 'role A') : (lang === 'zh' ? '角色 B' : 'role B');

  if (lang === 'zh') {
    return `/loop dynamic 你是 coord ${roleLabel}（${r.name}）。协调 Hub：${hubUrl}

第一步：若尚未运行，启动后台 watcher（记录 PID）：
while true; do
  resp=$(curl -sf --max-time 3700 "${hubUrl}/wait/${role}" 2>/dev/null || echo "")
  [ -z "$resp" ] && continue
  echo "${r.wakeSentinel} {\\"hub\\":$resp}"
done

每轮被唤醒或首次执行时：
1. curl -s ${hubUrl}/profile  → 读取 roles、workflow、task 约束
2. curl -s ${hubUrl}/state    → 读取 epoch、turn、stopped
3. 若 stopped=true 或 epoch >= max_epochs → 总结后停止 loop
4. 按 profile 中 ${roleLabel} 的 goal、responsibilities、forbidden 执行
5. 按 workflow.transitions 在完成后 POST ${hubUrl}/signal 给对端
6. 同一 epoch 只处理一次；不 push 除非用户要求`;
  }

  return `/loop dynamic You are coord ${roleLabel} (${r.name}). Hub: ${hubUrl}

Step 1 — start background watcher if not running (record PID):
while true; do
  resp=$(curl -sf --max-time 3700 "${hubUrl}/wait/${role}" 2>/dev/null || echo "")
  [ -z "$resp" ] && continue
  echo "${r.wakeSentinel} {\\"hub\\":$resp}"
done

Each wake or first run:
1. curl -s ${hubUrl}/profile  → roles, workflow, task constraints
2. curl -s ${hubUrl}/state    → epoch, turn, stopped
3. If stopped=true or epoch >= max_epochs → summarize and stop loop
4. Follow ${roleLabel} goal, responsibilities, forbidden from profile
5. On completion POST ${hubUrl}/signal per workflow.transitions
6. Process each epoch once; do not push unless user asks`;
}

function applyTemplate(templateId) {
  const tpl = getLocalizedTemplate(templateId, TEMPLATES);
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

function generatePrompts() {
  const profile = getFormProfile();
  const hubUrl = document.getElementById('hubUrl').value.trim().replace(/\/$/, '');

  const promptA = buildPrompt('A', profile, hubUrl);
  const promptB = buildPrompt('B', profile, hubUrl);

  const elA = document.getElementById('promptA');
  const elB = document.getElementById('promptB');
  elA.textContent = promptA;
  elB.textContent = promptB;
  elA.classList.remove('empty');
  elB.classList.remove('empty');

  document.getElementById('promptAName').textContent = profile.roles.A.name;
  document.getElementById('promptBName').textContent = profile.roles.B.name;
  document.getElementById('profileJson').textContent = JSON.stringify(profile, null, 2);
}

function showToast(message) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2000);
}

function initSetupUI() {
  const templateSelect = document.getElementById('templateSelect');
  const generateBtn = document.getElementById('generateBtn');

  renderTemplateOptions();
  applyTemplate(templateSelect.value);

  const placeholders = ['promptA', 'promptB'];
  placeholders.forEach((id) => {
    const el = document.getElementById(id);
    const key = id === 'promptA' ? 'setup.placeholderA' : 'setup.placeholderB';
    el.textContent = typeof t === 'function' ? t(key) : '';
    el.classList.add('empty');
  });

  templateSelect.addEventListener('change', () => applyTemplate(templateSelect.value));
  generateBtn.addEventListener('click', generatePrompts);

  document.querySelectorAll('.btn-copy').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const targetId = btn.dataset.target;
      const text = document.getElementById(targetId)?.textContent;
      if (!text || document.getElementById(targetId)?.classList.contains('empty')) return;

      try {
        await navigator.clipboard.writeText(text);
        const orig = btn.textContent;
        btn.textContent = typeof t === 'function' ? t('setup.copied') : 'Copied!';
        btn.classList.add('copied');
        showToast(btn.textContent);
        setTimeout(() => {
          btn.textContent = orig;
          btn.classList.remove('copied');
        }, 1500);
      } catch {
        showToast(typeof t === 'function' ? t('setup.copyFailed') : 'Copy failed');
      }
    });
  });
}

window.onLanguageChange = () => {
  renderTemplateOptions();
  const templateId = document.getElementById('templateSelect')?.value;
  if (templateId && TEMPLATES[templateId]) {
    applyTemplate(templateId);
  }

  ['promptA', 'promptB'].forEach((id) => {
    const el = document.getElementById(id);
    if (el?.classList.contains('empty')) {
      const key = id === 'promptA' ? 'setup.placeholderA' : 'setup.placeholderB';
      el.textContent = t(key);
    }
  });

  if (!document.getElementById('promptA')?.classList.contains('empty')) {
    generatePrompts();
  }
};

document.querySelectorAll('a[href^="#"]').forEach((link) => {
  link.addEventListener('click', (e) => {
    const id = link.getAttribute('href');
    if (id === '#') return;
    const target = document.querySelector(id);
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
});

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
);

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.feature-card, .arch-card, .pipeline-step').forEach((el) => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(12px)';
    el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
    observer.observe(el);
  });

  initSetupUI();
});
