"""
MandiMitra — Shared constants across all Lambda functions.
"""

# DynamoDB table name
PRICE_TABLE_NAME = "MandiMitraPrices"

# data.gov.in Agmarknet API
AGMARKNET_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
AGMARKNET_BASE_URL = f"https://api.data.gov.in/resource/{AGMARKNET_RESOURCE_ID}"

# Top commodities to track (covers 80%+ of Indian farmer queries)
TRACKED_COMMODITIES = [
    "Wheat", "Soyabean", "Onion", "Tomato", "Potato",
    "Mustard", "Chana", "Maize", "Cotton", "Rice (Paddy)",
    "Garlic", "Moong Dal", "Urad Dal", "Bajra", "Jowar",
    "Groundnut", "Turmeric", "Red Chilli", "Coriander", "Cumin"
]

# States to cover (major agricultural states)
TRACKED_STATES = [
    "Madhya Pradesh", "Rajasthan", "Maharashtra", "Uttar Pradesh",
    "Gujarat", "Karnataka", "Punjab", "Haryana", "Andhra Pradesh",
    "Telangana", "Tamil Nadu", "Bihar", "West Bengal", "Chhattisgarh"
]

# MSP rates for 2025-26 (₹ per quintal) — sourced from Ministry of Agriculture
MSP_RATES = {
    "Wheat": 2275,
    "Rice (Paddy)": 2300,
    "Soyabean": 4892,
    "Chana": 5440,
    "Mustard": 5650,
    "Maize": 2225,
    "Bajra": 2625,
    "Jowar": 3371,
    "Moong Dal": 8682,
    "Urad Dal": 7400,
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
    "Wheat": 1, "Rice (Paddy)": 1, "Chana": 1, "Maize": 1,
    "Bajra": 1, "Jowar": 1, "Mustard": 1, "Soyabean": 2,
    "Groundnut": 2, "Cotton": 1, "Moong Dal": 2, "Urad Dal": 2,
    "Coriander": 3, "Cumin": 2, "Turmeric": 3, "Red Chilli": 3,
    "Garlic": 5, "Onion": 6, "Potato": 6, "Tomato": 9,
}

# Storage cost estimate (₹ per quintal per day)
STORAGE_COST_PER_DAY = {
    "Wheat": 1.5, "Rice (Paddy)": 1.5, "Soyabean": 2.0,
    "Onion": 5.0, "Tomato": 15.0, "Potato": 4.0,
    "default": 2.0,
}

# Transport cost: ₹ per quintal per km (truck avg)
TRANSPORT_COST_PER_QTL_PER_KM = 0.8

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
}
