/* ============================================================
 * RHC 市场洞察新闻数据 —— 全系统共享
 * 首页(panel.html) / 新闻中心(insights.html) / 销售素材库(sales.html) 共用
 * 更新新闻时只需修改本文件，三处自动同步。
 *
 * category 取值：
 *   industry   行业趋势（宏观/市场规模/投资/政策）
 *   market     市场动态（区域需求/展会/认证/采购趋势）
 *   competitor 同行新闻（竞品及同行公司商业动作）
 *   product    产品技术（新品发布/技术突破）
 *
 * 前期手动维护；后期接入 RSS 自动抓取时，替换本数据源即可，
 * 各页面渲染逻辑无需改动。
 * ============================================================ */
var RHC_INSIGHT_DATA = [];

/* ============================================================
 * RSS 实时数据引导（panel/library/sales 三页共享）
 * 数据唯一来源为后端 /api/insights（RSS 定时抓取 + LLM 翻译分类）。
 * 页面打开后异步拉取并覆盖空数据；拉取失败时标记离线，
 * 由各页面自行展示提示，不使用任何本地快照（避免内容闪烁）。
 * 新闻中心 insights.html 自带四列看板引导，不重复拉取。
 * 每 10 分钟静默轮询，条数或后端刷新时间变化才重渲染。
 * ============================================================ */
(function () {
  if (location.pathname.indexOf('insights.html') !== -1) return;

  var POLL_INTERVAL = 10 * 60 * 1000;
  var _lastSig = null;

  function rerender() {
    try {
      if (typeof renderInsightList === 'function') renderInsightList(_currentInsightCat || 'all');
    } catch (e) {}
    try { if (typeof renderMaterials === 'function') renderMaterials(); } catch (e) {}
    try { if (typeof renderLibFavorites === 'function') renderLibFavorites(); } catch (e) {}
  }

  function pull() {
    fetch('/api/insights')
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (res) {
        window.__INSIGHTS_OFFLINE = false;
        if (!res.items || !res.items.length) { rerender(); return; }
        var sig = res.items.length + '|' + (res.last_refresh && res.last_refresh.time ? res.last_refresh.time : '');
        if (sig === _lastSig) return;
        _lastSig = sig;
        window.RHC_INSIGHT_DATA = res.items;
        rerender();
      })
      .catch(function () {
        window.__INSIGHTS_OFFLINE = true;
        rerender();
      });
  }

  setTimeout(pull, 200);
  setInterval(pull, POLL_INTERVAL);
})();
