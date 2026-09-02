#!/usr/bin/env python3
"""Fix all bugs in sales.html and sync to backend/frontend/sales.html"""
import os
import re

REPO_DIR = '/Coze/Drive/扣子/所有对话/主对话/rhc-repo'
FRONTEND_SALES = os.path.join(REPO_DIR, 'frontend/sales.html')
BACKEND_SALES = os.path.join(REPO_DIR, 'backend/frontend/sales.html')
PANEL_HTML = os.path.join(REPO_DIR, 'frontend/panel.html')


def extract_panel_insight_data():
    """Extract RHC_INSIGHT_DATA from panel.html and return as single-line JS variable declaration."""
    with open(PANEL_HTML, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the variable
    idx = content.find('RHC_INSIGHT_DATA = [')
    if idx == -1:
        raise ValueError("RHC_INSIGHT_DATA not found in panel.html")

    # Find matching closing bracket
    bracket_start = content.find('[', idx)
    depth = 0
    i = bracket_start
    while i < len(content):
        if content[i] == '[':
            depth += 1
        elif content[i] == ']':
            depth -= 1
            if depth == 0:
                break
        i += 1

    full_block = content[idx:i+1]
    # Minify: remove leading spaces per line, join into compact form
    lines = full_block.split('\n')
    compact_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped:
            compact_lines.append(stripped)
    compact = ' '.join(compact_lines)
    # Fix: panel uses "RHC_INSIGHT_DATA = [" but sales uses "var RHC_INSIGHT_DATA=["
    compact = compact.replace('RHC_INSIGHT_DATA = [', 'var RHC_INSIGHT_DATA=[')
    return compact


def fix_bug1_nested_comment(content):
    """Fix Bug 1: nested JS comment on grading rules line."""
    old = '/* 分级规则从规则配置中心读取/* 分级规则从规则配置中心读取（assets/rhc-config.js），不再写死在本页面 */'
    new = '/* 分级规则从规则配置中心读取（assets/rhc-config.js），不再写死在本页面 */'
    if old not in content:
        print("WARNING: Bug 1 pattern not found, checking alternative...")
        # Try to find the nested pattern
        pattern = r'/\* 分级规则从规则配置中心读取/\* 分级规则从规则配置中心读取[^*]*\*/'
        match = re.search(pattern, content)
        if match:
            content = content.replace(match.group(0), new)
            print(f"Bug 1 fixed via regex: {match.group(0)[:60]}...")
        else:
            print("WARNING: Could not find Bug 1 pattern")
    else:
        content = content.replace(old, new)
        print("Bug 1 fixed: nested comment cleaned up")
    return content


def fix_bug3_insight_data(content, panel_data_compact):
    """Fix Bug 3: replace RHC_INSIGHT_DATA with panel.html version for ID sync."""
    # Find the current RHC_INSIGHT_DATA block in sales.html
    idx = content.find('var RHC_INSIGHT_DATA=[')
    if idx == -1:
        idx = content.find('var RHC_INSIGHT_DATA = [')
    if idx == -1:
        raise ValueError("RHC_INSIGHT_DATA not found in sales.html")

    bracket_start = content.find('[', idx)
    depth = 0
    i = bracket_start
    while i < len(content):
        if content[i] == '[':
            depth += 1
        elif content[i] == ']':
            depth -= 1
            if depth == 0:
                break
        i += 1

    old_block = content[idx:i+1]
    content = content.replace(old_block, panel_data_compact)
    print(f"Bug 3 fixed: RHC_INSIGHT_DATA replaced ({len(old_block)} -> {len(panel_data_compact)} chars)")
    return content


def build_modal_html():
    """Build the new inline modal HTML (replacing iframe modal)."""
    return '''<div id="library-modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:9999;align-items:center;justify-content:center">
  <div class="lib-modal-box">
    <div class="lib-modal-header">
      <span class="lib-modal-title">📚 个人素材库</span>
      <button class="lib-modal-close" onclick="closeLibraryModal()">&times;</button>
    </div>
    <div class="lib-modal-tabs">
      <div class="lib-modal-tab active" data-tab="favorites" onclick="switchLibModalTab('favorites')">我的收藏</div>
      <div class="lib-modal-tab" data-tab="following" onclick="switchLibModalTab('following')">我的关注</div>
    </div>
    <div class="lib-modal-body">
      <!-- 我的收藏 Tab -->
      <div id="lib-tab-favorites">
        <div class="lib-modal-search">
          <input type="text" id="lib-search-input" placeholder="搜索收藏的新闻..." oninput="renderLibFavorites()">
          <span class="lib-modal-count" id="lib-fav-count">共 0 条</span>
        </div>
        <div class="lib-modal-filter">
          <div class="lib-filter-chip active" data-cat="all" onclick="setLibFilter('all')">全部</div>
          <div class="lib-filter-chip" data-cat="industry" onclick="setLibFilter('industry')">行业趋势</div>
          <div class="lib-filter-chip" data-cat="market" onclick="setLibFilter('market')">市场动态</div>
          <div class="lib-filter-chip" data-cat="competitor" onclick="setLibFilter('competitor')">同行新闻</div>
        </div>
        <div class="lib-modal-list" id="lib-fav-list">
          <!-- JS 动态渲染 -->
        </div>
      </div>
      <!-- 我的关注 Tab -->
      <div id="lib-tab-following" style="display:none">
        <div class="lib-settings-section">
          <div class="lib-settings-title">📍 关注的区域市场</div>
          <div class="lib-checkbox-group" id="lib-pref-regions"></div>
        </div>
        <div class="lib-settings-section">
          <div class="lib-settings-title">🔧 关注的产品线</div>
          <div class="lib-checkbox-group" id="lib-pref-products"></div>
        </div>
        <div class="lib-settings-section">
          <div class="lib-settings-title">🏥 关注的客户类型</div>
          <div class="lib-checkbox-group" id="lib-pref-customers"></div>
        </div>
        <div style="margin-top:16px">
          <button class="btn btn-primary btn-sm" onclick="saveLibPreferences()">保存设置</button>
        </div>
      </div>
    </div>
  </div>
</div>'''


def build_modal_css():
    """Build CSS styles for the inline modal."""
    return '''
/* ===== 个人素材库弹窗（内嵌式） ===== */
.lib-modal-box{
  background:#fff;border-radius:12px;width:90%;max-width:640px;height:70vh;
  position:relative;box-shadow:0 20px 60px rgba(0,0,0,0.3);
  display:flex;flex-direction:column;overflow:hidden;
  font-family:var(--font-sans);
}
.lib-modal-header{
  display:flex;align-items:center;justify-content:space-between;
  padding:14px 20px;border-bottom:1px solid var(--color-border-light);
  flex-shrink:0;
}
.lib-modal-title{font-size:15px;font-weight:700;color:var(--color-text)}
.lib-modal-close{
  background:none;border:none;font-size:22px;cursor:pointer;color:#999;
  width:28px;height:28px;display:flex;align-items:center;justify-content:center;
  border-radius:4px;transition:all var(--transition-fast);line-height:1;
}
.lib-modal-close:hover{background:var(--color-surface);color:var(--color-text)}
.lib-modal-tabs{
  display:flex;gap:0;border-bottom:1px solid var(--color-border-light);
  flex-shrink:0;background:var(--color-surface);
}
.lib-modal-tab{
  padding:10px 20px;font-size:12px;font-weight:600;
  color:var(--color-text-secondary);cursor:pointer;
  border-bottom:2px solid transparent;transition:all var(--transition-fast);
  margin-bottom:-1px;
}
.lib-modal-tab:hover{color:var(--color-primary)}
.lib-modal-tab.active{color:var(--color-primary);border-bottom-color:var(--color-primary);background:#fff}
.lib-modal-body{flex:1;overflow-y:auto;padding:16px 20px}

/* 收藏 tab */
.lib-modal-search{display:flex;gap:8px;align-items:center;margin-bottom:12px;flex-wrap:wrap}
.lib-modal-search input[type="text"]{
  flex:1;min-width:160px;padding:6px 12px 6px 32px;border-radius:16px;
  background:#fff url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='%239CA3AF' stroke-width='2'%3E%3Ccircle cx='11' cy='11' r='8'/%3E%3Cline x1='21' y1='21' x2='16.65' y2='16.65'/%3E%3C/svg%3E") 10px center no-repeat;
  border:1px solid var(--color-border);font-size:12px;
}
.lib-modal-search input[type="text"]:focus{outline:none;border-color:var(--color-primary)}
.lib-modal-count{font-size:11px;color:var(--color-text-tertiary);white-space:nowrap}

.lib-modal-filter{display:flex;gap:4px;margin-bottom:14px;flex-wrap:wrap}
.lib-filter-chip{
  padding:4px 12px;font-size:11px;font-weight:500;
  color:var(--color-text-secondary);background:var(--color-surface);
  border:1px solid var(--color-border);border-radius:12px;
  cursor:pointer;transition:all var(--transition-fast);
}
.lib-filter-chip:hover{border-color:var(--color-primary);color:var(--color-primary)}
.lib-filter-chip.active{
  background:var(--color-primary-light);border-color:var(--color-primary);
  color:var(--color-primary);font-weight:600;
}

.lib-modal-list{display:flex;flex-direction:column;gap:8px}
.lib-fav-card{
  background:var(--color-surface);border:1px solid var(--color-border);
  border-radius:8px;padding:10px 12px;transition:all var(--transition-fast);
}
.lib-fav-card:hover{box-shadow:0 2px 8px rgba(0,0,0,0.06);border-color:var(--color-primary)}
.lib-fav-title{font-size:12px;font-weight:600;color:var(--color-text);line-height:1.5;margin-bottom:4px}
.lib-fav-meta{display:flex;align-items:center;gap:6px;margin-bottom:4px}
.lib-fav-cat{
  display:inline-flex;align-items:center;padding:1px 6px;border-radius:3px;
  font-size:10px;font-weight:600;line-height:1.4;
}
.lib-fav-cat.industry{background:#E3F2FD;color:#1565C0}
.lib-fav-cat.market{background:#E8F5E9;color:#2E7D32}
.lib-fav-cat.competitor{background:#FFF3E0;color:#E65100}
.lib-fav-date{font-size:11px;color:var(--color-text-tertiary)}
.lib-fav-summary{font-size:11px;color:var(--color-text-secondary);line-height:1.6;margin-bottom:6px}
.lib-fav-actions{display:flex;gap:6px;flex-wrap:wrap}
.lib-fav-actions button{font-size:10px;padding:3px 8px;border-radius:4px;font-weight:500}

/* 关注 tab */
.lib-settings-section{
  background:var(--color-surface);border:1px solid var(--color-border);
  border-radius:8px;padding:12px 14px;margin-bottom:12px;
}
.lib-settings-title{font-size:12px;font-weight:700;color:var(--color-text);margin-bottom:10px;display:flex;align-items:center;gap:6px}
.lib-checkbox-group{display:flex;flex-wrap:wrap;gap:6px}
.lib-checkbox-item{
  display:inline-flex;align-items:center;gap:4px;padding:4px 10px;border-radius:12px;
  border:1px solid var(--color-border);font-size:11px;font-weight:500;
  color:var(--color-text-secondary);cursor:pointer;transition:all var(--transition-fast);
  user-select:none;
}
.lib-checkbox-item:hover{border-color:var(--color-primary);color:var(--color-primary)}
.lib-checkbox-item.checked{
  background:var(--color-primary-light);border-color:var(--color-primary);
  color:var(--color-primary);font-weight:600;
}
.lib-checkbox-item input{display:none}

.lib-empty{
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  text-align:center;padding:30px 16px;gap:6px;color:var(--color-text-tertiary);
}
.lib-empty .lib-empty-title{font-size:13px;font-weight:600;color:var(--color-text-secondary)}
.lib-empty .lib-empty-desc{font-size:11px;color:var(--color-text-tertiary);max-width:280px;line-height:1.6}
'''


def build_modal_js():
    """Build JS functions for the inline modal."""
    return '''
/* ===== 素材库弹窗（内嵌式）逻辑 ===== */
var libModalCurrentTab = 'favorites';
var libModalFilter = 'all';
var LIB_REGION_OPTIONS = [
  {value:'brazil',label:'巴西'},{value:'africa',label:'非洲'},{value:'southeast-asia',label:'东南亚'},
  {value:'middle-east',label:'中东'},{value:'north-america',label:'北美'},{value:'europe',label:'欧洲'},
  {value:'china',label:'国内'},{value:'asia',label:'亚太'}
];
var LIB_PRODUCT_OPTIONS = [
  {value:'anesthesia-workstation',label:'麻醉工作站'},{value:'ventilator',label:'呼吸机'},
  {value:'v5-plus',label:'V5 Plus'},{value:'x35vet',label:'X35VET'},
  {value:'portable-anesthesia',label:'便携麻醉设备'},{value:'monitor',label:'监护仪'},
  {value:'infusion-pump',label:'注射泵/输液泵'}
];
var LIB_CUSTOMER_OPTIONS = [
  {value:'animal-hospital',label:'动物医院'},{value:'clinic',label:'兽医诊所'},
  {value:'research',label:'科研院所'},{value:'education',label:'教育机构'},
  {value:'distributor',label:'经销商'},{value:'government',label:'政府采购'}
];

function openLibraryModal(){
  var modal=document.getElementById('library-modal');
  modal.style.display='flex';
  switchLibModalTab('favorites');
  renderLibFavorites();
  renderLibPreferences();
}
function closeLibraryModal(){
  document.getElementById('library-modal').style.display='none';
}
function switchLibModalTab(tab){
  libModalCurrentTab=tab;
  document.getElementById('lib-tab-favorites').style.display=tab==='favorites'?'':'none';
  document.getElementById('lib-tab-following').style.display=tab==='following'?'':'none';
  document.querySelectorAll('.lib-modal-tab').forEach(function(t){
    t.classList.toggle('active',t.getAttribute('data-tab')===tab);
  });
}

/* 收藏列表 */
function getLibSavedIds(){
  try{return JSON.parse(localStorage.getItem('rhc_saved_insights')||'[]')}catch(e){return[]}
}
function saveLibSavedIds(ids){localStorage.setItem('rhc_saved_insights',JSON.stringify(ids))}

function setLibFilter(cat){
  libModalFilter=cat;
  document.querySelectorAll('.lib-filter-chip').forEach(function(c){
    c.classList.toggle('active',c.getAttribute('data-cat')===cat);
  });
  renderLibFavorites();
}

function renderLibFavorites(){
  var savedIds=getLibSavedIds();
  var items=RHC_INSIGHT_DATA.filter(function(item){return savedIds.indexOf(item.id)>=0});
  if(libModalFilter!=='all'){
    items=items.filter(function(item){return item.category===libModalFilter});
  }
  var keyword='';
  var searchEl=document.getElementById('lib-search-input');
  if(searchEl)keyword=(searchEl.value||'').trim().toLowerCase();
  if(keyword){
    items=items.filter(function(item){
      return item.title.toLowerCase().indexOf(keyword)>=0||
             item.summary.toLowerCase().indexOf(keyword)>=0;
    });
  }
  items.sort(function(a,b){return b.date.localeCompare(a.date)});
  var countEl=document.getElementById('lib-fav-count');
  if(countEl)countEl.textContent='共 '+items.length+' 条';
  var container=document.getElementById('lib-fav-list');
  if(!container)return;
  if(items.length===0){
    var savedTotal=getLibSavedIds().length;
    if(savedTotal===0){
      container.innerHTML='<div class="lib-empty">'+
        '<svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z"/></svg>'+
        '<div class="lib-empty-title">还没有收藏任何资讯</div>'+
        '<div class="lib-empty-desc">前往首页「市场洞察」，点击新闻卡片上的收藏按钮，感兴趣的资讯会自动收集到这里</div>'+
      '</div>';
    }else{
      container.innerHTML='<div class="lib-empty">'+
        '<div class="lib-empty-title">当前分类下没有收藏</div>'+
        '<div class="lib-empty-desc">试试切换到「全部」查看所有收藏</div>'+
      '</div>';
    }
    return;
  }
  var html='';
  items.forEach(function(item){
    var catClass=item.category;
    var actions='';
    if(item.url){
      actions+='<a href="'+item.url+'" target="_blank" rel="noopener" class="btn btn-outline btn-sm">查看原文 ↗</a>';
    }
    actions+='<button class="btn btn-outline btn-sm" onclick="useLibInMail(\''+item.id+'\')">✉️ 用于写邮件</button>';
    actions+='<button class="btn btn-outline btn-sm" style="border-color:#ffcdd2;color:#e53935" onclick="removeLibFav(\''+item.id+'\')">移除</button>';
    html+='<div class="lib-fav-card">'+
      '<div class="lib-fav-title">'+escHtml(item.title)+'</div>'+
      '<div class="lib-fav-meta">'+
        '<span class="lib-fav-cat '+catClass+'">'+escHtml(item.categoryLabel)+'</span>'+
        '<span class="lib-fav-date">'+escHtml(item.date)+'</span>'+
      '</div>'+
      '<div class="lib-fav-summary">'+escHtml(item.summary)+'</div>'+
      '<div class="lib-fav-actions">'+actions+'</div>'+
    '</div>';
  });
  container.innerHTML=html;
}

function removeLibFav(id){
  var ids=getLibSavedIds();
  ids=ids.filter(function(i){return i!==id});
  saveLibSavedIds(ids);
  renderLibFavorites();
  renderMailMaterials();
  showToast('已从素材库移除','success');
}

function useLibInMail(id){
  closeLibraryModal();
  // 切换到邮件助手页并选中素材
  var mailNav=document.querySelector('[data-page=mail]');
  if(mailNav)switchPage('mail',mailNav);
  // 自动勾选该素材
  if(selectedMaterialIds.indexOf(id)<0){
    if(selectedMaterialIds.length>=2){
      showToast('最多选择2条素材','warning');
      return;
    }
    selectedMaterialIds.push(id);
  }
  renderMailMaterials();
  showToast('已添加到邮件素材','success');
}

/* 关注设置 */
function getLibPreferences(){
  try{return JSON.parse(localStorage.getItem('rhc_user_preferences')||'{}')}catch(e){return{}}
}

function renderLibPreferences(){
  var prefs=getLibPreferences();
  var prefRegions=prefs.regions||[];
  var prefProducts=prefs.products||[];
  var prefCustomers=prefs.customers||[];
  renderLibCheckboxGroup('lib-pref-regions',LIB_REGION_OPTIONS,prefRegions);
  renderLibCheckboxGroup('lib-pref-products',LIB_PRODUCT_OPTIONS,prefProducts);
  renderLibCheckboxGroup('lib-pref-customers',LIB_CUSTOMER_OPTIONS,prefCustomers);
}

function renderLibCheckboxGroup(containerId,options,selected){
  var container=document.getElementById(containerId);
  if(!container)return;
  var html='';
  options.forEach(function(opt){
    var checked=selected.indexOf(opt.value)>=0;
    html+='<label class="lib-checkbox-item'+(checked?' checked':'')+'" onclick="toggleLibCheckbox(this)">'+
      '<input type="checkbox" value="'+opt.value+'"'+(checked?' checked':'')+'>'+
      escHtml(opt.label)+
    '</label>';
  });
  container.innerHTML=html;
}

function toggleLibCheckbox(el){
  var input=el.querySelector('input');
  input.checked=!input.checked;
  el.classList.toggle('checked',input.checked);
}

function saveLibPreferences(){
  var prefs={};
  prefs.regions=getLibCheckedValues('lib-pref-regions');
  prefs.products=getLibCheckedValues('lib-pref-products');
  prefs.customers=getLibCheckedValues('lib-pref-customers');
  localStorage.setItem('rhc_user_preferences',JSON.stringify(prefs));
  showToast('设置已保存','success');
}

function getLibCheckedValues(containerId){
  var vals=[];
  var container=document.getElementById(containerId);
  if(container){
    container.querySelectorAll('input:checked').forEach(function(input){vals.push(input.value)});
  }
  return vals;
}

function escHtml(s){
  var d=document.createElement('div');
  d.textContent=s;
  return d.innerHTML;
}
'''


def fix_bug2_modal(content):
    """Fix Bug 2: Replace iframe modal with inline content modal."""
    # Find the old library-modal div block
    old_modal_pattern = re.compile(
        r'<div id="library-modal"[^>]*>.*?</div>\s*</div>',
        re.DOTALL
    )
    match = old_modal_pattern.search(content)
    if not match:
        raise ValueError("Could not find library-modal in sales.html")

    old_modal = match.group(0)
    new_modal = build_modal_html()
    content = content.replace(old_modal, new_modal)
    print(f"Bug 2 fixed: modal replaced ({len(old_modal)} -> {len(new_modal)} chars)")

    # Add CSS styles before </style> closing tag or before the modal
    # Find the end of the style section (last </style> before body content)
    # We'll add CSS right before the modal
    css_block = f'\n<style>\n{build_modal_css()}\n</style>\n'
    # Insert CSS right before the library-modal div
    content = content.replace(
        '<div id="library-modal"',
        css_block + '<div id="library-modal"'
    )
    print("Bug 2 fixed: modal CSS added")

    # Add JS functions - replace the old openLibraryModal/closeLibraryModal functions
    # Find the old functions
    old_funcs_pattern = re.compile(
        r'function openLibraryModal\(\)\{[^}]*\}\s*function closeLibraryModal\(\)\{[^}]*\}',
        re.DOTALL
    )
    match = old_funcs_pattern.search(content)
    if match:
        old_funcs = match.group(0)
        new_js = build_modal_js()
        content = content.replace(old_funcs, new_js)
        print(f"Bug 2 fixed: modal JS replaced ({len(old_funcs)} -> {len(new_js)} chars)")
    else:
        print("WARNING: Could not find openLibraryModal/closeLibraryModal functions")

    return content


def main():
    # Read files
    with open(FRONTEND_SALES, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"Original sales.html: {len(content)} chars")

    # Step 1: Get panel.html RHC_INSIGHT_DATA
    panel_data = extract_panel_insight_data()
    print(f"Panel RHC_INSIGHT_DATA: {len(panel_data)} chars")

    # Step 2: Fix Bug 1 - nested comment
    content = fix_bug1_nested_comment(content)

    # Step 3: Fix Bug 3 - ID sync (replace RHC_INSIGHT_DATA with panel version)
    content = fix_bug3_insight_data(content, panel_data)

    # Step 4: Fix Bug 2 & 4 - replace iframe modal with inline content
    content = fix_bug2_modal(content)

    # Write frontend file
    with open(FRONTEND_SALES, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\nFixed sales.html written to frontend/: {len(content)} chars")

    # Sync to backend
    with open(BACKEND_SALES, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Synced to backend/frontend/sales.html: {len(content)} chars")

    # Verify files are identical
    with open(FRONTEND_SALES, 'r', encoding='utf-8') as f:
        f1 = f.read()
    with open(BACKEND_SALES, 'r', encoding='utf-8') as f:
        f2 = f.read()
    assert f1 == f2, "Files are not identical!"
    print("Verification: frontend and backend files are identical ✓")

    # Sanity checks
    # Check no nested comment remains
    assert '分级规则从规则配置中心读取/* 分级规则' not in content, "Bug 1 not fixed!"
    print("Sanity check: no nested comment ✓")

    # Check no iframe in modal
    assert '<iframe src="library.html"' not in content, "Bug 2 not fixed!"
    print("Sanity check: no iframe in modal ✓")

    # Check ID format
    assert 'ins-001' in content, "ID format check failed!"
    assert 'ins-012' in content, "ID format check failed!"
    print("Sanity check: ID format is ins-XXX ✓")

    # Check required elements exist
    assert 'lib-modal-box' in content, "Modal box CSS missing!"
    assert 'lib-tab-favorites' in content, "Favorites tab missing!"
    assert 'lib-tab-following' in content, "Following tab missing!"
    assert 'switchLibModalTab' in content, "Tab switch function missing!"
    assert 'renderLibFavorites' in content, "Favorites render function missing!"
    assert 'saveLibPreferences' in content, "Preferences save function missing!"
    print("Sanity check: all modal elements present ✓")

    print("\n✅ All fixes applied successfully!")


if __name__ == '__main__':
    main()
