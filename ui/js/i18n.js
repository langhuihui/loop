const STORAGE_KEY = 'cursor-ab-coord-ui-lang';

const translations = {
  en: {
    'page.title': 'cursor-ab-coord setup',
    'status.connecting': 'Connecting…',
    'status.online': 'Hub online · epoch {epoch} · turn {turn}',
    'status.offline': 'Hub offline',
    'config.title': 'Configuration',
    'config.generate': 'Generate & apply',
    'config.importProfile': 'Import profile',
    'config.exportProfile': 'Export profile',
    'config.clearState': 'Clear state',
    'config.clearConfirm': 'Clear saved profile, state, history, and pending messages?',
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
    'prompts.copyAll': 'Copy all',
    'prompts.copyAllTitle': 'cursor-ab-coord startup prompts',
    'prompts.copyAllOrder': 'Paste order: start Session B first, then Session A.',
    'prompts.noConstraints': '(none)',
    'prompts.hubState': 'Hub state',
    'prompts.hubHistory': 'Hub history',
    'prompts.refresh': 'Refresh',
    'snapshot.refresh': 'Refresh snapshot',
    'health.ok': 'No health warnings.',
    'outcomes.label': 'Outcomes',
    'lessons.title': 'Shared lessons',
    'lessons.empty': 'No lessons yet.',
    'lessons.placeholder': 'Reusable note or pitfall',
    'lessons.add': 'Add lesson',
    'toast.copied': 'Copied',
    'toast.applied': 'Configuration applied',
    'toast.cleared': 'State cleared',
    'toast.exported': 'Profile exported',
    'toast.imported': 'Profile imported',
    'toast.lessonAdded': 'Lesson added',
    'error.hubOffline': 'Hub is not running. Start it with ./scripts/start.sh',
    'error.taskRequired': 'Task title is required',
    'error.setupFailed': 'Setup failed',
    'error.clearFailed': 'Clear failed',
    'error.importFailed': 'Import failed',
    'error.exportFailed': 'Export failed',
    'error.maxEpochsInteger': 'Max epochs must be a positive integer',
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
    'config.importProfile': '导入 Profile',
    'config.exportProfile': '导出 Profile',
    'config.clearState': '清空状态',
    'config.clearConfirm': '确定清空已保存的 profile、状态、历史和待处理消息吗？',
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
    'prompts.copyAll': '复制全部',
    'prompts.copyAllTitle': 'cursor-ab-coord 启动提示词',
    'prompts.copyAllOrder': '粘贴顺序：先启动会话 B，再启动会话 A。',
    'prompts.noConstraints': '（无）',
    'prompts.hubState': 'Hub 状态',
    'prompts.hubHistory': 'Hub 历史',
    'prompts.refresh': '刷新',
    'snapshot.refresh': '刷新快照',
    'health.ok': '暂无健康警告。',
    'outcomes.label': '结果统计',
    'lessons.title': '共享经验',
    'lessons.empty': '暂无经验。',
    'lessons.placeholder': '可复用经验或坑点',
    'lessons.add': '添加经验',
    'toast.copied': '已复制',
    'toast.applied': '配置已应用',
    'toast.cleared': '状态已清空',
    'toast.exported': 'Profile 已导出',
    'toast.imported': 'Profile 已导入',
    'toast.lessonAdded': '经验已添加',
    'error.hubOffline': 'Hub 未运行，请执行 ./scripts/start.sh',
    'error.taskRequired': '请填写任务标题',
    'error.setupFailed': '应用配置失败',
    'error.clearFailed': '清空状态失败',
    'error.importFailed': '导入失败',
    'error.exportFailed': '导出失败',
    'error.maxEpochsInteger': '最大轮次必须是正整数',
    'tpl.dev-review': '开发 + 审查（默认）',
    'tpl.test-fix': '测试 + 修复',
    'tpl.plan-implement': '方案 + 实现',
    'tpl.security-fix': '安全 + 修复',
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

document.addEventListener('DOMContentLoaded', initI18n);
