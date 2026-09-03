# -*- coding: utf-8 -*-
"""本地离线自测：用本地 HTTP mock 验证 find-email 核心逻辑（解析/抓取/过滤/排序/kind/超时/全失败）。
不触外网：搜索引擎函数 monkeypatch 为返回本地 URL；DDG/Bing HTML 解析用本地 fixture 页面。"""
import sys, os, re, threading, time, json
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
from app import main  # noqa: E402

# ---------- Mock 站点 ----------
OFFICIAL_HOME = """<html><body>
<h1>Acme Vet Supplies</h1>
<a href="/about-us">About</a>
<a href="/contact-us/">Contact Us</a>
<a href="https://facebook.com/acme">FB</a>
<a href="/files/catalog.pdf">Catalog PDF</a>
<span>webmaster@example.com</span>
<img src="/static/logo@2x.png">
<span>info@w3.org</span>
</body></html>"""

CONTACT_PAGE = """<html><body><h1>Contact</h1>
<p>Email us: <a href="mailto:sales@acmevet.com">sales@acmevet.com</a></p>
<p>General: info@acmevet.com &amp; partner@acmevet.com</p>
<p>Org foo@schema.org</p>
<p>this-is-a-very-long-email-address-over-forty-characters@acmevet.com</p>
</body></html>"""

ABOUT_PAGE = """<html><body><h1>About</h1>
<p>Reach our team at hello@acmevet.com</p></body></html>"""

SIGNAL_PAGE = """<html><body><h1>Press Release</h1>
<p>Acme Vet Supplies opens new clinic...</p>
<p>Media contact: press@news-wire.example.net</p>
<p>Also reach press@acmevet.com</p>
</body></html>"""

DDG_PAGE = """<html><body>
<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.acmevet.com%2F&amp;rut=xx">Acme Vet</a>
<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Facmevet.com%2Fcontact-us%2F&amp;rut=xx">Contact</a>
<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.facebook.com%2Facme&amp;rut=xx">FB</a>
<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Facmevet.com%2Ffiles%2Fcatalog.pdf&amp;rut=xx">PDF</a>
<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.linkedin.com%2Fcompany%2Facme&amp;rut=xx">LI</a>
</body></html>"""

BING_PAGE = """<html><body>
<a href="https://www.acmevet.com/">Acme</a>
<a href="https://cn.bing.com/ck/a?u=x">bing redirect</a>
<a href="https://www.acmevet.com/about-us">About</a>
</body></html>"""

ROUTES = {
    "/": ("text/html; charset=utf-8", OFFICIAL_HOME),
    "/about-us": ("text/html; charset=utf-8", ABOUT_PAGE),
    "/contact-us/": ("text/html; charset=utf-8", CONTACT_PAGE),
    "/signal": ("text/html; charset=utf-8", SIGNAL_PAGE),
    "/ddg": ("text/html; charset=utf-8", DDG_PAGE),
    "/bing": ("text/html; charset=utf-8", BING_PAGE),
    "/files/catalog.pdf": ("application/pdf", b"%PDF-1.4 fake"),
}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ROUTES:
            ctype, body = ROUTES[path]
            data = body if isinstance(body, bytes) else body.encode()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(404); self.end_headers()

server = HTTPServer(("127.0.0.1", 0), Handler)
port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{port}"

# 「新闻稿」页面：挂在主服务器 /press，但通过 _http_get 重定向用假域名访问，
# 模拟「新闻原文域 ≠ 官网域」，验证 kind=新闻原文
ROUTES["/press"] = ("text/html; charset=utf-8",
    "<html><body>Media: press@news-wire.example.net and press@acmevet.com</body></html>")
NEWS = "http://www.news-wire-diff-domain-test.example/press"
_orig_http_get = main._http_get
def _patched_get(url, timeout=main._EMAIL_FETCH_TIMEOUT):
    if url == NEWS:
        return _orig_http_get(BASE + "/press", timeout)
    return _orig_http_get(url, timeout)
main._http_get = _patched_get

failures = []
def check(name, cond, detail=""):
    print(("PASS" if cond else "FAIL"), name, ("-> " + detail if not cond else ""))
    if not cond: failures.append(name)

# 1) DDG uddg 还原
u = main._ddg_real_url("//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.acmevet.com%2F&rut=x")
check("DDG uddg 还原真实URL", u == "https://www.acmevet.com/", u)

