"""
RHC 业务表底座 —— 客户档案 / 邮件记录 / PI订单（复用订单表）/ 系统配置

数据源：飞书多维表格 RHC_产品数据库 base。
- 客户档案：复用现有「客户表」（tblssVBrZu8VyF2n），幂等补字段
  （分级/来源线索/客户状态/创建时间）；邮箱复用现有「邮箱」字段，
  地区复用现有「国家/地区」字段，备注复用现有「备注」字段。
- PI 订单：复用现有「订单表」（tbl5ftcUigUYS4Oi），幂等补字段
  （币种/PI状态/关联客户）。订单表当前状态为履约 9 节点语义，
  PI 阶段（草稿/已发送/已确认）用独立「PI状态」字段表达，
  已成交/已取消写入「当前状态」单选，兼容 dashboard 订单分布。
- 邮件记录：base 中不存在，幂等新建「邮件记录」表。
- 系统配置：base 中不存在，幂等新建「系统配置」表（key/value 两列）。

所有表名/table_id 优先按名称查找，找不到再用内置 table_id 常量兜底。
零新依赖：smtplib/imaplib/ssl 均标准库。
"""
import json
import time
import smtplib
import imaplib
import email
from email.header import decode_header, make_header
from email.utils import parseaddr
from datetime import datetime, timezone, timedelta

from app.main import _feishu_api, _tv  # 复用统一飞书请求与字段归一化

CST = timezone(timedelta(hours=8))

# 现有表（盘点确认，按名查找优先；常量仅兜底）
CUSTOMERS_TABLE_NAME = "客户表"
ORDERS_TABLE_NAME = "订单表"
MAILS_TABLE_NAME = "邮件记录"
CONFIG_TABLE_NAME = "系统配置"

_tid_cache = {}

# 内存缓存（短 TTL，与线索表模式一致）
_cust_cache = {"data": None, "ts": 0.0}
_mail_cache = {"data": None, "ts": 0.0}
_pi_cache = {"data": None, "ts": 0.0}
_cache_ttl = 20

# 邮箱配置默认值（QQ 邮箱提示，值留空）
EMAIL_CONFIG_DEFAULTS = {
    "email_address": "",
    "smtp_host": "smtp.qq.com",
    "smtp_port": "465",
    "imap_host": "imap.qq.com",
    "imap_port": "993",
    "email_auth_code": "",
}
SENSITIVE_CONFIG_KEYS = {"email_auth_code"}


def _find_table_id(name, fallback_tid=None):
    """按表名查找 table_id（缓存）；找不到返回 fallback_tid。"""
    if name in _tid_cache:
        return _tid_cache[name]
    from app.main import FEISHU_ATK
    resp = _feishu_api("GET", f"/bitable/v1/apps/{FEISHU_ATK}/tables?page_size=100")
    tid = None
    for t in resp.get("data", {}).get("items", []):
        _tid_cache[t.get("name")] = t.get("table_id")
        if t.get("name") == name:
            tid = t.get("table_id")
    if not tid:
        tid = fallback_tid
        if tid:
            _tid_cache[name] = tid
    return tid


def _ensure_fields(tid, schema):
    """幂等补字段：schema = [{'field_name','type','property'?}, ...]。
    已存在字段跳过；单选缺选项则 PUT 补齐。内部吞异常不阻断读流程。"""
    from app.main import FEISHU_ATK
    try:
        resp = _feishu_api(
            "GET", f"/bitable/v1/apps/{FEISHU_ATK}/tables/{tid}/fields?page_size=100")
        existing = {f.get("field_name", ""): f for f in resp.get("data", {}).get("items", [])}
        for fdef in schema:
            name = fdef["field_name"]
            cur = existing.get(name)
            if not cur:
                _feishu_api("POST",
                            f"/bitable/v1/apps/{FEISHU_ATK}/tables/{tid}/fields", fdef)
                print(f"[business] 表 {tid} 补字段「{name}」")
                continue
            if fdef.get("type") == 3 and fdef.get("property", {}).get("options"):
                want = {o["name"] for o in fdef["property"]["options"]}
                have = {o.get("name", "") for o in
                        (cur.get("property") or {}).get("options", [])}
                missing = want - have
                if missing:
                    merged = list((cur.get("property") or {}).get("options", [])) + \
                             [{"name": n} for n in sorted(missing)]
                    _feishu_api(
                        "PUT",
                        f"/bitable/v1/apps/{FEISHU_ATK}/tables/{tid}/fields/{cur.get('field_id')}",
                        {"field_name": name, "type": 3,
                         "property": {"options": merged}})
                    print(f"[business] 表 {tid} 单选「{name}」补选项：{sorted(missing)}")
    except Exception as e:
        print(f"[business] 字段补齐检查失败（忽略）: {e}")


