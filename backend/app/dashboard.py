"""
RHC 经营仪表盘 —— 数据聚合与 AI 经营速览

- collect_dashboard_stats()：聚合商机信号（insights_store）与商机线索（飞书多维表）
  的真实统计数字，供 /api/dashboard/stats 使用。
- get_ai_brief()：基于统计数字调 DeepSeek 生成 SCQA 结构的中文经营诊断；
  文件缓存 1 小时（backend/data/dashboard_ai_brief.json），refresh=1 强制重新生成。

铁律：所有数字均来自真实数据源；未接入环节（发信/回信/PI/成交、客户、订单）
一律如实标注，LLM prompt 明确禁止引入任何外部数字。
"""
import json
import os
import time
from datetime import datetime, timezone, timedelta

import httpx

CST = timezone(timedelta(hours=8))

# 信号 regions 取值（与 insights_llm.py 的地区枚举一致）-> 中文标签
REGION_LABELS = {
    "global": "全球",
    "north-america": "北美",
    "europe": "欧洲",
    "africa": "非洲",
    "middle-east": "中东",
    "southeast-asia": "东南亚",
    "brazil": "巴西",
    "china": "中国",
    "asia": "亚洲",
}

# AI 经营速览文件缓存（backend/data/ 已在 .gitignore 中，Railway 重启后自动重建）
_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_CACHE_PATH = os.path.join(_DATA_DIR, "dashboard_ai_brief.json")
_SNAPSHOT_DIR = os.path.join(_DATA_DIR, "dashboard_snapshots")
_CACHE_TTL = 3600  # 1 小时


def _snapshot_path(date_str):
    return os.path.join(_SNAPSHOT_DIR, f"{date_str}.json")


def save_daily_snapshot(stats: dict):
    """把当日聚合数字落一份 JSON 快照（backend/data/dashboard_snapshots/YYYY-MM-DD.json）。
    同一天多次调用覆盖写（保存最新一次聚合），供环比与 AI 速览趋势分析使用。
    快照只含统计数字，不含团队个人明细之外的任何敏感信息；写入失败不阻断主流程。"""
    try:
        os.makedirs(_SNAPSHOT_DIR, exist_ok=True)
        snap = {
            "date": _now_cst().strftime("%Y-%m-%d"),
            "generated_at": stats.get("generated_at", ""),
            "signals": stats.get("signals"),
            "leads": stats.get("leads"),
            "funnel": [{"key": f.get("key"), "label": f.get("label"),
                        "value": f.get("value"), "available": f.get("available")}
                       for f in stats.get("funnel", [])],
            "regions": stats.get("regions"),
            "team": stats.get("team"),
        }
        tmp = _snapshot_path(snap["date"]) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)
        os.replace(tmp, _snapshot_path(snap["date"]))
    except Exception as e:
        print(f"[dashboard] 每日快照写入失败（不阻断）: {e}")


def load_snapshots(days: int = 7):
    """读取最近 N 天（含今天）的每日快照，按日期升序返回。
    文件缺失/损坏自动跳过。"""
    out = []
    today = _now_cst().date()
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        try:
            with open(_snapshot_path(d.strftime("%Y-%m-%d")), "r", encoding="utf-8") as f:
                out.append(json.load(f))
        except Exception:
            continue
    return out

# 超期未跟进口径（写在注释里供前端/后续维护参照）：
# 线索状态 = 跟进中，且「认领时间」距今超过 3 天（72 小时），且「跟进备注」为空。
# 说明：线索表目前没有「备注更新时间」字段，无法判断备注最后更新时刻，
# 因此以「跟进备注是否为空」作为“认领后是否有过跟进动作”的代理指标：
# 认领超过 3 天仍未填写任何跟进备注，视为超期未跟进。
OVERDUE_DAYS = 3


def _now_cst():
    return datetime.now(CST)


def _parse_claim_time(s):
    """解析线索「认领时间」（飞书表中为 'YYYY-MM-DD HH:MM:SS' 文本，CST）。
    兼容纯日期/ISO 等格式；解析失败返回 None。"""
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
                "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(tzinfo=CST)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=CST)
        return dt.astimezone(CST)
    except Exception:
        return None