# 2) DDG fixture 解析（本地复刻函数行为：直接对 /ddg 页面跑同款正则）
import urllib.request as _ur
req = _ur.Request(BASE + "/ddg", headers={"User-Agent": main._FIND_UA})
with _ur.urlopen(req, timeout=5) as r:
    ddg_html = r.read().decode()
ddg_urls = []
for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"', ddg_html):
    ux = main._ddg_real_url(m.group(1).replace("&amp;", "&"))
    if ux and ux not in ddg_urls: ddg_urls.append(ux)
check("DDG 解析 5 条结果", len(ddg_urls) == 5, str(ddg_urls))

# 3) 候选域名筛选
doms = main._candidate_official_domains(ddg_urls)
check("候选域名剔除社媒/PDF且去重", doms == ["www.acmevet.com"], str(doms))

# 4) Bing 解析：bing/microsoft 域过滤
req = _ur.Request(BASE + "/bing", headers={"User-Agent": main._FIND_UA})
with _ur.urlopen(req, timeout=5) as r:
    bing_html = r.read().decode()
from urllib.parse import urlparse
burls = []
for m in re.finditer(r'<a[^>]+href="(https?://[^"]+)"', bing_html):
    ux = m.group(1); host = urlparse(ux).netloc.lower()
    if "bing.com" in host or "microsoft.com" in host: continue
    burls.append(ux)
check("Bing 过滤自身跳转链接", burls == ["https://www.acmevet.com/", "https://www.acmevet.com/about-us"], str(burls))

# 5) 邮箱噪声过滤
bad = ["a@example.com", "x@sentry.io", "logo@2x.png", "y@w3.org", "z@schema.org",
       "this-is-a-very-long-email-address-over-forty-characters@acmevet.com",
       "good@acmevet.com", "sales@acmevet.com"]
valid = [e for e in bad if main._is_valid_email(e)]
check("噪声邮箱过滤", valid == ["good@acmevet.com", "sales@acmevet.com"], str(valid))

# 5b) 公司名 -> slug
check("slug 去 Inc 后缀", main._company_slug("Zoetis Inc.") == "zoetis", main._company_slug("Zoetis Inc."))
check("slug 多词连写", main._company_slug("Acme Veterinary Supplies Ltd") == "acmeveterinarysupplies")
check("首页匹配公司关键词", main._homepage_matches_company("<title>Acme Vet Supplies</title>", "Acme Vet", "acmevet") is True)
check("无关首页不匹配", main._homepage_matches_company("<title>Wikipedia</title>x"*1, "Acme Vet", "acmevet") is False)

# 5c) 多级降级：第 1 级直猜命中即不调用后续级
_calls = []
def _lvl_good(c, logs, dl): _calls.append("guess"); return ["www.acmevet.com"]
def _lvl_bad(c, logs, dl): _calls.append("later"); return ["should-not-be-used"]
main._discover_by_guess = _lvl_good
main._discover_by_ddg_ia = _lvl_bad
main._discover_by_wikipedia = _lvl_bad
main._discover_by_search_engines = _lvl_bad
_h, _l = main._discover_official_hosts("Acme", time.time()+35)
check("直猜命中即短路后续级", _calls == ["guess"] and _h == ["www.acmevet.com"], str(_calls))
# 前级失败逐级降级
_calls = []
main._discover_by_guess = lambda c, logs, dl: (_calls.append("g"), [])[1]
main._discover_by_ddg_ia = lambda c, logs, dl: (_calls.append("ia"), [])[1]
main._discover_by_wikipedia = lambda c, logs, dl: (_calls.append("w"), ["wikipedia-found.com"])[1]
main._discover_by_search_engines = lambda c, logs, dl: (_calls.append("b"), ["x.com"])[1]
_h, _l = main._discover_official_hosts("Acme", time.time()+35)
check("逐级降级到 Wikipedia 命中", _calls == ["g", "ia", "w"] and _h == ["wikipedia-found.com"], str(_calls))