def _create_table(name, fields):
    """新建飞书表，返回 table_id。"""
    from app.main import FEISHU_ATK
    _tid_cache.pop(name, None)
    resp = _feishu_api("POST", f"/bitable/v1/apps/{FEISHU_ATK}/tables",
                       {"table": {"name": name, "default_view_name": "列表",
                                  "fields": fields}})
    tid = resp.get("data", {}).get("table_id")
    if not tid:
        raise RuntimeError(f"创建「{name}」表失败: {resp}")
    print(f"[business] 已创建飞书表「{name}」: {tid}")
    return tid


# ============================================================
# 表初始化（幂等）
# ============================================================

# 客户表：复用现有字段 + 幂等补 4 个新字段
CUSTOMER_FIELDS_SCHEMA = [
    {"field_name": "分级", "type": 3,
     "property": {"options": [{"name": n} for n in ("A", "B", "C", "未分级")]}},
    {"field_name": "来源线索", "type": 1},       # 线索 record_id
    {"field_name": "客户状态", "type": 3,
     "property": {"options": [{"name": n} for n in ("活跃", "沉睡")]}},
    {"field_name": "创建时间", "type": 1},
]
# 客户表字段映射（短 key -> 飞书字段名；复用现有字段）
CUSTOMER_FIELD_MAP = {
    "name": "客户名称",
    "grade": "分级",
    "region": "国家/地区",
    "source_lead": "来源线索",
    "email": "邮箱",
    "contact": "联系人",
    "cust_status": "客户状态",
    "follow_status": "跟进状态",
    "channel": "来源渠道",
    "products": "主营产品",
    "created_at": "创建时间",
    "note": "备注",
    "record_id": "record_id",
}

# 订单表（PI 复用）：幂等补 3 个字段
ORDER_PI_FIELDS_SCHEMA = [
    {"field_name": "币种", "type": 1},
    {"field_name": "PI状态", "type": 3,
     "property": {"options": [{"name": n} for n in
                              ("草稿", "已发送", "已确认", "已成交", "已取消")]}},
    {"field_name": "关联客户", "type": 1},       # 客户 record_id
]
PI_FIELD_MAP = {
    "pi_no": "订单号",
    "customer_name": "客户名称",
    "region": "国家/地区",
    "amount": "订单金额（原币）",
    "currency": "币种",
    "status": "PI状态",
    "fulfill_status": "当前状态",
    "created_at": "下单日期",
    "products": "产品明细",
    "sales": "负责销售",
    "customer_id": "关联客户",
    "note": "备注",
    "record_id": "record_id",
}
PI_STATUS_OPTIONS = ("草稿", "已发送", "已确认", "已成交", "已取消")

# 邮件记录表（新建）
MAIL_FIELDS = [
    {"field_name": "方向", "type": 3,
     "property": {"options": [{"name": "发件"}, {"name": "收件"}]}},
    {"field_name": "发件人邮箱", "type": 1},
    {"field_name": "收件人邮箱", "type": 1},
    {"field_name": "关联线索", "type": 1},
    {"field_name": "关联客户", "type": 1},
    {"field_name": "主题", "type": 1},
    {"field_name": "正文摘要", "type": 1},
    {"field_name": "时间", "type": 1},
    {"field_name": "状态", "type": 3,
     "property": {"options": [{"name": n} for n in
                              ("发送成功", "发送失败", "已收件", "已回复")]}},
    {"field_name": "消息ID", "type": 1},
]
MAIL_FIELD_MAP = {
    "direction": "方向",
    "from": "发件人邮箱",
    "to": "收件人邮箱",
    "lead_id": "关联线索",
    "customer_id": "关联客户",
    "subject": "主题",
    "summary": "正文摘要",
    "time": "时间",
    "status": "状态",
    "message_id": "消息ID",
    "record_id": "record_id",
}

