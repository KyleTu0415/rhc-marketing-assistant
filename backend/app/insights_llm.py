"""
RHC 市场洞察 —— LLM 加工：英文新闻 -> 中文标题/摘要 + 分类 + 地区 + 相关性筛选

调用 OpenAI 兼容接口（默认 DeepSeek），批量处理，成本约几分钱/轮。
"""
import json
import os
import httpx

SYSTEM_PROMPT = """你是兽医医疗器械出口公司（安瑞康 RHC，产品：动物麻醉机、监护仪、影像设备、注射泵等）的市场情报编辑。
我会给你一批英文行业新闻（标题+摘要），你需要：
1. 判断相关性：只保留与【兽医/动物医疗行业、兽医设备器械、动物医药、宠物医疗市场、兽医诊所经营、同行商业动态】相关的新闻。
   纯宠物趣事、人类医疗、体育娱乐、政治、股市大盘等无关内容一律剔除。
2. 把保留的新闻翻译成专业中文：标题简洁专业（20-35字），摘要1-2句（40-70字），面向外贸销售人员阅读。
3. 分类（category）四选一：
   - industry 行业趋势：宏观市场规模、投资融资、行业政策、行业报告
   - market 市场动态：区域市场需求、展会、认证采购、诊所经营趋势
   - competitor 同行新闻：同行公司（IDEXX/Zoetis/Covetrus/Midmark/其他兽医器械与药企）的商业动作、并购、合作
   - product 产品技术：新品发布、技术突破、药物获批、临床技术
4. 地区（regions，可多选，从以下取值）：
   global 全球 / north-america 北美 / europe 欧洲 / africa 非洲 /
   middle-east 中东 / southeast-asia 东南亚 / brazil 巴西 / china 中国 / asia 亚洲
   新闻未提及具体地区时给 ["global"]。

严格只输出 JSON 数组，不要任何解释文字。格式：
[{"id": 0, "relevant": true, "category": "market", "title_zh": "中文标题", "summary_zh": "中文摘要", "regions": ["north-america"]}, ...]
不相关的新闻输出 {"id": 编号, "relevant": false}，id 必须与输入编号一一对应。"""


def _client_cfg():
    return {
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1").rstrip("/"),
        "model": os.getenv("OPENAI_TEXT_MODEL", "deepseek-chat"),
    }


def process_items(raw_items: list, batch_size: int = 10) -> list:
    """
    输入：rss_sources 抓取的原始条目（含 title/summary/url/date/source）
    输出：加工后的条目列表（仅相关项），字段对齐 rhc-insights.js：
      id/category/categoryLabel/categoryColor/title/summary/date/url/regions/source
    """
    cfg = _client_cfg()
    if not cfg["api_key"]:
        # 未配置 LLM：降级为原样保留（英文），不阻塞流程
        return _fallback_items(raw_items)

    results = []
    for start in range(0, len(raw_items), batch_size):
        batch = raw_items[start:start + batch_size]
        processed = _call_llm(cfg, batch)
        if processed is None:
            continue
        for idx, item in enumerate(batch):
            p = processed.get(idx)
            if not p or not p.get("relevant"):
                continue
            results.append({
                "category": p.get("category", "market"),
                "categoryLabel": CATEGORY_LABELS.get(p.get("category"), "市场动态"),
                "categoryColor": p.get("category", "market"),
                "title": p.get("title_zh") or item["title"],
                "summary": p.get("summary_zh") or (item.get("summary", "")[:120]),
                "date": item["date"],
                "url": item.get("url", ""),
                "regions": p.get("regions") or ["global"],
                "source": item.get("source", ""),
                "title_en": item["title"],
            })
    return results


CATEGORY_LABELS = {
    "industry": "行业趋势",
    "market": "市场动态",
    "competitor": "同行新闻",
    "product": "产品技术",
}