# 6) 端到端：mock 官网发现返回本地 mock host（https 失败走 http 兜底）
main._discover_official_hosts = lambda c, dl: ([f"127.0.0.1:{port}"], ["直猜域名命中"])
t0 = time.time()
res = main.find_lead_email_candidates("Acme Vet Supplies", NEWS)
elapsed = time.time() - t0
print("候选结果:", json.dumps(res, ensure_ascii=False, indent=1))
emails = [c["email"] for c in res["candidates"]]
check("端到端返回 ok", res.get("ok") is True)
check("抓到官网邮箱 sales/info/hello/partner",
      {"sales@acmevet.com", "info@acmevet.com", "hello@acmevet.com", "partner@acmevet.com"} <= set(emails), str(emails))
check("抓到新闻原文邮箱 press@news-wire", "press@news-wire.example.net" in emails, str(emails))
check("噪声邮箱未出现",
      not any(e.endswith(("example.com", "w3.org", "schema.org", "2x.png")) or len(e) > 40 for e in emails), str(emails))
kinds = [c["kind"] for c in res["candidates"]]
check("官网候选排前、news-wire 为新闻原文",
      kinds[-1] == "新闻原文" and all(k == "官网" for k in kinds[:-1]),
      str([(c["email"], c["kind"]) for c in res["candidates"]]))
check("最多 5 个候选", len(res["candidates"]) <= 5, str(len(emails)))
check("每条含 source_url/host/kind",
      all(c.get("source_url") and c.get("host") and c.get("kind") for c in res["candidates"]))
check(f"耗时 {elapsed:.1f}s < 35s", elapsed < 35)

# 7) 官网发现链路全失败（各级返回空/原因入日志）-> RuntimeError 且含原因摘要
main._discover_official_hosts = lambda c, dl: ([], ["直猜域名无命中", "DDG-IA:URLError",
                                                    "Wikipedia:URLError", "Bing:302 挑战"])
try:
    main.find_lead_email_candidates("Nobody Co")
    check("官网发现全失败抛 RuntimeError", False)
except RuntimeError as e:
    check("官网发现全失败抛 RuntimeError", "官网发现失败" in str(e) and "Wikipedia" in str(e), str(e)[:100])

# 8) 发现到官网但页面无邮箱 -> 空候选 + message（不算失败）
main._discover_official_hosts = lambda c, dl: (["127.0.0.1:%d" % port], ["直猜命中"])
# mock 官网首页/子页均无邮箱：用一个返回空 body 的路径 —— 复用 /press 含 press@…，故改为空站
ROUTES["/empty"] = ("text/html; charset=utf-8", "<html><body>welcome no contact info here</body></html>")
def _empty_discovery(c, dl):
    # 返回一个 host，其首页与 contact/about 都无邮箱：直接 monkeypatch 抓取
    return ["127.0.0.1:%d" % port], ["直猜命中"]
_orig_crawl = main._crawl_official_site
main._crawl_official_site = lambda host, dl: [{"url": BASE + "/empty", "html": ROUTES["/empty"][1]}]
res2 = main.find_lead_email_candidates("Empty Co", "")
main._crawl_official_site = _orig_crawl
check("官网无邮箱返回空候选+message（非502）",
      res2.get("ok") and res2.get("candidates") == [] and "未在公开网页" in res2.get("message", ""),
      str(res2)[:120])

# 9) 预算耗尽：到点即返回不卡死（官网发现前已超时 -> hosts 空 -> RuntimeError 也应快速）
main._discover_official_hosts = lambda c, dl: ([], ["超时"])
main._FIND_EMAIL_BUDGET = 0.01
time.sleep(0.05)
t0 = time.time()
try:
    res3 = main.find_lead_email_candidates("Acme", BASE + "/signal")
    check("超预算安全返回", res3.get("ok") is True, str(res3)[:80])
except RuntimeError:
    check("超预算安全返回", (time.time() - t0) < 5, "RuntimeError 快速返回")
main._FIND_EMAIL_BUDGET = 35.0

# 10) 单个页面异常被吞（原文链接 404 不影响官网结果）
main._discover_official_hosts = lambda c, dl: (["127.0.0.1:%d" % port], ["直猜命中"])
res4 = main.find_lead_email_candidates("Acme", BASE + "/not-exist-page-404")
check("原文页404不影响官网抓取", res4.get("ok") and any(
    c["email"] == "info@acmevet.com" for c in res4["candidates"]), str(res4)[:120])

server.shutdown()
print("\n%d failures" % len(failures))
sys.exit(1 if failures else 0)