# 系统配置表（新建，key/value 两列；主字段为 key）
CONFIG_FIELDS = [
    {"field_name": "配置键", "type": 1},
    {"field_name": "配置值", "type": 1},
]


def customers_table_id():
    tid = _find_table_id(CUSTOMERS_TABLE_NAME, "tblssVBrZu8VyF2n")
    _ensure_fields(tid, CUSTOMER_FIELDS_SCHEMA)
    return tid


def orders_table_id():
    tid = _find_table_id(ORDERS_TABLE_NAME, "tbl5ftcUigUYS4Oi")
    _ensure_fields(tid, ORDER_PI_FIELDS_SCHEMA)
    return tid


def mails_table_id(create_if_missing=True):
    tid = _find_table_id(MAILS_TABLE_NAME)
    if not tid and create_if_missing:
        tid = _create_table(MAILS_TABLE_NAME, MAIL_FIELDS)
    return tid


def config_table_id(create_if_missing=True):
    tid = _find_table_id(CONFIG_TABLE_NAME)
    if not tid and create_if_missing:
        tid = _create_table(CONFIG_TABLE_NAME, CONFIG_FIELDS)
    return tid


# ============================================================
# 通用读取
# ============================================================

# 飞书日期字段（type=5）的值为 epoch 毫秒，需要可读化
_DATE_FIELDS = {"created_at"}


def _fmt_date(v):
    """飞书日期值（epoch 毫秒）-> 'YYYY-MM-DD'；字符串原样返回。"""
    if isinstance(v, (int, float)):
        try:
            return datetime.fromtimestamp(v / 1000, CST).strftime("%Y-%m-%d")
        except Exception:
            return str(v)
    return _tv(v)


def _to_epoch_ms(s):
    """'YYYY-MM-DD' 或 'YYYY-MM-DD HH:MM:SS' -> 飞书日期字段所需的 epoch 毫秒。
    已是数字则原样返回。"""
    if isinstance(s, (int, float)):
        return int(s)
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt).replace(tzinfo=CST)
            return int(dt.timestamp() * 1000)
        except ValueError:
            continue
    return None


def _norm(rec, field_map):
    fl = rec.get("fields", {})
    out = {"record_id": rec.get("record_id", "")}
    for short, full in field_map.items():
        if short == "record_id":
            continue
        if short in _DATE_FIELDS:
            out[short] = _fmt_date(fl.get(full))
        else:
            out[short] = _tv(fl.get(full))
    return out


def _fetch_all(tid, field_map, cache, force_refresh=False):
    now = time.time()
    if not force_refresh and cache["data"] is not None and now - cache["ts"] < _cache_ttl:
        return list(cache["data"])
    from app.main import FEISHU_ATK
    items, pt = [], None
    while True:
        path = f"/bitable/v1/apps/{FEISHU_ATK}/tables/{tid}/records?page_size=100"
        if pt:
            path += f"&page_token={pt}"
        resp = _feishu_api("GET", path)
        d = resp.get("data", {})
        items.extend(_norm(it, field_map) for it in d.get("items", []))
        if not d.get("has_more"):
            break
        pt = d.get("page_token")
    cache["data"] = items
    cache["ts"] = now
    return list(items)


def _invalidate(*caches):
    for c in caches:
        c["data"] = None
        c["ts"] = 0.0


# ============================================================
# 客户档案
# ============================================================

def fetch_customers(force_refresh=False):
    return _fetch_all(customers_table_id(), CUSTOMER_FIELD_MAP,
                      _cust_cache, force_refresh)


def _fetch_all_readonly(tid, field_map, cache):
    """只读拉取：tid 为 None（表未创建）时返回 []，不触发建表。"""
    if not tid:
        return []
    return _fetch_all(tid, field_map, cache, force_refresh=True)


def create_customer(fields: dict):
    """创建客户档案。fields 用飞书字段名。返回归一化记录。"""
    from app.main import FEISHU_ATK
    tid = customers_table_id()
    resp = _feishu_api(
        "POST", f"/bitable/v1/apps/{FEISHU_ATK}/tables/{tid}/records",
        {"fields": fields})
    rec = resp.get("data", {}).get("record", {})
    _invalidate(_cust_cache)
    return _norm(rec, CUSTOMER_FIELD_MAP) if rec else dict(fields)


