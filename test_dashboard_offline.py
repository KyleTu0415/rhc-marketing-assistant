"""离线自测：dashboard 统计聚合逻辑（mock 信号/线索数据，不依赖飞书与网络）。"""
import sys, os, json
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
CST = timezone(timedelta(hours=8))

from app import dashboard  # noqa: E402

today = datetime.now(CST).strftime("%Y-%m-%d")
yesterday = (datetime.now(CST) - timedelta(days=1)).strftime("%Y-%m-%d")
five_days_ago = (datetime.now(CST) - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
one_day_ago = (datetime.now(CST) - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")

# ---- mock 信号：10 条；今日新增 2 条；url-1 被有效线索认领，url-x 被已释放线索认领 ----
mock_signals = []
for i in range(10):
    date = today if i < 2 else "2026-07-0%d" % (1 + i % 9)
    regions = [["north-america"], ["global"], ["europe"], ["africa"], ["asia"],
               ["global"], ["north-america"], ["north-america"], ["europe"], ["global"]][i]
    mock_signals.append({
        "title": f"signal-{i}", "date": date, "url": f"https://x{i}.com",
        "regions": regions, "is_opportunity": True,
        "opp_type": ["clinic_expansion", "tender", "expo", "channel", "company_move"][i % 5],
        "source": "rss-mock",
    })
# 非商机/种子信号不应计入
mock_signals.append({"title": "noise", "date": today, "url": "https://noise.com",
                     "regions": ["global"], "is_opportunity": False,
                     "opp_type": "none", "source": "rss-mock"})
mock_signals.append({"title": "seed", "date": today, "url": "https://seed.com",
                     "regions": ["global"], "is_opportunity": True,
                     "opp_type": "tender", "source": "seed"})

# ---- mock 线索：跟进中 3（1 条超期无备注、1 条超期但有备注=不超期、1 条 1 天内=不超期）、
#      已转客户 1、已释放 1 ----
mock_leads = [
    {"状态": "跟进中", "原文链接": "https://x0.com", "认领时间": five_days_ago,
     "跟进备注": "", "认领人": "Ella"},                                          # 超期
    {"状态": "跟进中", "原文链接": "https://x1.com", "认领时间": five_days_ago,
     "跟进备注": "已发开发信，等回复", "认领人": "Tom"},                            # 不超期（有备注）
    {"状态": "跟进中", "原文链接": "https://x2.com", "认领时间": one_day_ago,
     "跟进备注": "", "认领人": "Ella"},                                          # 不超期（3天内）
    {"状态": "已转客户", "原文链接": "https://x3.com", "认领时间": five_days_ago,
     "跟进备注": "已建档", "认领人": "Tom"},
    {"状态": "已释放", "原文链接": "https://x4.com", "认领时间": five_days_ago,
     "跟进备注": "", "认领人": ""},
]

# 在数据源层打桩：让真实 _collect_signals 的过滤逻辑（RSS-only、is_opportunity、
# opp_type 合法性）在 mock 数据上实际运行
from app import insights_store  # noqa: E402
insights_store.get_items = lambda: mock_signals
dashboard._collect_leads = lambda: mock_leads

# 漏斗后半段依赖飞书邮件记录表/订单表：离线环境模拟「表未接入」降级，
# 后四层应为 None（前端灰框架）；同时模拟「已接入但为 0」场景验证点亮。
from app import business  # noqa: E402
business.funnel_mail_stats = lambda: {"sent": None, "replied": None}
business.funnel_pi_stats = lambda: {"pi": None, "won": None}

stats = dashboard.collect_dashboard_stats()
print(json.dumps(stats, ensure_ascii=False, indent=2))

s, l = stats["signals"], stats["leads"]
checks = [
    ("信号总数=10（排除非商机与seed）", s["total"] == 10),
    ("今日新增=2", s["today_new"] == 2),
    ("已认领=4（x0/x1/x2 跟进中 + x3 已转客户；已释放 x4 不算）", s["claimed"] == 4),
    ("待认领=6", s["unclaimed"] == 6),
    ("线索总数=5", l["total"] == 5),
    ("跟进中=3", l["following"] == 3),
    ("已转客户=1", l["won"] == 1),
    ("已释放=1", l["released"] == 1),
    ("超期未跟进=1", l["overdue"] == 1),
    ("漏斗层1=10", stats["funnel"][0]["value"] == 10),
    ("漏斗层2(已认领)=有效线索4", stats["funnel"][1]["value"] == 4),
    ("漏斗后四层未接入=None", all(f["value"] is None for f in stats["funnel"][2:])),
    ("认领转化率=4/10=0.4", abs(stats["conversion"][0]["rate"]-0.4)<1e-9),
    ("后续转化率=None", all(c["rate"] is None for c in stats["conversion"][1:])),
    ("地区分布北美=3", [r for r in stats["regions"] if r["key"] == "north-america"][0]["count"] == 3),
    ("地区分布按数量倒序", [r["count"] for r in stats["regions"]] ==
        sorted([r["count"] for r in stats["regions"]], reverse=True)),
    # ---- 商机跟进状况（admin 全员）----
    ("team 全员 2 人", len(stats["team"]) == 2),
    ("team_scope=team(admin)", stats["team_scope"] == "team"),
    ("Ella: total2/active2/overdue1，超期置首",
        stats["team"][0] == {"name": "Ella", "claimed_total": 2, "active": 2, "overdue": 1}),
    ("Tom: total2(跟进中1+已转客户1)/active1/overdue0，置底",
        stats["team"][1] == {"name": "Tom", "claimed_total": 2, "active": 1, "overdue": 0}),
]
team_admin = {p["name"]: p for p in stats["team"]}
assert team_admin["Ella"]["overdue"] == 1 and team_admin["Tom"]["overdue"] == 0

# 销售角色只看自己
stats_sales = dashboard.collect_dashboard_stats(
    user_info={"username": "tom", "role": "sales", "name": "Tom"})
assert stats_sales["team_scope"] == "me"
assert len(stats_sales["team"]) == 1 and stats_sales["team"][0]["name"] == "Tom"
print("PASS 销售角色只看到本人那一行（Tom）")

# 没有任何认领的销售看到空数组（前端显示空状态）
stats_nobody = dashboard.collect_dashboard_stats(
    user_info={"username": "bob", "role": "sales", "name": "Bob"})
assert stats_nobody["team"] == []
print("PASS 无认领记录的销售 team 为空数组（前端走空状态）")

# 内部调用（user_info=None，如 AI 速览聚合）不做过滤
assert dashboard.collect_dashboard_stats()["team_scope"] == "team"
fails = [name for name, ok in checks if not ok]
print("\n==== 断言结果 ====")
for name, ok in checks:
    print(("PASS " if ok else "FAIL ") + name)
assert not fails, f"失败: {fails}"

# 漏斗后半段「已接入且有真实数据」：发信2/回信1/PI1/成交1，层间转化率应可算
business.funnel_mail_stats = lambda: {"sent": 2, "replied": 1}
business.funnel_pi_stats = lambda: {"pi": 1, "won": 1}
stats_lit = dashboard.collect_dashboard_stats()
fmap = {f["key"]: f for f in stats_lit["funnel"]}
assert fmap["emailed"]["value"] == 2 and fmap["emailed"]["available"] is True
assert fmap["replied"]["value"] == 1 and fmap["pi"]["value"] == 1 and fmap["deal"]["value"] == 1
# claimed=4 -> emailed 2/4=0.5；emailed2->replied1 0.5；replied1->pi1 1.0；pi1->deal1 1.0
cmap = {(c["from"], c["to"]): c for c in stats_lit["conversion"]}
assert abs(cmap[("claimed", "emailed")]["rate"] - 0.5) < 1e-9
assert abs(cmap[("emailed", "replied")]["rate"] - 0.5) < 1e-9
assert abs(cmap[("replied", "pi")]["rate"] - 1.0) < 1e-9
assert abs(cmap[("pi", "deal")]["rate"] - 1.0) < 1e-9
print("PASS 漏斗后半段点亮：发信2/回信1/PI1/成交1，层间转化率正确计算")
# 回到未接入降级态供后续断言
business.funnel_mail_stats = lambda: {"sent": None, "replied": None}
business.funnel_pi_stats = lambda: {"pi": None, "won": None}

# 线索表失败降级：线索侧 None、信号侧正常
dashboard._collect_leads = lambda: (_ for _ in ()).throw(RuntimeError("feishu down"))
stats2 = dashboard.collect_dashboard_stats()
assert stats2["leads_available"] is False
assert stats2["leads"]["following"] is None
assert stats2["signals"]["total"] == 10
# 降级时认领相关指标无法判断，据实 None（前端显示「—」）
assert stats2["signals"]["claimed"] is None
assert stats2["funnel"][1]["value"] is None
assert stats2["conversion"][0]["rate"] is None
print("PASS 线索表失败降级（线索字段 null，信号统计正常，漏斗 claimed=2）")

# prompt 事实清单离线评审
dashboard._collect_leads = lambda: mock_leads
prompt = dashboard._stats_for_prompt(stats)
print("\n==== 喂给 LLM 的事实清单 ====")
print(prompt)
assert "10" in prompt and "超期未跟进线索（认领超过 3 天且无跟进备注）：1 条" in prompt
assert "尚未接入，暂无数据" in prompt
assert "Ella" not in prompt and "Tom" not in prompt, "团队明细不应进入 AI prompt"
print("PASS AI prompt 不含团队个人明细（仅统计数字）")
print("\n全部离线断言通过 ✅")