def _collect_signals():
    """读取商机信号（与 /api/signals 完全一致的口径：线上只取 RSS 真新闻，
    种子快照仅在 RSS 为空时兜底；is_opportunity=true 且 opp_type 合法）。
    返回信号条目列表（insights_store 原始字段）。"""
    from app import insights_store
    try:
        from app.insights_llm import OPP_TYPES
    except Exception:
        OPP_TYPES = ("clinic_expansion", "tender", "expo", "channel", "company_move")
    all_items = insights_store.get_items()
    rss_items = [it for it in all_items if it.get("source") != "seed"]
    base_items = rss_items if rss_items else all_items
    return [it for it in base_items
            if it.get("is_opportunity") and it.get("opp_type") in OPP_TYPES]


def _collect_leads():
    """读取飞书「商机线索」表全部记录；失败时抛出异常（由调用方降级）。"""
    # 懒加载避免循环导入（main.py 在模块加载期导入本模块）
    from app.main import _fetch_leads
    return _fetch_leads()


def collect_dashboard_stats(user_info=None):
    """聚合经营仪表盘所需全部真实统计数字。

    user_info：_verify_token 返回的登录信息（含 role/name/username），
    用于「团队跟进」卡片的角色权限：admin 返回全员排行，其余角色
    （sales/viewer）只返回本人那一行。

    返回结构：
    {
      "generated_at": "YYYY-MM-DD HH:MM",
      "signals": {"total", "today_new", "unclaimed", "claimed"},
      "leads":  {"total", "following", "won", "released", "overdue",
                 "active", "overdue_days"},
      "team": [{"name","claimed_total","active","overdue"}, ...按超期/跟进中倒序],
      "team_scope": "team"(全员) | "me"(仅本人),
      "funnel": [{"key","label","value"(int|None),"available":bool}, ...6 层],
      "conversion": [{"from","to","rate"(float|None),"available":bool}, ...5 段],
      "regions": [{"key","label","count"}, ...按数量倒序],
      "data_notes": {"orders": False, "customers": False, "mail": False}
    }
    """
    signals = _collect_signals()
    try:
        leads = _collect_leads()
        leads_ok = True
    except Exception as e:
        print(f"[dashboard] 线索表读取失败，线索相关指标降级为不可用: {e}")
        leads = []
        leads_ok = False

    now = _now_cst()
    today_str = now.strftime("%Y-%m-%d")

    # ---- 信号侧 ----
    signals_total = len(signals)
    today_new = sum(1 for s in signals if (s.get("date") or "")[:10] == today_str)

    # 有效线索（跟进中/已转客户）按原文链接建索引，与 /api/signals 的
    # claimed enrichment 同口径：被释放的线索不算认领，信号回到待认领状态。
    lead_by_url = {}
    if leads_ok:
        for ld in leads:
            status = ld.get("状态", "")
            url = (ld.get("原文链接") or "").strip()
            if status in ("跟进中", "已转客户") and url:
                lead_by_url[url] = ld

    # 信号的认领状态完全依赖线索表匹配；线索表不可用时认领数无法判断，
    # 据实返回 None（前端显示「—」），不用 0 冒充。
    claimed = None
    unclaimed = None
    if leads_ok:
        claimed = sum(1 for s in signals if (s.get("url") or "").strip() in lead_by_url)
        unclaimed = signals_total - claimed

    # ---- 线索侧 ----
    leads_total = len(leads) if leads_ok else None
    leads_following = sum(1 for l in leads if l.get("状态") == "跟进中") if leads_ok else None
    leads_won = sum(1 for l in leads if l.get("状态") == "已转客户") if leads_ok else None
    leads_released = sum(1 for l in leads if l.get("状态") == "已释放") if leads_ok else None
    leads_active = (leads_following or 0) + (leads_won or 0) if leads_ok else None

    overdue = 0
    # 「商机跟进状况」卡片：按认领人聚合（与指标卡同一套超期口径）
    person_map = {}  # name -> {"claimed_total","active","overdue"}
    if leads_ok:
        for l in leads:
            if l.get("状态") != "跟进中":
                continue
            ct = _parse_claim_time(l.get("认领时间"))
            note = (l.get("跟进备注") or "").strip()
            # 超期口径：认领超过 3 天 且 跟进备注为空（见模块顶部注释）
            if ct and (now - ct) > timedelta(days=OVERDUE_DAYS) and not note:
                overdue += 1
        for l in leads:
            name = (l.get("认领人") or "").strip()
            if not name:
                continue
            p = person_map.setdefault(name, {"name": name, "claimed_total": 0,
                                             "active": 0, "overdue": 0})
            p["claimed_total"] += 1
            if l.get("状态") == "跟进中":
                p["active"] += 1
                ct = _parse_claim_time(l.get("认领时间"))
                note = (l.get("跟进备注") or "").strip()
                if ct and (now - ct) > timedelta(days=OVERDUE_DAYS) and not note:
                    p["overdue"] += 1

    # 角色权限：admin 看全员排行；销售/其他角色只看本人那一行。
    # user_info 为 None（内部调用，如 AI 速览聚合）时不做过滤。
    is_admin = (not user_info) or user_info.get("role") == "admin"
    team = list(person_map.values())
    if user_info and user_info.get("role") != "admin":
        me = (user_info.get("name") or user_info.get("username") or "").strip()
        team = [p for p in team if p["name"] == me]
    # 排序：超期数多的在前（优先处理风险），其次跟进中、认领总数；
    # 跟进中为 0 的人自然置底
    team.sort(key=lambda p: (-p["overdue"], -p["active"], -p["claimed_total"], p["name"]))
    team_scope = "team" if is_admin else "me"

    # ---- 销售漏斗（6 层）----
    # 前两层真数据：商机信号池=信号总数；已认领=有效线索数（跟进中+已转客户，
    # 与信号 claimed 标记同口径）。后四层（发信/回信/PI/成交）依赖邮件助手
    # 与订单数据，尚未接入，value=None 由前端显示灰框架。
    # 已认领层：线索表可用时用有效线索数（与信号 claimed 标记同口径）；
    # 线索表不可用时该层无法统计，置为未接入（None）。
    claimed_val = leads_active if leads_ok else None

    # 后四层：从邮件记录表 / 订单表（PI）真实统计点亮；
    # 表不存在或读取失败时对应字段为 None，前端保持灰框架「—」。
    # 只读路径：不会因为查看仪表盘而自动建空表。
    emailed_val = replied_val = pi_val = deal_val = None
    try:
        from app import business
        mstat = business.funnel_mail_stats()
        pstat = business.funnel_pi_stats()
        emailed_val = mstat.get("sent")
        replied_val = mstat.get("replied")
        pi_val = pstat.get("pi")
        deal_val = pstat.get("won")
    except Exception as e:
        print(f"[dashboard] 漏斗后半段统计失败（降级灰框架）: {e}")

    funnel = [
        {"key": "signals", "label": "商机信号池", "value": signals_total, "available": True},
        {"key": "claimed", "label": "已认领", "value": claimed_val, "available": leads_ok},
        {"key": "emailed", "label": "已发开发信", "value": emailed_val,
         "available": emailed_val is not None},
        {"key": "replied", "label": "已回信建档", "value": replied_val,
         "available": replied_val is not None},
        {"key": "pi", "label": "已出 PI", "value": pi_val, "available": pi_val is not None},
        {"key": "deal", "label": "已成交", "value": deal_val,
         "available": deal_val is not None},
    ]

    def _rate(a, b):
        # 转化率 = 下一层 / 上一层；任一层未接入或上一层为 0 时返回 None
        if a is None or b is None or b == 0:
            return None
        return round(a / b, 4)

    conversion = [
        {"from": "signals", "to": "claimed",
         "rate": _rate(claimed_val, signals_total), "available": leads_ok},
        {"from": "claimed", "to": "emailed",
         "rate": _rate(emailed_val, claimed_val),
         "available": emailed_val is not None and claimed_val is not None},
        {"from": "emailed", "to": "replied",
         "rate": _rate(replied_val, emailed_val),
         "available": emailed_val is not None and replied_val is not None},
        {"from": "replied", "to": "pi",
         "rate": _rate(pi_val, replied_val),
         "available": pi_val is not None and replied_val is not None},
        {"from": "pi", "to": "deal",
         "rate": _rate(deal_val, pi_val),
         "available": pi_val is not None and deal_val is not None},
    ]

    # ---- 商机地区分布（信号 regions 字段，可多选，逐 region 计数）----
    region_counts = {}
    for s in signals:
        for r in (s.get("regions") or ["global"]):
            rk = str(r or "global").strip() or "global"
            region_counts[rk] = region_counts.get(rk, 0) + 1
    regions = [{"key": k, "label": REGION_LABELS.get(k, k), "count": v}
               for k, v in region_counts.items()]
    regions.sort(key=lambda x: (-x["count"], x["key"]))

    return {
        "ok": True,
        "generated_at": now.strftime("%Y-%m-%d %H:%M"),
        "leads_available": leads_ok,
        "signals": {
            "total": signals_total,
            "today_new": today_new,
            "unclaimed": unclaimed,
            "claimed": claimed,
        },
        "leads": {
            "total": leads_total,
            "following": leads_following,
            "won": leads_won,
            "released": leads_released,
            "active": leads_active,
            "overdue": overdue,
            "overdue_days": OVERDUE_DAYS,
        },
        "team": team,
        "team_scope": team_scope,
        "funnel": funnel,
        "conversion": conversion,
        "regions": regions,
        # 客户/订单/邮件环节尚未接入飞书表，前端据实显示空状态
        "data_notes": {"orders": False, "customers": False, "mail": False},
    }


