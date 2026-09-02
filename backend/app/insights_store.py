"""
RHC 市场洞察 —— 新闻存储与刷新编排

- 数据持久化：data/insights.json（Railway 临时磁盘，重启自动从种子重建）
- 种子数据：首次启动从前端 rhc-insights.js 迁移现有 12 条
- 去重：URL 归一化 + 标题指纹
- 刷新：抓取 RSS -> 粗筛 -> LLM 加工 -> 去重合并 -> 落盘
- 自动调度：后台协程每 6 小时抓取一次；手动刷新限频 10 分钟
"""
import json
import os
import re
import threading
import time
from datetime import datetime, timezone, timedelta

from . import rss_sources
from . import insights_llm

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATA_FILE = os.path.join(DATA_DIR, "insights.json")
SEED_JS = os.path.join(BASE_DIR, "frontend", "assets", "rhc-insights.js")

REFRESH_MIN_INTERVAL = 600        # 手动刷新限频 10 分钟
AUTO_REFRESH_INTERVAL = 12 * 3600  # 自动抓取间隔 12 小时（一天 2 次）
MAX_ITEMS = 500                   # 最多保留 500 条

_lock = threading.Lock()
_state = {
    "items": [],
    "last_refresh_ts": 0,
    "last_refresh_info": None,
    "refreshing": False,
}


# ---------------- 种子数据迁移 ----------------
def _seed_from_js() -> list:
    """从前端 rhc-insights.js 提取现有新闻（对象字面量 -> JSON）。"""
    try:
        with open(SEED_JS, "r", encoding="utf-8") as f:
            js = f.read()
        m = re.search(r"var\s+RHC_INSIGHT_DATA\s*=\s*(\[.*?\]);", js, re.S)
        if not m:
            return []
        raw = m.group(1)
        # 去掉 // 行注释（JS 源里的分类分隔注释），但保留 URL 的 ://
        raw = re.sub(r"(?<!:)//[^\n]*", "", raw)
        # JS 对象键加引号（行首缩进或 { , 之后的标识符键）
        raw = re.sub(r"([{\[,]\s*|\n\s*)([a-zA-Z_]\w*)\s*:", r'\1"\2":', raw)
        # 单引号字符串 -> 双引号
        raw = raw.replace("'", '"')
        # 去尾逗号
        raw = re.sub(r",\s*([}\]])", r"\1", raw)
        items = json.loads(raw, strict=False)
        for it in items:
            it.setdefault("source", "seed")
        return items
    except Exception as e:
        print(f"[insights_store] 种子迁移失败: {e}")
        return []


def _load():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            _state["items"] = data.get("items", [])
            _state["last_refresh_ts"] = data.get("last_refresh_ts", 0)
            _state["last_refresh_info"] = data.get("last_refresh_info")
            if _state["items"]:
                return
        except Exception as e:
            print(f"[insights_store] 数据文件读取失败: {e}")
    # 首次启动：迁移种子
    _state["items"] = _seed_from_js()
    print(f"[insights_store] 种子数据 {len(_state['items'])} 条")
    _save()


def _save():
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({
            "items": _state["items"],
            "last_refresh_ts": _state["last_refresh_ts"],
            "last_refresh_info": _state["last_refresh_info"],
        }, f, ensure_ascii=False, indent=1)
    os.replace(tmp, DATA_FILE)


# ---------------- 去重 ----------------
def _norm_url(url: str) -> str:
    u = (url or "").strip().lower()
    u = re.sub(r"^https?://(www\.)?", "", u)
    u = u.rstrip("/").split("?")[0]
    return u


def _title_fp(title: str) -> str:
    t = re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", (title or "").lower())
    return t[:60]


def _existing_keys(items: list):
    urls = set()
    fps = set()
    for it in items:
        if it.get("url"):
            urls.add(_norm_url(it["url"]))
        fps.add(_title_fp(it.get("title_en") or it.get("title", "")))
    return urls, fps


