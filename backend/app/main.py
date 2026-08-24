"""
RHC Medical 营销助手 - 主应用
"""
import re
import tempfile
from fastapi import FastAPI, HTTPException, Query, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from app.config import settings
try:
    try:
    try:
        from app.feishu_client import feishu
    except ImportError:
        feishu = None
except ImportError:
    feishu = None
except ImportError:
    feishu = None
try:
    try:
    try:
        from app.models import CopyRequest, CopyResponse, ComposeRequest, ComposeResponse, ProductUpsertRequest
    except ImportError:
        from pydantic import BaseModel
        class CopyRequest(BaseModel):
            product_id: str = ''
            target_language: str = 'en'
            tone: str = 'professional'
        class CopyResponse(BaseModel):
            title: str = ''
            body: str = ''
            hashtags: list = []
        class ComposeRequest(BaseModel):
            animal: str = ''
            product_id: str = ''
            style: str = 'professional'
            text: str = ''
        class ComposeResponse(BaseModel):
            composed_image_url: str = ''
            copy: dict = {}
            animal_image_url: str = ''
        class ProductUpsertRequest(BaseModel):
            name: str = ''
            description: str = ''
            category: str = ''
            specifications: dict = {}
            certifications: list = []
            target_market: str = ''
            custom_fields: dict = {}
except ImportError:
    from pydantic import BaseModel
    class CopyRequest(BaseModel): product_id: str = ''; target_language: str = 'en'; tone: str = 'professional'
    class CopyResponse(BaseModel): title: str = ''; body: str = ''; hashtags: list = []
    class ComposeRequest(BaseModel): animal: str = ''; product_id: str = ''; style: str = 'professional'; text: str = ''
    class ComposeResponse(BaseModel): composed_image_url: str = ''; copy: dict = {}; animal_image_url: str = ''
    class ProductUpsertRequest(BaseModel): name: str = ''; description: str = ''; category: str = ''; specifications: dict = {}; certifications: list = []; target_market: str = ''; custom_fields: dict = {}
except ImportError:
    from pydantic import BaseModel
    class CopyRequest(BaseModel): pass
    class CopyResponse(BaseModel): pass
    class ComposeRequest(BaseModel):
        product_image_url: str = ""
        prompt: str = ""
        style: str = "professional"
    class ComposeResponse(BaseModel): pass
    class ProductUpsertRequest(BaseModel): pass
try:
    try:
    try:
        from app.llm import generate_copy
    except ImportError:
        def generate_copy(product_id: str, target_language: str = 'en', tone: str = 'professional'):
            return {'title': 'Coming Soon', 'body': 'LLM module not deployed', 'hashtags': []}
except ImportError:
    def generate_copy(product_id: str, target_language: str = 'en', tone: str = 'professional'):
        return {'title': 'Coming Soon', 'body': 'LLM module not deployed', 'hashtags': []}
except ImportError:
    def generate_copy(text, **kwargs):
        return {"text": text, "note": "LLM module not available"}
from app.composer import compose_image, generate_background, generate_animal_cutout, THEMES

app = FastAPI(title="RHC Marketing Assistant API", version="0.1.0")

app.add_middleware(

    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded images from local uploads directory
import os as _os
_uploads_dir = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(__file__))), "uploads")
_os.makedirs(_uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_uploads_dir), name="uploads")

# Serve uploaded images locally (replaces freeimage.host)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "rhc-marketing-assistant"}