# ============================================================
# AI 经营速览（DeepSeek，SCQA 结构，文件缓存 1 小时）
# ============================================================

AI_SYSTEM_PROMPT = """你是 RHC 安瑞康（兽医医疗器械出口公司，产品：动物麻醉机、监护仪、影像设备、注射泵等）外贸营销系统的经营分析顾问，面向外贸销售团队负责人输出每日经营诊断。

写作要求（必须严格遵守）：
1. 你只能引用用户提供的「今日经营统计」中的数字，禁止引入任何外部数字、行业均值、市场规模或你自己猜测的数据；统计中没有的数字一律不得出现。
2. 用 SCQA 结构组织 3-5 句中文，连贯成段，不要标题、不要序号、不要分点：
   - S 现状：当前信号池与线索盘的真实情况；
   - C 变化/冲突：今日新增、认领率、超期等数字反映出的矛盾或压力；
   - Q 瓶颈定位：必须明确指出销售漏斗的瓶颈环节（如信号大量积压待认领、认领率偏低、认领后跟进超期等），用统计数字支撑；
   - A 行动建议：针对瓶颈给出 1-2 条具体可执行的销售动作建议。
3. 统计中标注为「未接入/暂无数据」的环节（发信、回信、PI、成交、客户、订单），必须如实表述为「客户/订单数据接入后自动纳入诊断」或类似意思，不得推测这些环节的数字。
3.1 若统计中提供了「环比参考」数字，可据此判断变化趋势，但必须注明对比日期；若提示「快照积累中」，则不得做任何增长/下降的趋势判断。
4. 全文禁止出现「演示」「假数据」「模拟」「mock」等字样；语气专业、简洁、直接，像销售主管的晨会点评。
5. 只输出诊断正文，不要任何前后缀说明。"""


