"""
MandiMitra — Shared constants across all Lambda functions.
"""

# DynamoDB table name
PRICE_TABLE_NAME = "MandiMitraPrices"

# data.gov.in Agmarknet API
AGMARKNET_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
AGMARKNET_BASE_URL = f"https://api.data.gov.in/resource/{AGMARKNET_RESOURCE_ID}"

# Top commodities to track (covers 80%+ of Indian farmer queries)
# Names must match data_ingestion COMMODITIES list (which matches Agmarknet API filter names)
TRACKED_COMMODITIES = [
    "Wheat", "Soyabean", "Onion", "Tomato", "Potato",
    "Mustard", "Chana", "Maize", "Cotton", "Rice",
    "Garlic", "Moong", "Urad", "Bajra", "Jowar",
    "Groundnut", "Turmeric", "Red Chilli", "Coriander", "Cumin"
]

# English ↔ Hindi translations for all commodities (covers DB names + variants)
COMMODITY_TRANSLATIONS = {
    "Wheat": "गेहूं", "Soyabean": "सोयाबीन", "Onion": "प्याज",
    "Tomato": "टमाटर", "Potato": "आलू", "Chana": "चना",
    "Mustard": "सरसों", "Cotton": "कपास", "Maize": "मक्का",
    "Rice": "धान", "Garlic": "लहसुन", "Moong": "मूंग",
    "Urad": "उड़द", "Bajra": "बाजरा", "Jowar": "ज्वार",
    "Groundnut": "मूंगफली", "Turmeric": "हल्दी", "Red Chilli": "लाल मिर्च",
    "Coriander": "धनिया", "Cumin": "जीरा",
    # Variant names (for backward compatibility)
    "Rice (Paddy)": "धान", "Moong Dal": "मूंग दाल", "Urad Dal": "उड़द दाल",
}

# Reverse mapping: Hindi → English (auto-generated from COMMODITY_TRANSLATIONS)
HINDI_TO_ENGLISH = {v: k for k, v in COMMODITY_TRANSLATIONS.items()}
# Also add transliterated Hindi names
HINDI_TO_ENGLISH.update({
    "sarson": "Mustard", "gehun": "Wheat", "aloo": "Potato",
    "pyaz": "Onion", "tamatar": "Tomato", "soyabin": "Soyabean",
    "makka": "Maize", "kapas": "Cotton", "dhan": "Rice",
    "lahsun": "Garlic", "moong": "Moong", "urad": "Urad",
    "bajra": "Bajra", "jowar": "Jowar", "moongfali": "Groundnut",
    "haldi": "Turmeric", "lal mirch": "Red Chilli",
    "dhaniya": "Coriander", "jeera": "Cumin", "chana": "Chana",
})

# Hindi → English state mapping
HINDI_TO_ENGLISH_STATE = {
    "राजस्थान": "Rajasthan", "मध्य प्रदेश": "Madhya Pradesh",
    "महाराष्ट्र": "Maharashtra", "उत्तर प्रदेश": "Uttar Pradesh",
    "गुजरात": "Gujarat", "कर्नाटक": "Karnataka",
    "पंजाब": "Punjab", "हरियाणा": "Haryana",
    "आंध्र प्रदेश": "Andhra Pradesh", "तेलंगाना": "Telangana",
    "तमिल नाडु": "Tamil Nadu", "बिहार": "Bihar",
    "पश्चिम बंगाल": "West Bengal", "छत्तीसगढ़": "Chhattisgarh",
}


def normalize_commodity(name: str) -> str:
    """Translate Hindi/transliterated commodity name to English DB name."""
    if not name:
        return name
    # Check Hindi → English mapping (exact match)
    if name in HINDI_TO_ENGLISH:
        return HINDI_TO_ENGLISH[name]
    # Check case-insensitive transliterated match
    lower = name.lower().strip()
    if lower in HINDI_TO_ENGLISH:
        return HINDI_TO_ENGLISH[lower]
    # Check if already a valid English name (case-insensitive)
    for eng in TRACKED_COMMODITIES:
        if eng.lower() == lower:
            return eng
    return name  # Return as-is if no match


