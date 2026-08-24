"""
RHC Marketing Assistant - Main Application
"""
from fastapi import FastAPI, HTTPException
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
        name: str = ""
        description: str = ""
        category: str = ""
        specifications: Dict[str, Any] = {}
        certifications: List[str] = []
        target_market: str = ""
        custom_fields: Dict[str, Any] = {}

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "RHC Marketing Assistant API",
        "version": "1.0.0",
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "modules": {
            "composer": True,
            "feishu": feishu is not None,
            "llm": generate_copy.__module__ if hasattr(generate_copy, "__module__") else "stub"
        }
    }

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

@app.post("/api/products", response_model=dict)
async def api_product_upsert(req: ProductUpsertRequest):
    try:
        return {"status": "ok", "message": "Product upserted", "product": req.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/products")
async def api_products_list():
    import urllib.request as _ur
        _AID="cli_aa0228e3abf8dcbd";_ASE="o645YodfdUCBKagae4LpMchcD1AL2mp2"
        _ATK="BwhybTEUVacyTksmocbcKvgCnQf";_TID="tbl2r6IQqgKiiEnE"
        try:
            tr=_ur.Request("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",data=json.dumps({"app_id":_AID,"app_secret":_ASE}).encode(),headers={"Content-Type":"application/json"},method="POST")
            with _ur.urlopen(tr,timeout=10) as r:_tk=json.loads(r.read()).get("tenant_access_token")
            _all=[];_pt=None
            while True:
                _u=f"https://open.feishu.cn/open-apis/bitable/v1/apps/{_ATK}/tables/{_TID}/records?page_size=100"
                if _pt:_u+=f"&page_token={_pt}"
                with _ur.urlopen(_ur.Request(_u,headers={"Authorization":f"Bearer {_tk}"}),timeout=15) as r:_d=json.loads(r.read())
                _all.extend(_d.get("data",{}).get("items",[]))
                if not _d.get("data",{}).get("has_more"):break
                _pt=_d.get("data",{}).get("page_token")
            def _tv(v):
                if v is None:return ""
                if isinstance(v,list):return ", ".join(str(x.get("text",x) if isinstance(x,dict) else x) for x in v)
                if isinstance(v,dict):return v.get("text",str(v))
                return str(v)
            ps=[{"record_id":it.get("record_id",""),"product_model":_tv(it.get("fields",{}).get("product_model","")),"product_name":_tv(it.get("fields",{}).get("product_name_cn",it.get("fields",{}).get("product_name",""))),"category":_tv(it.get("fields",{}).get("category","")),"main_selling_point":_tv(it.get("fields",{}).get("main_selling_point","")),"product_image_url":_tv(it.get("fields",{}).get("product_image_url","")),"price_tier":_tv(it.get("fields",{}).get("price_tier","")),"status":_tv(it.get("fields",{}).get("status",""))} for it in _all]
            return {"items":ps,"total":len(ps)}
        except Exception as e:
            return {"items":[],"error":str(e)}

static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
