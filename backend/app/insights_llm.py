"""
RHC 市场洞察 —— LLM 加工：英文新闻 -> 中文标题/摘要 + 分类 + 地区 + 相关性筛选

调用 OpenAI 兼容接口（默认 DeepSeek），批量处理，成本约几分钱/轮。
"""
import json
import os
import re
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
5. 商机信号判断（is_opportunity / opp_type）：判断该新闻是否构成可能带来
   【设备销售机会】的外贸商机事件。只有以下事件才算商机（is_opportunity=true）：
   - clinic_expansion 诊所扩张：兽医诊所/宠物医院/连锁机构的扩张、融资、新机构开业、新院区
   - tender 招标采购：设备/医疗器械招标、政府采购、集中采购、设备采购计划、中标
   - expo 展会活动：兽医/宠物医疗行业展会、行业大会、学术会议的预告或举办
   - channel 渠道动态：经销商、分销商、代理商的合作签约、渠道布局、授权代理
   - company_move 采购合作：企业（含同行/养殖集团）的大额采购、战略合作、合资、并购、产能扩张
   以下情况【不算】商机（is_opportunity=false，opp_type="none"）：纯行业科普、
   趋势报告/市场规模分析、单纯的产品发布或技术突破、人事任命、财报营收数据
   （除非伴随融资扩张）、监管政策、动物医学研究结论。拿不准时给 false。
   opp_type 只能取：clinic_expansion / tender / expo / channel / company_move / none。
6. 对判定为商机（is_opportunity=true）的条目，额外输出 opp_org：
   该商机事件涉及的【主要公司/机构/组织名称】，用英文原名或当地官方名称
   （如 "Animal Friends Alliance"、"Amferia"、"Kogi State Government"）；
   一条新闻涉及多个主体时，取与该商机最直接相关的一个主体；
   无法确定时输出空字符串 ""，严禁编造。非商机条目输出空字符串 ""。

严格只输出 JSON 数组，不要任何解释文字。格式：
[{"id": 0, "relevant": true, "category": "market", "title_zh": "中文标题", "summary_zh": "中文摘要", "regions": ["north-america"], "is_opportunity": false, "opp_type": "none", "opp_org": ""}, ...]
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
            is_opp, opp_type, opp_org = _norm_opp(p)
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
                "is_opportunity": is_opp,
                "opp_type": opp_type,
                # 商机涉及的主要公司/机构（LLM 提取，仅商机条目可能非空；缺字段/异常时为空串）
                "opp_org": opp_org,
            })
    return results


CATEGORY_LABELS = {
    "industry": "行业趋势",
    "market": "市场动态",
    "competitor": "同行新闻",
    "product": "产品技术",
}

# 商机类型 -> 中文标签 / 标签色。
# 配色复用四列看板色板（industry 蓝 #1565C0 / market 绿 #2E7D32 /
# competitor 橙 #E65100 / product 紫 #7C3AED）并做同色系扩展：
#   clinic_expansion 青（success 系 #00796B，机构扩张/正向增长）
#   tender           红（品牌红 #C8102E，高优先销售机会）
#   expo             亮蓝（info 系 #1565C0→#0277BD，展会活动）
#   channel          琥珀（warning 系 #EF6C00，渠道动态，区别于同行橙）
#   company_move     靛紫（#5B21B6，企业动作，区别于产品紫）
OPP_LABELS = {
    "clinic_expansion": "诊所扩张",
    "tender": "招标采购",
    "expo": "展会机会",
    "channel": "渠道动态",
    "company_move": "采购动态",
}
OPP_COLORS = {
    "clinic_expansion": "#00796B",
    "tender": "#C8102E",
    "expo": "#0277BD",
    "channel": "#EF6C00",
    "company_move": "#5B21B6",
}
OPP_TYPES = tuple(OPP_LABELS.keys())


def _norm_opp(p: dict) -> tuple:
    """归一化商机字段（LLM 路径与降级路径共用）。
    返回 (is_opportunity: bool, opp_type: str, opp_org: str)。
    以 is_opportunity 布尔为准；opp_type 非法/缺失时按布尔自动修正，
    保证 is_opportunity 为 True 时一定带有效类型。
    opp_org 为 LLM 提取的商机主体机构名：缺字段/异常不报错，
    非商机条目一律归一为空串（降级关键词路径不猜机构名）。"""
    opp_type = str(p.get("opp_type", "") or "").strip().lower()
    if opp_type not in OPP_TYPES:
        opp_type = "none"
    flag = bool(p.get("is_opportunity", False))
    if flag and opp_type == "none":
        opp_type = "company_move"  # 模型只给了 true 没给类型：兜底为采购合作
    if not flag and opp_type != "none":
        flag = True               # 给了有效类型但漏标布尔：视为商机
    opp_org = ""
    if flag:
        try:
            opp_org = str(p.get("opp_org", "") or "").strip()
        except Exception:
            opp_org = ""
    return flag, opp_type, opp_org


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


