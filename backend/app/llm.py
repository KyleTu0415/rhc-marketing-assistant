# -*- coding: utf-8 -*-
"""llm.py - Generate social media copy via Coze workflow"""
import os, json, httpx, time

COZE_PAT = os.getenv("COZE_PAT", "")
WORKFLOW_ID = os.getenv("COZE_WORKFLOW_ID", "")
COZE_BASE = "https://api.coze.cn/v1"

PRODUCTS = {
    "V5 Plus": {"cn":"动物专用麻醉机","en":"Animal Anesthesia Machine","cat":"麻醉机","sp":"精准潮气量控制，集成多气体监测"},
    "F5 Plus": {"cn":"小动物麻醉机","en":"Small Animal Anesthesia Machine","cat":"麻醉机","sp":"紧凑设计，精准流量控制"},
    "A5": {"cn":"小动物麻醉工作站","en":"Anesthesia Workstation","cat":"麻醉工作站","sp":"多参数监测"},
    "A7": {"cn":"小动物麻醉机","en":"Small Animal Anesthesia Machine","cat":"麻醉机","sp":"七氟醚专用"},
    "F6": {"cn":"小动物麻醉机","en":"Small Animal Anesthesia Machine","cat":"麻醉机","sp":"经济实惠"},
    "SP500": {"cn":"注射泵","en":"Syringe Pump","cat":"辅助设备","sp":"高精度微量注射"},
    "VP100": {"cn":"呼吸泵","en":"Ventilation Pump","cat":"辅助设备","sp":"便携式呼吸机"},
}
PLATFORM_NAMES = {"LinkedIn":"LinkedIn","Facebook":"Facebook","Instagram":"Instagram","Twitter":"Twitter/X","WhatsApp":"WhatsApp"}
TONE_MAP = {"专业可信":"professional","友好亲切":"friendly","简洁有力":"concise","技术导向":"technical"}


def generate_copy(product_id="", target_language="en", tone="professional",
                  product_model="", platform="", language="", extra_keywords=""):
    model = product_model or product_id
    lang = language or target_language
    plat = platform or "LinkedIn"
    kw = extra_keywords or ""
    p = PRODUCTS.get(model, {})
    name_cn = p.get("cn", model)
    name_en = p.get("en", model)
    sp = p.get("sp", "High-quality pet medical device")
    cat = p.get("cat", "medical device")
    is_en = lang.lower() in ("en","english","英语","英文")
    ll = "English" if is_en else "Chinese"
    pl = PLATFORM_NAMES.get(plat, plat)
    tl = TONE_MAP.get(tone, tone)
    prompt = "Generate a " + pl + " social media post in " + ll + " with " + tl + " tone for RHC pet medical device."
    prompt += " Product: " + name_en + " (" + name_cn + "). Model: " + model + ". Category: " + cat + "."
    prompt += " Selling point: " + sp + "."
    if kw: prompt += " Additional keywords: " + kw + "."
    prompt += " Output: headline (max 80 chars), body (3-5 sentences), 5-8 hashtags including #RHC #VeterinaryEquipment. JSON only."
    try:
        r = httpx.post(COZE_BASE + "/workflow/run",
            headers={"Authorization":"Bearer "+COZE_PAT,"Content-Type":"application/json"},
            json={"workflow_id":WORKFLOW_ID,"parameters":{"input":prompt}},
            timeout=60.0)
        r.raise_for_status()
        d = r.json()
        # Coze workflow response parsing
        output = d.get("data", "")
        if isinstance(output, str):
            try: output = json.loads(output)
            except: pass
        if isinstance(output, dict):
            text = output.get("output", output.get("result", output.get("text", "")))
        else:
            text = str(output)
        if text and text.startswith("{"):
            res = json.loads(text)
            return {"title":res.get("headline",""),"body":res.get("body",""),"hashtags":res.get("hashtags",[])}
        # Fallback: return structured response
        return {"title":"RHC "+name_en,"body":text[:500] if text else ("Professional "+cat+" for veterinary clinics. "+sp),"hashtags":["#RHC","#VeterinaryEquipment","#PetHealth"]}
    except Exception as e:
        return {"title":"RHC "+name_en,"body":"Professional "+cat+" for veterinary clinics. "+sp,"hashtags":["#RHC","#VeterinaryEquipment","#PetHealth"]}
