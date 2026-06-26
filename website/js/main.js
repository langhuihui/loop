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

function readMaxEpochs() {
  const raw = document.getElementById('maxEpochs').value.trim();
  const value = Number(raw);
  if (!raw || !Number.isInteger(value) || value < 1) {
    throw new Error(typeof t === 'function' ? t('setup.maxEpochsError') : 'Max epochs must be a positive integer');
  }
  return value;
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
    maxEpochs: readMaxEpochs(),
    lang: window.currentLang || 'en',
  };
}

function buildPrompt(role, profile, hubUrl) {
  const r = profile.roles[role];
  const lang = window.currentLang === 'zh' ? 'zh' : 'en';
  const roleLabel = role === 'A' ? (lang === 'zh' ? '角色 A' : 'role A') : (lang === 'zh' ? '角色 B' : 'role B');
  const watcherSnippet = `last_wake_id=0
while true; do
  resp=$(curl -sf --max-time 3700 "${hubUrl}/wait/${role}?since=\${last_wake_id}" 2>/dev/null || echo "")
  [ -z "$resp" ] && continue
  next_wake_id=$(printf '%s' "$resp" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("id", 0))' 2>/dev/null || echo 0)
  if [ "$next_wake_id" -gt "$last_wake_id" ] 2>/dev/null; then last_wake_id="$next_wake_id"; fi
  echo "${r.wakeSentinel} {\\"hub\\":$resp}"
done`;

  if (lang === 'zh') {
    return `/loop dynamic 你是 coord ${roleLabel}（${r.name}）。协调 Hub：${hubUrl}

第一步：若尚未运行，启动后台 watcher（记录 PID）。watcher 必须输出到当前 agent 终端 stdout；不要重定向到文件，否则 /loop 看不到唤醒。watcher 使用 wake id 自愈去重，多个 watcher 不会抢走彼此的消息：
${watcherSnippet}

每轮被唤醒或首次执行时：
1. 每轮都重新 curl -s ${hubUrl}/snapshot；不要依赖记忆，尤其是上下文压缩后
2. 若 snapshot.state.stopped=true、recommended_action=stop，或 epoch >= max_epochs → 总结后停止 loop
3. 判断是否轮到你：被 watcher 唤醒即表示轮到你；若为首次启动且未收到唤醒，仅当 state.turn == ${role} 时才执行，否则回到 watcher 等待对端 signal
4. 按 profile 中 ${roleLabel} 的 goal、responsibilities、forbidden 执行
5. 完成后先记录结果，再 POST ${hubUrl}/signal 给对端；payload.outcome 必须是 progress、blocked、no-op、done 之一（hub 默认把 turn 设为 target）
6. 若发现可复用的经验/坑点，POST ${hubUrl}/lessons，包含 role、epoch、text
7. 同一 epoch 只处理一次；不 push 除非用户要求`;
  }

  return `/loop dynamic You are coord ${roleLabel} (${r.name}). Hub: ${hubUrl}

Step 1 — start background watcher if not running (record PID). The watcher must print to this agent terminal's stdout; do not redirect it to a file, or /loop will not see the wake. The watcher uses wake ids for self-healing dedupe, so duplicate watchers cannot steal each other's wake:
${watcherSnippet}

Each wake or first run:
1. Re-read curl -s ${hubUrl}/snapshot every round; do not rely on memory, especially after context compaction
2. If snapshot.state.stopped=true, recommended_action=stop, or epoch >= max_epochs → summarize and stop loop
3. Decide whether it is your turn: being woken means it is your turn; on a first run without a wake, only act when state.turn == ${role}, otherwise return to the watcher and wait for the other role's signal
4. Follow ${roleLabel} goal, responsibilities, forbidden from profile
5. Record the result before advancing, then POST ${hubUrl}/signal to the other role; payload.outcome must be one of progress, blocked, no-op, done (the hub defaults turn to the target)
6. When you learn a reusable lesson or pitfall, POST ${hubUrl}/lessons with role, epoch, text
7. Process each epoch once; do not push unless user asks`;
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
  let profile;
  try {
    profile = getFormProfile();
  } catch (err) {
    window.alert(err.message);
    return;
  }
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