def update_customer(record_id: str, fields: dict):
    from app.main import FEISHU_ATK
    tid = customers_table_id()
    _feishu_api("PUT",
                f"/bitable/v1/apps/{FEISHU_ATK}/tables/{tid}/records/{record_id}",
                {"fields": fields})
    _invalidate(_cust_cache)


def find_customer_by_email(email_addr: str):
    em = (email_addr or "").strip().lower()
    if not em:
        return None
    for c in fetch_customers():
        if (c.get("email") or "").strip().lower() == em:
            return c
    return None


def ensure_customer_from_lead(lead: dict):
    """线索转客户联动：按「公司机构」建客户档案；同邮箱客户已存在则不重复创建。
    返回 (customer_record, created: bool)。"""
    email_addr = (lead.get("联系邮箱") or "").strip()
    if email_addr:
        exist = find_customer_by_email(email_addr)
        if exist:
            return exist, False
    now_str = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")
    fields = {
        "客户名称": (lead.get("公司机构") or lead.get("标题") or "未命名客户").strip(),
        "国家/地区": lead.get("地区", ""),
        "联系人": "",
        "邮箱": email_addr,
        "来源渠道": "其他",
        "主营产品": "",
        "备注": (lead.get("摘要") or "")[:500],
        # 幂等补充字段
        "分级": "未分级",
        "来源线索": lead.get("record_id", ""),
        "客户状态": "活跃",
        "创建时间": now_str,
    }
    rec = create_customer(fields)
    return rec, True


# ============================================================
# PI 订单（复用订单表）
# ============================================================

def fetch_pi(force_refresh=False):
    return _fetch_all(orders_table_id(), PI_FIELD_MAP, _pi_cache, force_refresh)


def create_pi(fields: dict):
    from app.main import FEISHU_ATK
    tid = orders_table_id()
    # 「下单日期」为飞书日期字段（type=5），需 epoch 毫秒
    if fields.get("下单日期"):
        ms = _to_epoch_ms(fields["下单日期"])
        if ms:
            fields["下单日期"] = ms
    resp = _feishu_api(
        "POST", f"/bitable/v1/apps/{FEISHU_ATK}/tables/{tid}/records",
        {"fields": fields})
    rec = resp.get("data", {}).get("record", {})
    _invalidate(_pi_cache)
    return _norm(rec, PI_FIELD_MAP) if rec else dict(fields)


def update_pi(record_id: str, fields: dict):
    from app.main import FEISHU_ATK
    tid = orders_table_id()
    _feishu_api("PUT",
                f"/bitable/v1/apps/{FEISHU_ATK}/tables/{tid}/records/{record_id}",
                {"fields": fields})
    _invalidate(_pi_cache)


# ============================================================
# 邮件记录
# ============================================================

def fetch_mails(force_refresh=False, lead_id=None, create_if_missing=False):
    """读取邮件记录。create_if_missing=False（默认）时表不存在不自动建表，
    返回 []；发信/同步等写路径显式传 True 才建表。"""
    items = _fetch_all_readonly(
        mails_table_id(create_if_missing=create_if_missing),
        MAIL_FIELD_MAP, _mail_cache) if not create_if_missing else \
        _fetch_all(mails_table_id(create_if_missing=True),
                   MAIL_FIELD_MAP, _mail_cache, force_refresh)
    if lead_id:
        items = [m for m in items if m.get("lead_id") == lead_id]
    return items


def create_mail(fields: dict):
    from app.main import FEISHU_ATK
    tid = mails_table_id()
    resp = _feishu_api(
        "POST", f"/bitable/v1/apps/{FEISHU_ATK}/tables/{tid}/records",
        {"fields": fields})
    rec = resp.get("data", {}).get("record", {})
    _invalidate(_mail_cache)
    return _norm(rec, MAIL_FIELD_MAP) if rec else dict(fields)


# ============================================================
# 系统配置（key/value）
# ============================================================

