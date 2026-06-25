const STORAGE_KEY = 'cursor-ab-coord-ui-lang';

const translations = {
  en: {
    'page.title': 'cursor-ab-coord setup',
    'status.connecting': 'Connecting…',
    'status.online': 'Hub online · epoch {epoch} · turn {turn}',
    'status.offline': 'Hub offline',
    'config.title': 'Configuration',
    'config.generate': 'Generate & apply',
    'config.template': 'Workflow template',
    'role.a': 'Role A',
    'role.b': 'Role B',
    'field.name': 'Name',
    'field.goal': 'Goal',
    'field.responsibilities': 'Responsibilities (one per line)',
    'field.forbidden': 'Forbidden (one per line)',
    'task.title': 'Runtime task',
    'field.taskTitle': 'Title',
    'field.branch': 'Branch',
    'field.maxEpochs': 'Max epochs',
    'field.constraints': 'Constraints (one per line)',
    'field.taskPlaceholder': 'Implement feature X',
    'prompts.title': 'Session prompts',
    'prompts.hint': 'Start <strong>Session B</strong> first, then <strong>Session A</strong>.',
    'prompts.placeholder': 'Apply configuration to generate prompts…',
    'prompts.copy': 'Copy',
    'prompts.hubState': 'Hub state',
    'toast.copied': 'Copied',
    'toast.applied': 'Configuration applied',
    'error.hubOffline': 'Hub is not running. Start it with ./scripts/start.sh',
    'error.taskRequired': 'Task title is required',
    'error.setupFailed': 'Setup failed',
    'tpl.dev-review': 'Dev + Review (default)',
    'tpl.test-fix': 'Test + Fix',
    'tpl.plan-implement': 'Plan + Implement',
    'tpl.security-fix': 'Security + Fix',
  },

  zh: {
    'page.title': 'cursor-ab-coord 配置',
    'status.connecting': '连接中…',
    'status.online': 'Hub 在线 · 轮次 {epoch} · 当前 {turn}',
    'status.offline': 'Hub 离线',
    'config.title': '配置',
    'config.generate': '生成并应用',
    'config.template': '工作流模板',
    'role.a': '角色 A',
    'role.b': '角色 B',
    'field.name': '名称',
    'field.goal': '目标',
    'field.responsibilities': '职责（每行一条）',
    'field.forbidden': '禁止事项（每行一条）',
    'task.title': '运行时任务',
    'field.taskTitle': '标题',
    'field.branch': '分支',
    'field.maxEpochs': '最大轮次',
    'field.constraints': '约束（每行一条）',
    'field.taskPlaceholder': '实现功能 X',
    'prompts.title': '会话提示词',
    'prompts.hint': '先启动<strong>会话 B</strong>，再启动<strong>会话 A</strong>。',
    'prompts.placeholder': '点击「生成并应用」后显示提示词…',
    'prompts.copy': '复制',
    'prompts.hubState': 'Hub 状态',
    'toast.copied': '已复制',
    'toast.applied': '配置已应用',
    'error.hubOffline': 'Hub 未运行，请执行 ./scripts/start.sh',
    'error.taskRequired': '请填写任务标题',
    'error.setupFailed': '应用配置失败',
    'tpl.dev-review': '开发 + 审查（默认）',
    'tpl.test-fix': '测试 + 修复',
    'tpl.plan-implement': '方案 + 实现',
    'tpl.security-fix': '安全 + 修复',
  },
};