def _stats_for_prompt(stats: dict) -> str:
    """把统计数字整理成喂给 LLM 的事实清单（纯数字，不含任何建议性文字）。"""
    sig = stats["signals"]
    ld = stats["leads"]
    na = "暂无数据"
    lines = [
        f"统计时间：{stats['generated_at']}（北京时间）",
        f"商机信号总数：{sig['total']} 条",
        f"今日新增商机信号：{sig['today_new']} 条",
        f"待认领信号：{sig['unclaimed'] if sig['unclaimed'] is not None else na}",
        f"已认领信号：{sig['claimed'] if sig['claimed'] is not None else na}",
    ]
    if stats.get("leads_available"):
        claim_rate = (sig["claimed"] / sig["total"] * 100) if sig["total"] and sig["claimed"] is not None else 0
        lines += [
            f"商机线索总数：{ld['total']} 条（跟进中 {ld['following']}、"
            f"已转客户 {ld['won']}、已释放 {ld['released']}）",
            f"超期未跟进线索（认领超过 {ld['overdue_days']} 天且无跟进备注）：{ld['overdue']} 条",
            f"信号认领率：{claim_rate:.1f}%",
        ]
    else:
        lines.append("商机线索表暂时读取失败，线索明细暂无数据。")
    if stats["regions"]:
        top = "、".join(f"{r['label']} {r['count']}" for r in stats["regions"])
        lines.append(f"商机信号地区分布：{top}")
    lines.append("销售漏斗后半段（已发开发信、已回信建档、已出 PI、已成交）："
                 "邮件助手与订单数据尚未接入，暂无数据。")
    lines.append("客户档案、订单履约数据：尚未接入，暂无数据。")

    # 环比趋势：最近 7 天快照中，与最近一个**更早日期**的快照对比
    # （今天刚落的快照与当前数字相同，不构成环比）。快照不足时如实说明，
    # 不编造趋势数字。
    snaps = load_snapshots(7)
    today_date = _now_cst().strftime("%Y-%m-%d")
    earlier = [s for s in snaps if s.get("date") and s["date"] != today_date]
    if earlier:
        prev = earlier[-1]  # 最近一个更早日期的快照
        ps, pl = prev.get("signals") or {}, prev.get("leads") or {}
        lines.append(
            f"环比参考（{prev.get('date')} 快照 → 今日）："
            f"信号总数 {ps.get('total', '—')} → {sig['total']}；"
            f"待认领 {ps.get('unclaimed', '—') if ps.get('unclaimed') is not None else '—'} → "
            f"{sig['unclaimed'] if sig['unclaimed'] is not None else '—'}；"
            f"跟进中线索 {pl.get('following', '—')} → {ld.get('following')}；"
            f"超期线索 {pl.get('overdue', '—')} → {ld.get('overdue')}。"
            "引用环比数字时须同时说明对比日期。")
    else:
        lines.append("环比趋势：每日快照积累中，暂无足够历史数据，"
                     "不要对趋势（增长/下降）做任何数字判断。")
    return "今日经营统计（全部为系统真实统计数字）：\n" + "\n".join(f"- {x}" for x in lines)