def _config_rows(force_refresh=False, create_if_missing=False):
    now = time.time()
    if not force_refresh and _cfg_cache["data"] is not None \
            and now - _cfg_cache["ts"] < 30:
        return dict(_cfg_cache["data"])
    tid = config_table_id(create_if_missing=create_if_missing)
    if not tid:
        # 配置表尚未创建：读路径返回空（不触发建表）
        _cfg_cache["data"] = {}
        _cfg_cache["ts"] = now
        return {}
    from app.main import FEISHU_ATK
    rows, pt = {}, None
    while True:
        path = f"/bitable/v1/apps/{FEISHU_ATK}/tables/{tid}/records?page_size=100"
        if pt:
            path += f"&page_token={pt}"
        resp = _feishu_api("GET", path)
        d = resp.get("data", {})
        for it in d.get("items", []):
            fl = it.get("fields", {})
            k = _tv(fl.get("配置键"))
            if k:
                rows[k] = {"value": _tv(fl.get("配置值")),
                           "record_id": it.get("record_id", "")}
        if not d.get("has_more"):
            break
        pt = d.get("page_token")
    _cfg_cache["data"] = dict(rows)
    _cfg_cache["ts"] = now
    return dict(rows)


_cfg_cache = {"data": None, "ts": 0.0}


def get_config(include_sensitive: bool):
    """返回配置 dict。默认值与已存值合并；非 admin 不返回敏感项（授权码）。"""
    try:
        rows = _config_rows()
    except Exception as e:
        print(f"[business] 配置表读取失败，仅返回默认值: {e}")
        rows = {}
    out = dict(EMAIL_CONFIG_DEFAULTS)
    for k, v in rows.items():
        out[k] = v["value"]
    if not include_sensitive:
        for k in SENSITIVE_CONFIG_KEYS:
            if out.get(k):
                out[k] = "********"  # 已配置但不明文回传
    out["_configured_keys"] = sorted(k for k, v in rows.items() if v.get("value"))
    return out


def set_config_kv(key: str, value: str):
    """upsert 一个配置项（按配置键查重）。写路径，表不存在则创建。"""
    from app.main import FEISHU_ATK
    rows = _config_rows(force_refresh=True, create_if_missing=True)
    tid = config_table_id(create_if_missing=True)
    if key in rows and rows[key].get("record_id"):
        _feishu_api("PUT",
                    f"/bitable/v1/apps/{FEISHU_ATK}/tables/{tid}/records/{rows[key]['record_id']}",
                    {"fields": {"配置值": value}})
    else:
        _feishu_api("POST", f"/bitable/v1/apps/{FEISHU_ATK}/tables/{tid}/records",
                    {"fields": {"配置键": key, "配置值": value}})
    _cfg_cache["data"] = None
    _cfg_cache["ts"] = 0.0


def get_email_settings():
    """取真实邮箱配置（含授权码明文，仅服务端发信/收信用）。
    未配置邮箱地址或授权码时返回 None。"""
    try:
        rows = _config_rows()
    except Exception:
        return None
    cfg = dict(EMAIL_CONFIG_DEFAULTS)
    for k, v in rows.items():
        cfg[k] = v["value"]
    if not cfg.get("email_address") or not cfg.get("email_auth_code"):
        return None
    return cfg


# ============================================================
# 真实发信（smtplib SSL，零新依赖）
# ============================================================

class EmailNotConfigured(Exception):
    pass


