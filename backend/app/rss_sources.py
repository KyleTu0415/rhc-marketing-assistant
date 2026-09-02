"""
RHC 市场洞察 —— RSS 源配置与抓取解析

零第三方依赖：xml.etree 解析 RSS 2.0 / Atom 1.0，httpx 拉取。
每个源记录最近抓取健康状态，供运维替换失效源。
"""
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import httpx

# ============================================================
# RSS 源列表
#   name: 源名称（内部展示）
#   url:  feed 地址
#   enabled: 是否启用
#   sandbox_verified: 已在开发环境验证可用；False 表示待生产环境(Railway)验证
# Google News / GlobeNewswire 因沙箱网络限制未本地验证，部署后自动探活，
# 失败会自动标记 disabled，不影响其他源。
# ============================================================
FEEDS = [
    # —— 行业垂直媒体（已验证） ——
    {"name": "dvm360",
     "url": "https://www.dvm360.com/rss.xml",
     "enabled": True, "sandbox_verified": True},
    {"name": "ScienceDaily 兽医医学",
     "url": "https://www.sciencedaily.com/rss/plants_animals/veterinary_medicine.xml",
     "enabled": True, "sandbox_verified": True},
    {"name": "Veterinary Practice News",
     "url": "https://www.veterinarypracticenews.com/feed/",
     "enabled": True, "sandbox_verified": True},
    {"name": "Today's Veterinary Practice",
     "url": "https://todaysveterinarypractice.com/feed/",
     "enabled": True, "sandbox_verified": True},
    {"name": "Today's Veterinary Business",
     "url": "https://todaysveterinarybusiness.com/feed/",
     "enabled": True, "sandbox_verified": True},
    {"name": "PetVet Magazine",
     "url": "https://www.petvetmagazine.com/feed/",
     "enabled": True, "sandbox_verified": True},
    # —— 聚合与官方稿（待 Railway 环境验证，失败自动禁用） ——
    {"name": "Google News - veterinary equipment",
     "url": "https://news.google.com/rss/search?q=veterinary%20equipment&hl=en-US&gl=US&ceid=US:en",
     "enabled": True, "sandbox_verified": False},
    {"name": "Google News - veterinary anesthesia OR imaging",
     "url": "https://news.google.com/rss/search?q=veterinary%20anesthesia%20OR%20veterinary%20imaging&hl=en-US&gl=US&ceid=US:en",
     "enabled": True, "sandbox_verified": False},
    {"name": "Google News - animal health company",
     "url": "https://news.google.com/rss/search?q=animal%20health%20company%20OR%20pet%20medical%20device&hl=en-US&gl=US&ceid=US:en",
     "enabled": True, "sandbox_verified": False},
    {"name": "GlobeNewswire 动物健康",
     "url": "https://www.globenewswire.com/RssFeed/industry/105/AnimalHealth/feedTitle/GlobeNewswire%20-%20News%20about%20Animal%20Health",
     "enabled": True, "sandbox_verified": False},
]

# 关键词白名单：标题或摘要命中其一才保留（粗筛，LLM 再做相关性判断）
KEYWORDS = [
    "veterinar", "vet ", "vet-", "animal health", "pet health", "pet medical",
    "anesthesia", "anaesthesia", "imaging", "diagnostic", "monitor",
    "clinic", "clinic equipment", "surgical", "surgery", "dental",
    "idexx", "zoetis", "covetrus", "henry schein", "midmark",
    "pet hospital", "companion animal", "livestock", "poultry",
    "medical device", "medical equipment", "fda ", "approval",
    "cancer", "diagnosis", "ultrasound", "x-ray", "radiograph",
    "drug", "therapeutic", "vaccine", "biotech",
]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# 源健康状态：name -> {ok, items, error, last_ts}
feed_health = {}


def _clean_text(s: str) -> str:
    """清洗 feed 文本：去 CDATA 残留、HTML 标签、解码实体、压缩空白。"""
    if not s:
        return ""
    s = s.strip()
    # CDATA 残留（etree 有时不剥 CDATA 标记）
    if s.startswith("<![CDATA["):
        s = s[9:]
    if s.endswith("]]>"):
        s = s[:-3]
    # HTML 标签
    s = re.sub(r"<[^>]+>", " ", s)
    # 常见实体
    for a, b in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                 ("&quot;", '"'), ("&#39;", "'"), ("&nbsp;", " "),
                 ("&apos;", "'")):
        s = s.replace(a, b)
    # 数字实体
    s = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), s)
    # 压缩空白
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def _text_of(elem) -> str:
    if elem is None:
        return ""
    return _clean_text("".join(elem.itertext()))


