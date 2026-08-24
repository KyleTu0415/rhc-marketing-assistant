"""RHC Medical - Social Media Copy Generator (v3)

Formatting rules:
1. Each post has 1-3 key points max
2. Content split into paragraphs, each starts with platform-specific emoji icon
3. Titles are human-sounding, can use rhetorical questions
4. Each platform has its own emoji and style conventions
"""

import json

# === Emoji conventions per platform ===
# LinkedIn:  📊 stats  💡 insight  🎯 target  📩 CTA  🔍 discover  🏥 clinic
# Facebook:  👉 pointer  ✅ check  💪 strong  📨 send  🚫 pain point
# Instagram: ✨ sparkle  🐾 paw  📌 pin  💬 chat  🏥 clinic  🩺 stethoscope  ⚡ energy
# Twitter:   🩺 stethoscope  ⚡ energy
# YouTube:   ▶️ play  🔑 key feature  ✅ check  👨‍⚕️ doctor  📋 list  🏆 trophy  📨 contact

# === V5 Plus templates (hero product) ===

V5_LINKEDIN = {
    "title": "Is Your Vet Clinic Losing Patients Because of the Anesthesia Room?",
    "body": "📊 68% of small animal clinics lack a dedicated DR imaging room.\n📉 42% of referral patients are lost during the transfer process.\n\nThe problem isn’t talent — it’s equipment that doesn’t fit the space.\n\n🎯 The RHC V5 Plus Anesthesia Machine was designed for exactly this:\n\n💡 Compact footprint — fits in clinics under 20m² without renovation\n💡 Dual-flow vaporizer — precise delivery for animals from 2kg to 80kg\n💡 Fast induction — reduces prep time by up to 40%\n\nBuilt for veterinary clinics that need hospital-grade anesthesia\nwithout the hospital-grade footprint.\n\n📩 Want the full spec comparison? Drop a comment or send us a message.",
    "hashtags": ["#VeterinaryEquipment", "#AnimalHealth", "#VetClinic", "#RHC", "#PetAnesthesia"]
}

V5_FACEBOOK = {
    "title": "Small clinic, big cases — how do you handle anesthesia?",
    "body": "👉 If your clinic handles 10+ surgeries a week, you know:\n   every second counts, and your anesthesia machine can’t be the bottleneck.\n\n✅ The RHC V5 Plus was built for vets who work in tight spaces\n   but refuse to compromise on precision.\n\n✅ Dual vaporizer flow = one machine for cats, dogs, and large animals.\n   No more switching equipment between cases.\n\n💪 Compact enough for a 20m² room. Serious about patient safety.\n\n📨 Send us a message for pricing and shipping info.",
    "hashtags": ["#VetLife", "#VeterinaryMedicine", "#RHC"]
}

V5_INSTAGRAM = {
    "title": "Your anesthesia room just got an upgrade ✨",
    "body": "✨ Meet the RHC V5 Plus — the compact anesthesia workstation\n   that’s changing how small clinics operate.\n\n🐾 Why vets are switching:\n\n🏥 Fits in spaces under 20m² — no renovation needed\n🩺 Dual-flow vaporizer covers 2kg to 80kg patients\n⚡ Fast induction cuts prep time by 40%\n\n💬 DM us for a quote or to schedule a live demo.\n\n#VeterinaryEquipment #VetClinic #AnimalHealth #PetSurgery #VetLife #AnimalAnesthesia #VetMed #PetHealth #VetCommunity #VetWorld #RHC #SmallAnimalVet #VeterinarySurgery #VetPractice #ClinicLife",
    "hashtags": ["#VeterinaryEquipment", "#VetClinic", "#AnimalHealth", "#PetSurgery",
                  "#VetLife", "#AnimalAnesthesia", "#VetMed", "#PetHealth",
                  "#VetCommunity", "#VetWorld", "#RHC", "#SmallAnimalVet",
                  "#VeterinarySurgery", "#VetPractice", "#ClinicLife"]
}

V5_TWITTER = {
    "title": "Compact anesthesia for small clinics.",
    "body": "🩺 RHC V5 Plus: hospital-grade anesthesia in a 20m² footprint.\n⚡ Dual-flow vaporizer. Fast induction. Built for vets.\n#VetMed #AnimalHealth",
    "hashtags": ["#VetMed", "#AnimalHealth"]
}

V5_YOUTUBE = {
    "title": "RHC V5 Plus Anesthesia Machine — Full Overview for Veterinary Clinics",
    "body": "▶️ What is the RHC V5 Plus?\n   A compact, dual-flow anesthesia workstation designed for\n   veterinary clinics that need precision without the footprint.\n\n🔑 Key Features:\n   ✅ Fits in rooms under 20m² — ideal for small and mobile clinics\n   ✅ Dual-flow vaporizer: accurate delivery from 2kg to 80kg patients\n   ✅ Fast induction reduces prep time by up to 40%\n\n👨‍⚕️ Who is it for?\n   Private vet clinics, mobile veterinary services, and animal hospitals\n   looking to upgrade without major renovation.\n\n📨 Contact us for a live demo or pricing details.",
    "hashtags": ["#VeterinaryEquipment", "#RHC", "#AnimalAnesthesia", "#VetMed"]
}

# === Default templates (for all other products) ===