# ---------------- 刷新编排 ----------------
def refresh(force: bool = False) -> dict:
    """手动/自动刷新入口。force=True 跳过限频。
    慢操作（RSS 抓取 + LLM 翻译，约 20s~2min）在锁外执行，期间页面请求
    读取上一轮数据不被阻塞；仅状态翻转与结果提交使用短锁。"""
    with _lock:
        if _state["refreshing"]:
            return {"limited": True, "reason": "refreshing"}
        if not force and time.time() - _state["last_refresh_ts"] < REFRESH_MIN_INTERVAL:
            remain = int(REFRESH_MIN_INTERVAL - (time.time() - _state["last_refresh_ts"]))
            return {"limited": True, "reason": "rate_limited", "remain_seconds": remain}
        _state["refreshing"] = True

    try:
        t0 = time.time()
        # —— 锁外：RSS 抓取（约 15-25 秒）——
        raw = rss_sources.fetch_all_feeds()

        with _lock:
            snapshot = list(_state["items"])
        existing_urls, existing_fps = _existing_keys(snapshot)

        # 粗去重：URL/标题指纹命中的不送 LLM（省 token）
        new_raw = []
        for it in raw:
            if it.get("url") and _norm_url(it["url"]) in existing_urls:
                continue
            if _title_fp(it["title"]) in existing_fps:
                continue
            new_raw.append(it)

        # —— 阶段1：英文原文立即入库（约 20 秒页面即有新闻），
        #          配 LLM 时标记 pending_translate，阶段2 被中文版替换 ——
        en_items = insights_llm._fallback_items(new_raw)
        for it in en_items:
            it["lang"] = "en"
            it["pending_translate"] = True
        n_en = _commit_items(en_items)
        print(f"[insights_store] 阶段1 英文新闻已发布 {n_en} 条，耗时 {time.time()-t0:.0f}s")

        if not insights_llm._client_cfg().get("api_key"):
            # 未配 LLM：英文即最终版
            info = _build_info(t0, len(raw), len(new_raw), len(snapshot))
            with _lock:
                _state["last_refresh_ts"] = time.time()
                _state["last_refresh_info"] = info
            info["limited"] = False
            return info

        # —— 阶段2（锁外，约 1-2 分钟）：LLM 翻译分类精筛 ——
        processed = insights_llm.process_items(new_raw) if new_raw else []
        zh = []
        for p in processed:
            fp_en = _title_fp(p.get("title_en", ""))
            fp_zh = _title_fp(p.get("title", ""))
            u = _norm_url(p.get("url", ""))
            if p.get("url") and u in existing_urls:
                continue
            if fp_en in existing_fps or fp_zh in existing_fps:
                continue
            existing_urls.add(u)
            existing_fps.add(fp_en)
            existing_fps.add(fp_zh)
            p["lang"] = "zh"
            zh.append(p)

        # 用中文版替换阶段1英文条目：仅替换翻译成功的；
        # 未翻译/翻译失败/判无关的英文条目保留为最终版（宁多勿漏）
        zh_urls = {_norm_url(p.get("url", "")) for p in zh if p.get("url")}
        with _lock:
            kept = []
            for it in _state["items"]:
                if it.get("pending_translate"):
                    u = _norm_url(it.get("url", ""))
                    if u in zh_urls:
                        continue  # 有中文版，丢弃英文条目
                    it.pop("pending_translate", None)  # 保留英文为最终版
                kept.append(it)
            _state["items"] = kept
        n_zh = _commit_items(zh)
        print(f"[insights_store] 阶段2 中文新闻替换完成，中文 {n_zh} 条，总耗时 {time.time()-t0:.0f}s")

        info = _build_info(t0, len(raw), len(new_raw), len(snapshot))
        with _lock:
            _state["last_refresh_ts"] = time.time()
            _state["last_refresh_info"] = info
        info["limited"] = False
        return info
    finally:
        with _lock:
            _state["refreshing"] = False


def _commit_items(new_items: list) -> int:
    """短锁内合并条目：分配 ID、排序、裁剪、保存。去重由调用方完成
    （阶段2 中文条目的 URL 与阶段1 英文条目相同，此处不能再按 URL 去重）。"""
    with _lock:
        max_num = 0
        for it in _state["items"]:
            m = re.match(r"ins-(\d+)", it.get("id", ""))
            if m:
                max_num = max(max_num, int(m.group(1)))
        for p in new_items:
            max_num += 1
            p["id"] = f"ins-{max_num:03d}"
            p.setdefault("products", [])
        _state["items"].extend(new_items)
        _state["items"].sort(key=lambda x: x.get("date", ""), reverse=True)
        if len(_state["items"]) > MAX_ITEMS:
            _state["items"] = _state["items"][:MAX_ITEMS]
        _save()
        return len(new_items)


def _build_info(t0: float, fetched: int, candidates: int, snapshot_len: int) -> dict:
    with _lock:
        total = len(_state["items"])
    return {
        "time": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M"),
        "fetched": fetched,
        "new_candidates": candidates,
        "added": total - snapshot_len,
        "total": total,
        "cost_seconds": round(time.time() - t0, 1),
        "sources": rss_sources.health_snapshot(),
    }


def get_items() -> list:
    with _lock:
        return list(_state["items"])


def status() -> dict:
    with _lock:
        return {
            "total": len(_state["items"]),
            "refreshing": _state["refreshing"],
            "last_refresh": _state["last_refresh_info"],
            "min_interval": REFRESH_MIN_INTERVAL,
            "sources": rss_sources.health_snapshot(),
        }


# ---------------- 自动调度 ----------------
def _auto_loop():
    # 启动后 15 秒做首轮（英文新闻约 20 秒即可发布），之后每 12 小时
    time.sleep(15)
    while True:
        try:
            with _lock:
                due = (time.time() - _state["last_refresh_ts"]) >= AUTO_REFRESH_INTERVAL
            if due:
                print("[insights_store] 自动刷新开始")
                info = refresh(force=True)
                print(f"[insights_store] 自动刷新完成: 新增 {info.get('added')} 条")
        except Exception as e:
            print(f"[insights_store] 自动刷新异常: {e}")
        time.sleep(1800)  # 每 30 分钟检查一次是否到期


def start_scheduler():
    t = threading.Thread(target=_auto_loop, daemon=True)
    t.start()
    print("[insights_store] 自动刷新调度器已启动（12小时间隔，启动15秒后首轮）")


# 模块导入即加载数据
_load()
