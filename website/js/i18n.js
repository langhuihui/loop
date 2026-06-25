const translations = {
  en: {
    'nav.flow': 'Flow',
    'nav.setup': 'Setup UI',
    'nav.arch': 'Architecture',
    'nav.github': 'GitHub',

    'hero.badge': 'Skill · MCP · Local UI · MIT',
    'hero.title1': 'One skill to start,',
    'hero.title2': 'two sessions in sync',
    'hero.desc': 'Run <code>coord-setup</code> in Cursor — MCP starts the hub, you configure roles and tasks in a local UI, then copy generated <code>/loop</code> prompts into Session A and B.',
    'hero.cta': 'Try the setup UI',
    'hero.learn': 'See the flow',

    'flow.title': 'End-to-end flow',
    'flow.desc': 'The hub still handles cross-session wake via long-poll. Skill and UI handle everything before the loop starts.',
    'flow.s1.title': 'Trigger <code>coord-setup</code> skill',
    'flow.s1.desc': 'In any Cursor chat, ask the agent to set up A/B coordination.',
    'flow.s2.title': 'MCP starts the hub',
    'flow.s2.desc': 'Skill calls MCP <code>coord_start</code> — hub listens on <code>127.0.0.1:9900</code>.',
    'flow.s3.title': 'Open the config UI',
    'flow.s3.desc': 'Skill returns a link. Pick a template, edit A/B goals, set task and branch.',
    'flow.s4.title': 'Generate & copy prompts',
    'flow.s4.desc': 'UI writes profile to hub, renders short <code>/loop dynamic</code> prompts for each role.',
    'flow.s5.title': 'Paste into Session B, then A',
    'flow.s5.desc': 'Start B first, then A. Watchers wake each session when the other signals.',
    'flow.lane.user': 'You',
    'flow.lane.runtime': 'Runtime',
    'flow.lane.sessions': 'Sessions',
    'flow.node.skill': 'coord-setup skill',
    'flow.node.ui': 'Config UI',
    'flow.node.prompts': 'Copy prompts',
    'flow.hub': 'Coord Hub',
    'flow.node.a': 'Session A',
    'flow.node.b': 'Session B',

    'setup.title': 'Setup UI preview',
    'setup.desc': 'Interactive mock of the hub config page. In production this lives at <code>GET /ui</code> on the running hub.',
    'setup.mock': 'Demo only — sample output, nothing is sent',
    'setup.template': 'Workflow template',
    'setup.roleA': 'Role A',
    'setup.roleB': 'Role B',
    'setup.name': 'Name',
    'setup.goal': 'Goal',
    'setup.responsibilities': 'Responsibilities (one per line)',
    'setup.forbidden': 'Forbidden (one per line)',
    'setup.task': 'Runtime task',
    'setup.taskTitle': 'Title',
    'setup.branch': 'Branch',
    'setup.maxEpochs': 'Max epochs',
    'setup.constraints': 'Constraints (one per line)',
    'setup.hubUrl': 'Hub URL',
    'setup.generate': 'Generate prompts',
    'setup.copy': 'Copy',
    'setup.copied': 'Copied!',
    'setup.profileJson': 'Profile JSON (POST /profile)',
    'setup.hint': 'Start Session <strong>B</strong> first, paste its prompt, then Session <strong>A</strong>.',
    'setup.placeholderA': 'Click "Generate prompts" to preview Session A /loop prompt…',
    'setup.placeholderB': 'Click "Generate prompts" to preview Session B /loop prompt…',

    'tpl.dev-review': 'Dev + Review (default)',
    'tpl.test-fix': 'Test + Fix',
    'tpl.plan-implement': 'Plan + Implement',
    'tpl.security-fix': 'Security + Fix',

    'feat1.title': 'Custom roles',
    'feat1.desc': 'Profile + workflow template + runtime task — dev/review is just one preset.',
    'feat2.title': 'Skill entry',
    'feat2.desc': '<code>coord-setup</code> starts MCP, opens UI, guides you through config.',
    'feat3.title': 'Short prompts',
    'feat3.desc': 'Agents read <code>/profile</code> and <code>/state</code> — rules live on the hub, not in chat.',
    'feat4.title': '/loop wake',
    'feat4.desc': 'Background <code>curl /wait/&lt;role&gt;</code> still bridges sessions after setup.',

    'arch.title': 'Architecture',
    'arch.desc': 'Each layer has a single job. Skill guides, MCP operates, UI configures, hub coordinates, sessions execute.',
    'arch.skill.layer': 'Skill',
    'arch.skill.title': 'coord-setup',
    'arch.skill.1': 'Call MCP to start/stop hub',
    'arch.skill.2': 'Return UI link to user',
    'arch.skill.3': 'Explain paste order (B then A)',
    'arch.mcp.layer': 'MCP',
    'arch.mcp.title': 'coord_* tools',
    'arch.ui.layer': 'UI',
    'arch.ui.title': 'GET /ui',
    'arch.ui.1': 'Template picker + role editor',
    'arch.ui.2': 'Task, branch, constraints',
    'arch.ui.3': 'Generate → GET /prompt/A|B',
    'arch.hub.layer': 'Hub',
    'arch.hub.title': 'coord-hub.py',

    'setup.copyFailed': 'Copy failed',
    'field.taskPlaceholder': 'Implement feature X',

    'footer.license': 'MIT License',
    'footer.tagline': 'Configure once in the UI, coordinate forever in /loop.',
  },

  zh: {
    'nav.flow': '流程',
    'nav.setup': '配置 UI',
    'nav.arch': '架构',
    'nav.github': 'GitHub',

    'hero.badge': 'Skill · MCP · 本地 UI · MIT',
    'hero.title1': '一个 Skill 启动，',
    'hero.title2': '两个会话协同',
    'hero.desc': '在 Cursor 中运行 <code>coord-setup</code> — MCP 启动 Hub，你在本地 UI 配置角色与任务，然后复制生成的 <code>/loop</code> 提示词到会话 A 和 B。',
    'hero.cta': '试用配置 UI',
    'hero.learn': '查看流程',

    'flow.title': '端到端流程',
    'flow.desc': 'Hub 仍通过长轮询负责跨会话唤醒。Skill 和 UI 负责 loop 启动前的一切配置。',
    'flow.s1.title': '触发 <code>coord-setup</code> skill',
    'flow.s1.desc': '在任意 Cursor 聊天中，让 Agent 设置 A/B 协作。',
    'flow.s2.title': 'MCP 启动 Hub',
    'flow.s2.desc': 'Skill 调用 MCP <code>coord_start</code> — Hub 监听 <code>127.0.0.1:9900</code>。',
    'flow.s3.title': '打开配置 UI',
    'flow.s3.desc': 'Skill 返回链接。选择模板，编辑 A/B 目标，设置任务与分支。',
    'flow.s4.title': '生成并复制提示词',
    'flow.s4.desc': 'UI 将 profile 写入 Hub，为每个角色生成简短的 <code>/loop dynamic</code> 提示词。',
    'flow.s5.title': '粘贴到会话 B，再 A',
    'flow.s5.desc': '先启动 B，再启动 A。Watcher 在对方 signal 时唤醒各自会话。',
    'flow.lane.user': '你',
    'flow.lane.runtime': '运行时',
    'flow.lane.sessions': '会话',
    'flow.node.skill': 'coord-setup skill',
    'flow.node.ui': '配置 UI',
    'flow.node.prompts': '复制提示词',
    'flow.hub': '协调 Hub',
    'flow.node.a': '会话 A',
    'flow.node.b': '会话 B',

    'setup.title': '配置 UI 预览',
    'setup.desc': 'Hub 配置页的交互式预览。正式版将托管在运行中 Hub 的 <code>GET /ui</code>。',
    'setup.mock': '仅演示 — 示例输出，不发送任何请求',
    'setup.template': '工作流模板',
    'setup.roleA': '角色 A',
    'setup.roleB': '角色 B',
    'setup.name': '名称',
    'setup.goal': '目标',
    'setup.responsibilities': '职责（每行一条）',
    'setup.forbidden': '禁止事项（每行一条）',
    'setup.task': '运行时任务',
    'setup.taskTitle': '标题',
    'setup.branch': '分支',
    'setup.maxEpochs': '最大轮次',
    'setup.constraints': '约束（每行一条）',
    'setup.hubUrl': 'Hub 地址',
    'setup.generate': '生成提示词',
    'setup.copy': '复制',
    'setup.copied': '已复制！',
    'setup.profileJson': 'Profile JSON（POST /profile）',
    'setup.hint': '先启动会话 <strong>B</strong> 并粘贴提示词，再启动会话 <strong>A</strong>。',
    'setup.placeholderA': '点击「生成提示词」预览会话 A 的 /loop 提示词…',
    'setup.placeholderB': '点击「生成提示词」预览会话 B 的 /loop 提示词…',

    'tpl.dev-review': '开发 + 审查（默认）',
    'tpl.test-fix': '测试 + 修复',
    'tpl.plan-implement': '方案 + 实现',
    'tpl.security-fix': '安全 + 修复',

    'feat1.title': '自定义角色',
    'feat1.desc': 'Profile + 工作流模板 + 运行时任务 — 开发/审查只是其中一个预设。',
    'feat2.title': 'Skill 入口',
    'feat2.desc': '<code>coord-setup</code> 启动 MCP、打开 UI、引导完成配置。',
    'feat3.title': '简短提示词',
    'feat3.desc': 'Agent 读取 <code>/profile</code> 和 <code>/state</code> — 规则存在 Hub，不塞进聊天。',
    'feat4.title': '/loop 唤醒',
    'feat4.desc': '配置完成后，后台 <code>curl /wait/&lt;role&gt;</code> 仍负责跨会话唤醒。',

    'arch.title': '架构',
    'arch.desc': '每层只做一件事。Skill 引导，MCP 操作，UI 配置，Hub 协调，会话执行。',
    'arch.skill.layer': 'Skill',
    'arch.skill.title': 'coord-setup',
    'arch.skill.1': '调用 MCP 启停 Hub',
    'arch.skill.2': '返回 UI 链接给用户',
    'arch.skill.3': '说明粘贴顺序（先 B 后 A）',
    'arch.mcp.layer': 'MCP',
    'arch.mcp.title': 'coord_* 工具',
    'arch.ui.layer': 'UI',
    'arch.ui.title': 'GET /ui',
    'arch.ui.1': '模板选择 + 角色编辑',
    'arch.ui.2': '任务、分支、约束',
    'arch.ui.3': '生成 → GET /prompt/A|B',
    'arch.hub.layer': 'Hub',
    'arch.hub.title': 'coord-hub.py',

    'setup.copyFailed': '复制失败',
    'field.taskPlaceholder': '实现功能 X',

    'footer.license': 'MIT 许可证',
    'footer.tagline': '在 UI 配置一次，在 /loop 中持续协调。',
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

const STORAGE_KEY = 'cursor-ab-coord-lang';

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

function detectLanguage() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === 'en' || stored === 'zh') return stored;

  const langs = navigator.languages || [navigator.language || 'en'];
  for (const lang of langs) {
    if (lang.toLowerCase().startsWith('zh')) return 'zh';
  }
  return 'en';
}

function applyLanguage(lang) {
  const dict = translations[lang];
  if (!dict) return;

  document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';

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

function t(key) {
  const lang = window.currentLang || 'en';
  return translations[lang]?.[key] ?? translations.en[key] ?? key;
}

function initI18n() {
  const lang = detectLanguage();
  applyLanguage(lang);

  const toggle = document.getElementById('langToggle');
  if (toggle) {
    toggle.addEventListener('click', () => {
      const next = window.currentLang === 'zh' ? 'en' : 'zh';
      applyLanguage(next);
    });
  }
}

document.addEventListener('DOMContentLoaded', initI18n);