@app.get("/api/proxy-image")
async def proxy_image(url: str = Query(..., description="飞书文件链接")):
    """代理下载飞书私有图片，返回图片二进制供前端 <img> 显示"""
    m = re.search(r"/file/([A-Za-z0-9]+)", url)
    if not m:
        raise HTTPException(status_code=400, detail="invalid feishu file url")
    token = m.group(1)
    try:
        data = await feishu.download_media(token)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"download failed: {e}")
    ctype = "image/png" if data[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
    return Response(content=data, media_type=ctype, headers={"Cache-Control": "public, max-age=86400"})


@app.get("/api/products")
async def list_products(
    product_model: str | None = Query(None, description="按型号精确筛选"),
):
    """获取产品列表，支持按型号筛选"""
    filter_obj = None
    if product_model:
        filter_obj = {
            "conjunction": "and",
            "conditions": [
                {
                    "field_name": "product_model",
                    "operator": "is",
                    "value": [product_model],
                }
            ],
        }

    try:
        records = await feishu.list_records(
            settings.FEISHU_PRODUCT_TABLE_ID, filter_obj=filter_obj
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"飞书读取失败: {e}")

    products = []
    for r in records:
        f = r.get("fields", {})
        products.append(
            {
                "record_id": r.get("record_id"),
                "product_model": _extract_text(f.get("product_model")),
                "product_name": _extract_text(f.get("product_name")),
                "category": _extract_text(f.get("category")),
                "key_specs": _extract_text(f.get("key_specs")),
                "main_selling_point": _extract_text(f.get("main_selling_point")),
                "product_image_url": _extract_url_field(f.get("product_image_url")),
            }
        )
    return {"count": len(products), "items": products}


@app.get("/api/products/{record_id}")
async def get_product(record_id: str):
    """获取单个产品详情"""
    try:
        r = await feishu.get_record(settings.FEISHU_PRODUCT_TABLE_ID, record_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"飞书读取失败: {e}")
    f = r.get("fields", {})
    return {
        "record_id": r.get("record_id"),
        "product_model": _extract_text(f.get("product_model")),
        "product_name": _extract_text(f.get("product_name")),
        "category": _extract_text(f.get("category")),
        "key_specs": _extract_text(f.get("key_specs")),
        "main_selling_point": _extract_text(f.get("main_selling_point")),
        "product_image_url": _extract_url_field(f.get("product_image_url")),
    }


@app.post("/api/products")
async def create_product(req: ProductUpsertRequest):
    """新增产品到飞书多维表格"""
    fields = {}
    if req.product_model:
        fields["product_model"] = req.product_model
    if req.product_name:
        fields["product_name"] = req.product_name
    if req.category:
        fields["category"] = req.category
    if req.key_specs:
        fields["key_specs"] = req.key_specs
    if req.main_selling_point:
        fields["main_selling_point"] = req.main_selling_point
    if req.product_image_url:
        # product_image_url is a text field in Feishu, write as plain string
        fields["product_image_url"] = req.product_image_url
    try:
        record = await feishu.create_record(settings.FEISHU_PRODUCT_TABLE_ID, fields)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"飞书创建失败: {e}")
    f = record.get("fields", {})
    return {
        "record_id": record.get("record_id"),
        "product_model": _extract_text(f.get("product_model")),
        "product_name": _extract_text(f.get("product_name")),
        "category": _extract_text(f.get("category")),
        "key_specs": _extract_text(f.get("key_specs")),
        "main_selling_point": _extract_text(f.get("main_selling_point")),
        "product_image_url": _extract_url_field(f.get("product_image_url")),
    }


@app.put("/api/products/{record_id}")
async def update_product(record_id: str, req: ProductUpsertRequest):
    """更新飞书多维表格中的产品"""
    # Only send non-empty fields to avoid overwriting with empty strings
    fields = {}
    if req.product_model:
        fields["product_model"] = req.product_model
    if req.product_name:
        fields["product_name"] = req.product_name
    if req.category:
        fields["category"] = req.category
    if req.key_specs:
        fields["key_specs"] = req.key_specs
    if req.main_selling_point:
        fields["main_selling_point"] = req.main_selling_point
    if req.product_image_url:
        # product_image_url is a text field in Feishu, write as plain string
        fields["product_image_url"] = req.product_image_url
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    try:
        record = await feishu.update_record(settings.FEISHU_PRODUCT_TABLE_ID, record_id, fields)
    except Exception as e:
        import traceback
        with open(r"C:\Users\EDY\Desktop\RHC\backend_error.log", "a", encoding="utf-8") as lf:
            lf.write(f"PUT {record_id} failed: {type(e).__name__}: {e}\n")
            lf.write(f"Fields: {fields}\n")
            lf.write(traceback.format_exc() + "\n\n")
        raise HTTPException(status_code=502, detail=f"飞书更新失败: {e}")
    f = record.get("fields", {})
    return {
        "record_id": record.get("record_id"),
        "product_model": _extract_text(f.get("product_model")),
        "product_name": _extract_text(f.get("product_name")),
        "category": _extract_text(f.get("category")),
        "key_specs": _extract_text(f.get("key_specs")),
        "main_selling_point": _extract_text(f.get("main_selling_point")),
        "product_image_url": _extract_url_field(f.get("product_image_url")),
    }


