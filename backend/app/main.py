"""
RHC Marketing Assistant - Main Application
"""
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import os
import sys
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
    items = insights_store.get_items()
    return {
        "items": items,
        "total": len(items),
        "last_refresh": insights_store.status().get("last_refresh"),
    }

@app.post("/api/insights/refresh")
async def api_insights_refresh():
    from app import insights_store
    return insights_store.refresh(force=False)

@app.get("/api/insights/status")
async def api_insights_status():
    from app import insights_store
    return insights_store.status()

try:
    from app import insights_store
    insights_store.start_scheduler()
except Exception as _e:
    print(f"[insights] 模块初始化失败: {_e}")

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