def send_email(to_addr: str, subject: str, body: str, lead_id: str = "",
               customer_id: str = ""):
    """SMTP SSL 发信并落「邮件记录」。
    成功返回记录 dict；邮箱未配置抛 EmailNotConfigured；
    发送失败落「发送失败」记录后抛出异常。"""
    cfg = get_email_settings()
    if not cfg:
        raise EmailNotConfigured("邮箱未配置，请管理员在配置中心填写授权码")
    frm = cfg["email_address"]
    now_str = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")
    msg = email.message_from_string(body) if body.startswith(("From:", "MIME")) else None
    if msg is None:
        from email.mime.text import MIMEText
        from email.utils import formataddr
        msg = MIMEText(body, "plain", "utf-8")
        msg["From"] = formataddr(("RHC Sales", frm))
        msg["To"] = to_addr
        msg["Subject"] = subject
    else:
        if not msg.get("From"):
            msg["From"] = frm
        if not msg.get("To"):
            msg["To"] = to_addr
        if not msg.get("Subject"):
            msg["Subject"] = subject
    message_id = msg.get("Message-ID", "")
    status = "发送成功"
    err = None
    try:
        port = int(cfg.get("smtp_port") or 465)
        if port == 465:
            with smtplib.SMTP_SSL(cfg["smtp_host"], port, timeout=30) as s:
                s.login(frm, cfg["email_auth_code"])
                s.sendmail(frm, [to_addr], msg.as_string())
        else:
            with smtplib.SMTP(cfg["smtp_host"], port, timeout=30) as s:
                s.starttls()
                s.login(frm, cfg["email_auth_code"])
                s.sendmail(frm, [to_addr], msg.as_string())
    except Exception as e:
        status = "发送失败"
        err = e
    fields = {
        "方向": "发件",
        "发件人邮箱": frm,
        "收件人邮箱": to_addr,
        "关联线索": lead_id or "",
        "关联客户": customer_id or "",
        "主题": subject or (msg.get("Subject") or ""),
        "正文摘要": (body or "")[:200],
        "时间": now_str,
        "状态": status,
        "消息ID": message_id,
    }
    try:
        rec = create_mail(fields)
    except Exception as e2:
        print(f"[business] 发信记录落库失败: {e2}")
        rec = fields
    if err:
        raise RuntimeError(f"邮件发送失败：{err}")
    return rec


# ============================================================
# 收件同步（imaplib，拉最近 30 天，按邮箱匹配线索/客户，消息ID 去重）
# ============================================================

def _decode_mime(s):
    if not s:
        return ""
    try:
        return str(make_header(decode_header(s)))
    except Exception:
        return str(s)


def sync_inbox():
    """IMAP 拉取最近 30 天收件箱邮件，落「邮件记录」。
    按发件人邮箱匹配线索「联系邮箱」/客户「邮箱」自动关联；消息ID 去重。
    返回 {"synced": n, "skipped": n}。邮箱未配置抛 EmailNotConfigured。"""
    cfg = get_email_settings()
    if not cfg:
        raise EmailNotConfigured("邮箱未配置，请管理员在配置中心填写授权码")
    # 同步前确保邮件记录表存在（写路径，允许建表）；读取已有消息ID 集合（去重）
    existing = set()
    try:
        mails_table_id(create_if_missing=True)
        for m in fetch_mails(force_refresh=True, create_if_missing=True):
            if m.get("message_id"):
                existing.add(m["message_id"].strip())
    except Exception as e:
        print(f"[business] 读取已有邮件记录失败（继续同步）: {e}")

    # 线索/客户邮箱索引
    lead_by_email, cust_by_email = {}, {}
    try:
        from app.main import _fetch_leads
        for ld in _fetch_leads():
            em = (ld.get("联系邮箱") or "").strip().lower()
            if em:
                lead_by_email[em] = ld.get("record_id", "")
    except Exception as e:
        print(f"[business] 线索索引失败: {e}")
    try:
        for c in fetch_customers(force_refresh=True):
            em = (c.get("email") or "").strip().lower()
            if em:
                cust_by_email[em] = c.get("record_id", "")
    except Exception as e:
        print(f"[business] 客户索引失败: {e}")

    synced = skipped = 0
    port = int(cfg.get("imap_port") or 993)
    conn = imaplib.IMAP4_SSL(cfg["imap_host"], port)
    try:
        conn.login(cfg["email_address"], cfg["email_auth_code"])
        conn.select("INBOX", readonly=True)
        since = (datetime.now(CST) - timedelta(days=30)).strftime("%d-%b-%Y")
        typ, data = conn.search(None, f'(SINCE {since})')
        if typ != "OK":
            return {"synced": 0, "skipped": 0}
        ids = data[0].split()
        for num in ids:
            typ, msg_data = conn.fetch(num, "(RFC822)")
            if typ != "OK" or not msg_data or not msg_data[0]:
                continue
            try:
                msg = email.message_from_bytes(msg_data[0][1])
            except Exception:
                continue
            mid = (msg.get("Message-ID") or "").strip()
            if mid and mid in existing:
                skipped += 1
                continue
            frm_addr = parseaddr(msg.get("From", ""))[1].strip().lower()
            to_addr = parseaddr(msg.get("To", ""))[1].strip()
            subject = _decode_mime(msg.get("Subject", ""))
            # 正文摘要（取 text/plain 前 200 字）
            body_text = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            payload = part.get_payload(decode=True)
                            charset = part.get_content_charset() or "utf-8"
                            body_text = payload.decode(charset, errors="ignore")
                            break
                        except Exception:
                            continue
            else:
                try:
                    payload = msg.get_payload(decode=True)
                    charset = msg.get_content_charset() or "utf-8"
                    body_text = (payload or b"").decode(charset, errors="ignore")
                except Exception:
                    body_text = ""
            date_hdr = msg.get("Date", "")
            try:
                dt = email.utils.parsedate_to_datetime(date_hdr)
                time_str = dt.astimezone(CST).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                time_str = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")
            lead_id = lead_by_email.get(frm_addr, "")
            customer_id = cust_by_email.get(frm_addr, "")
            # 回信判定：主题含 Re: 且能关联到线索/客户
            is_reply = subject.lower().startswith("re:") and (lead_id or customer_id)
            fields = {
                "方向": "收件",
                "发件人邮箱": frm_addr,
                "收件人邮箱": to_addr or cfg["email_address"],
                "关联线索": lead_id,
                "关联客户": customer_id,
                "主题": subject[:200],
                "正文摘要": body_text[:200],
                "时间": time_str,
                "状态": "已回复" if is_reply else "已收件",
                "消息ID": mid,
            }
            try:
                create_mail(fields)
                if mid:
                    existing.add(mid)
                synced += 1
            except Exception as e:
                print(f"[business] 收件记录落库失败: {e}")
    finally:
        try:
            conn.close()
            conn.logout()
        except Exception:
            pass
    return {"synced": synced, "skipped": skipped}