_FORBIDDEN_WORDS = ("演示", "假数据", "模拟", "mock", "Mock", "MOCK")


def _call_deepseek(prompt: str) -> str:
    """调 DeepSeek（OpenAI 兼容接口，复用 insights_llm 的环境变量配置）。
    失败抛异常。"""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY 未配置")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
    model = os.getenv("OPENAI_TEXT_MODEL", "deepseek-chat")
    with httpx.Client(timeout=90) as client:
        resp = client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": AI_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.4,
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(f"LLM HTTP {resp.status_code}: {resp.text[:200]}")
        content = resp.json()["choices"][0]["message"]["content"].strip()
    if not content:
        raise RuntimeError("LLM 返回空内容")
    if any(w in content for w in _FORBIDDEN_WORDS):
        raise RuntimeError("LLM 输出包含禁用字样，拒绝采用")
    return content


def _read_cache():
    """读取缓存文件，返回 dict 或 None。"""
    try:
        with open(_CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write_cache(brief: str, stats: dict):
    try:
        os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
        tmp = _CACHE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({
                "brief": brief,
                "generated_at": _now_cst().strftime("%Y-%m-%d %H:%M:%S"),
                "generated_ts": time.time(),
                "stats_generated_at": stats.get("generated_at", ""),
            }, f, ensure_ascii=False, indent=2)
        os.replace(tmp, _CACHE_PATH)
    except Exception as e:
        print(f"[dashboard] AI 速览缓存写入失败（不影响本次返回）: {e}")


def get_ai_brief(force_refresh: bool = False):
    """返回 AI 经营速览。

    - force_refresh=False：缓存 1 小时内有效直接返回；否则现场生成；
      生成失败时若有旧缓存则降级返回旧缓存（stale=True），无缓存则抛异常。
    - force_refresh=True（刷新按钮）：跳过缓存现场生成；失败抛异常，
      由前端显示「诊断生成中，请稍后刷新」。
    返回 {"ok", "brief", "generated_at", "cached"/"stale"}。
    """
    cache = None if force_refresh else _read_cache()
    if cache and (time.time() - cache.get("generated_ts", 0) < _CACHE_TTL):
        return {"ok": True, "brief": cache["brief"],
                "generated_at": cache.get("generated_at", ""), "cached": True}

    stats = collect_dashboard_stats()
    try:
        brief = _call_deepseek(_stats_for_prompt(stats))
    except Exception as e:
        print(f"[dashboard] AI 速览生成失败: {e}")
        if not force_refresh and cache and cache.get("brief"):
            return {"ok": True, "brief": cache["brief"],
                    "generated_at": cache.get("generated_at", ""), "stale": True}
        raise
    _write_cache(brief, stats)
    return {"ok": True, "brief": brief,
            "generated_at": _now_cst().strftime("%Y-%m-%d %H:%M"), "cached": False}