@app.delete("/api/products/{record_id}")
async def delete_product(record_id: str):
    """删除飞书多维表格中的产品"""
    try:
        await feishu.delete_record(settings.FEISHU_PRODUCT_TABLE_ID, record_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"飞书删除失败: {e}")
    return {"ok": True, "record_id": record_id}


@app.get("/api/animals")
async def list_animals():
    """获取动物素材列表"""
    try:
        records = await feishu.list_records(settings.FEISHU_ANIMAL_TABLE_ID)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"飞书读取失败: {e}")

    animals = []
    for r in records:
        f = r.get("fields", {})
        animals.append(
            {
                "record_id": r.get("record_id"),
                "animal_name": _extract_text(f.get("animal_name")),
                "animal_cn": _extract_text(f.get("animal_cn")),
                "category": _extract_text(f.get("category")),
                "animal_image_url": _extract_url_field(f.get("image_url")),
            }
        )
    return {"count": len(animals), "items": animals}


@app.post("/api/copy/generate", response_model=CopyResponse)
async def generate_copy_endpoint(req: CopyRequest):
    """根据产品信息生成社媒文案"""
    filter_obj = {
        "conjunction": "and",
        "conditions": [
            {
                "field_name": "product_model",
                "operator": "is",
                "value": [req.product_model],
            }
        ],
    }
    try:
        records = await feishu.list_records(
            settings.FEISHU_PRODUCT_TABLE_ID, filter_obj=filter_obj
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"飞书读取失败: {e}")

    if not records:
        raise HTTPException(status_code=404, detail=f"未找到产品: {req.product_model}")

    f = records[0].get("fields", {})
    product_info = {
        "product_name": _extract_text(f.get("product_name")),
        "category": _extract_text(f.get("category")),
        "key_specs": _extract_text(f.get("key_specs")),
        "main_selling_point": _extract_text(f.get("main_selling_point")),
    }

    try:
        result = await generate_copy(
            product_model=req.product_model,
            product_info=product_info,
            platform=req.platform,
            language=req.language,
            extra_keywords=req.extra_keywords,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"文案生成失败: {e}")

    return result


@app.get("/api/compose/themes")
async def list_themes():
    """列出可用的合成主题"""
    return {
        "themes": [
            {"id": k, "name": k.replace("-", " ").title()} for k in THEMES.keys()
        ]
    }


