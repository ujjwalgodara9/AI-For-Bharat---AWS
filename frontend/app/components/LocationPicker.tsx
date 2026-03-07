"use client";

import { useState, useEffect, useMemo } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

// Fallback hardcoded states in case API is down
const FALLBACK_STATES = [
  "Andhra Pradesh", "Assam", "Bihar", "Chandigarh", "Goa", "Gujarat",
  "Haryana", "Himachal Pradesh", "Jammu and Kashmir", "Karnataka", "Kerala",
  "Madhya Pradesh", "Maharashtra", "NCT of Delhi", "Nagaland", "Odisha",
  "Punjab", "Rajasthan", "Tamil Nadu", "Telangana", "Tripura",
  "Uttar Pradesh", "Uttarakhand", "West Bengal",
];

interface DistrictData {
  district: string;
  mandis: string[];
}

interface LocationPickerProps {
  language: string;
  isOpen: boolean;
  onClose: () => void;
  onSelectLocation: (location: {
    latitude: number;
    longitude: number;
    label: string;
    state: string;
    city?: string;
  }) => void;
}

export default function LocationPicker({
  language,
  isOpen,
  onClose,
  onSelectLocation,
}: LocationPickerProps) {
  const [selectedState, setSelectedState] = useState("");
  const [gpsLoading, setGpsLoading] = useState(false);
  const [gpsError, setGpsError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  // Dynamic data from API
  const [states, setStates] = useState<string[]>(FALLBACK_STATES);
  const [districts, setDistricts] = useState<DistrictData[]>([]);
  const [loadingStates, setLoadingStates] = useState(false);
  const [loadingDistricts, setLoadingDistricts] = useState(false);

  const isHindi = language === "hi";

  // Fetch states from API on mount
  useEffect(() => {
    if (!API_BASE || !isOpen) return;
    const cached = sessionStorage.getItem("mm_states");
    if (cached) {
      try { setStates(JSON.parse(cached)); return; } catch { /* use fallback */ }
    }
    setLoadingStates(true);
    fetch(`${API_BASE}/prices/_locations`)
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data?.states?.length) {
          setStates(data.states);
          sessionStorage.setItem("mm_states", JSON.stringify(data.states));
        }
      })
      .catch(() => { /* use fallback */ })
      .finally(() => setLoadingStates(false));
  }, [isOpen]);

  // Fetch districts when state selected
  useEffect(() => {
    if (!selectedState || !API_BASE) { setDistricts([]); return; }
    const cacheKey = `mm_districts_${selectedState}`;
    const cached = sessionStorage.getItem(cacheKey);
    if (cached) {
      try { setDistricts(JSON.parse(cached)); return; } catch { /* fetch fresh */ }
    }
    setLoadingDistricts(true);
    fetch(`${API_BASE}/prices/_locations?state=${encodeURIComponent(selectedState)}`)
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data?.districts) {
          setDistricts(data.districts);
          sessionStorage.setItem(cacheKey, JSON.stringify(data.districts));
        }
      })
      .catch(() => { /* empty districts */ })
      .finally(() => setLoadingDistricts(false));
  }, [selectedState]);

  // Filter states/districts by search
  const filteredStates = useMemo(() => {
    if (!searchQuery.trim()) return states;
    const q = searchQuery.toLowerCase();
    return states.filter(s => s.toLowerCase().includes(q));
  }, [states, searchQuery]);

  const filteredDistricts = useMemo(() => {
    if (!searchQuery.trim()) return districts;
    const q = searchQuery.toLowerCase();
    return districts
      .map(d => ({
        ...d,
        mandis: d.mandis.filter(m => m.toLowerCase().includes(q)),
      }))
      .filter(d => d.district.toLowerCase().includes(q) || d.mandis.length > 0);
  }, [districts, searchQuery]);

  if (!isOpen) return null;

  const handleGps = () => {
    if (!navigator.geolocation) {
      setGpsError(isHindi ? "GPS इस डिवाइस पर उपलब्ध नहीं है" : "GPS not available on this device");
      return;
    }
    setGpsLoading(true);
    setGpsError("");
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        let detectedState = "";
        let detectedCity = "";
        let locationLabel = "Live GPS";
        try {
          const res = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&addressdetails=1&accept-language=en`,
            { headers: { "User-Agent": "MandiMitra/1.0 (agricultural-market-app)" } }
          );
          if (res.ok) {
            const data = await res.json();
            const addr = data.address || {};
            const rawState = addr.state || "";
            const rawCity = addr.city || addr.town || addr.county || addr.state_district || addr.village || "";

            // Match Nominatim state to our known states list
            let matchedState = "";
            if (rawState) {
              const found = states.find(
                (s) => s.toLowerCase() === rawState.toLowerCase() ||
                       rawState.toLowerCase().includes(s.toLowerCase()) ||
                       s.toLowerCase().includes(rawState.toLowerCase())
              );
              matchedState = found || rawState;
            } else if (rawCity) {
              // Union territories (Delhi, Chandigarh) may not have state field
              const cityLower = rawCity.toLowerCase().replace("new ", "");
              const found = states.find(
                (s) => s.toLowerCase().includes(cityLower) || cityLower.includes(s.toLowerCase())
              );
              if (found) matchedState = found;
            }

            detectedState = matchedState;
            detectedCity = rawCity;
            if (detectedCity && detectedState) locationLabel = `${detectedCity}, ${detectedState}`;
            else if (detectedState) locationLabel = detectedState;
            else if (detectedCity) locationLabel = detectedCity;
          }
        } catch {
          // GPS still works without reverse geocoding
        }
        setGpsLoading(false);
        onSelectLocation({ latitude: lat, longitude: lon, label: locationLabel, state: detectedState, city: detectedCity });
        onClose();
      },
      (err) => {
        setGpsLoading(false);
        if (err.code === 1) {
          setGpsError(isHindi
            ? "GPS की अनुमति नहीं दी गई। पुनः प्रयास करें या नीचे से चुनें।"
            : "Location permission denied. Retry or select below.");
        } else {
          setGpsError(isHindi
            ? "GPS से लोकेशन नहीं मिल सका। पुनः प्रयास करें या नीचे से चुनें।"
            : "Could not get GPS location. Retry or select below.");
        }
      },
      { enableHighAccuracy: false, timeout: 10000 }
    );
  };

  const handleSelectState = (state: string) => {
    setSelectedState(state);
    setSearchQuery("");
  };

  const handleSelectDistrict = (district: string) => {
    onSelectLocation({
      latitude: 0,
      longitude: 0,
      label: `${district}, ${selectedState}`,
      state: selectedState,
      city: district,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end sm:items-center justify-center">
      <div className="bg-white rounded-t-2xl sm:rounded-2xl w-full max-w-lg max-h-[85vh] overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="bg-gradient-to-r from-[#2d6a4f] to-[#40916c] text-white px-4 py-3 flex items-center justify-between">
          <div>
            <h3 className="font-bold">
              {isHindi ? "अपनी लोकेशन चुनें" : "Select Your Location"}
            </h3>
            <p className="text-xs text-green-200 mt-0.5">
              {isHindi ? "पास की मंडियां और भाव दिखाने के लिए" : "To show nearby mandis and local prices"}
            </p>
          </div>
          <button onClick={onClose} className="text-white/80 hover:text-white text-2xl leading-none">
            &times;
          </button>
        </div>

        {/* GPS option — always available for retry */}
        <button
          onClick={handleGps}
          disabled={gpsLoading}
          className="w-full px-4 py-3 flex items-center gap-3 border-b hover:bg-green-50 transition-colors disabled:opacity-60"
        >
          <span className="text-2xl">{gpsLoading ? "..." : "📡"}</span>
          <div className="text-left">
            <p className="font-semibold text-[#2d6a4f]">
              {gpsLoading
                ? (isHindi ? "GPS खोज रहे हैं..." : "Detecting GPS...")
                : (isHindi ? "Live Location (GPS)" : "Live Location (GPS)")}
            </p>
            <p className="text-xs text-gray-500">
              {isHindi ? "अपना सटीक स्थान उपयोग करें" : "Use your exact current location"}
            </p>
          </div>
        </button>

        {/* GPS error with retry hint */}
        {gpsError && (
          <div className="px-4 py-2.5 bg-amber-50 border-b border-amber-100 flex items-start gap-2">
            <span className="text-amber-500 text-sm mt-0.5">⚠️</span>
            <p className="text-xs text-amber-700">{gpsError}</p>
          </div>
        )}

        {/* Search box */}
        <div className="px-3 py-2 border-b">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={isHindi ? "🔍 राज्य या जिला खोजें..." : "🔍 Search state or district..."}
            className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 focus:border-[#2d6a4f] focus:outline-none focus:ring-1 focus:ring-[#2d6a4f]/20"
          />
        </div>

        {/* State/District list */}
        <div className="overflow-y-auto max-h-[55vh] p-2">
          {!selectedState ? (
            // Show states
            <div className="space-y-0.5">
              {selectedState === "" && (
                <p className="text-xs text-gray-400 px-2 py-1 font-medium uppercase tracking-wide">
                  {isHindi ? `👇 राज्य चुनें (${filteredStates.length})` : `👇 Select State (${filteredStates.length})`}
                </p>
              )}
              {loadingStates && (
                <p className="text-xs text-gray-400 px-3 py-2 animate-pulse">
                  {isHindi ? "राज्य लोड हो रहे हैं..." : "Loading states..."}
                </p>
              )}
              {filteredStates.map((state) => (
                <button
                  key={state}
                  onClick={() => handleSelectState(state)}
                  className="w-full text-left px-3 py-2.5 rounded-lg hover:bg-green-50 transition-colors flex items-center justify-between group"
                >
                  <span className="text-sm font-medium text-gray-700 group-hover:text-[#2d6a4f]">{state}</span>
                  <span className="text-gray-300 group-hover:text-[#2d6a4f] text-xs">&#9654;</span>
                </button>
              ))}
              {filteredStates.length === 0 && (
                <p className="text-xs text-gray-400 px-3 py-4 text-center">
                  {isHindi ? "कोई राज्य नहीं मिला" : "No states found"}
                </p>
              )}
            </div>
          ) : (
            // Show districts for selected state
            <div className="space-y-0.5">
              <button
                onClick={() => { setSelectedState(""); setSearchQuery(""); }}
                className="text-xs text-[#2d6a4f] px-2 py-1 font-semibold flex items-center gap-1 hover:underline"
              >
                &#9664; {isHindi ? "सभी राज्य" : "All States"}
              </button>

              <p className="text-xs text-gray-400 px-2 py-1 font-medium uppercase tracking-wide">
                {selectedState}
              </p>

              {/* State-level option */}
              <button
                onClick={() => {
                  onSelectLocation({
                    latitude: 0,
                    longitude: 0,
                    label: selectedState,
                    state: selectedState,
                  });
                  onClose();
                }}
                className="w-full text-left px-3 py-2.5 rounded-lg hover:bg-green-50 transition-colors border border-green-200 bg-green-50/50"
              >
                <span className="text-sm font-semibold text-[#2d6a4f]">
                  📍 {selectedState} ({isHindi ? "पूरा राज्य" : "Entire state"})
                </span>
              </button>

              {loadingDistricts && (
                <p className="text-xs text-gray-400 px-3 py-2 animate-pulse">
                  {isHindi ? "जिले लोड हो रहे हैं..." : "Loading districts..."}
                </p>
              )}

              {/* District groups */}
              {filteredDistricts.map((d) => (
                <button
                  key={d.district}
                  onClick={() => handleSelectDistrict(d.district)}
                  className="w-full text-left px-3 py-2.5 rounded-lg hover:bg-green-50 transition-colors flex items-center justify-between group"
                >
                  <div>
                    <span className="text-sm text-gray-700 group-hover:text-[#2d6a4f]">📌 {d.district}</span>
                    <span className="text-xs text-gray-400 ml-2">
                      {d.mandis.length} {isHindi ? "मंडी" : (d.mandis.length === 1 ? "mandi" : "mandis")}
                    </span>
                  </div>
                  <span className="text-gray-300 group-hover:text-[#2d6a4f] text-xs">&#9654;</span>
                </button>
              ))}

              {!loadingDistricts && filteredDistricts.length === 0 && (
                <p className="text-xs text-gray-400 px-3 py-4 text-center">
                  {isHindi ? "कोई जिला नहीं मिला" : "No districts found"}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Skip option */}
        <div className="border-t px-4 py-2.5">
          <button
            onClick={onClose}
            className="w-full text-center text-xs text-gray-400 hover:text-gray-600 py-1"
          >
            {isHindi ? "बाद में चुनें — बिना लोकेशन के भी पूछ सकते हैं" : "Skip for now — you can still ask without location"}
          </button>
        </div>
      </div>
    </div>
  );
}
