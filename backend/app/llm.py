# -*- coding: utf-8 -*-
"""
llm.py - 调用 DeepSeek API 生成社媒推文
"""
import os
import json
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY", os.getenv("DEEPSEEK_API_KEY", "")),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1"),
)
MODEL = os.getenv("OPENAI_TEXT_MODEL", "deepseek-chat")

PRODUCTS = {
    "V5 Plus": {"name_cn": "动物专用麻醉机", "name_en": "Animal Anesthesia Machine", "category": "麻醉机", "selling_point": "精准潮气量控制，集成多气体监测，适用于猫狗等小动物手术麻醉"},
    "F5 Plus": {"name_cn": "小动物麻醉机", "name_en": "Small Animal Anesthesia Machine", "category": "麻醉机", "selling_point": "紧凑设计，精准流量控制，适合小型诊所"},
    "A5": {"name_cn": "小动物麻醉工作站", "name_en": "Small Animal Anesthesia Workstation", "category": "麻醉工作站", "selling_point": "多参数监测，适用于犬猫等常见宠物"},
    "A7": {"name_cn": "小动物麻醉机", "name_en": "Small Animal Anesthesia Machine", "category": "麻醉机", "selling_point": "七氟醚专用，精确挥发罐控制"},
    "F6": {"name_cn": "小动物麻醉机", "name_en": "Small Animal Anesthesia Machine", "category": "麻醉机", "selling_point": "经济实惠，操作简单"},
    "SP500": {"name_cn": "注射泵", "name_en": "Syringe Pump", "category": "辅助设备", "selling_point": "高精度微量注射，适用于宠物ICU"},
    "VP100": {"name_cn": "呼吸泵", "name_en": "Ventilation Pump", "category": "辅助设备", "selling_point": "便携式宠物呼吸机，适用于麻醉恢复期"},
}

PLATFORM_NAMES = {
    "LinkedIn": "LinkedIn", "Facebook": "Facebook", "Instagram": "Instagram",
    "Twitter": "Twitter/X", "WhatsApp": "WhatsApp",
}
TONE_MAP = {
    "专业可信": "professional and trustworthy", "友好亲切": "friendly and approachable",
    "简洁有力": "concise and impactful", "技术导向": "technical and data-driven",
}


def generate_copy(product_id="", target_language="en", tone="professional",
                  product_model="", platform="", language="", extra_keywords=""):
    model = product_model or product_id
    lang = language or target_language
    plat = platform or "LinkedIn"
    keywords = extra_keywords or ""
    product = PRODUCTS.get(model, {})
    product_name_cn = product.get("name_cn", model)
    product_name_en = product.get("name_en", model)
    selling_point = product.get("selling_point", f"RHC {product_name_cn}")
    category = product.get("category", "pet medical device")
    is_english = lang.lower() in ("en", "english", "英语", "英文")
    lang_label = "English" if is_english else "Chinese"
    platform_label = PLATFORM_NAMES.get(plat, plat)
    tone_label = TONE_MAP.get(tone, tone)
    prompt = f"""You are a professional social media marketing copywriter for RHC (Real Healthcare), a pet medical device company.

Product: {product_name_en} ({product_name_cn})
Model: {model}
Category: {category}
Key Selling Point: {selling_point}
{f"Additional Keywords: {keywords}" if keywords else ""}

Generate a {platform_label} post in {lang_label} with a {tone_label} tone.

Requirements:
1. Headline: A catchy headline (max 80 characters)
2. Body: 3-5 sentences highlighting the product key benefits for veterinary professionals
3. Hashtags: 5-8 relevant hashtags (include #RHC #VeterinaryEquipment)

Output format (JSON only, no markdown):
{{"headline": "...", "body": "...", "hashtags": ["#tag1", "#tag2", ...]}}
"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a professional social media copywriter. Always respond in valid JSON format only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=500,
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("
", 1)[1] if "
" in content else content
            content = content.rsplit("```", 1)[0].strip()
        result = json.loads(content)
        return {"title": result.get("headline", ""), "body": result.get("body", ""), "hashtags": result.get("hashtags", [])}
    except Exception as e:
        return {"title": f"RHC {product_name_en}", "body": f"Professional {category} for veterinary clinics. {selling_point}", "hashtags": ["#RHC", "#VeterinaryEquipment", "#PetHealth"]}