@app.post("/api/compose", response_model=ComposeResponse)
async def compose_endpoint(req: ComposeRequest):
    """合成营销图片：支持 background/animal_cutout/compose 三种模式"""
    resolve_log = []

    # Mode: background - 生成纯净背景图（无文字无产品）
    if req.mode == "background":
        if req.ai_background:
            # AI background mode - call Coze workflow (pure scene, no product)
            from app.composer import generate_ai_background
            result = generate_ai_background(req.ai_prompt or "", req.ai_style or "professional")
            return ComposeResponse(image_url=result["image_url"], debug_log=result.get("debug_log", ""))
        else:
            # Gradient background mode
            result = compose_image(
                title="",
                subtitle="",
                theme=req.theme,
            )
            return ComposeResponse(image_url=result["image_url"], debug_log=result.get("debug_log", ""))

    # Mode: animal_cutout - 搜索动物图片并抠图
    if req.mode == "animal_cutout":
        if not req.prompt:
            raise HTTPException(status_code=400, detail="请提供动物描述(prompt)")
        result = generate_animal_cutout(req.prompt, settings.REMOVE_BG_API_KEY)
        if not result.get("image_url"):
            raise HTTPException(status_code=502, detail=result.get("error", "动物图生成失败"))
        return ComposeResponse(image_url=result["image_url"], debug_log=result.get("debug_log", ""))

    # Default mode: compose - 背景 + 产品 + 动物 + 文字
    # 如果传了产品型号但没给图片URL，从飞书取产品图
    product_url = req.product_image_url or ""
    if not product_url and req.product_model:
        filter_obj = {
            "conjunction": "and",
            "conditions": [
                {
                    "field_name": "product_model",
                    "operator": "is",
                    "value": [req.product_model],
                }
            ],
        }
        try:
            records = await feishu.list_records(
                settings.FEISHU_PRODUCT_TABLE_ID, filter_obj=filter_obj
            )
            if records:
                f = records[0].get("fields", {})
                product_url = _extract_url_field(f.get("product_image_url"))
                resolve_log.append(
                    f"[info] feishu product lookup: {len(records)} records, "
                    f"image_url={'yes' if product_url else 'empty'}"
                )
            else:
                resolve_log.append(
                    f"[warn] no product found for model: {req.product_model}"
                )
        except Exception as e:
            resolve_log.append(
                f"[warn] feishu product lookup failed: {type(e).__name__}: {e}"
            )

    # 解析飞书私有链接（下载到临时文件）
    product_url = await _resolve_feishu_url(product_url, "product", resolve_log)
    animal_url = await _resolve_feishu_url(
        req.animal_image_url or "", "animal", resolve_log
    )
    bg_url = await _resolve_feishu_url(
        req.background_image_url or "", "background", resolve_log
    )

    try:
        result = compose_image(
            product_image_url=product_url,
            animal_image_url=animal_url,
            background_image_url=bg_url,
            title=req.title or "",
            subtitle=req.subtitle or "",
            theme=req.theme,
            product_position=req.product_position,
            product_zoom=req.product_zoom,
            animal_position=req.animal_position,
            animal_zoom=req.animal_zoom,
            text_position=req.text_position,
            text_zoom=req.text_zoom,
            ai_background=req.ai_background,
            ai_prompt=req.ai_prompt or "",
            ai_style=req.ai_style or "professional",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片合成失败: {e}")

    debug = "\n".join(resolve_log)
    if result.get("debug_log"):
        debug = debug + "\n" + result["debug_log"] if debug else result["debug_log"]

    return ComposeResponse(image_url=result["image_url"], debug_log=debug)


@app.post("/api/cutout")
async def cutout_endpoint(file: bytes = File(...)):
    """接收上传图片，调用 remove.bg 抠图，返回透明 PNG URL"""
    if not settings.REMOVE_BG_API_KEY:
        raise HTTPException(status_code=400, detail="remove.bg API Key 未配置")
    try:
        from app.composer import cutout_with_remove_bg, upload_image

# Serve uploaded images from local directory
        from PIL import Image
        import io as _io
        result_bytes = cutout_with_remove_bg(file, settings.REMOVE_BG_API_KEY)
        img = Image.open(_io.BytesIO(result_bytes)).convert("RGBA")
        url = upload_image(img)
        return {"image_url": url, "debug_log": "cutout success"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"抠图失败: {e}")


# ========== 工具函数 ==========

def _is_feishu_file(url: str) -> bool:
    """判断是否为飞书云空间私有文件链接"""
    return bool(url and "feishu.cn/file/" in url)


async def _resolve_feishu_url(url: str, label: str, log: list) -> str:
    """如果是飞书私有链接，下载到临时文件并返回 file:/// 路径"""
    if not _is_feishu_file(url):
        return url
    try:
        m = re.search(r"/file/([A-Za-z0-9]+)", url)
        if not m:
            log.append(f"[warn] {label}: cannot extract token from {url[:80]}")
            return url
        token = m.group(1)
        data = await feishu.download_media(token)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmp.write(data)
        tmp.close()
        file_uri = "file:///" + tmp.name.replace("\\", "/")
        log.append(
            f"[ok] {label}: downloaded feishu file {len(data)} bytes"
        )
        return file_uri
    except Exception as e:
        log.append(f"[warn] {label}: feishu download failed: {type(e).__name__}: {e}")
        return url


def _extract_text(value) -> str:
    """飞书多维表格文本字段可能是 list[{type:text,text:...}] 或 str"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(item.get("text", ""))
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(value)


def _extract_url_field(value) -> str:
    """飞书 URL/mention 字段: list[{link, text, token, type:url/mention}] 或 str"""
    if not value:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                # 优先用完整链接
                link = item.get("link") or ""
                if link.startswith("http"):
                    return link
                # 从 token 构造飞书文件链接
                token = item.get("token") or ""
                if token:
                    return f"https://www.feishu.cn/file/{token}"
                return item.get("text") or item.get("url") or ""
        return ""
    if isinstance(value, dict):
        link = value.get("link") or ""
        if link.startswith("http"):
            return link
        token = value.get("token") or ""
        if token:
            return f"https://www.feishu.cn/file/{token}"
        return value.get("text") or value.get("url") or ""
    return str(value)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