# 降级商机关键词（无 LLM Key 时用）。按优先级排列：
# 招标 > 诊所扩张 > 展会 > 渠道 > 企业采购合作；都不命中则 none。
# 用正则词边界匹配，避免 "expansion"/"expands" 漏匹配（\b 兼容变形词干），
# 也避免关键词片段误命中。
_FB_OPP_RULES = [
    ("tender", [
        r"\btender\b", r"\btendering\b", r"\bbid (?:for|on)\b", r"\bbidding\b",
        r"\bprocurement\b", r"\bgovernment (?:bid|purchase)\b",
        r"\bcontract (?:award|awarded)\b", r"\bawarded .{0,20}(?:contract|supply)\b",
        r"\bpurchase order\b", r"\brequest for (?:proposal|quotation|tender)\b",
        r"\brfp\b", r"\brfq\b", r"\bsupply contract\b",
    ]),
    ("clinic_expansion", [
        r"\bnew (?:vet(?:erinary)?|animal|pet) (?:clinic|hospital|practice)\b",
        r"\b(?:vet(?:erinary)?|animal|pet) (?:clinic|hospital|practice) (?:opens|open|launches|expands|opening)\b",
        r"\b(?:clinic|hospital) (?:expansion|expands|expanded|chain|group)\b",
        r"\bvet(?:erinary)? (?:chain|group)\b",
        r"\b(?:raises|raised|secures?) \$[\d.]+\s*(?:million|m|billion)?",
        r"\bfunding round\b", r"\bseries [a-d]\b",
        r"\bexpansion plan\b", r"\bnew location\b", r"\bgrand opening\b",
    ]),
    ("expo", [
        r"\bexp(?:o|os)\b", r"\bexhibition\b", r"\btrade show\b",
        r"\b(?:vet(?:erinary)?|animal health) (?:conference|congress|meeting|summit|show)\b",
        r"\bvmx\b", r"\bnavc (?:live|conference)\b", r"\bwestern veterinary conference\b",
        r"\bwvc\b",
    ]),
    ("channel", [
        r"\bdistributor(?:ship)?\b", r"\bdistribution (?:agreement|deal|partnership|partner|network|rights)\b",
        r"\bdealership\b", r"\bdealer network\b", r"\bauthorized (?:dealer|reseller|agent)\b",
        r"\bexclusive (?:distributor|distribution)\b", r"\bvalue[- ]added reseller\b", r"\bvar\b",
        r"\bsigns .{0,30}(?:distribut|dealer|agent|reseller)",
    ]),
    ("company_move", [
        r"\bstrategic (?:partnership|cooperation|alliance|agreement)\b",
        r"\bjoint venture\b", r"\bmemorandum of understanding\b", r"\bmou\b",
        r"\bacquires?\b", r"\bacquisition\b", r"\bmerger\b",
        r"\bmajor (?:equipment |device )?(?:order|purchase|buy)\b",
        r"\bpurchase[sd]? .{0,30}(?:equipment|devices?|machines?)",
        r"\bmanufacturing facility\b", r"\bproduction capacity\b",
        r"\bnew factory\b", r"\bcapacity expansion\b",
    ]),
]
_FB_OPP_RES = [(ot, [re.compile(p, re.I) for p in pats]) for ot, pats in _FB_OPP_RULES]


def _fb_opp(text: str) -> str:
    """降级路径：关键词启发式判断商机类型，命中返回 opp_type，否则 'none'。"""
    for ot, pats in _FB_OPP_RES:
        if any(rx.search(text) for rx in pats):
            return ot
    return "none"


def _fallback_items(raw_items: list) -> list:
    """无 LLM Key 时的降级：保留英文原文，用关键词启发式分类到四列，
    并按关键词启发式标记商机信号（is_opportunity/opp_type）。"""
    out = []
    for it in raw_items:
        text = f"{it['title']} {it.get('summary', '')} {it.get('source', '')}"
        cat = _fb_classify(text)
        opp_type = _fb_opp(text)
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
            "is_opportunity": opp_type != "none",
            "opp_type": opp_type,
            # 降级路径不做机构名正则猜测，统一留空
            "opp_org": "",
        })
    return out