DEFAULT_LINKEDIN = {
    "title": "What’s Really Holding Back Your Clinic’s Efficiency?",
    "body": "Most veterinary clinics don’t have a talent problem —\nthey have an equipment problem.\n\n🔍 Here’s what we see again and again:\n\n💡 Outdated devices slowing down procedures\n💡 Equipment that doesn’t fit the space you have\n💡 Inconsistent results across different animal sizes\n\n🏥 RHC Medical designs professional-grade veterinary devices\nthat solve all three — built for real clinics, real budgets,\nand real animal patients.\n\n📩 Want to see how our equipment fits your workflow?\n   Drop a comment or send us a message.",
    "hashtags": ["#VeterinaryEquipment", "#AnimalHealth", "#VetClinic", "#RHC"]
}

DEFAULT_FACEBOOK = {
    "title": "Vet life is tough. Your equipment shouldn’t make it harder.",
    "body": "👉 We talk to clinics every week that are tired of:\n   🚫 Equipment that breaks down at the worst time\n   🚫 Devices too big for their treatment room\n   🚫 Inconsistent results between small and large animals\n\n✅ RHC Medical builds veterinary devices that are:\n   compact, reliable, and built for everyday clinical use.\n\n📨 Message us to learn more or request a quote.",
    "hashtags": ["#VetLife", "#VeterinaryMedicine", "#RHC"]
}

DEFAULT_INSTAGRAM = {
    "title": "Built for the clinic. Designed for the animals. ✨",
    "body": "✨ RHC Medical — professional veterinary equipment\n   trusted by clinics worldwide.\n\n📌 What sets us apart:\n\n🏥 Compact design that fits any clinic layout\n🔬 Precision engineering for consistent results\n💪 Built for daily use — durable and easy to maintain\n\n💬 DM us for product details or a live demo.",
    "hashtags": ["#VeterinaryEquipment", "#VetClinic", "#AnimalHealth", "#PetSurgery",
                  "#VetLife", "#AnimalCare", "#VetMed", "#PetHealth",
                  "#VetCommunity", "#RHC", "#ClinicLife", "#VetWorld",
                  "#VeterinarySurgery", "#PetCare", "#AnimalWelfare"]
}

DEFAULT_TWITTER = {
    "title": "Veterinary equipment, built right.",
    "body": "🩺 RHC Medical: professional-grade devices for veterinary clinics.\n⚡ Compact. Reliable. Designed for real-world use.\n#VetMed #AnimalHealth",
    "hashtags": ["#VetMed", "#AnimalHealth"]
}

DEFAULT_YOUTUBE = {
    "title": "RHC Medical — Professional Veterinary Equipment Overview",
    "body": "▶️ About RHC Medical\n   We design and manufacture professional-grade veterinary devices\n   for clinics and hospitals around the world.\n\n📋 What We Offer:\n   ✅ Anesthesia systems — precision dual-flow vaporizers\n   ✅ Imaging equipment — compact DR and ultrasound solutions\n   ✅ Surgical tools — built for daily clinical use\n\n🏆 Why Clinics Choose RHC:\n   ✅ Compact designs that fit existing clinic layouts\n   ✅ Consistent performance across animal sizes\n   ✅ Reliable after-sales support worldwide\n\n📨 Visit our website or contact us for a product demo.",
    "hashtags": ["#VeterinaryEquipment", "#RHC", "#VetMed", "#AnimalHealth"]
}

# === Router ===

COPY_DB = {
    "V5-Plus": {
        "linkedin": V5_LINKEDIN,
        "facebook": V5_FACEBOOK,
        "instagram": V5_INSTAGRAM,
        "twitter": V5_TWITTER,
        "youtube": V5_YOUTUBE,
    }
}

DEFAULT_DB = {
    "linkedin": DEFAULT_LINKEDIN,
    "facebook": DEFAULT_FACEBOOK,
    "instagram": DEFAULT_INSTAGRAM,
    "twitter": DEFAULT_TWITTER,
    "youtube": DEFAULT_YOUTUBE,
}


def generate_copy(product_id=None, target_language=None, tone=None,
                  product_model=None, platform=None, language=None,
                  extra_keywords=None, **kwargs):
    pid = product_id or product_model or ""
    plat = (platform or "linkedin").lower().strip()
    plat_key = plat.replace(" ", "").replace("/", "")
    if "linked" in plat_key: plat_key = "linkedin"
    elif "face" in plat_key: plat_key = "facebook"
    elif "insta" in plat_key: plat_key = "instagram"
    elif "twit" in plat_key or "x" == plat_key: plat_key = "twitter"
    elif "you" in plat_key: plat_key = "youtube"

    product_key = None
    for k in COPY_DB:
        if k.lower().replace("-", "").replace(" ", "") == pid.lower().replace("-", "").replace(" ", ""):
            product_key = k
            break
    if not product_key and "v5" in pid.lower() and "plus" in pid.lower():
        product_key = "V5-Plus"

    if product_key and plat_key in COPY_DB[product_key]:
        entry = COPY_DB[product_key][plat_key]
    elif plat_key in DEFAULT_DB:
        entry = DEFAULT_DB[plat_key]
    else:
        entry = DEFAULT_LINKEDIN

    return {
        "title": entry["title"],
        "body": entry["body"],
        "hashtags": entry["hashtags"],
    }