def normalize_state(name: str) -> str:
    """Translate Hindi state name to English."""
    if not name:
        return name
    if name in HINDI_TO_ENGLISH_STATE:
        return HINDI_TO_ENGLISH_STATE[name]
    return name


# States to cover (major agricultural states)
TRACKED_STATES = [
    "Madhya Pradesh", "Rajasthan", "Maharashtra", "Uttar Pradesh",
    "Gujarat", "Karnataka", "Punjab", "Haryana", "Andhra Pradesh",
    "Telangana", "Tamil Nadu", "Bihar", "West Bengal", "Chhattisgarh"
]

# MSP rates for 2025-26 (₹ per quintal) — sourced from Ministry of Agriculture
MSP_RATES = {
    "Wheat": 2275,
    "Rice (Paddy)": 2300, "Rice": 2300,
    "Soyabean": 4892,
    "Chana": 5440,
    "Mustard": 5650,
    "Maize": 2225,
    "Bajra": 2625,
    "Jowar": 3371,
    "Moong Dal": 8682, "Moong": 8682,
    "Urad Dal": 7400, "Urad": 7400,
    "Groundnut": 6377,
    "Cotton": 7121,
    "Onion": None,      # No MSP for onion
    "Tomato": None,     # No MSP for tomato
    "Potato": None,     # No MSP for potato
    "Garlic": None,
    "Turmeric": None,
    "Red Chilli": None,
    "Coriander": None,
    "Cumin": None,
}

# Perishability index (1 = can store years, 10 = rots in days)
PERISHABILITY_INDEX = {
    "Wheat": 1, "Rice (Paddy)": 1, "Rice": 1, "Chana": 1, "Maize": 1,
    "Bajra": 1, "Jowar": 1, "Mustard": 1, "Soyabean": 2,
    "Groundnut": 2, "Cotton": 1, "Moong Dal": 2, "Moong": 2, "Urad Dal": 2, "Urad": 2,
    "Coriander": 3, "Cumin": 2, "Turmeric": 3, "Red Chilli": 3,
    "Garlic": 5, "Onion": 6, "Potato": 6, "Tomato": 9,
}

# Storage cost estimate (₹ per quintal per day)
STORAGE_COST_PER_DAY = {
    "Wheat": 1.5, "Rice (Paddy)": 1.5, "Rice": 1.5, "Soyabean": 2.0,
    "Onion": 5.0, "Tomato": 15.0, "Potato": 4.0,
    "default": 2.0,
}

# Transport cost: ₹ per quintal per km (truck avg)
TRANSPORT_COST_PER_QTL_PER_KM = 0.8