const templatesZh = {
  'dev-review': {
    roles: {
      A: {
        name: '开发者',
        goal: '按小步实现用户任务；每完成一块即交给审查者。',
        responsibilities: [
          '从 Hub 读取当前任务与约束',
          '在 state.branch 上实现下一小块功能',
          '完成一块后 signal 审查者',
        ],
        forbidden: [
          '不要修 review 反馈 — 那是 B 的工作',
          '不要 push，除非用户要求',
        ],
      },
      B: {
        name: '审查者',
        goal: '审查开发者变更；能修则直接修并提交。',
        responsibilities: [
          '审查 A 的 diff 与提交',
          '直接修复明确问题',
          '用英文 message 提交，然后 signal A 继续',
        ],
        forbidden: [
          '不要扩展任务范围',
          '不要 push，除非用户要求',
        ],
      },
    },
    task: {
      title: '实现功能 X',
      constraints: ['不要启动测试服务器', '提交信息用英文'],
    },
  },
  'test-fix': {
    roles: {
      A: {
        name: '测试者',
        goal: '为给定范围编写并运行测试；将失败报告给修复者。',
        responsibilities: [
          '为任务添加或更新测试用例',
          '运行测试并记录失败',
          '将失败摘要 signal 给修复者',
        ],
        forbidden: ['不要修改生产代码 — 那是 B 的工作'],
      },
      B: {
        name: '修复者',
        goal: '修复代码直至测试通过；提交修复并交回测试者。',
        responsibilities: [
          '阅读 payload 中的测试失败信息',
          '修复代码直至测试通过',
          '提交并 signal 测试者进行下一轮',
        ],
        forbidden: ['不要削弱测试来凑通过'],
      },
    },
    task: {
      title: '为模块 Y 添加测试',
      constraints: ['运行测试需加超时', '不要写不稳定测试'],
    },
  },
  'plan-implement': {
    roles: {
      A: {
        name: '架构师',
        goal: '为任务产出简洁的技术方案。',
        responsibilities: [
          '将需求拆解为实现步骤',
          '定义接口与文件布局',
          '将方案 signal 给实现者',
        ],
        forbidden: ['不要写实现代码'],
      },
      B: {
        name: '实现者',
        goal: '按方案实现；提交可工作的代码。',
        responsibilities: [
          '遵循 payload 中的架构师方案',
          '实现并自检',
          '提交后如需继续则 signal 架构师',
        ],
        forbidden: ['不要擅自改架构，除非 signal blocked'],
      },
    },
    task: {
      title: '设计并实现 API 端点 Z',
      constraints: ['方案控制在 200 行以内', '匹配现有代码风格'],
    },
  },
  'security-fix': {
    roles: {
      A: {
        name: '审计员',
        goal: '对变更做安全审查；标记漏洞。',
        responsibilities: [
          '扫描 diff 中的安全问题',
          '评定严重级别',
          '将发现 signal 给开发者',
        ],
        forbidden: ['不要改代码 — 只报告'],
      },
      B: {
        name: '开发者',
        goal: '修复报告的安全问题并提交。',
        responsibilities: [
          '处理审计员发现的问题',
          '必要时添加回归测试',
          '提交并 signal 审计员复检',
        ],
        forbidden: ['不要忽略严重问题'],
      },
    },
    task: {
      title: '安全审计近期认证相关变更',
      constraints: ['遵循 OWASP Top 10', '提交中不要含密钥'],
    },
  },
};

function detectLanguage() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === 'en' || stored === 'zh') return stored;
  const langs = navigator.languages || [navigator.language || 'en'];
  for (const lang of langs) {
    if (lang.toLowerCase().startsWith('zh')) return 'zh';
  }
  return 'en';
}

function t(key, vars = {}) {
  const lang = window.currentLang || 'en';
  let text = translations[lang]?.[key] ?? translations.en[key] ?? key;
  Object.entries(vars).forEach(([k, v]) => {
    text = text.replace(`{${k}}`, v);
  });
  return text;
}

function applyLanguage(lang) {
  const dict = translations[lang];
  if (!dict) return;

  document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
  document.title = dict['page.title'] || translations.en['page.title'];

  document.querySelectorAll('[data-i18n]').forEach((el) => {
    const key = el.getAttribute('data-i18n');
    const text = dict[key];
    if (text !== undefined) el.innerHTML = text;
  });

  document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
    const key = el.getAttribute('data-i18n-placeholder');
    const text = dict[key];
    if (text !== undefined) el.placeholder = text;
  });

  document.querySelectorAll('[data-placeholder-key]').forEach((el) => {
    if (el.classList.contains('empty')) {
      const key = el.getAttribute('data-placeholder-key');
      const text = dict[key];
      if (text !== undefined) el.textContent = text;
    }
  });

  document.querySelectorAll('.lang-opt').forEach((el) => {
    el.classList.toggle('active', el.dataset.lang === lang);
  });

  localStorage.setItem(STORAGE_KEY, lang);
  window.currentLang = lang;

  if (typeof window.onLanguageChange === 'function') {
    window.onLanguageChange(lang);
  }
}

function initI18n() {
  applyLanguage(detectLanguage());
  const toggle = document.getElementById('langToggle');
  if (toggle) {
    toggle.addEventListener('click', () => {
      const next = window.currentLang === 'zh' ? 'en' : 'zh';
      applyLanguage(next);
    });
  }
}

function getLocalizedTemplate(templateId, serverTemplates) {
  if (window.currentLang === 'zh' && templatesZh[templateId]) {
    const zh = templatesZh[templateId];
    const base = serverTemplates[templateId];
    return {
      ...base,
      roles: {
        A: { ...base.roles.A, ...zh.roles.A },
        B: { ...base.roles.B, ...zh.roles.B },
      },
      task: { ...base.task, ...zh.task },
    };
  }
  return serverTemplates[templateId];
}

document.addEventListener('DOMContentLoaded', initI18n);
