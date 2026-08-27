#!/usr/bin/env python3
"""Update login.html with new design: form optimization, third-party login,
product preview mockup, and stats bar."""

import sys

# ---- New CSS additions (to be inserted before the Toast section) ----
NEW_CSS_ADDITIONS = '''
/* ===== Login card enhanced ===== */
.login-card{
  border-radius:16px;
  box-shadow:0 8px 32px rgba(0,0,0,0.08);
  padding:36px 32px;
}
.login-card .card-title{font-size:24px;font-weight:700}
.login-card .card-subtitle{font-size:14px;color:var(--color-text-secondary);margin-top:6px;margin-bottom:28px}

/* Enhanced form inputs */
.form-group{margin-bottom:18px}
.input-with-icon input{
  height:44px;
  padding:10px 14px 10px 42px;
  border-radius:8px;
  border-color:#D1D5DB;
  font-size:14px;
}
.input-with-icon input:focus{
  border-color:var(--color-primary);
  box-shadow:0 0 0 3px rgba(200,16,46,0.12);
}
.input-with-icon .input-icon{color:var(--color-text-tertiary)}
.input-with-icon input:focus + .input-icon{color:var(--color-primary)}

/* Enhanced button */
.btn{
  height:44px;
  border-radius:8px;
  font-size:15px;
  font-weight:600;
  transition:all 0.2s ease;
  width:100%;
}
.btn-primary{
  background:var(--color-primary);
  color:#fff;
  box-shadow:0 2px 8px rgba(200,16,46,0.3);
}
.btn-primary:hover{
  background:var(--color-primary-dark);
  box-shadow:0 4px 12px rgba(200,16,46,0.35);
}
.btn-primary:active{transform:translateY(1px)}

/* Remember row */
.form-row{
  display:flex;align-items:center;justify-content:space-between;
  margin-bottom:20px;font-size:13px;
}
.checkbox-wrap{
  display:flex;align-items:center;gap:8px;
  cursor:pointer;color:var(--color-text-secondary);user-select:none;
}
.checkbox-wrap input{
  width:16px;height:16px;cursor:pointer;accent-color:var(--color-primary);
}
.forgot-link{color:var(--color-primary);font-size:13px}

/* Divider with "or" */
.or-divider{
  display:flex;align-items:center;
  margin:20px 0 16px;
  position:relative;
}
.or-divider::before,
.or-divider::after{
  content:'';flex:1;height:1px;background:var(--color-border);
}
.or-divider span{
  padding:0 12px;
  background:#fff;
  font-size:12px;color:var(--color-text-tertiary);
  position:relative;z-index:1;
}

/* Third-party login */
.social-login{
  display:flex;gap:12px;margin-bottom:20px;
}
.social-btn{
  flex:1;
  height:44px;
  border-radius:8px;
  display:flex;align-items:center;justify-content:center;gap:8px;
  font-size:14px;font-weight:500;
  cursor:pointer;
  transition:all 0.2s ease;
  background:#fff;
  border:1px solid;
}
.social-btn svg{width:20px;height:20px}
.social-btn-wechat{
  border-color:#07C160;
  color:#07C160;
}
.social-btn-wechat:hover{
  background:#F0FAF4;
  border-color:#06AD56;
}
.social-btn-workwechat{
  border-color:#0082EF;
  color:#0082EF;
}
.social-btn-workwechat:hover{
  background:#F0F7FF;
  border-color:#0066CC;
}

/* Demo tip enhanced */
.demo-tip{
  margin-top:0;
  padding:8px 12px;
  background:#FFF1F3;
  border:none;
  border-radius:6px;
  font-size:12px;
  color:var(--color-primary);
  text-align:center;
}
.demo-tip svg{width:14px;height:14px;vertical-align:-2px;margin-right:6px}

/* Register entry / admin note */
.register-entry{
  margin-top:16px;
  text-align:center;
  font-size:12px;
  color:var(--color-text-tertiary);
}

/* ===== Product Preview ===== */
.product-preview{
  width:100%;max-width:400px;
  margin:24px auto 0;
  border-radius:8px;
  border:1px solid var(--color-border);
  box-shadow:0 4px 16px rgba(0,0,0,0.06);
  overflow:hidden;
  background:#fff;
  transition:all 0.3s ease;
}
.product-preview:hover{
  transform:translateY(-2px);
  box-shadow:0 8px 24px rgba(0,0,0,0.10);
}
.browser-bar{
  height:28px;
  background:#F3F4F6;
  display:flex;align-items:center;
  padding:0 10px;
  gap:6px;
  position:relative;
}
.browser-dots{display:flex;gap:6px}
.browser-dots span{
  width:8px;height:8px;border-radius:50%;display:block;
}
.browser-dots .dot-red{background:#FF5F57}
.browser-dots .dot-yellow{background:#FEBC2E}
.browser-dots .dot-green{background:#28C840}
.browser-address{
  position:absolute;left:50%;top:50%;
  transform:translate(-50%,-50%);
  background:#E5E7EB;
  border-radius:4px;
  padding:2px 10px;
  font-size:9px;
  color:#9CA3AF;
  white-space:nowrap;
}
.browser-content{
  padding:12px;
  background:#fff;
}
.dashboard-header{
  display:flex;align-items:center;justify-content:space-between;
  margin-bottom:10px;
}
.dashboard-title{
  font-size:10px;font-weight:700;color:var(--color-text);
}
.dashboard-live{
  display:flex;align-items:center;gap:4px;
  font-size:8px;color:var(--color-primary);
}
.dashboard-live .live-dot{
  width:6px;height:6px;border-radius:50%;
  background:var(--color-primary);
  animation:blink 1.5s ease-in-out infinite;
}
@keyframes blink{
  0%,100%{opacity:1}
  50%{opacity:0.4}
}

/* Mini metric cards */
.metric-row{
  display:flex;gap:6px;
  margin-bottom:10px;
}
.metric-card{
  flex:1;
  background:#FAFAFA;
  border-radius:6px;
  padding:8px 6px;
}
.metric-card .metric-icon{
  width:16px;height:16px;
  margin-bottom:4px;
}
.metric-card .metric-value{
  font-size:10px;font-weight:700;color:var(--color-text);
  line-height:1.2;
}
.metric-card .metric-value.green{color:#10B981}
.metric-card .metric-label{
  font-size:7px;color:var(--color-text-secondary);
  margin-top:2px;
}

/* Mini line chart */
.chart-area{
  height:50px;
  margin-bottom:8px;
  position:relative;
}
.chart-area svg{width:100%;height:100%;display:block}
.chart-dots{
  position:absolute;bottom:0;left:0;right:0;
  display:flex;justify-content:space-between;
  padding:0 2px;
}
.chart-dots span{
  width:4px;height:4px;border-radius:50%;
  background:#D1D5DB;
}

/* Ring progress row */
.progress-row{
  display:flex;align-items:center;justify-content:flex-end;
  gap:6px;
}
.ring-chart{width:28px;height:28px;flex-shrink:0}
.progress-text{
  font-size:8px;color:var(--color-text-secondary);
}

/* ===== Stats Bar ===== */
.stats-bar{
  width:100%;max-width:400px;
  margin:16px auto 0;
  display:flex;
  background:#fff;
  border:1px solid var(--color-border);
  border-radius:8px;
  box-shadow:0 2px 8px rgba(0,0,0,0.04);
  overflow:hidden;
}
.stats-item{
  flex:1;
  text-align:center;
  padding:14px 8px;
  position:relative;
}
.stats-item:not(:last-child)::after{
  content:'';position:absolute;
  right:0;top:50%;transform:translateY(-50%);
  width:1px;height:24px;
  background:var(--color-border);
}
.stats-item .stats-icon{
  width:14px;height:14px;
  color:var(--color-primary);
  opacity:0.7;
  margin:0 auto 4px;
}
.stats-item .stats-number{
  font-size:18px;font-weight:700;
  color:var(--color-primary);
  line-height:1.2;
}
.stats-item .stats-label{
  font-size:11px;
  color:var(--color-text-secondary);
  margin-top:2px;
}

/* ===== Form panel layout adjustment ===== */
.form-panel{
  flex:1;
  display:flex;
  flex-direction:column;
  justify-content:flex-start;
  align-items:center;
  padding:40px 20px;
  padding-top:48px;
  background:var(--color-bg);
}
'''