# ============================================================
# 销售漏斗后半段统计（邮件 / PI 真表点亮；表不可用返回 None 保持灰框架）
# ============================================================

def funnel_mail_stats():
    """返回 {'sent': n|None, 'replied': n|None}。
    sent    = 邮件记录表中「方向=发件」且状态=发送成功的去重线索/客户覆盖数
              （按 关联线索+关联客户+收件人邮箱 去重，避免同一客户多封重复计数）
    replied = 收件中「状态=已回复」覆盖的线索/客户数（客户回函建档口径）
    邮件记录表不存在/读取失败 -> None（前端显「—」灰框架）。
    注意：只读路径，表不存在时不自动建表。"""
    try:
        mails = _fetch_all_readonly(
            mails_table_id(create_if_missing=False), MAIL_FIELD_MAP, _mail_cache)
    except Exception as e:
        print(f"[business] 漏斗邮件统计失败（降级 None）: {e}")
        return {"sent": None, "replied": None}
    sent_keys, replied_keys = set(), set()
    for m in mails:
        direction = (m.get("direction") or "").strip()
        status = (m.get("status") or "").strip()
        lead_id = (m.get("lead_id") or "").strip()
        cust_id = (m.get("customer_id") or "").strip()
        to_addr = (m.get("to") or "").strip().lower()
        if direction == "发件" and status == "发送成功":
            sent_keys.add(lead_id or cust_id or to_addr)
        elif direction == "收件" and status == "已回复":
            replied_keys.add(lead_id or cust_id)
    return {"sent": len(sent_keys), "replied": len(replied_keys)}


def funnel_pi_stats():
    """返回 {'pi': n|None, 'won': n|None}。
    pi  = PI状态 属于有效推进态（已发送/已确认/已成交）的 PI 数（草稿/已取消不计）
    won = PI状态=已成交 或 履约「当前状态=已成交」的订单数
    订单表读取失败 -> None。"""
    try:
        pis = fetch_pi(force_refresh=True)
    except Exception as e:
        print(f"[business] 漏斗PI统计失败（降级 None）: {e}")
        return {"pi": None, "won": None}
    pi_active = {"已发送", "已确认", "已成交"}
    pi_n = sum(1 for p in pis if (p.get("status") or "").strip() in pi_active)
    won_n = sum(1 for p in pis
                if (p.get("status") or "").strip() == "已成交"
                or (p.get("fulfill_status") or "").strip() == "已成交")
    return {"pi": pi_n, "won": won_n}