# Storage tips per commodity — warehouse eligibility, method, conditions
STORAGE_TIPS = {
    "Wheat": {"method": "Dry gunny bags in ventilated room, moisture <12%. Use neem leaves to repel insects.", "warehouse": True, "ideal_temp": "25-30°C", "humidity": "<60%", "method_hi": "सूखी बोरियों में हवादार कमरे में रखें, नमी <12%। कीड़ों से बचाव के लिए नीम की पत्तियाँ रखें।"},
    "Rice (Paddy)": {"method": "Store in dry jute bags, keep on wooden pallets. Ensure moisture <14%.", "warehouse": True, "ideal_temp": "25-30°C", "humidity": "<65%", "method_hi": "सूखी जूट की बोरियों में, लकड़ी के फट्टों पर रखें। नमी <14% रखें।"},
    "Soyabean": {"method": "Clean dry bags, away from moisture. Store in cool dry place.", "warehouse": True, "ideal_temp": "20-25°C", "humidity": "<65%", "method_hi": "साफ सूखी बोरियों में, नमी से दूर। ठंडी सूखी जगह पर रखें।"},
    "Chana": {"method": "Dry clean bags, store elevated. Add dry neem leaves for pest control.", "warehouse": True, "ideal_temp": "25-30°C", "humidity": "<60%", "method_hi": "सूखी साफ बोरियों में ऊंचाई पर रखें। कीट नियंत्रण के लिए सूखी नीम की पत्तियाँ डालें।"},
    "Mustard": {"method": "Store in airtight containers or clean bags. Keep dry and cool.", "warehouse": True, "ideal_temp": "20-25°C", "humidity": "<60%", "method_hi": "एयरटाइट बर्तनों या साफ बोरियों में रखें। सूखा और ठंडा रखें।"},
    "Maize": {"method": "Dry to <12% moisture before storage. Use metal bins if possible.", "warehouse": True, "ideal_temp": "25-30°C", "humidity": "<65%", "method_hi": "भंडारण से पहले <12% नमी तक सुखाएं। हो सके तो धातु के डिब्बों में रखें।"},
    "Cotton": {"method": "Press into bales, store in dry covered area. Avoid direct sunlight.", "warehouse": True, "ideal_temp": "25-35°C", "humidity": "<65%", "method_hi": "गांठों में दबाएं, सूखी ढकी जगह में रखें। सीधी धूप से बचाएं।"},
    "Bajra": {"method": "Store in dry airtight containers. Sun-dry before storage.", "warehouse": True, "ideal_temp": "25-30°C", "humidity": "<60%", "method_hi": "सूखे एयरटाइट बर्तनों में रखें। भंडारण से पहले धूप में सुखाएं।"},
    "Jowar": {"method": "Store in jute bags on raised platforms. Keep ventilated.", "warehouse": True, "ideal_temp": "25-30°C", "humidity": "<60%", "method_hi": "जूट की बोरियों में ऊंचे चबूतरे पर रखें। हवादार रखें।"},
    "Moong Dal": {"method": "Store in airtight bags with dried neem. Keep dry.", "warehouse": True, "ideal_temp": "20-25°C", "humidity": "<60%", "method_hi": "सूखी नीम के साथ एयरटाइट बैग में रखें। सूखा रखें।"},
    "Urad Dal": {"method": "Clean dry airtight containers. Use turmeric powder for pest control.", "warehouse": True, "ideal_temp": "20-25°C", "humidity": "<60%", "method_hi": "साफ सूखे एयरटाइट बर्तनों में। कीट नियंत्रण के लिए हल्दी पाउडर मिलाएं।"},
    "Groundnut": {"method": "Dry to <8% moisture. Store in jute bags in cool ventilated area.", "warehouse": True, "ideal_temp": "20-25°C", "humidity": "<65%", "method_hi": "<8% नमी तक सुखाएं। ठंडी हवादार जगह में जूट की बोरियों में रखें।"},
    "Onion": {"method": "Well-ventilated storage with airflow, avoid stacking. Use bamboo shelves.", "warehouse": False, "ideal_temp": "25-30°C", "humidity": "<70%", "method_hi": "अच्छी हवा वाली जगह में, ढेर न लगाएं। बांस की अलमारियों पर रखें।"},
    "Tomato": {"method": "Cool shade, do NOT stack. Sell within 2-3 days. Refrigerate if possible.", "warehouse": False, "ideal_temp": "10-15°C", "humidity": "85-90%", "method_hi": "ठंडी छाया में रखें, ढेर न लगाएं। 2-3 दिन में बेचें। हो सके तो फ्रिज में रखें।"},
    "Potato": {"method": "Store in dark, cool, ventilated area. Avoid sunlight (turns green).", "warehouse": True, "ideal_temp": "4-10°C", "humidity": "85-90%", "method_hi": "अंधेरी, ठंडी, हवादार जगह में रखें। धूप से बचाएं (हरा हो जाता है)।"},
    "Garlic": {"method": "Hang in mesh bags with good airflow. Keep dry.", "warehouse": False, "ideal_temp": "25-30°C", "humidity": "<60%", "method_hi": "जालीदार बैग में लटकाएं, अच्छी हवा दें। सूखा रखें।"},
    "Turmeric": {"method": "Dry thoroughly, store in gunny bags. Can be stored for months.", "warehouse": True, "ideal_temp": "25-30°C", "humidity": "<65%", "method_hi": "अच्छी तरह सुखाएं, बोरियों में रखें। महीनों तक रख सकते हैं।"},
    "Red Chilli": {"method": "Sun-dry fully, store in airtight bags. Keep away from moisture.", "warehouse": True, "ideal_temp": "25-30°C", "humidity": "<60%", "method_hi": "पूरी तरह धूप में सुखाएं, एयरटाइट बैग में रखें। नमी से दूर रखें।"},
    "Coriander": {"method": "Dry seeds well, store in cloth bags in cool area.", "warehouse": True, "ideal_temp": "20-25°C", "humidity": "<60%", "method_hi": "बीजों को अच्छी तरह सुखाएं, कपड़े की बोरियों में ठंडी जगह रखें।"},
    "Cumin": {"method": "Sun-dry completely, store in airtight containers.", "warehouse": True, "ideal_temp": "20-25°C", "humidity": "<60%", "method_hi": "पूरी तरह धूप में सुखाएं, एयरटाइट बर्तनों में रखें।"},
}
# Aliases for DB name variants
STORAGE_TIPS["Rice"] = STORAGE_TIPS["Rice (Paddy)"]
STORAGE_TIPS["Moong"] = STORAGE_TIPS["Moong Dal"]
STORAGE_TIPS["Urad"] = STORAGE_TIPS["Urad Dal"]