# ---- New responsive additions (product preview + stats bar hide on mobile) ----
NEW_RESPONSIVE_ADDITIONS = '''
  .product-preview,.stats-bar{display:none}
  .form-panel{padding:32px 20px}
  .login-card{padding:32px 28px}
'''

def update_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()

    # 1. Replace the old .form-panel CSS block
    old_form_panel = '''/* Right form panel */
.form-panel{
  flex:1;display:flex;align-items:center;justify-content:center;
  padding:40px;background:var(--color-bg);
}'''
    # We'll keep the old .form-panel but replace it with new one via the additions block
    # Actually let's just remove it from old and let new one take over
    # Better: replace the old .login-card block too

    # Strategy: Insert all new CSS before the "/* Toast */" comment
    # Then replace the old .login-card and related blocks are overridden by the new ones
    # since they come later in the stylesheet

    # Insert new CSS before Toast section
    toast_marker = '/* Toast */'
    if toast_marker not in html:
        print(f"ERROR: Toast marker not found in {filepath}")
        return False

    html = html.replace(toast_marker, NEW_CSS_ADDITIONS + '\n' + toast_marker)

    # 2. Update responsive section: replace the old form-panel responsive rule
    # Find the max-width:960px media query and add product-preview/stats-bar display:none
    old_responsive_form = '  .form-panel{padding:32px 20px}\n  .login-card{padding:32px 24px}'
    new_responsive_form = '  .product-preview,.stats-bar{display:none}\n  .form-panel{padding:32px 20px}\n  .login-card{padding:32px 28px}'
    html = html.replace(old_responsive_form, new_responsive_form)

    # 3. Replace the entire content of .form-panel div
    old_form_panel_content = '''  <!-- Right form panel -->
  <div class="form-panel">
    <div class="login-card">
      <h2 class="card-title">欢迎登录</h2>
      <p class="card-subtitle">请输入您的账号信息以继续</p>

      <form id="loginForm" onsubmit="handleLogin(event)">
        <div class="form-group">
          <label for="username">用户名</label>
          <div class="input-with-icon">
            <input type="text" id="username" name="username" placeholder="请输入用户名" value="Ella" autocomplete="username">
            <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
          </div>
        </div>

        <div class="form-group">
          <label for="password">密码</label>
          <div class="input-with-icon">
            <input type="password" id="password" name="password" placeholder="请输入密码" value="demo123" autocomplete="current-password">
            <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <rect x="3" y="11" width="18" height="11" rx="2"/>
              <path d="M7 11V7a5 5 0 0110 0v4"/>
            </svg>
          </div>
        </div>

        <div class="form-row">
          <label class="checkbox-wrap">
            <input type="checkbox" id="remember" checked>
            <span>记住我</span>
          </label>
          <a href="#" class="forgot-link" onclick="showToast('请联系管理员重置密码','error');return false;">忘记密码？</a>
        </div>

        <button type="submit" class="btn btn-primary" id="loginBtn">
          登录
        </button>

        <div class="demo-tip">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
          演示环境，任意账号密码即可登录
        </div>
      </form>
    </div>
  </div>'''

    new_form_panel_content = '''  <!-- Right form panel -->
  <div class="form-panel">
    <div class="login-card">
      <h2 class="card-title">欢迎登录</h2>
      <p class="card-subtitle">请输入您的账号信息以继续</p>

      <form id="loginForm" onsubmit="handleLogin(event)">
        <div class="form-group">
          <label for="username">用户名</label>
          <div class="input-with-icon">
            <input type="text" id="username" name="username" placeholder="请输入用户名" value="Ella" autocomplete="username">
            <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
          </div>
        </div>

        <div class="form-group">
          <label for="password">密码</label>
          <div class="input-with-icon">
            <input type="password" id="password" name="password" placeholder="请输入密码" value="demo123" autocomplete="current-password">
            <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <rect x="3" y="11" width="18" height="11" rx="2"/>
              <path d="M7 11V7a5 5 0 0110 0v4"/>
            </svg>
          </div>
        </div>

        <div class="form-row">
          <label class="checkbox-wrap">
            <input type="checkbox" id="remember" checked>
            <span>记住我</span>
          </label>
          <a href="#" class="forgot-link" onclick="showToast('请联系管理员重置密码','error');return false;">忘记密码？</a>
        </div>

        <button type="submit" class="btn btn-primary" id="loginBtn">
          登录
        </button>
      </form>

      <div class="or-divider">
        <span>或</span>
      </div>

      <div class="social-login">
        <button type="button" class="social-btn social-btn-wechat" onclick="showToast('微信登录即将开放，敬请期待','')">
          <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M8.691 2.188C3.891 2.188 0 5.476 0 9.53c0 2.212 1.17 4.203 3.002 5.55a.59.59 0 01.213.665l-.39 1.48c-.019.07-.048.141-.048.213 0 .163.13.295.29.295a.326.326 0 00.167-.054l1.903-1.114a.864.864 0 01.717-.098 10.16 10.16 0 002.837.403c.276 0 .543-.027.811-.05-.857-2.578.157-4.972 1.932-6.446 1.703-1.415 3.882-1.98 5.853-1.838-.576-3.583-4.196-6.348-8.596-6.348zM5.785 5.991c.642 0 1.162.529 1.162 1.18 0 .65-.52 1.178-1.162 1.178-.642 0-1.162-.528-1.162-1.179 0-.65.52-1.18 1.162-1.18zm5.813 0c.642 0 1.162.529 1.162 1.18 0 .65-.52 1.178-1.162 1.178-.642 0-1.162-.528-1.162-1.179 0-.65.52-1.18 1.162-1.18zm5.34 2.867c-1.797-.052-3.746.512-5.28 1.786-1.72 1.428-2.687 3.72-1.78 6.22.942 2.453 3.666 4.229 6.884 4.229.826 0 1.622-.12 2.361-.336a.722.722 0 01.598.082l1.584.926a.272.272 0 00.14.047c.134 0 .24-.111.24-.247 0-.06-.023-.12-.038-.177l-.327-1.233a.582.582 0 01-.023-.156.49.49 0 01.201-.398C23.024 18.48 24 16.82 24 14.98c0-3.21-2.931-5.837-6.656-6.088V8.89c-.135-.01-.27-.027-.407-.032zm-2.53 3.274c.535 0 .969.44.969.982a.976.976 0 01-.969.983.976.976 0 01-.969-.983c0-.542.434-.982.97-.982zm4.844 0c.535 0 .969.44.969.982a.976.976 0 01-.969.983.976.976 0 01-.969-.983c0-.542.434-.982.969-.982z"/>
          </svg>
          微信登录
        </button>
        <button type="button" class="social-btn social-btn-workwechat" onclick="showToast('企业微信登录即将开放，敬请期待','')">
          <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M18.63 1.875C15.234.343 11.443 0 7.637 0 3.42 0 0 2.965 0 6.64c0 2.067 1.127 3.912 2.896 5.15a.652.652 0 01.237.735l-.354 1.373a.608.608 0 00.186.607c.093.078.214.13.338.13.06 0 .121-.013.178-.037l1.77-1.033a.81.81 0 01.666-.092 8.62 8.62 0 002.61.373c.168 0 .333-.01.5-.03l.004-.002.043-.007c.593-.086 1.182-.206 1.762-.36l.048-.013c.068-.02.136-.04.204-.063.047-.015.094-.03.14-.046l.05-.019c.123-.047.245-.098.366-.15l.036-.015.057-.025c.112-.049.223-.1.332-.154l.059-.029c.22-.11.436-.228.649-.353l.044-.027.034-.02c.197-.117.39-.242.579-.375.092-.065.183-.132.273-.202l.044-.035.037-.029c.155-.122.306-.248.453-.38l.037-.033.051-.046c.128-.117.253-.237.375-.36l.023-.023.05-.05c.084-.083.167-.168.248-.255l.022-.024c.103-.113.203-.229.3-.348l.02-.024.042-.051c.076-.092.15-.186.222-.281l.012-.016c.093-.125.184-.252.272-.382l.011-.016.039-.057c.061-.089.12-.18.177-.272l.009-.015c.076-.124.149-.25.219-.378l.005-.01c.062-.112.122-.226.179-.342l.006-.012c.053-.106.104-.214.153-.323.017-.038.033-.076.05-.114.044-.1.086-.2.126-.303.013-.033.026-.066.038-.1.038-.104.074-.21.108-.316.012-.038.023-.075.035-.113.03-.097.058-.196.083-.296.009-.036.018-.071.026-.108.02-.083.038-.167.054-.252.006-.03.012-.06.018-.09.012-.06.023-.121.033-.182.005-.03.01-.06.014-.09.007-.043.013-.086.019-.13l.004-.03.008-.048c.006-.036.011-.071.016-.107l.004-.028c.005-.036.009-.072.012-.108l.004-.027.005-.036c.005-.037.009-.073.012-.11l.004-.03.004-.03.002-.024v-.006c.004-.048.006-.096.007-.145 0-.048-.002-.096-.006-.143v-.01c-.004-.043-.01-.086-.016-.128l-.005-.033c-.005-.033-.011-.065-.017-.098l-.005-.027c-.006-.032-.013-.064-.02-.096l-.005-.025c-.007-.031-.014-.062-.022-.092l-.007-.027c-.008-.03-.017-.06-.026-.09l-.006-.022c-.01-.03-.02-.06-.03-.088l-.009-.027c-.011-.03-.023-.059-.035-.088l-.008-.02c-.013-.029-.026-.058-.04-.086l-.011-.023c-.014-.029-.029-.057-.044-.085l-.009-.018c-.015-.028-.032-.056-.048-.083l-.012-.022c-.016-.027-.034-.054-.051-.08l-.011-.017c-.018-.027-.036-.053-.055-.079l-.012-.016c-.019-.026-.039-.052-.059-.077l-.01-.013c-.02-.025-.041-.05-.062-.074l-.01-.012c-.022-.024-.044-.048-.067-.071l-.013-.013c-.022-.023-.045-.046-.069-.068l-.014-.013c-.024-.023-.048-.045-.073-.067l-.012-.01c-.026-.022-.052-.044-.079-.065l-.014-.01c-.027-.02-.055-.04-.083-.06l-.012-.008c-.029-.02-.058-.039-.088-.057l-.013-.008c-.03-.019-.06-.037-.09-.055l-.014-.008c-.031-.018-.062-.035-.094-.052l-.015-.008c-.032-.017-.065-.033-.098-.049l-.014-.007c-.034-.016-.068-.032-.102-.047l-.016-.007c-.034-.015-.069-.03-.104-.044l-.014-.006c-.036-.015-.072-.029-.109-.043l-.014-.005c-.037-.014-.074-.028-.111-.041l-.016-.005c-.038-.013-.076-.026-.114-.038l-.014-.005c-.039-.013-.078-.025-.117-.037l-.016-.004c-.04-.012-.08-.024-.12-.035l-.014-.004c-.041-.012-.082-.023-.123-.033l-.015-.004c-.042-.01-.084-.02-.127-.03l-.014-.003c-.044-.01-.088-.019-.132-.028l-.013-.003c-.045-.009-.089-.018-.134-.026l-.015-.003c-.045-.008-.09-.016-.136-.023l-.015-.002c-.046-.007-.092-.014-.139-.02l-.015-.002c-.047-.006-.094-.012-.141-.018l-.015-.002c-.047-.006-.095-.011-.143-.016l-.014-.001c-.048-.005-.096-.01-.144-.014l-.015-.001c-.049-.004-.098-.008-.147-.012-.05-.004-.1-.007-.15-.01l-.004-.001c-.05-.003-.1-.006-.151-.008h-.004c-.101-.005-.202-.008-.304-.01h-.006c-.102-.002-.204-.003-.306-.003h-.006c-.102 0-.204.001-.306.003h-.006c-.102.002-.203.005-.304.01h-.004c-.051.002-.101.005-.151.008l-.004.001c-.05.003-.1.006-.15.01l-.015.001c-.049.004-.098.008-.147.012l-.015.001c-.048.004-.096.009-.144.014l-.014.001c-.048.005-.096.01-.143.016l-.015.002c-.047.006-.094.012-.141.018l-.015.002c-.046.007-.091.015-.136.023l-.015.003c-.045.008-.089.017-.134.026l-.013.003c-.044.009-.088.018-.132.028l-.014.003c-.042.01-.085.02-.127.03l-.014.004c-.041.01-.082.021-.123.033l-.014.004c-.04.011-.08.023-.12.035l-.016.004c-.039.012-.078.024-.117.037l-.014.005c-.038.012-.076.025-.114.038l-.016.005c-.037.013-.074.027-.111.041l-.014.005c-.037.014-.073.028-.109.043l-.014.006c-.035.014-.07.029-.104.044l-.014.007c-.034.016-.068.032-.102.047l-.016.007c-.033.016-.066.032-.098.049l-.014.008c-.032.017-.063.034-.094.052l-.014.008c-.03.018-.06.036-.09.055l-.013.008c-.03.018-.059.037-.088.057l-.012.008c-.028.02-.056.04-.083.06l-.014.01c-.027.021-.052.043-.079.065l-.014.01c-.026.022-.052.044-.079.067l-.012.01c-.025.022-.049.044-.073.067l-.014.013c-.024.022-.047.045-.069.068l-.013.013c-.023.023-.045.047-.067.071l-.01.012c-.021.024-.042.049-.062.074l-.01.013c-.02.025-.039.051-.059.077l-.012.016c-.019.026-.037.052-.055.079l-.011.017c-.017.027-.035.053-.051.08l-.012.022c-.016.027-.033.055-.048.083l-.009.018c-.016.029-.031.057-.044.086l-.011.023c-.014.028-.027.057-.04.086l-.008.02c-.012.029-.024.058-.035.088l-.009.027c-.01.028-.02.058-.03.088l-.006.022c-.009.03-.018.06-.026.09l-.007.027c-.008.03-.015.061-.022.092l-.005.025c-.007.032-.014.064-.02.096l-.005.027c-.006.033-.012.065-.017.098l-.005.033c-.006.042-.012.085-.016.128v.01c-.004.047-.006.095-.007.143 0 .049.001.097.007.145v.006l.002.024.004.03.004.03.004.03c.003.037.007.073.012.11l.005.036.004.027c.003.036.007.072.012.107l.004.028c.005.036.01.071.016.107l.008.048.004.03c.006.044.012.087.019.13l.014.09.033.182c.006.03.012.06.018.09.01.061.021.122.033.182.006.03.012.06.018.09.016.085.034.169.054.252.008.037.017.072.026.108.025.1.053.199.083.296.012.038.023.075.035.113.034.106.07.212.108.316.012.034.025.067.038.1.04.103.082.203.126.303.017.038.033.076.05.114.049.109.1.217.153.323l.006.012c.057.116.117.23.179.342l.005.01c.07.128.143.254.219.378l.009.015c.057.092.116.183.177.272l.039.057c.088.13.179.257.272.382l.012.016c.072.095.146.189.222.281l.042.051c.097.119.197.235.3.348l.022.024c.081.087.164.172.248.255l.05.05.023.023c.122.123.247.243.375.36l.051.046.037.033c.147.132.298.258.453.38l.044.035.037.029c.09.07.181.137.273.202.189.133.382.258.579.375l.034.02.044.027c.213.125.429.243.649.353l.059.029c.109.054.22.105.332.154l.057.025.036.015c.121.052.243.103.366.15l.05.019.14.046.048.013c.068.023.136.043.204.063l.048.013c.58.154 1.169.274 1.762.36l.043.007.004.002c.167.02.333.03.5.03.89 0 1.744-.126 2.553-.356v.005c.679-.191 1.327-.443 1.939-.751v.002l.047-.026.006-.003c.075-.041.148-.084.22-.129l.006-.004.022-.013c.073-.045.144-.092.214-.141l.006-.004.021-.014c.07-.049.138-.1.205-.152l.007-.005.023-.017c.067-.052.132-.106.196-.162l.006-.005.024-.02c.063-.056.125-.114.185-.174l.006-.006.024-.023c.06-.06.118-.121.174-.185l.007-.006.023-.024c.056-.06.109-.122.161-.185l.005-.006.024-.028c.052-.063.102-.127.149-.193l.005-.007.022-.03c.047-.066.092-.133.135-.201l.003-.005.021-.032c.042-.068.082-.137.12-.207l.005-.009.02-.035c.038-.07.074-.141.108-.213l.004-.009.018-.038c.034-.072.066-.145.096-.219l.003-.007.017-.04c.03-.074.058-.15.084-.226l.002-.006.016-.043c.027-.076.052-.154.075-.232l.002-.006.015-.047c.023-.078.044-.157.063-.237l.002-.008.014-.05c.02-.08.038-.16.054-.242l.001-.009.012-.054c.017-.081.032-.164.045-.246l.004-.018c.044-.252.075-.508.093-.767l.002-.026c.008-.085.012-.171.012-.257 0-.09-.004-.18-.011-.27l-.002-.028c-.007-.088-.018-.176-.031-.263l-.002-.017c-.014-.088-.03-.175-.05-.26l-.003-.014c-.019-.085-.042-.169-.067-.252l-.003-.012c-.025-.083-.053-.164-.084-.243l-.004-.012c-.031-.079-.065-.156-.102-.231l-.004-.01c-.037-.075-.077-.148-.12-.219l-.004-.008c-.043-.071-.089-.14-.137-.206l-.005-.007c-.048-.066-.1-.13-.154-.19l-.003-.004c-.054-.06-.11-.118-.169-.173l-.003-.003c-.059-.055-.12-.107-.183-.157l-.005-.004c-.063-.05-.128-.096-.195-.14l-.005-.003c-.067-.044-.136-.084-.207-.121l-.005-.003c-.071-.037-.144-.07-.219-.1l-.005-.002c-.075-.03-.151-.057-.229-.082l-.004-.001c-.078-.025-.157-.047-.238-.066l-.007-.002c-.081-.019-.163-.035-.246-.049l-.003-.001c-.083-.014-.167-.025-.252-.033l-.005-.001c-.085-.008-.171-.013-.258-.016l-.005-.001c-.258-.012-.518-.015-.778-.01l-.004.001c-.173.003-.346.01-.519.02z"/>
          </svg>
          企业微信
        </button>
      </div>

      <div class="demo-tip">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
        演示环境 · 任意账号密码即可登录
      </div>

      <div class="register-entry">
        账号由管理员统一配置，如有问题请联系管理员
      </div>
    </div>

    <!-- Product Preview -->
    <div class="product-preview">
      <div class="browser-bar">
        <div class="browser-dots">
          <span class="dot-red"></span>
          <span class="dot-yellow"></span>
          <span class="dot-green"></span>
        </div>
        <div class="browser-address">rhc.healthcare/dashboard</div>
      </div>
      <div class="browser-content">
        <div class="dashboard-header">
          <div class="dashboard-title">经营仪表盘</div>
          <div class="dashboard-live">
            <span class="live-dot"></span>
            实时
          </div>
        </div>

        <div class="metric-row">
          <div class="metric-card">
            <svg class="metric-icon" viewBox="0 0 16 16" fill="none" stroke="#C8102E" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <rect x="2" y="4" width="2.5" height="10" rx="0.5"/>
              <rect x="6.75" y="2" width="2.5" height="12" rx="0.5"/>
              <rect x="11.5" y="6" width="2.5" height="8" rx="0.5"/>
            </svg>
            <div class="metric-value">¥128.5万</div>
            <div class="metric-label">本月营收</div>
          </div>
          <div class="metric-card">
            <svg class="metric-icon" viewBox="0 0 16 16" fill="none" stroke="#3B82F6" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 3.5a1.5 1.5 0 011.5 1.5v5a1.5 1.5 0 01-1.5 1.5H6l-3.5 3v-3H2a1.5 1.5 0 01-1.5-1.5V5A1.5 1.5 0 012 3.5z"/>
            </svg>
            <div class="metric-value">1,247</div>
            <div class="metric-label">内容生成</div>
          </div>
          <div class="metric-card">
            <svg class="metric-icon" viewBox="0 0 16 16" fill="none" stroke="#10B981" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="2,10 6,6 9,9 14,4"/>
              <path d="M14 4H10M14 4v4"/>
            </svg>
            <div class="metric-value green">+23.5%</div>
            <div class="metric-label">环比增长</div>
          </div>
        </div>

        <div class="chart-area">
          <svg viewBox="0 0 360 50" preserveAspectRatio="none">
            <defs>
              <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#C8102E" stop-opacity="0.08"/>
                <stop offset="100%" stop-color="#C8102E" stop-opacity="0"/>
              </linearGradient>
            </defs>
            <path d="M0,40 C40,35 60,28 90,30 C120,32 140,22 170,20 C200,18 220,25 250,18 C280,11 300,8 330,6 C345,5 360,4 360,4 L360,50 L0,50 Z" fill="url(#chartGradient)"/>
            <path d="M0,40 C40,35 60,28 90,30 C120,32 140,22 170,20 C200,18 220,25 250,18 C280,11 300,8 330,6 C345,5 360,4 360,4" fill="none" stroke="#C8102E" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          <div class="chart-dots">
            <span></span>
            <span></span>
            <span></span>
            <span></span>
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>

        <div class="progress-row">
          <svg class="ring-chart" viewBox="0 0 32 32">
            <circle cx="16" cy="16" r="12" fill="none" stroke="#F3F4F6" stroke-width="3"/>
            <circle cx="16" cy="16" r="12" fill="none" stroke="#C8102E" stroke-width="3"
              stroke-dasharray="75.4 25.1" stroke-dashoffset="0"
              transform="rotate(-90 16 16)" stroke-linecap="round"/>
          </svg>
          <div class="progress-text">目标完成 78%</div>
        </div>
      </div>
    </div>

    <!-- Stats Bar -->
    <div class="stats-bar">
      <div class="stats-item">
        <svg class="stats-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 21h18"/>
          <path d="M5 21V7l7-4 7 4v14"/>
          <path d="M9 9h1M9 13h1M9 17h1M14 9h1M14 13h1M14 17h1"/>
        </svg>
        <div class="stats-number">50+</div>
        <div class="stats-label">服务企业</div>
      </div>
      <div class="stats-item">
        <svg class="stats-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
          <polyline points="14,2 14,8 20,8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
          <polyline points="10,9 9,9 8,9"/>
        </svg>
        <div class="stats-number">10,000+</div>
        <div class="stats-label">营销内容</div>
      </div>
      <div class="stats-item">
        <svg class="stats-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="2" y1="12" x2="22" y2="12"/>
          <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/>
        </svg>
        <div class="stats-number">30+</div>
        <div class="stats-label">覆盖国家</div>
      </div>
      <div class="stats-item">
        <svg class="stats-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
          <polyline points="22,4 12,14.01 9,11.01"/>
        </svg>
        <div class="stats-number">98%</div>
        <div class="stats-label">客户满意度</div>
      </div>
    </div>
  </div>'''

    if old_form_panel_content not in html:
        print(f"ERROR: Old form panel content not found in {filepath}")
        # Try to debug - find the approximate location
        idx = html.find('class="form-panel"')
        print(f"form-panel found at index: {idx}")
        return False

    html = html.replace(old_form_panel_content, new_form_panel_content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"Successfully updated: {filepath}")
    return True

if __name__ == '__main__':
    base = '/Coze/Drive/扣子/所有对话/主对话/rhc-repo'
    files = [
        f'{base}/frontend/login.html',
        f'{base}/backend/frontend/login.html',
    ]
    ok = True
    for f in files:
        if not update_file(f):
            ok = False
    if not ok:
        sys.exit(1)
    print("All files updated successfully.")
