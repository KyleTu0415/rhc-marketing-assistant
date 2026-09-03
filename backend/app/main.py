"""
RHC Marketing Assistant - Main Application
"""
import json
import hmac
import hashlib
import base64
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import os
import sys
import threading
import uvicorn
from datetime import datetime

# Optional imports
try:
    from app.feishu_client import feishu
except ImportError:
    feishu = None

try:
    from app.models import (
        CopyRequest, CopyResponse,
        ComposeRequest, ComposeResponse,
        ProductUpsertRequest
    )
except ImportError:
    class CopyRequest(BaseModel):
        product_id: str = ""
        target_language: str = "en"
        tone: str = "professional"
        product_model: str = ""
        platform: str = ""
        language: str = ""
        extra_keywords: str = ""

    class CopyResponse(BaseModel):
        title: str = ""
        body: str = ""
        hashtags: List[str] = []

    class ComposeRequest(BaseModel):
        animal: str = ""
        product_id: str = ""
        style: str = "professional"
        text: str = ""
        mode: str = ""
        prompt: str = ""
        ai_background: bool = False
        ai_prompt: str = ""
        ai_style: str = ""

    class ComposeResponse(BaseModel):
        composed_image_url: str = ""
        copy: Dict[str, Any] = {}
        animal_image_url: str = ""

    class ProductUpsertRequest(BaseModel):
        product_model: str = ""
        product_name: str = ""
        category: str = ""
        main_selling_point: str = ""
        product_image_url: str = ""
        price_tier: str = ""
        status: str = "active"

try:
    from app.llm import generate_copy
except ImportError:
    def generate_copy(product_id: str, target_language: str = "en", tone: str = "professional"):
        return {"title": "Coming Soon", "body": "LLM module not deployed", "hashtags": []}

try:
    from app.config import settings
except ImportError:
    class Settings:
        coze_pat: str = os.getenv("COZE_PAT", "")
        coze_workflow_id: str = os.getenv("COZE_WORKFLOW_ID", "")
        openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
        openai_text_model: str = os.getenv("OPENAI_TEXT_MODEL", "deepseek-chat")
    settings = Settings()

app = FastAPI(title="RHC Marketing Assistant", version="1.0.0")

# ============================================================
# 认证系统 (Auth)
# ============================================================
SECRET_KEY = os.getenv("RHC_SECRET_KEY", "rhc-marketing-secret-2026")
TOKEN_EXPIRY = 24 * 60 * 60  # 24 hours

# 兜底账号：飞书多维表格不可用（网络/凭证/限流）时使用，保证系统不会被锁死。
# 正常账号数据源为飞书「系统账号」表（见下方 _load_users 相关逻辑）。
USERS = {
    "ella": {"password": "rhc2026", "role": "admin", "name": "Ella"},
}