# Crop harvest and sowing seasons (month numbers)
# harvest = peak supply → prices typically under pressure
# sowing = off-season → limited supply, prices may hold or rise
CROP_SEASONS = {
    "Wheat": {"harvest": [3, 4], "sowing": [10, 11], "type": "Rabi"},
    "Rice (Paddy)": {"harvest": [10, 11], "sowing": [6, 7], "type": "Kharif"},
    "Soyabean": {"harvest": [10, 11], "sowing": [6, 7], "type": "Kharif"},
    "Chana": {"harvest": [3, 4], "sowing": [10, 11], "type": "Rabi"},
    "Mustard": {"harvest": [2, 3], "sowing": [10, 11], "type": "Rabi"},
    "Maize": {"harvest": [9, 10], "sowing": [6, 7], "type": "Kharif"},
    "Cotton": {"harvest": [10, 11, 12], "sowing": [5, 6], "type": "Kharif"},
    "Bajra": {"harvest": [9, 10], "sowing": [6, 7], "type": "Kharif"},
    "Jowar": {"harvest": [10, 11], "sowing": [6, 7], "type": "Kharif"},
    "Moong Dal": {"harvest": [9, 10], "sowing": [6, 7], "type": "Kharif"},
    "Urad Dal": {"harvest": [9, 10], "sowing": [6, 7], "type": "Kharif"},
    "Groundnut": {"harvest": [10, 11], "sowing": [6, 7], "type": "Kharif"},
    "Onion": {"harvest": [1, 2, 3, 11, 12], "sowing": [6, 7, 8, 9], "type": "Multiple"},
    "Tomato": {"harvest": [1, 2, 3, 10, 11, 12], "sowing": [6, 7, 8, 9], "type": "Year-round"},
    "Potato": {"harvest": [1, 2, 3], "sowing": [10, 11], "type": "Rabi"},
    "Garlic": {"harvest": [2, 3, 4], "sowing": [9, 10, 11], "type": "Rabi"},
    "Turmeric": {"harvest": [1, 2, 3], "sowing": [6, 7], "type": "Kharif (long)"},
    "Red Chilli": {"harvest": [12, 1, 2], "sowing": [7, 8], "type": "Kharif"},
    "Coriander": {"harvest": [2, 3], "sowing": [10, 11], "type": "Rabi"},
    "Cumin": {"harvest": [2, 3], "sowing": [10, 11], "type": "Rabi"},
}
# Aliases for DB name variants
CROP_SEASONS["Rice"] = CROP_SEASONS["Rice (Paddy)"]
CROP_SEASONS["Moong"] = CROP_SEASONS["Moong Dal"]
CROP_SEASONS["Urad"] = CROP_SEASONS["Urad Dal"]

