/* ============================================================
 * RHC 知识问答 · 全局悬浮组件
 * 自包含（内联样式、class/id 均加 rhc-widget- 前缀），
 * 不依赖任何页面现有 CSS 变量或脚本；DOMContentLoaded 后自挂载。
 * ============================================================ */
(function () {
  'use strict';
  if (window.__RHC_WIDGET_LOADED__) return;
  window.__RHC_WIDGET_LOADED__ = true;

  var WIDGET_CSS =
    '#rhc-widget-root,#rhc-widget-root *{font-family:"HarmonyOS Sans SC","PingFang SC","Microsoft YaHei",system-ui,-apple-system,"Segoe UI",sans-serif;box-sizing:border-box;margin:0;padding:0}' +
    '#rhc-widget-fab{position:fixed;right:20px;bottom:20px;width:56px;height:56px;border-radius:50%;background:#C8102E;border:none;cursor:pointer;z-index:2147483600;display:flex;align-items:center;justify-content:center;box-shadow:0 6px 18px rgba(200,16,46,.35);transition:transform .15s ease,background .15s ease}' +
    '#rhc-widget-fab:hover{background:#A50D26;transform:scale(1.06)}' +
    '#rhc-widget-fab svg{width:26px;height:26px;color:#fff;display:block}' +
    '#rhc-widget-panel{position:fixed;right:20px;bottom:88px;width:340px;height:580px;max-height:75vh;min-width:280px;max-width:90vw;box-sizing:border-box;background:#FFFFFF;border:1px solid #E5E7EB;border-radius:14px;box-shadow:0 12px 36px rgba(0,0,0,.18);z-index:2147483601;display:none;flex-direction:column;overflow:auto;resize:both}' +
    '#rhc-widget-panel.rhc-widget-open{display:flex}' +
    '.rhc-widget-header{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:13px 26px 13px 16px;border-bottom:1px solid #F3F4F6;background:#FFFFFF;flex-shrink:0}' +
    '.rhc-widget-title{display:flex;flex-direction:column;gap:2px;min-width:0;margin-left:10px}' +
    '.rhc-widget-title-main{font-size:14px;font-weight:700;color:#C8102E;line-height:1.3}' +
    '.rhc-widget-title-sub{font-size:11px;color:#9CA3AF;line-height:1.3}' +
    '#rhc-widget-close{width:28px;height:28px;border-radius:6px;border:none;background:transparent;color:#9CA3AF;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;padding:0}' +
    '#rhc-widget-close:hover{background:#FDE8EB;color:#C8102E}' +
    '#rhc-widget-close svg{width:15px;height:15px;display:block}' +
    '.rhc-widget-messages{flex:1;min-height:0;overflow-y:auto;background:#F7F8FA;padding:10px;display:flex;flex-direction:column;gap:10px}' +
    '.rhc-widget-msg{display:flex;max-width:82%}' +
    '.rhc-widget-bot{align-self:flex-start;margin-left:8px}' +
    '.rhc-widget-user{align-self:flex-end;flex-direction:row-reverse;margin-right:8px}' +
    '.rhc-widget-bubble{display:block;padding:7px 10px;font-size:13px;line-height:1.8;white-space:pre-wrap;word-break:break-word;border-radius:12px}' +
    '.rhc-widget-bot .rhc-widget-bubble{background:#FFFFFF;border:none;box-shadow:0 2px 8px rgba(0,0,0,.08);border-radius:12px;color:#1A1A1A}' +
    '.rhc-widget-user .rhc-widget-bubble{background:#C8102E;color:#FFFFFF;border-radius:12px}' +
    '.rhc-widget-typing{display:inline-flex;gap:4px;align-items:center}' +
    '.rhc-widget-typing i{width:6px;height:6px;border-radius:50%;background:#9CA3AF;animation:rhc-widget-blink 1.2s infinite}' +
    '.rhc-widget-typing i:nth-child(2){animation-delay:.2s}' +
    '.rhc-widget-typing i:nth-child(3){animation-delay:.4s}' +
    '@keyframes rhc-widget-blink{0%,80%,100%{opacity:.3}40%{opacity:1}}' +
    '.rhc-widget-quick{display:flex;gap:6px;flex-wrap:wrap;padding:8px 10px 10px;background:#F7F8FA;flex-shrink:0;border-top:1px solid #ECEEF0}' +
    '.rhc-widget-chip{padding:4px 9px;border:1px solid #E5E7EB;border-radius:14px;font-size:11px;color:#6B7280;background:#FFFFFF;cursor:pointer;transition:all .15s ease;font-family:inherit;line-height:1.4}' +
    '.rhc-widget-chip:hover{border-color:#C8102E;color:#C8102E}' +
    '.rhc-widget-input-bar{display:flex;gap:6px;padding:8px 10px;border-top:1px solid #F3F4F6;background:#FFFFFF;flex-shrink:0}' +
    '.rhc-widget-input-bar input{flex:1;min-width:0;padding:7px 10px;font-size:12px;border:1px solid #E5E7EB;border-radius:6px;outline:none;font-family:inherit;color:#1A1A1A;background:#FFFFFF}' +
    '.rhc-widget-input-bar input:focus{border-color:#C8102E;box-shadow:0 0 0 3px rgba(200,16,46,.12)}' +
    '#rhc-widget-send{padding:7px 12px;border:none;border-radius:6px;background:#C8102E;color:#FFFFFF;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;flex-shrink:0;transition:background .15s ease}' +
    '#rhc-widget-send:hover{background:#A50D26}' +
    '@media (max-width:480px){#rhc-widget-panel{width:92vw;left:12px;right:12px;bottom:84px;height:60vh;max-height:70vh}#rhc-widget-fab{right:20px;bottom:20px}}';

  /* ===== 本地产品资料库（接口不可用时兜底，均为 RHC 真实在售产品） ===== */
  var PRODUCTS = [
    { model: 'V5 Plus', keywords: ['v5', 'v5 plus', 'v5plus', '旗舰', '工作站', '麻醉机', '麻醉工作站', '兽用麻醉', '小动物麻醉', '麻醉', 'anesthesia', 'anaesthesia', 'workstation', '触摸屏', '潮气量'],
      answer: 'V5 Plus 兽用麻醉工作站是 RHC 旗舰工作站，配备 12.1 寸可翻转触摸屏，潮气量覆盖 2–1600ml，适用于 200g–160kg 的小动物，通过 CE 与 ISO 13485 认证，适合宠物医院及兽医专科机构的常规与复杂手术麻醉。' },
    { model: 'X35VET', keywords: ['x35', 'x35vet', '主力', '麻醉机', '麻醉工作站', '兽用麻醉', '小动物', '猫', '狗', '犬', '宠物', '麻醉', 'anesthesia', 'anaesthesia', '涡轮', '涡轮驱动', '电动电控', '无需驱动气'],
      answer: 'X35VET 兽用麻醉机是 RHC 主力机型，配备 10.2 寸屏幕，潮气量 10–1600ml，覆盖 5–150kg 动物；采用电动电控涡轮驱动，无需外接驱动气，移动使用与门诊手术室场景均十分方便。' },
    { model: 'M800', keywords: ['m800', '大动物', '大型动物', '马', '牛', '马场', '牧场', '大动物麻醉', '大型动物麻醉', 'large animal', 'large-animal', 'equine', 'bovine', 'cattle', 'horse'],
      answer: 'M800 大动物麻醉工作站为大型动物专用，配备 15.6 寸屏幕，潮气量 50ml–19L，覆盖 5kg–1800kg 动物，通过 CE 与 ISO 13485 认证，适用于马、牛等大动物的临床麻醉与科研教学场景。' },
    { model: 'SA Series', keywords: ['sa series', 'sa-series', '注射泵', '输液泵', '输注', '注射', '泵', 'ders', '药库', 'infusion', 'syringe', 'pump', 'syringe pump', 'infusion pump'],
      answer: 'SA Series 注射泵具备 DERS 药库功能（剂量错误减量系统），支持精准输注与药物剂量安全管理，通过 CE 认证，适用于兽医医院术中、住院及急诊补液给药场景。' }
  ];

  var QUICK_QUESTIONS = [
    'V5 Plus 和 X35VET 有什么区别？',
    'M800 大动物工作站覆盖多大体重范围？',
    'SA Series 注射泵的 DERS 药库是什么？'
  ];

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function localAnswer(q) {
    var ql = String(q || '').toLowerCase();
    var hits = PRODUCTS.filter(function (p) {
      return p.keywords.some(function (k) { return ql.indexOf(k.toLowerCase()) >= 0; });
    });
    if (hits.length === 0) {
      return '您好，我目前掌握的产品信息覆盖以下四款 RHC 在售产品：\n· V5 Plus 兽用麻醉工作站（旗舰，200g–160kg 小动物）\n· X35VET 兽用麻醉机（主力机型，电动电控涡轮驱动）\n· M800 大动物麻醉工作站（5kg–1800kg，马/牛等大动物）\n· SA Series 注射泵（DERS 药库功能，CE）\n请直接输入产品型号或应用场景（如「麻醉机」「大动物」「注射泵」），我会给出对应说明。更复杂的商务与报价问题请联系销售同事。';
    }
    return hits.map(function (p) { return '【' + p.model + '】\n' + p.answer; }).join('\n\n');
  }

  function init() {
    if (document.getElementById('rhc-widget-root')) return;
    var mount = document.body || document.documentElement;
    if (!mount) return;

    var style = document.createElement('style');
    style.setAttribute('type', 'text/css');
    style.textContent = WIDGET_CSS;
    mount.appendChild(style);

    var root = document.createElement('div');
    root.id = 'rhc-widget-root';

    var chipsHtml = QUICK_QUESTIONS.map(function (q) {
      return '<button type="button" class="rhc-widget-chip" data-q="' + esc(q) + '">' + esc(q) + '</button>';
    }).join('');

    root.innerHTML =
      '<button type="button" id="rhc-widget-fab" aria-label="打开知识问答" title="知识问答">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>' +
      '</button>' +
      '<div id="rhc-widget-panel" role="dialog" aria-label="知识问答">' +
        '<div class="rhc-widget-header">' +
          '<div class="rhc-widget-title"><span class="rhc-widget-title-main">知识问答</span><span class="rhc-widget-title-sub">基于RHC产品资料库</span></div>' +
          '<button type="button" id="rhc-widget-close" aria-label="关闭">' +
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>' +
          '</button>' +
        '</div>' +
        '<div class="rhc-widget-messages" id="rhc-widget-messages"></div>' +
        '<div class="rhc-widget-quick" id="rhc-widget-quick">' + chipsHtml + '</div>' +
        '<div class="rhc-widget-input-bar">' +
          '<input type="text" id="rhc-widget-input" placeholder="输入产品问题，例如：V5 Plus 适合哪些动物？">' +
          '<button type="button" id="rhc-widget-send">发送</button>' +
        '</div>' +
      '</div>';
    mount.appendChild(root);

    var panel = document.getElementById('rhc-widget-panel');
    var fab = document.getElementById('rhc-widget-fab');
    var closeBtn = document.getElementById('rhc-widget-close');
    var sendBtn = document.getElementById('rhc-widget-send');
    var input = document.getElementById('rhc-widget-input');
    var quickBox = document.getElementById('rhc-widget-quick');
    var messages = document.getElementById('rhc-widget-messages');

    function setOpen(open) {
      if (open) { panel.classList.add('rhc-widget-open'); }
      else { panel.classList.remove('rhc-widget-open'); }
    }
    fab.onclick = function () { setOpen(!panel.classList.contains('rhc-widget-open')); };
    closeBtn.onclick = function () { setOpen(false); };
    sendBtn.onclick = function () { sendQuestion(); };
    input.onkeydown = function (e) { if (e && e.key === 'Enter') sendQuestion(); };
    quickBox.onclick = function (e) {
      var t = e && e.target;
      if (t && t.getAttribute && t.getAttribute('data-q')) {
        ask(t.getAttribute('data-q'));
      }
    };

    addMsg('bot', '您好，我是 RHC 知识问答助手。您可以向我咨询 V5 Plus、X35VET、M800、SA Series 等在售产品的参数、适用场景与配置信息。点击常见问题，或直接输入问题开始。');

    function addMsg(role, text) {
      var row = document.createElement('div');
      row.className = 'rhc-widget-msg ' + (role === 'user' ? 'rhc-widget-user' : 'rhc-widget-bot');
      row.innerHTML = '<span class="rhc-widget-bubble">' + esc(text) + '</span>';
      messages.appendChild(row);
      messages.scrollTop = messages.scrollHeight;
    }

    function ask(q) {
      q = String(q || '').trim();
      if (!q) return;
      addMsg('user', q);
      input.value = '';
      var typing = document.createElement('div');
      typing.className = 'rhc-widget-msg rhc-widget-bot';
      typing.id = 'rhc-widget-typing';
      typing.innerHTML = '<span class="rhc-widget-bubble rhc-widget-typing"><i></i><i></i><i></i></span>';
      messages.appendChild(typing);
      messages.scrollTop = messages.scrollHeight;

      function finish(text) {
        var ty = document.getElementById('rhc-widget-typing');
        if (ty && ty.remove) ty.remove();
        addMsg('bot', text);
      }
      fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: q })
      })
        .then(function (r) { if (!r.ok) throw new Error('chat ' + r.status); return r.json(); })
        .then(function (d) {
          var text = d.reply || d.message || d.response || d.answer || d.text || (d.data && (d.data.reply || d.data.message)) || '';
          if (!text) throw new Error('empty chat reply');
          finish(String(text));
        })
        .catch(function () {
          setTimeout(function () { finish(localAnswer(q)); }, 300);
        });
    }

    function sendQuestion() {
      var q = input.value;
      if (q && String(q).trim()) ask(q);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