def _create_token(username: str) -> str:
    """Create a simple signed token: base64(json(payload)).signature"""
    payload = {
        "user": username,
        "exp": int(time.time()) + TOKEN_EXPIRY,
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    sig = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"

def _verify_token(token: str) -> Optional[dict]:
    """Verify token and return user info, or None if invalid/expired."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, sig = parts
        expected_sig = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        if payload.get("exp", 0) < time.time():
            return None
        username = payload.get("user")
        if not username:
            return None
        # 角色/姓名从当前用户源（飞书表优先，失败回退 USERS）取，
        # 以便在飞书表中修改角色后，已签发的 token 也能拿到最新角色。
        users = _get_users()
        u = users.get(username)
        if u:
            return {"username": username, "role": u["role"], "name": u["name"]}
        return None
    except Exception:
        return None

def _get_token_from_request(request: Request) -> Optional[str]:
    """Extract token from Authorization header or cookie."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    # Check cookie
    cookie_token = request.cookies.get("rhc_auth_token")
    if cookie_token:
        return cookie_token
    return None

class LoginRequest(BaseModel):
    username: str = ""
    password: str = ""

@app.post("/api/auth/login")
async def api_auth_login(req: LoginRequest):
    username = req.username.strip()
    password = req.password.strip()
    if not username or not password:
        return JSONResponse({"ok": False, "message": "请输入用户名和密码"})
    # 账号来自飞书「系统账号」表（60秒内存缓存）；飞书故障时回退兜底 USERS
    users = _get_users()
    user = users.get(username)
    if (not user or user["password"] != password):
        # 登录失败时强制刷新一次账号缓存再判（覆盖「刚在飞书表里新增账号/改密码」
        # 但缓存尚未过期的场景）；仍失败则返回错误
        users = _get_users(force_refresh=True)
        user = users.get(username)
    if not user or user["password"] != password:
        return JSONResponse({"ok": False, "message": "用户名或密码错误"})
    if not user.get("enabled", True):
        return JSONResponse({"ok": False, "message": "该账号已停用，请联系管理员"})
    token = _create_token(username)
    resp = JSONResponse({
        "ok": True,
        "token": token,
        "user": {"username": username, "role": user["role"], "name": user["name"]},
    })
    # Also set cookie for convenience
    resp.set_cookie(
        key="rhc_auth_token",
        value=token,
        max_age=TOKEN_EXPIRY,
        httponly=False,
        samesite="lax",
    )
    return resp

@app.get("/api/auth/me")
async def api_auth_me(request: Request):
    token = _get_token_from_request(request)
    if not token:
        return JSONResponse({"ok": False, "message": "未登录"}, status_code=401)
    user_info = _verify_token(token)
    if not user_info:
        return JSONResponse({"ok": False, "message": "登录已过期"}, status_code=401)
    return {"ok": True, "user": user_info}

@app.post("/api/auth/logout")
async def api_auth_logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("rhc_auth_token")
    return resp


@app.middleware("http")
async def no_cache_middleware(request, call_next):
    # 框架快速迭代期：HTML页面与数据快照禁用浏览器缓存，避免用户看到旧版
    resp = await call_next(request)
    path = request.url.path
    if path.endswith(".html") or path == "/" or path.endswith("snapshot.json"):
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    return resp

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/api/health")
async def api_health():
    return {"status": "ok"}

@app.post("/api/copy/generate", response_model=CopyResponse)
async def api_copy_generate(req: CopyRequest):
    try:
        result = generate_copy(
            product_id=req.product_id,
            target_language=req.target_language,
            tone=req.tone,
            product_model=req.product_model,
            platform=req.platform,
            language=req.language,
            extra_keywords=req.extra_keywords
        )
        return CopyResponse(
            title=result.get("title", ""),
            body=result.get("body", ""),
            hashtags=result.get("hashtags", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/compose")
async def api_compose(req: ComposeRequest):
    try:
        # Handle mode-based routing
        mode = getattr(req, 'mode', '') or ''
        if mode == 'animal_cutout':
            from app.composer import generate_animal_cutout
            prompt = getattr(req, 'prompt', '') or ''
            result = generate_animal_cutout(prompt=prompt)
            return {"image_url": result.get("image_url", ""), "status": result.get("status", "failed")}
        elif mode == 'background' or getattr(req, 'ai_background', False):
            from app.composer import generate_ai_background
            ai_prompt = getattr(req, 'ai_prompt', '') or getattr(req, 'text', '') or ''
            ai_style = getattr(req, 'ai_style', '') or getattr(req, 'style', 'professional') or 'professional'
            result = generate_ai_background(prompt=ai_prompt, style=ai_style)
            return result
        else:
            from app.composer import compose_image
            result = compose_image(
                animal=req.animal,
                text=req.text,
                style=req.style
            )
            return ComposeResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai-background")
async def api_ai_background(req: ComposeRequest):
    try:
        from app.composer import generate_ai_background
        result = generate_ai_background(
            prompt=req.text,
            style=req.style
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/animal-image")
async def api_animal_image(animal: str):
    try:
        from app.composer import search_animal_image
        url = search_animal_image(animal)
        return {"animal": animal, "image_url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/animals")
async def api_animals_list():
    return {"items": ["cat", "dog", "rabbit", "horse", "cow", "sheep", "goat", "pig"]}

FEISHU_AID = os.getenv("FEISHU_APP_ID", "")
FEISHU_ASE = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_ATK = os.getenv("FEISHU_APP_TOKEN", "")
FEISHU_TID = os.getenv("FEISHU_TABLE_ID", "")

def _feishu_token():
    import urllib.request as _ur
    tr = _ur.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=json.dumps({"app_id": FEISHU_AID, "app_secret": FEISHU_ASE}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with _ur.urlopen(tr, timeout=10) as r:
        return json.loads(r.read()).get("tenant_access_token")

def _feishu_headers():
    return {"Authorization": f"Bearer {_feishu_token()}", "Content-Type": "application/json"}

def _tv(v):
    if v is None: return ""
    if isinstance(v, list): return ", ".join(str(x.get("text", x) if isinstance(x, dict) else x) for x in v)
    if isinstance(v, dict): return v.get("text", str(v))
    return str(v)

# ============================================================
# 系统账号表（飞书多维表格数据源，替代硬编码 USERS）
# 用户可直接在飞书表「系统账号」中增删账号；表结构不存在时自动建表+种子数据。
# TODO: 演示阶段密码明文存储，正式版需改为哈希存储（如 bcrypt）。
# ============================================================
ACCOUNT_TABLE_NAME = "系统账号"
_ACCOUNT_CACHE_TTL = 60  # 账号列表内存缓存秒数，避免每次登录都调飞书 API

_account_table_id = None
_users_cache = {"data": None, "ts": 0.0}

def _feishu_api(method, path, payload=None, timeout=15):
    """统一的飞书 API 请求（沿用项目现有 urllib 风格，不引入新依赖）。"""
    import urllib.request as _ur
    import urllib.error as _ue
    url = f"https://open.feishu.cn/open-apis{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    rq = _ur.Request(url, data=data, headers=_feishu_headers(), method=method)
    try:
        with _ur.urlopen(rq, timeout=timeout) as r:
            return json.loads(r.read())
    except _ue.HTTPError as e:
        # 读取错误响应体，便于日志定位（凭证失效/限流/参数错误等）
        detail = ""
        try:
            detail = e.read().decode()[:300]
        except Exception:
            pass
        raise RuntimeError(f"feishu api {method} {path} -> HTTP {e.code}: {detail}")

def _ensure_account_table():
    """确保多维表中存在「系统账号」表，返回 table_id；不存在则自动创建。"""
    global _account_table_id
    if _account_table_id:
        return _account_table_id
    if not FEISHU_ATK:
        raise RuntimeError("FEISHU_APP_TOKEN 未配置")
    # 1) 列出多维表下所有数据表，按名字查找
    resp = _feishu_api("GET", f"/bitable/v1/apps/{FEISHU_ATK}/tables?page_size=100")
    for t in resp.get("data", {}).get("items", []):
        if t.get("name") == ACCOUNT_TABLE_NAME:
            _account_table_id = t.get("table_id")
            return _account_table_id
    # 2) 不存在则创建（主字段为第一个 field：用户名，文本类型）
    fields = [
        {"field_name": "用户名", "type": 1},  # 文本（主字段）
        {"field_name": "密码", "type": 1},    # 文本；TODO: 正式版改为加密存储
        {"field_name": "姓名", "type": 1},    # 文本
        {"field_name": "角色", "type": 3,     # 单选
         "property": {"options": [
             {"name": "admin"}, {"name": "sales"}, {"name": "viewer"}]}},
        {"field_name": "启用", "type": 3,     # 单选：是/否
         "property": {"options": [{"name": "是"}, {"name": "否"}]}},
    ]
    resp = _feishu_api("POST", f"/bitable/v1/apps/{FEISHU_ATK}/tables",
                       {"table": {"name": ACCOUNT_TABLE_NAME,
                                  "default_view_name": "账号列表",
                                  "fields": fields}})
    _account_table_id = resp.get("data", {}).get("table_id")
    if not _account_table_id:
        raise RuntimeError(f"创建「{ACCOUNT_TABLE_NAME}」表失败: {resp}")
    print(f"[auth] 已创建飞书账号表「{ACCOUNT_TABLE_NAME}」: {_account_table_id}")
    return _account_table_id

def _seed_accounts_if_empty(tid):
    """表为空时写入种子账号（与兜底 USERS 一致：ella / rhc2026 / Ella / admin / 启用）。"""
    resp = _feishu_api(
        "GET", f"/bitable/v1/apps/{FEISHU_ATK}/tables/{tid}/records?page_size=1")
    if resp.get("data", {}).get("total", 0) > 0 or resp.get("data", {}).get("items"):
        return
    fields = {"用户名": "ella", "密码": "rhc2026", "姓名": "Ella",
              "角色": "admin", "启用": "是"}
    _feishu_api("POST", f"/bitable/v1/apps/{FEISHU_ATK}/tables/{tid}/records",
                {"fields": fields})
    print("[auth] 账号表为空，已写入种子账号 ella/admin")

def _fetch_users_from_feishu():
    """从飞书「系统账号」表读取全部账号，返回 {username: {password,role,name,enabled}}。"""
    tid = _ensure_account_table()
    _seed_accounts_if_empty(tid)
    users = {}
    page_token = None
    while True:
        path = f"/bitable/v1/apps/{FEISHU_ATK}/tables/{tid}/records?page_size=100"
        if page_token:
            path += f"&page_token={page_token}"
        resp = _feishu_api("GET", path)
        data = resp.get("data", {})
        for it in data.get("items", []):
            fl = it.get("fields", {})
            username = _tv(fl.get("用户名")).strip()
            if not username:
                continue
            # 单选字段读取值可能是 {"text": "admin"} 结构，统一用 _tv 归一
            role = _tv(fl.get("角色")).strip() or "admin"
            if role not in ("admin", "sales", "viewer"):
                role = "admin"
            enabled = _tv(fl.get("启用")).strip()
            users[username] = {
                "password": _tv(fl.get("密码")),
                "role": role,
                "name": _tv(fl.get("姓名")) or username,
                # 单选「启用」未填写时默认视为启用；仅明确为「否」才停用
                "enabled": enabled != "否",
                # 飞书记录 ID，账号管理改/删使用；内部字段，不参与登录比对
                "_record_id": it.get("record_id", ""),
            }
        if not data.get("has_more"):
            break
        page_token = data.get("page_token")
    return users

def _get_users(force_refresh=False):
    """获取账号字典：优先飞书表（60秒缓存），飞书失败时回退硬编码 USERS。
    force_refresh=True 时跳过缓存强制拉取（登录失败重试场景使用）。"""
    now = time.time()
    if not force_refresh and _users_cache["data"] is not None \
            and now - _users_cache["ts"] < _ACCOUNT_CACHE_TTL:
        return _users_cache["data"]
    try:
        users = _fetch_users_from_feishu()
        _users_cache["data"] = users
        _users_cache["ts"] = now
        return users
    except Exception as e:
        # 兜底：飞书故障（网络/凭证/限流）时回退硬编码账号，保证系统不被锁死
        print(f"[auth] 警告: 读取飞书账号表失败，回退到内置兜底账号: {e}")
        if _users_cache["data"] is not None:
            # 有旧缓存则沿用旧数据（可能略有延迟，但不影响登录可用性）
            return _users_cache["data"]
        return USERS

def _warmup_account_table():
    """启动后台预热：尽早建表/写种子，失败不影响服务启动（登录时仍会自动重试/回退）。"""
    try:
        _get_users(force_refresh=True)
        if _users_cache["data"] is not None:
            print("[auth] 飞书账号表初始化完成")
        else:
            print("[auth] 飞书账号表暂不可用，当前使用内置兜底账号（登录时会自动重试）")
    except Exception as e:
        print(f"[auth] 飞书账号表初始化失败（登录时将自动重试/回退兜底账号）: {e}")

def _invalidate_users_cache():
    """写操作成功后调用：立即失效账号缓存并强制刷新，保证改完马上生效。
    刷新失败则置空缓存（下次读取会重新拉取；拉取失败仍回退兜底 USERS）。"""
    _users_cache["data"] = None
    _users_cache["ts"] = 0.0
    try:
        _get_users(force_refresh=True)
    except Exception as e:
        print(f"[admin] 账号缓存刷新失败，下次读取将重试: {e}")

def _find_user_by_record_id(record_id):
    """按飞书 record_id 找到对应账号：返回 (username, user_dict) 或 (None, None)。
    管理写操作专用：强制拉取最新数据，避免 60 秒缓存内拿到旧记录。"""
    users = _get_users(force_refresh=True)
    for uname, u in users.items():
        if u.get("_record_id") == record_id:
            return uname, u
    return None, None

def _count_active_admins(users):
    """统计启用中的 admin 数量（用于「最后一个管理员」防呆）。"""
    return sum(1 for u in users.values()
               if u.get("role") == "admin" and u.get("enabled", True))

# ============================================================
# 账号管理 API（配置中心「账号管理」页）
# 所有接口需登录；写操作（增/改/删）仅限 admin 角色。
# 数据源：飞书多维表「系统账号」表；写操作成功后立即失效账号缓存。
# ============================================================
class AdminAccountCreate(BaseModel):
    username: str = ""
    password: str = ""
    name: str = ""
    role: str = "viewer"

class AdminAccountUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None
    enabled: Optional[bool] = None

@app.get("/api/admin/accounts")
async def api_admin_accounts_list(request: Request):
    token = _get_token_from_request(request)
    if not token or not _verify_token(token):
        return JSONResponse({"ok": False, "message": "未登录或登录已过期"}, status_code=401)
    try:
        users = _get_users(force_refresh=True)
    except Exception as e:
        print(f"[admin] 读取账号列表失败: {e}")
        return JSONResponse({"ok": False, "message": f"读取账号列表失败：{e}"}, status_code=502)
    items = []
    for uname, u in users.items():
        items.append({
            "username": uname,
            "name": u.get("name", uname),
            "role": u.get("role", "viewer"),
            "enabled": u.get("enabled", True),
            "record_id": u.get("_record_id", ""),
        })
    return {"ok": True, "items": items, "total": len(items)}

@app.post("/api/admin/accounts")
async def api_admin_account_create(req: AdminAccountCreate, request: Request):
    token = _get_token_from_request(request)
    user_info = _verify_token(token) if token else None
    if not user_info:
        return JSONResponse({"ok": False, "message": "未登录或登录已过期"}, status_code=401)
    if user_info.get("role") != "admin":
        return JSONResponse({"ok": False, "message": "仅管理员可新增账号"}, status_code=403)

    username = (req.username or "").strip()
    password = req.password or ""
    name = (req.name or "").strip() or username
    role = (req.role or "").strip()
    if not username:
        return JSONResponse({"ok": False, "message": "用户名不能为空"}, status_code=400)
    if len(password) < 6:
        return JSONResponse({"ok": False, "message": "密码至少 6 位"}, status_code=400)
    if role not in ("admin", "sales", "viewer"):
        return JSONResponse({"ok": False, "message": "角色仅支持 admin / sales / viewer"}, status_code=400)

    try:
        users = _get_users(force_refresh=True)
        if username in users:
            return JSONResponse({"ok": False, "message": f"用户名「{username}」已存在，请更换"}, status_code=400)
        tid = _ensure_account_table()
        fields = {"用户名": username, "密码": password, "姓名": name,
                  "角色": role, "启用": "是"}
        resp = _feishu_api(
            "POST", f"/bitable/v1/apps/{FEISHU_ATK}/tables/{tid}/records",
            {"fields": fields})
        rec = resp.get("data", {}).get("record", {})
        _invalidate_users_cache()
        return {"ok": True, "message": "账号已创建",
                "record_id": rec.get("record_id", ""),
                "account": {"username": username, "name": name,
                            "role": role, "enabled": True,
                            "record_id": rec.get("record_id", "")}}
    except Exception as e:
        print(f"[admin] 新增账号失败（{username}）: {e}")
        return JSONResponse({"ok": False, "message": f"新增账号失败：{e}"}, status_code=502)

@app.put("/api/admin/accounts/{record_id}")
async def api_admin_account_update(record_id: str, req: AdminAccountUpdate, request: Request):
    token = _get_token_from_request(request)
    user_info = _verify_token(token) if token else None
    if not user_info:
        return JSONResponse({"ok": False, "message": "未登录或登录已过期"}, status_code=401)
    if user_info.get("role") != "admin":
        return JSONResponse({"ok": False, "message": "仅管理员可修改账号"}, status_code=403)

    try:
        target_uname, target_user = _find_user_by_record_id(record_id)
        if not target_user:
            return JSONResponse({"ok": False, "message": "账号不存在或已被删除"}, status_code=404)

        fields = {}
        if req.name is not None:
            name = req.name.strip() or target_uname
            fields["姓名"] = name
        if req.role is not None:
            role = req.role.strip()
            if role not in ("admin", "sales", "viewer"):
                return JSONResponse({"ok": False, "message": "角色仅支持 admin / sales / viewer"}, status_code=400)
            fields["角色"] = role
        if req.password is not None and req.password != "":
            # 空字符串/不传 = 不修改密码
            if len(req.password) < 6:
                return JSONResponse({"ok": False, "message": "密码至少 6 位"}, status_code=400)
            fields["密码"] = req.password
        if req.enabled is not None:
            fields["启用"] = "是" if req.enabled else "否"

        # ---- 防呆规则 ----
        is_self = (target_uname == user_info.get("username"))
        if is_self and fields.get("启用") == "否":
            return JSONResponse({"ok": False, "message": "不能停用当前登录账号"}, status_code=400)
        # 预演变更后的状态：不能让系统失去最后一个启用中的 admin
        new_role = fields.get("角色", target_user.get("role"))
        new_enabled = fields.get("启用")
        new_enabled = True if new_enabled == "是" else (False if new_enabled == "否" else target_user.get("enabled", True))
        if new_role != "admin" or not new_enabled:
            # 取最新全量账号模拟变更后统计
            users_now = _get_users(force_refresh=True)
            remain = 0
            for uname, u in users_now.items():
                r = new_role if uname == target_uname else u.get("role")
                en = new_enabled if uname == target_uname else u.get("enabled", True)
                if r == "admin" and en:
                    remain += 1
            if remain < 1:
                return JSONResponse({"ok": False, "message": "系统至少需保留一个启用中的管理员账号"}, status_code=400)

        if not fields:
            return {"ok": True, "message": "无需要修改的内容"}
        _feishu_api(
            "PUT",
            f"/bitable/v1/apps/{FEISHU_ATK}/tables/{_account_table_id}/records/{record_id}",
            {"fields": fields})
        _invalidate_users_cache()
        return {"ok": True, "message": "账号已更新"}
    except Exception as e:
        print(f"[admin] 修改账号失败（{record_id}）: {e}")
        return JSONResponse({"ok": False, "message": f"修改账号失败：{e}"}, status_code=502)

@app.delete("/api/admin/accounts/{record_id}")
async def api_admin_account_delete(record_id: str, request: Request):
    token = _get_token_from_request(request)
    user_info = _verify_token(token) if token else None
    if not user_info:
        return JSONResponse({"ok": False, "message": "未登录或登录已过期"}, status_code=401)
    if user_info.get("role") != "admin":
        return JSONResponse({"ok": False, "message": "仅管理员可删除账号"}, status_code=403)

    try:
        target_uname, target_user = _find_user_by_record_id(record_id)
        if not target_user:
            return JSONResponse({"ok": False, "message": "账号不存在或已被删除"}, status_code=404)
        if target_uname == user_info.get("username"):
            return JSONResponse({"ok": False, "message": "不能删除当前登录账号"}, status_code=400)
        # 不能删除最后一个启用中的 admin
        if target_user.get("role") == "admin" and target_user.get("enabled", True) \
                and _count_active_admins(_get_users(force_refresh=True)) <= 1:
            return JSONResponse({"ok": False, "message": "系统至少需保留一个启用中的管理员账号"}, status_code=400)
        _feishu_api(
            "DELETE",
            f"/bitable/v1/apps/{FEISHU_ATK}/tables/{_account_table_id}/records/{record_id}")
        _invalidate_users_cache()
        return {"ok": True, "message": f"账号「{target_uname}」已删除"}
    except Exception as e:
        print(f"[admin] 删除账号失败（{record_id}）: {e}")
        return JSONResponse({"ok": False, "message": f"删除账号失败：{e}"}, status_code=502)

@app.post("/api/products")
async def api_product_create(req: ProductUpsertRequest):
    import urllib.request as _ur
    try:
        fields = {"product_model": req.product_model, "product_name_cn": req.product_name,
                  "category": req.category, "main_selling_point": req.main_selling_point,
                  "product_image_url": req.product_image_url, "status": req.status or "active"}
        rq = _ur.Request(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_ATK}/tables/{FEISHU_TID}/records",
            data=json.dumps({"fields": fields}).encode(), headers=_feishu_headers(), method="POST")
        with _ur.urlopen(rq, timeout=15) as r:
            resp = json.loads(r.read())
        rec = resp.get("data", {}).get("record", {})
        fl = rec.get("fields", {})
        return {"record_id": rec.get("record_id", ""),
                "product_model": _tv(fl.get("product_model", req.product_model)),
                "product_name": _tv(fl.get("product_name_cn", fl.get("product_name", req.product_name))),
                "category": _tv(fl.get("category", req.category)),
                "main_selling_point": _tv(fl.get("main_selling_point", req.main_selling_point)),
                "product_image_url": _tv(fl.get("product_image_url", req.product_image_url)),
                "status": _tv(fl.get("status", req.status))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/products/{record_id}")
async def api_product_update(record_id: str, req: ProductUpsertRequest):
    import urllib.request as _ur
    try:
        fields = {}
        if req.product_model: fields["product_model"] = req.product_model
        if req.product_name: fields["product_name_cn"] = req.product_name
        if req.category: fields["category"] = req.category
        if req.main_selling_point: fields["main_selling_point"] = req.main_selling_point
        if req.product_image_url: fields["product_image_url"] = req.product_image_url
        rq = _ur.Request(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_ATK}/tables/{FEISHU_TID}/records/{record_id}",
            data=json.dumps({"fields": fields}).encode(), headers=_feishu_headers(), method="PUT")
        with _ur.urlopen(rq, timeout=15) as r:
            resp = json.loads(r.read())
        rec = resp.get("data", {}).get("record", {})
        fl = rec.get("fields", {})
        return {"record_id": record_id,
                "product_model": _tv(fl.get("product_model", req.product_model)),
                "product_name": _tv(fl.get("product_name_cn", fl.get("product_name", req.product_name))),
                "category": _tv(fl.get("category", req.category)),
                "main_selling_point": _tv(fl.get("main_selling_point", req.main_selling_point)),
                "product_image_url": _tv(fl.get("product_image_url", req.product_image_url)),
                "status": _tv(fl.get("status", req.status))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/products/{record_id}")
async def api_product_delete(record_id: str):
    import urllib.request as _ur
    try:
        rq = _ur.Request(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_ATK}/tables/{FEISHU_TID}/records/{record_id}",
            headers=_feishu_headers(), method="DELETE")
        with _ur.urlopen(rq, timeout=15) as r:
            json.loads(r.read())
        return {"status": "ok", "record_id": record_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cutout")
async def api_cutout(request: Request):
    """Accept image upload, remove background via rembg, return transparent PNG URL."""
    try:
        form = await request.form()
        file = form.get("file")
        if not file or not hasattr(file, "read"):
            raise HTTPException(status_code=400, detail="No file provided")
        file_data = await file.read()
        if not file_data:
            raise HTTPException(status_code=400, detail="Empty file")

        # Remove background
        from rembg import remove
        from PIL import Image
        import io as _io
        input_img = Image.open(_io.BytesIO(file_data))
        if input_img.mode not in ("RGB", "RGBA"):
            input_img = input_img.convert("RGBA" if "A" in input_img.getbands() else "RGB")
        # Downscale to avoid OOM on 512MB Railway instance (rembg is memory-heavy)
        max_dim = 1400
        w, h = input_img.size
        if max(w, h) > max_dim:
            scale = max_dim / float(max(w, h))
            input_img = input_img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
        output_img = remove(input_img)
        buf = _io.BytesIO()
        output_img.save(buf, format="PNG", optimize=True)
        cutout_bytes = buf.getvalue()

        # Upload to freeimage
        import urllib.request as _ur
        import uuid
        boundary = uuid.uuid4().hex
        filename = f"cutout_{uuid.uuid4().hex[:8]}.png"
        body = _build_multipart(boundary, cutout_bytes, filename)
        rq = _ur.Request(
            "https://freeimage.host/api/1/upload",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with _ur.urlopen(rq, timeout=60) as r:
            resp = json.loads(r.read())
        if resp and resp.get("image") and resp["image"].get("url"):
            return {"url": resp["image"]["url"], "status": "ok"}
        raise HTTPException(status_code=502, detail="Failed to upload cutout result")
    except HTTPException:
        raise
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"rembg not available: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/proxy-image")
async def api_proxy_image(url: str):
    """Proxy image to avoid CORS taint on canvas. Returns image bytes with CORS headers."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        from fastapi.responses import Response
        content_type = resp.headers.get("content-type", "image/png")
        return Response(
            content=resp.content,
            media_type=content_type,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=86400",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Proxy failed: {e}")


@app.post("/api/upload-image")
async def api_upload_image(request: Request):
    import urllib.request as _ur
    import uuid
    try:
        form = await request.form()
        file = form.get("file")
        if not file or not hasattr(file, "read"):
            raise HTTPException(status_code=400, detail="No file provided")
        file_data = await file.read()
        filename = file.filename or "upload.png"
        boundary = uuid.uuid4().hex
        body = _build_multipart(boundary, file_data, filename)
        rq = _ur.Request("https://freeimage.host/api/1/upload", data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
        with _ur.urlopen(rq, timeout=30) as r:
            resp = json.loads(r.read())
        if resp and resp.get("image") and resp["image"].get("url"):
            return {"url": resp["image"]["url"], "status": "ok"}
        err = resp.get("error", {}).get("message", "Upload failed") if resp else "Upload failed"
        raise HTTPException(status_code=502, detail=err)
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _build_multipart(boundary, file_data, filename):
    api_key = os.getenv("FREEIMAGE_API_KEY", "6d207e02198a847aa98d0a2a901485a5").encode()
    CRLF = b"\r\n"
    parts = [b"--" + boundary.encode(),
        b'Content-Disposition: form-data; name="key"', b"", api_key,
        b"--" + boundary.encode(),
        b'Content-Disposition: form-data; name="action"', b"", b"upload",
        b"--" + boundary.encode(),
        b'Content-Disposition: form-data; name="type"', b"", b"file",
        b"--" + boundary.encode(),
        b'Content-Disposition: form-data; name="source"; filename="' + filename.encode() + b'"',
        b"Content-Type: application/octet-stream", b"", file_data,
        b"--" + boundary.encode() + b"--"]
    return CRLF.join(parts)

@app.get("/api/products")
async def api_products_list():
    import urllib.request as _ur
    try:
        _tk=_feishu_token()
        _all=[]
        _pt=None
        while True:
            _u=f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_ATK}/tables/{FEISHU_TID}/records?page_size=100"
            if _pt:
                _u+=f"&page_token={_pt}"
            _rq=_ur.Request(_u, headers={"Authorization":f"Bearer {_tk}"})
            with _ur.urlopen(_rq,timeout=15) as r:
                _d=json.loads(r.read())
            _all.extend(_d.get("data",{}).get("items",[]))
            if not _d.get("data",{}).get("has_more"):
                break
            _pt=_d.get("data",{}).get("page_token")
        def _tv(v):
            if v is None:
                return ""
            if isinstance(v,list):
                return ", ".join(str(x.get("text",x) if isinstance(x,dict) else x) for x in v)
            if isinstance(v,dict):
                return v.get("text",str(v))
            return str(v)
        ps=[]
        for it in _all:
            fl=it.get("fields",{})
            ps.append({
                "record_id":it.get("record_id",""),
                "product_model":_tv(fl.get("product_model","")),
                "product_name":_tv(fl.get("product_name_cn",fl.get("product_name",""))),
                "category":_tv(fl.get("category","")),
                "main_selling_point":_tv(fl.get("main_selling_point","")),
                "product_image_url":_tv(fl.get("product_image_url","")),
                "price_tier":_tv(fl.get("price_tier","")),
                "status":_tv(fl.get("status",""))
            })
        return {"items":ps,"total":len(ps)}
    except Exception as e:
        return {"items":[],"error":str(e)}

# ============================================================
# 市场洞察 / 新闻中心 API
# ============================================================
@app.get("/api/insights")
async def api_insights_list():
    from app import insights_store
    all_items = insights_store.get_items()
    # 线上只对外提供 RSS 真新闻；source='seed' 的 12 条手工快照仅用于
    # 前端离线兜底（文件里自带），不混入线上数据。RSS 为空时才退回种子。
    rss_items = [it for it in all_items if it.get("source") != "seed"]
    items = rss_items if rss_items else all_items
    return {
        "items": items,
        "total": len(items),
        "last_refresh": insights_store.status().get("last_refresh"),
    }

@app.post("/api/insights/refresh")
async def api_insights_refresh():
    """手动刷新：后台线程执行抓取+翻译（20s~2min），立即返回受理状态，
    前端轮询 /api/insights 等待数据更新；避免长请求阻塞事件循环。"""
    from app import insights_store

    if insights_store.status().get("refreshing"):
        return {"accepted": False, "reason": "refreshing"}
    # 限频检查（在发起线程前快速判定）
    import time as _time
    if _time.time() - insights_store._state.get("last_refresh_ts", 0) < insights_store.REFRESH_MIN_INTERVAL:
        remain = int(insights_store.REFRESH_MIN_INTERVAL -
                     (_time.time() - insights_store._state.get("last_refresh_ts", 0)))
        return {"accepted": False, "reason": "rate_limited", "remain_seconds": remain}

    def _run():
        try:
            insights_store.refresh(force=True)
        except Exception as e:
            print(f"[insights] 后台刷新失败: {e}")

    threading.Thread(target=_run, daemon=True).start()
    return {"accepted": True}

@app.get("/api/insights/status")
async def api_insights_status():
    from app import insights_store
    return insights_store.status()

try:
    from app import insights_store
    insights_store.start_scheduler()
except Exception as _e:
    print(f"[insights] 模块初始化失败: {_e}")

# 启动时后台预热飞书「系统账号」表（建表+种子数据），不阻塞服务启动
threading.Thread(target=_warmup_account_table, daemon=True).start()

# Serve frontend - try multiple possible locations
_candidate_dirs = [
    os.path.join(os.path.dirname(__file__), "frontend"),                              # Railway root=backend/: /app/frontend
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend"),              # Railway root=repo: /backend/frontend
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend"),  # extra fallback
]
static_dir = None
for _d in _candidate_dirs:
    if os.path.isdir(_d):
        static_dir = _d
        break
if static_dir:
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