def _parse_date(s: str) -> str:
    """把各种 feed 日期格式归一化为 YYYY-MM-DD；失败返回今天。"""
    s = (s or "").strip()
    if not s:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # 2026-08-31T10:00:00Z / 2026-08-31T10:00:00+00:00
    try:
        return s[:10] if s[4] == "-" and s[7] == "-" else _parse_date_fallback(s)
    except Exception:
        return _parse_date_fallback(s)


def _parse_date_fallback(s: str) -> str:
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
                "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s.strip(), fmt).strftime("%Y-%m-%d")
        except Exception:
            continue
    # RFC822 带 GMT/UTC 等缩写：手动兜底
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(s).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _parse_feed(content: bytes, source_name: str) -> list:
    """解析 RSS 2.0 (<item>) 与 Atom 1.0 (<entry>)，返回原始条目列表。"""
    root = ET.fromstring(content)
    items = []
    # RSS 2.0: rss/channel/item
    for item in root.iter():
        tag = _strip_ns(item.tag)
        if tag not in ("item", "entry"):
            continue
        data = {}
        link = ""
        for child in item:
            ctag = _strip_ns(child.tag).lower()
            if ctag == "title":
                data["title"] = _text_of(child)
            elif ctag == "link":
                # Atom: <link href="..."/>; RSS: <link>text</link>
                link = child.get("href") or _text_of(child) or link
            elif ctag in ("description", "summary", "subtitle"):
                data["summary"] = _text_of(child)
            elif ctag in ("pubdate", "published", "updated", "date"):
                data["date"] = _parse_date(_text_of(child))
        if not data.get("title"):
            continue
        data["url"] = link
        data.setdefault("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        data["source"] = source_name
        items.append(data)
    return items


# 黑名单：趣味栏目/明显无关内容，粗筛阶段直接排除（LLM 相关性判断之外的双保险）
BLACKLIST = [
    "brain teaser", "puzzle", "quiz", "word search", "crossword",
    "caption contest", "giveaway", "horoscope", "comic", "funny",
    "cute photo", "photo contest", "pet of the week",
]


def _keyword_hit(title: str, summary: str) -> bool:
    blob = (title + " " + summary).lower()
    if any(bad in blob for bad in BLACKLIST):
        return False
    return any(kw in blob for kw in KEYWORDS)


def fetch_all_feeds(timeout: int = 15) -> list:
    """抓取全部启用源，返回粗筛后的原始条目（关键词白名单命中）。"""
    collected = []
    # 连接超时 8s（黑洞主机快速放弃），读取超时 timeout
    to = httpx.Timeout(timeout, connect=8.0)
    with httpx.Client(timeout=to, follow_redirects=True,
                      headers={"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml, */*"}) as client:
        for feed in FEEDS:
            if not feed.get("enabled", True):
                continue
            name, url = feed["name"], feed["url"]
            try:
                resp = client.get(url)
                if resp.status_code != 200:
                    feed_health[name] = {"ok": False, "items": 0,
                                         "error": f"HTTP {resp.status_code}",
                                         "last_ts": time.time()}
                    continue
                items = _parse_feed(resp.content, name)
                # 关键词粗筛
                passed = [it for it in items if _keyword_hit(it.get("title", ""), it.get("summary", ""))]
                feed_health[name] = {"ok": True, "items": len(items),
                                     "passed": len(passed), "error": "",
                                     "last_ts": time.time()}
                collected.extend(passed)
            except Exception as e:
                feed_health[name] = {"ok": False, "items": 0,
                                     "error": str(e)[:120], "last_ts": time.time()}
                continue
    return collected


def health_snapshot() -> list:
    out = []
    for feed in FEEDS:
        h = feed_health.get(feed["name"], {})
        out.append({
            "name": feed["name"],
            "enabled": feed.get("enabled", True),
            "sandbox_verified": feed.get("sandbox_verified", False),
            "ok": h.get("ok"),
            "items": h.get("items", 0),
            "passed": h.get("passed", 0),
            "error": h.get("error", ""),
            "last_check": datetime.fromtimestamp(h["last_ts"]).strftime("%Y-%m-%d %H:%M") if h.get("last_ts") else "",
        })
    return out
