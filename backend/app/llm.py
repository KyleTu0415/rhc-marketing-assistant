# -*- coding: utf-8 -*-
"""llm.py - Call DeepSeek API for social media copy generation"""
import os, json, httpx

API_KEY = os.getenv("OPENAI_API_KEY", os.getenv("DEEPSEEK_API_KEY", ""))
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
MODEL = os.getenv("OPENAI_TEXT_MODEL", "deepseek-chat")

PRODUCTS = {
    "V5 Plus": {"cn": "动物专用麻醉机", "en": "Animal Anesthesia Machine", "cat": "麻醉机", "sp": "精准潮气量控制，集成多气体监测"},
    "F5 Plus": {"cn": "小动物麻醉机", "en": "Small Animal Anesthesia Machine", "cat": "麻醉机", "sp": "紧凑设计，精准流量控制"},
    "A5": {"cn": "小动物麻醉工作站", "en": "Anesthesia Workstation", "cat": "麻醉工作站", "sp": "多参数监测，适用于犬猫宠物"},
    "A7": {"cn": "小动物麻醉机", "en": "Small Animal Anesthesia Machine", "cat": "麻醉机", "sp": "七氟醚专用，精确挥发罐控制"},
    "F6": {"cn": "小动物麻醉机", "en": "Small Animal Anesthesia Machine", "cat": "麻醉机", "sp": "经济实惠，操作简单"},
    "SP500": {"cn": "注射泵", "en": "Syringe Pump", "cat": "辅助设备", "sp": "高精度微量注射，适用于宠物ICU"},
    "VP100": {"cn": "呼吸泵", "en": "Ventilation Pump", "cat": "辅助设备", "sp": "便携式宠物呼吸机"},
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
    prompt = "You are a social media copywriter for RHC pet medical devices.\n"
    prompt += "Product: " + name_en + " (" + name_cn + ")\n"
    prompt += "Model: " + model + "\nCategory: " + cat + "\n"
    prompt += "Selling Point: " + sp + "\n"
    if kw:
        prompt += "Keywords: " + kw + "\n"
    prompt += "Generate a " + pl + " post in " + ll + " with " + tl + " tone.\n"
    prompt += "Requirements:\n"
    prompt += "1. Headline: max 80 chars\n"
    prompt += "2. Body: 3-5 sentences on key benefits\n"
    prompt += "3. Hashtags: 5-8 tags include #RHC #VeterinaryEquipment\n"
    prompt += "Output JSON only: {\"headline\":\"...\",\"body\":\"...\",\"hashtags\":[\"#tag1\"]}"
    try:
        r = httpx.post(BASE_URL + "/chat/completions",
            headers={"Authorization":"Bearer "+API_KEY,"Content-Type":"application/json"},
            json={"model":MODEL,"messages":[{"role":"system","content":"Respond in valid JSON only."},{"role":"user","content":prompt}],"temperature":0.7,"max_tokens":500},
            timeout=30.0)
        r.raise_for_status()
        d = r.json()
        text = d["choices"][0]["message"]["content"].strip()
        if text.startswith("```"):
            text = text.split("\n",1)[1] if "\n" in text else text
            text = text.rsplit("```",1)[0].strip()
        res = json.loads(text)
        return {"title":res.get("headline",""),"body":res.get("body",""),"hashtags":res.get("hashtags",[])}
    except Exception:
        return {"title":"RHC "+name_en,"body":"Professional "+cat+" for veterinary clinics. "+sp,"hashtags":["#RHC","#VeterinaryEquipment","#PetHealth"]}