# Weather impact on crop storage — shelf life multiplier
WEATHER_STORAGE_IMPACT = {
    "high_rain": {"shelf_life_factor": 0.5, "risk": "Moisture damage, fungal growth, faster spoilage", "risk_hi": "नमी से नुकसान, फफूंद लगना, जल्दी खराब होना"},
    "high_heat": {"shelf_life_factor": 0.6, "risk": "Accelerated spoilage, insect infestation", "risk_hi": "जल्दी सड़ना, कीड़े लगना"},
    "moderate_rain": {"shelf_life_factor": 0.75, "risk": "Moderate moisture risk, cover crops well", "risk_hi": "हल्की नमी का खतरा, फसल को अच्छे से ढकें"},
    "cold": {"shelf_life_factor": 1.2, "risk": "Cold can help preserve — but protect from frost", "risk_hi": "ठंड से संरक्षण अच्छा — लेकिन पाले से बचाएं"},
    "normal": {"shelf_life_factor": 1.0, "risk": "Normal conditions — follow standard storage", "risk_hi": "सामान्य स्थिति — मानक भंडारण करें"},
}

# Approximate GPS coordinates for major mandis (lat, lon)
# This is a subset — will expand from data
MANDI_COORDINATES = {
    "Indore": (22.7196, 75.8577),
    "Dewas": (22.9623, 76.0508),
    "Ujjain": (23.1793, 75.7849),
    "Bhopal": (23.2599, 77.4126),
    "Jabalpur": (23.1815, 79.9864),
    "Gwalior": (26.2183, 78.1828),
    "Ratlam": (23.3340, 75.0367),
    "Neemuch": (24.4620, 74.8670),
    "Mandsaur": (24.0716, 75.0696),
    "Kota": (25.2138, 75.8648),
    "Jaipur": (26.9124, 75.7873),
    "Jodhpur": (26.2389, 73.0243),
    "Nagpur": (21.1458, 79.0882),
    "Pune": (18.5204, 73.8567),
    "Nashik": (20.0059, 73.7798),
    "Ahmedabad": (23.0225, 72.5714),
    "Rajkot": (22.3039, 70.8022),
    "Lucknow": (26.8467, 80.9462),
    "Agra": (27.1767, 78.0081),
    "Kanpur": (26.4499, 80.3319),
    "Bengaluru": (12.9716, 77.5946),
    "Hubli": (15.3647, 75.1240),
    "Ludhiana": (30.9010, 75.8573),
    "Amritsar": (31.6340, 74.8723),
    "Karnal": (29.6857, 76.9905),
    "Hyderabad": (17.3850, 78.4867),
    "Warangal": (17.9784, 79.5941),
    "Chennai": (13.0827, 80.2707),
    "Madurai": (9.9252, 78.1198),
    "Patna": (25.6093, 85.1376),
    "Kolkata": (22.5726, 88.3639),
    "Raipur": (21.2514, 81.6296),
    # Haryana
    "Ambala": (30.3782, 76.7767),
    "Hisar": (29.1492, 75.7217),
    "Rohtak": (28.8955, 76.6066),
    "Panipat": (29.3909, 76.9635),
    "Sirsa": (29.5332, 75.0289),
    "Fatehabad": (29.5152, 75.4547),
    "Gurgaon": (28.4595, 77.0266),
    "Sonipat": (28.9931, 77.0151),
    # Delhi
    "Azadpur": (28.7077, 77.1781),
    "Delhi": (28.6139, 77.2090),
    # Punjab
    "Khanna": (30.6967, 76.2164),
    "Jalandhar": (31.3260, 75.5762),
    "Patiala": (30.3398, 76.3869),
    "Bathinda": (30.2070, 74.9519),
    # UP
    "Varanasi": (25.3176, 82.9739),
    "Shahjahanpur": (27.8827, 79.9110),
    "Bareilly": (28.3670, 79.4304),
    # Bihar
    "Hajipur": (25.6856, 85.2167),
    "Samastipur": (25.8626, 85.7810),
    # Gujarat
    "Surat": (21.1702, 72.8311),
    "Vadodara": (22.3072, 73.1812),
    "Junagadh": (21.5222, 70.4579),
    # Tamil Nadu
    "Coimbatore": (11.0168, 76.9558),
    "Salem": (11.6643, 78.1460),
    # Others
    "Dimapur": (25.9065, 93.7272),
    "Guwahati": (26.1445, 91.7362),
}