def _call_llm(cfg: dict, batch: list):
    """单批 LLM 调用，返回 {idx: processed_dict}；失败返回 None。"""
    user_lines = []
    for i, it in enumerate(batch):
        summary = (it.get("summary", "") or "").replace("\n", " ").replace("\r", " ")[:400]
        title = it["title"].replace("\n", " ")
        user_lines.append(f"[{i}] 标题: {title}\n    摘要: {summary}")
    user_prompt = "处理以下新闻：\n\n" + "\n\n".join(user_lines)

    try:
        with httpx.Client(timeout=90) as client:
            resp = client.post(
                f"{cfg['base_url']}/chat/completions",
                headers={"Authorization": f"Bearer {cfg['api_key']}",
                         "Content-Type": "application/json"},
                json={
                    "model": cfg["model"],
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"},
                },
            )
            if resp.status_code != 200:
                print(f"[insights_llm] LLM HTTP {resp.status_code}: {resp.text[:200]}")
                return None
            content = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(_extract_json(content))
        # 兼容：模型可能返回 {"items": [...]} 或直接数组
        if isinstance(data, dict):
            arr = data.get("items") or data.get("results") or data.get("data") or []
        else:
            arr = data
        out = {}
        for row in arr:
            try:
                out[int(row["id"])] = row
            except Exception:
                continue
        return out
    except Exception as e:
        print(f"[insights_llm] 调用失败: {e}")
        return None


def _extract_json(content: str) -> str:
    """从模型输出中提取 JSON 片段（防止模型带 markdown 围栏）。"""
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```", 2)[1] if "```" in content[3:] else content
        content = content.strip("`").strip()
        if content.startswith("json"):
            content = content[4:].strip()
    return content


# 降级分类关键词（无 LLM Key 时用，按优先级匹配标题+摘要+来源）
_FB_RULES = [
    # 同行新闻：公司商业动作（优先级高于产品，公司新品发布算同行动作）
    ("competitor", [
        "zoetis", "idexx", "covetrus", "midmark", "virbac", "heska", "elanco",
        "merck animal", "boehringer ingelheim", "cev", "mars petcare", "petco",
        "acquires", "acquisition", "merger", "partners with", "partnership",
        "raises $", "funding", "series a", "series b", "ipo", "revenue",
        "earnings", "quarterly", "financial results", "launches new", "unveils",
        "announces launch", "company announces", "appoints", "ceo",
    ]),
    # 产品技术：新品/技术/获批/临床
    ("product", [
        "new product", "launches", "launch", "unveil", "device", "monitor",
        "anesthesia", "imaging", "ultrasound", "x-ray", "radiograph", "ventilator",
        "infusion pump", "syringe pump", "sensor", "software", "ai-powered",
        "fda approves", "fda-approved", "approval", "approved", "clearance",
        "clinical study", "clinical trial", "study finds", "researchers",
        "breakthrough", "technology", "diagnostic", "test kit", "vaccine",
        "new drug", "therapeutic", "treatment for",
    ]),
    # 行业趋势：宏观/政策/投资/报告
    ("industry", [
        "market size", "market report", "industry report", "forecast", "outlook",
        "trends 20", "trend report", "billion", "million by", "cagr",
        "regulation", "regulatory", "legislation", "guideline", "guidelines",
        "aaha", "avma", "fda ", "usda", "policy", "veterinary industry",
        "pet care market", "veterinary market", "animal health market",
        "survey", "shortage", "workforce", "veterinarians are",
    ]),
]


def _fb_classify(text: str) -> str:
    """降级路径的关键词分类，返回 category key；兜底 market。"""
    t = text.lower()
    for cat, kws in _FB_RULES:
        if any(kw in t for kw in kws):
            return cat
    return "market"


def _fallback_items(raw_items: list) -> list:
    """无 LLM Key 时的降级：保留英文原文，用关键词启发式分类到四列。"""
    out = []
    for it in raw_items:
        text = f"{it['title']} {it.get('summary', '')} {it.get('source', '')}"
        cat = _fb_classify(text)
        out.append({
            "category": cat,
            "categoryLabel": CATEGORY_LABELS.get(cat, "市场动态"),
            "categoryColor": cat,
            "title": it["title"],
            "summary": (it.get("summary", "") or "")[:120],
            "date": it["date"],
            "url": it.get("url", ""),
            "regions": ["global"],
            "source": it.get("source", ""),
            "title_en": it["title"],
        })
    return out
