# MandiMitra — Data Inventory

## Data Source

**Agmarknet API** (Government of India — data.gov.in)
- Resource ID: `9ef84268-d588-465a-a308-a864a43d0070`
- Endpoint: `https://api.data.gov.in/resource/{resource_id}`
- Update frequency: Daily (mandis report prices each trading day)
- Access: Free API key from data.gov.in
- Rate limit: 500 requests/day (free tier)

## DynamoDB Table: MandiMitraPrices

**Total records:** 4,467 items
**Billing mode:** PAY_PER_REQUEST (on-demand)

### Schema

| Attribute | Type | Example |
|-----------|------|---------|
| PK (Partition Key) | String | `WHEAT#HARYANA` |
| SK (Sort Key) | String | `2026-02-28#INDRI APMC` |
| commodity | String | `Wheat` |
| state | String | `Haryana` |
| district | String | `Karnal` |
| mandi_name | String | `INDRI APMC` |
| arrival_date | String | `2026-02-28` |
| variety | String | `Desi (Red)` |
| min_price | Number | `2200` |
| max_price | Number | `2400` |
| modal_price | Number | `2300` |
| date_commodity | String | `2026-02-28#WHEAT` |

### Global Secondary Indexes

| GSI | PK | SK | Use Case |
|-----|----|----|----------|
| MANDI-INDEX | `mandi_name` | `date_commodity` | All commodities at a mandi |
| DATE-INDEX | `arrival_date` | `PK` | All prices on a given date |

## Tracked Commodities (20)

| Commodity | MSP (₹/qtl) | Perishability (1-10) | Storage Cost (₹/qtl/day) |
|-----------|-------------|---------------------|--------------------------|
| Wheat | 2,275 | 1 | 1.5 |
| Rice (Paddy) | 2,300 | 1 | 1.5 |
| Soyabean | 4,892 | 2 | 2.0 |
| Chana | 5,440 | 1 | 2.0 |
| Mustard | 5,650 | 1 | 2.0 |
| Maize | 2,225 | 1 | 2.0 |
| Bajra | 2,625 | 1 | 2.0 |
| Jowar | 3,371 | 1 | 2.0 |
| Moong Dal | 8,682 | 2 | 2.0 |
| Urad Dal | 7,400 | 2 | 2.0 |
| Groundnut | 6,377 | 2 | 2.0 |
| Cotton | 7,121 | 1 | 2.0 |
| Onion | No MSP | 6 | 5.0 |
| Tomato | No MSP | 9 | 15.0 |
| Potato | No MSP | 6 | 4.0 |
| Garlic | No MSP | 5 | 2.0 |
| Turmeric | No MSP | 3 | 2.0 |
| Red Chilli | No MSP | 3 | 2.0 |
| Coriander | No MSP | 3 | 2.0 |
| Cumin | No MSP | 2 | 2.0 |

## Tracked States (14)

Madhya Pradesh, Rajasthan, Maharashtra, Uttar Pradesh, Gujarat, Karnataka, Punjab, Haryana, Andhra Pradesh, Telangana, Tamil Nadu, Bihar, West Bengal, Chhattisgarh

## Mandi GPS Coordinates (55+)

Covers major mandis across all tracked states. Used for:
- `get_nearby_mandis()` — Haversine distance calculation
- Transport cost estimation (₹0.8 per quintal per km)

### Sample Mandis by State

| State | Mandis |
|-------|--------|
| Madhya Pradesh | Indore, Dewas, Ujjain, Bhopal, Jabalpur, Gwalior, Ratlam, Neemuch, Mandsaur |
| Rajasthan | Kota, Jaipur, Jodhpur |
| Maharashtra | Nagpur, Pune, Nashik |
| Gujarat | Ahmedabad, Rajkot, Surat, Vadodara, Junagadh |
| Uttar Pradesh | Lucknow, Agra, Kanpur, Varanasi, Shahjahanpur, Bareilly |
| Haryana | Karnal, Ambala, Hisar, Rohtak, Panipat, Sirsa, Fatehabad, Gurgaon, Sonipat |
| Punjab | Ludhiana, Amritsar, Khanna, Jalandhar, Patiala, Bathinda |
| Karnataka | Bengaluru, Hubli |
| Andhra Pradesh/Telangana | Hyderabad, Warangal |
| Tamil Nadu | Chennai, Madurai, Coimbatore, Salem |
| Bihar | Patna, Hajipur, Samastipur |
| West Bengal | Kolkata |
| Chhattisgarh | Raipur |
| Others | Delhi, Azadpur, Dimapur, Guwahati |

## Data Pipeline

### Ingestion Scripts

| Script | Purpose | Records |
|--------|---------|---------|
| `fetch_data_local.py` | Initial data fetch (limited) | ~300 |
| `fetch_more_data.py` | Targeted commodity/state fetch | ~2,000 |
| `fetch_all_data.py` | Aggressive state-by-state fetch | ~4,100 |
| `load_dynamodb.py` | Batch load to DynamoDB | - |
| `load_all_data.py` | Batch load all data files | - |

### Data Files (local)

| File | Records | Size |
|------|---------|------|
| `dynamodb_items.json` | ~300 | 83 KB |
| `dynamodb_items_all.json` | ~2,026 | 819 KB |
| `dynamodb_items_new.json` | ~3,572 | 1.4 MB |
| `raw_all_states.json` | ~4,110 | 967 KB |

### Lambda: mandimitra-data-ingestion

- Fetches from Agmarknet API for all tracked commodities × states
- Transforms to DynamoDB schema (PK/SK composite keys)
- Batch writes using `batch_writer()`
- Scheduled: Manual invocation (EventBridge schedule planned)

## Weather Data

**Source:** Open-Meteo API (free, no API key required)
- Endpoint: `https://api.open-meteo.com/v1/forecast`
- Coverage: Global (latitude/longitude based)
- Data: 5-day forecast (temperature, precipitation, wind, WMO weather codes)
- Used for: Agricultural advisory, sell timing recommendations

## Transport Cost Model

- Rate: ₹0.8 per quintal per km
- Distance: Haversine formula from user GPS to mandi GPS coordinates
- Net realization = modal_price - transport_cost

## Data Freshness

- Agmarknet data is updated daily by APMC mandis
- Our ingestion pulls data for current date + recent dates
- Frontend shows source + date citation: "Source: Agmarknet, DD-MMM-YYYY"
- If data unavailable, agent clearly states so (no hallucination)
