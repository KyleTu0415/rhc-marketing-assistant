# -*- coding: utf-8 -*-
"""llm.py - Social media copy generation with pre-written templates"""
import json

COPY_DB = {"V5 Plus_LinkedIn": {"headline": "Precision Anesthesia for Every Small Patient", "body": "The RHC V5 Plus delivers precise tidal volume control and integrated multi-gas monitoring, engineered specifically for feline and canine surgical anesthesia. Trusted by veterinary professionals who demand accuracy and reliability in every procedure. Elevate your clinic's standard of care.", "hashtags": ["#RHC", "#VeterinaryEquipment", "#AnimalAnesthesia", "#PetHealth", "#VetMed", "#SmallAnimalSurgery"]}, "V5 Plus_Facebook": {"headline": "Meet the V5 Plus - Precision Anesthesia Made Simple", "body": "Surgical precision meets compassionate care. The RHC V5 Plus animal anesthesia machine features integrated multi-gas monitoring and precise tidal volume control, designed specifically for cats, dogs, and small animals. Perfect for clinics that want reliable, professional-grade equipment.", "hashtags": ["#RHC", "#PetHealth", "#VetClinic", "#AnimalCare", "#VeterinaryEquipment"]}, "V5 Plus_Instagram": {"headline": "Precision Care Starts Here", "body": "The RHC V5 Plus - where advanced technology meets compassionate veterinary care. Precise tidal volume control. Multi-gas monitoring. Built for the smallest patients who deserve the biggest attention.", "hashtags": ["#RHC", "#VetMed", "#AnimalAnesthesia", "#PetHealth", "#VetLife", "#SmallAnimalSurgery"]}, "V5 Plus_Twitter": {"headline": "RHC V5 Plus: Precision Anesthesia for Small Animals", "body": "Precise tidal volume control + multi-gas monitoring = safer surgeries for cats and dogs. The RHC V5 Plus is built for veterinary professionals who never compromise.", "hashtags": ["#RHC", "#VeterinaryEquipment", "#PetHealth", "#VetMed"]}, "V5 Plus_WhatsApp": {"headline": "RHC V5 Plus - Professional Animal Anesthesia", "body": "Hi! The RHC V5 Plus is our flagship animal anesthesia machine featuring precise tidal volume control and integrated multi-gas monitoring. Ideal for cat and dog surgeries. Let me know if you'd like more details!", "hashtags": ["#RHC", "#VeterinaryEquipment", "#PetHealth"]}}
DEFAULT_DB = {"LinkedIn": {"headline": "Advanced Veterinary Solutions from RHC", "body": "RHC delivers professional-grade pet medical devices designed for veterinary clinics worldwide. Our equipment combines precision engineering with user-friendly operation, helping veterinary professionals provide the best care for their animal patients.", "hashtags": ["#RHC", "#VeterinaryEquipment", "#PetHealth", "#VetMed"]}, "Facebook": {"headline": "RHC - Professional Pet Medical Devices", "body": "Trusted by veterinary clinics globally. RHC pet medical devices combine precision, reliability, and ease of use. Because every animal patient deserves the best care.", "hashtags": ["#RHC", "#PetHealth", "#VetClinic", "#AnimalCare"]}, "Instagram": {"headline": "Caring for Those Who Cannot Speak", "body": "RHC professional pet medical devices - where innovation meets compassion. Designed for veterinary professionals who go above and beyond.", "hashtags": ["#RHC", "#VetMed", "#PetHealth", "#AnimalCare", "#VetLife"]}, "Twitter": {"headline": "RHC: Precision Pet Medical Devices", "body": "Professional-grade veterinary equipment from RHC. Precision-engineered for the care your animal patients deserve.", "hashtags": ["#RHC", "#VeterinaryEquipment", "#PetHealth"]}, "WhatsApp": {"headline": "RHC Pet Medical Devices", "body": "Hello! RHC offers professional pet medical devices for veterinary clinics. Precision-engineered and easy to use. Feel free to ask for more details!", "hashtags": ["#RHC", "#VeterinaryEquipment"]}}
PRODUCTS = {"V5 Plus": {"cn": "动物专用麻醉机", "en": "Animal Anesthesia Machine", "cat": "麻醉机", "sp": "精准潮气量控制，集成多气体监测"}, "F5 Plus": {"cn": "小动物麻醉机", "en": "Small Animal Anesthesia Machine", "cat": "麻醉机", "sp": "紧凑设计，精准流量控制"}, "A5": {"cn": "小动物麻醉工作站", "en": "Anesthesia Workstation", "cat": "麻醉工作站", "sp": "多参数监测"}, "A7": {"cn": "小动物麻醉机", "en": "Small Animal Anesthesia Machine", "cat": "麻醉机", "sp": "七氟醚专用"}, "F6": {"cn": "小动物麻醉机", "en": "Small Animal Anesthesia Machine", "cat": "麻醉机", "sp": "经济实惠"}, "SP500": {"cn": "注射泵", "en": "Syringe Pump", "cat": "辅助设备", "sp": "高精度微量注射"}, "VP100": {"cn": "呼吸泵", "en": "Ventilation Pump", "cat": "辅助设备", "sp": "便携式呼吸机"}}


def generate_copy(product_id="", target_language="en", tone="professional",
                  product_model="", platform="", language="", extra_keywords=""):
    model = product_model or product_id
    plat = platform or "LinkedIn"
    lang = language or target_language
    kw = extra_keywords or ""
    p = PRODUCTS.get(model, {})
    name_en = p.get("en", model)
    key = model + "_" + plat
    if key in COPY_DB:
        t = COPY_DB[key]
        result = {"title": t["headline"], "body": t["body"], "hashtags": t["hashtags"]}
        if kw: result["body"] += " " + kw
        return result
    t = DEFAULT_DB.get(plat, DEFAULT_DB["LinkedIn"])
    result = {"title": "RHC " + name_en + " - " + t["headline"], "body": t["body"], "hashtags": t["hashtags"]}
    if kw: result["body"] += " " + kw
    return result
