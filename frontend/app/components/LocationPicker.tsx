"use client";

import { useState, useEffect } from "react";

// Major agricultural states and cities with GPS coordinates
const LOCATIONS: Record<string, { lat: number; lon: number; cities: Record<string, { lat: number; lon: number }> }> = {
  "Madhya Pradesh": {
    lat: 23.26, lon: 77.41,
    cities: {
      "Indore": { lat: 22.72, lon: 75.86 },
      "Bhopal": { lat: 23.26, lon: 77.41 },
      "Ujjain": { lat: 23.18, lon: 75.78 },
      "Gwalior": { lat: 26.22, lon: 78.18 },
      "Jabalpur": { lat: 23.18, lon: 79.99 },
      "Ratlam": { lat: 23.33, lon: 75.04 },
      "Dewas": { lat: 22.96, lon: 76.05 },
      "Neemuch": { lat: 24.46, lon: 74.87 },
    },
  },
  "Rajasthan": {
    lat: 26.91, lon: 75.79,
    cities: {
      "Jaipur": { lat: 26.91, lon: 75.79 },
      "Jodhpur": { lat: 26.24, lon: 73.02 },
      "Kota": { lat: 25.21, lon: 75.86 },
      "Ajmer": { lat: 26.45, lon: 74.64 },
      "Udaipur": { lat: 24.57, lon: 73.69 },
    },
  },
  "Maharashtra": {
    lat: 19.08, lon: 72.88,
    cities: {
      "Pune": { lat: 18.52, lon: 73.86 },
      "Nashik": { lat: 20.01, lon: 73.78 },
      "Nagpur": { lat: 21.15, lon: 79.09 },
      "Sangli": { lat: 16.85, lon: 74.57 },
      "Solapur": { lat: 17.66, lon: 75.91 },
    },
  },
  "Uttar Pradesh": {
    lat: 26.85, lon: 80.95,
    cities: {
      "Lucknow": { lat: 26.85, lon: 80.95 },
      "Agra": { lat: 27.18, lon: 78.01 },
      "Kanpur": { lat: 26.45, lon: 80.33 },
      "Varanasi": { lat: 25.32, lon: 83.01 },
      "Meerut": { lat: 28.98, lon: 77.71 },
      "Bareilly": { lat: 28.37, lon: 79.43 },
    },
  },
  "Gujarat": {
    lat: 23.02, lon: 72.57,
    cities: {
      "Ahmedabad": { lat: 23.02, lon: 72.57 },
      "Rajkot": { lat: 22.30, lon: 70.80 },
      "Surat": { lat: 21.17, lon: 72.83 },
      "Junagadh": { lat: 21.52, lon: 70.46 },
      "Vadodara": { lat: 22.31, lon: 73.18 },
    },
  },
  "Punjab": {
    lat: 30.73, lon: 76.78,
    cities: {
      "Ludhiana": { lat: 30.90, lon: 75.86 },
      "Amritsar": { lat: 31.63, lon: 74.87 },
      "Jalandhar": { lat: 31.33, lon: 75.58 },
      "Patiala": { lat: 30.34, lon: 76.39 },
      "Bathinda": { lat: 30.21, lon: 74.95 },
      "Khanna": { lat: 30.70, lon: 76.22 },
    },
  },
  "Haryana": {
    lat: 29.06, lon: 76.09,
    cities: {
      "Karnal": { lat: 29.69, lon: 76.99 },
      "Hisar": { lat: 29.15, lon: 75.72 },
      "Sirsa": { lat: 29.53, lon: 75.03 },
      "Ambala": { lat: 30.38, lon: 76.78 },
      "Rohtak": { lat: 28.90, lon: 76.61 },
      "Panipat": { lat: 29.39, lon: 76.96 },
      "Sonipat": { lat: 28.99, lon: 77.02 },
      "Fatehabad": { lat: 29.52, lon: 75.45 },
    },
  },
  "Karnataka": {
    lat: 12.97, lon: 77.59,
    cities: {
      "Bengaluru": { lat: 12.97, lon: 77.59 },
      "Hubli": { lat: 15.36, lon: 75.12 },
      "Mysuru": { lat: 12.30, lon: 76.66 },
      "Davangere": { lat: 14.47, lon: 75.92 },
    },
  },
  "Tamil Nadu": {
    lat: 13.08, lon: 80.27,
    cities: {
      "Chennai": { lat: 13.08, lon: 80.27 },
      "Coimbatore": { lat: 11.01, lon: 76.96 },
      "Madurai": { lat: 9.93, lon: 78.12 },
      "Salem": { lat: 11.66, lon: 78.15 },
    },
  },
  "Andhra Pradesh": {
    lat: 17.39, lon: 78.49,
    cities: {
      "Hyderabad": { lat: 17.39, lon: 78.49 },
      "Warangal": { lat: 17.98, lon: 79.59 },
      "Guntur": { lat: 16.31, lon: 80.44 },
      "Kurnool": { lat: 15.83, lon: 78.04 },
    },
  },
  "West Bengal": {
    lat: 22.57, lon: 88.36,
    cities: {
      "Kolkata": { lat: 22.57, lon: 88.36 },
      "Siliguri": { lat: 26.73, lon: 88.43 },
      "Burdwan": { lat: 23.23, lon: 87.87 },
    },
  },
  "Bihar": {
    lat: 25.61, lon: 85.14,
    cities: {
      "Patna": { lat: 25.61, lon: 85.14 },
      "Muzaffarpur": { lat: 26.12, lon: 85.39 },
      "Gaya": { lat: 24.80, lon: 85.01 },
      "Hajipur": { lat: 25.69, lon: 85.22 },
    },
  },
  
};

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
  const [gpsAvailable, setGpsAvailable] = useState(true);
  const isHindi = language === "hi";

  // Check if GPS is even possible
  useEffect(() => {
    if (typeof navigator !== "undefined" && !navigator.geolocation) {
      setGpsAvailable(false);
    }
    // Check permission status if API available
    if (typeof navigator !== "undefined" && navigator.permissions) {
      navigator.permissions.query({ name: "geolocation" }).then((result) => {
        if (result.state === "denied") {
          setGpsAvailable(false);
          setGpsError(
            isHindi
              ? "GPS की अनुमति बंद है। कृपया नीचे से अपना राज्य/शहर चुनें।"
              : "Location permission is blocked. Please select your state/city below."
          );
        }
      }).catch(() => {
        // permissions API not available, GPS may still work
      });
    }
  }, [isHindi]);

  if (!isOpen) return null;

  const states = Object.keys(LOCATIONS);

  const handleGps = () => {
    if (!navigator.geolocation) {
      setGpsAvailable(false);
      setGpsError(isHindi ? "GPS इस डिवाइस पर उपलब्ध नहीं है" : "GPS not available on this device");
      return;
    }
    setGpsLoading(true);
    setGpsError("");
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;

        // Reverse geocode GPS → state + city using Nominatim (same API as backend geocoding.py)
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
            // Nominatim returns state in address.state
            const rawState = addr.state || "";
            // Map to our LOCATIONS dictionary format (remove trailing "State" if present)
            const stateNames = Object.keys(LOCATIONS);
            const matchedState = stateNames.find(
              (s) => s.toLowerCase() === rawState.toLowerCase() ||
                     rawState.toLowerCase().includes(s.toLowerCase()) ||
                     s.toLowerCase().includes(rawState.toLowerCase())
            );
            detectedState = matchedState || rawState;
            // City: try city, town, county, district in priority order
            detectedCity = addr.city || addr.town || addr.county || addr.state_district || addr.village || "";
            if (detectedCity && detectedState) {
              locationLabel = `${detectedCity}, ${detectedState}`;
            } else if (detectedState) {
              locationLabel = detectedState;
            } else if (detectedCity) {
              locationLabel = detectedCity;
            }
          }
        } catch (e) {
          // Reverse geocoding failed — GPS still works, just without state/city auto-fill
          console.warn("Reverse geocoding failed:", e);
        }

        setGpsLoading(false);
        onSelectLocation({
          latitude: lat,
          longitude: lon,
          label: locationLabel,
          state: detectedState,
          city: detectedCity,
        });
        onClose();
      },
      (err) => {
        setGpsLoading(false);
        setGpsAvailable(false);
        if (err.code === 1) {
          setGpsError(isHindi
            ? "GPS की अनुमति नहीं दी गई। कृपया नीचे से अपना राज्य/शहर चुनें।"
            : "Location permission denied. Please select your state/city below.");
        } else {
          setGpsError(isHindi
            ? "GPS से लोकेशन नहीं मिल सका। कृपया नीचे से अपना राज्य/शहर चुनें।"
            : "Could not get GPS location. Please select your state/city below.");
        }
      },
      { enableHighAccuracy: false, timeout: 10000 }
    );
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

        {/* GPS option — only show if potentially available */}
        {gpsAvailable && (
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
        )}

        {/* GPS error/denial message */}
        {gpsError && (
          <div className="px-4 py-2.5 bg-amber-50 border-b border-amber-100 flex items-start gap-2">
            <span className="text-amber-500 text-sm mt-0.5">⚠️</span>
            <p className="text-xs text-amber-700">{gpsError}</p>
          </div>
        )}

        {/* State/City list */}
        <div className="overflow-y-auto max-h-[60vh] p-2">
          {!selectedState ? (
            // Show states
            <div className="space-y-1">
              <p className="text-xs text-gray-400 px-2 py-1 font-medium uppercase tracking-wide">
                {isHindi ? "👇 अपना राज्य चुनें" : "👇 Select Your State"}
              </p>
              {states.map((state) => {
                const cityCount = Object.keys(LOCATIONS[state].cities).length;
                return (
                  <button
                    key={state}
                    onClick={() => setSelectedState(state)}
                    className="w-full text-left px-3 py-2.5 rounded-lg hover:bg-green-50 transition-colors flex items-center justify-between group"
                  >
                    <div>
                      <span className="text-sm font-medium text-gray-700 group-hover:text-[#2d6a4f]">{state}</span>
                      <span className="text-xs text-gray-400 ml-2">
                        {cityCount} {isHindi ? "शहर" : (cityCount === 1 ? "city" : "cities")}
                      </span>
                    </div>
                    <span className="text-gray-300 group-hover:text-[#2d6a4f] text-xs">&#9654;</span>
                  </button>
                );
              })}
            </div>
          ) : (
            // Show cities for selected state
            <div className="space-y-1">
              <button
                onClick={() => setSelectedState("")}
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
                  const loc = LOCATIONS[selectedState];
                  onSelectLocation({
                    latitude: loc.lat,
                    longitude: loc.lon,
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

              {/* City options */}
              {Object.entries(LOCATIONS[selectedState].cities).map(([city, coords]) => (
                <button
                  key={city}
                  onClick={() => {
                    onSelectLocation({
                      latitude: coords.lat,
                      longitude: coords.lon,
                      label: `${city}, ${selectedState}`,
                      state: selectedState,
                      city,
                    });
                    onClose();
                  }}
                  className="w-full text-left px-3 py-2.5 rounded-lg hover:bg-green-50 transition-colors flex items-center gap-2 group"
                >
                  <span className="text-gray-300 group-hover:text-[#2d6a4f]">📌</span>
                  <span className="text-sm text-gray-700 group-hover:text-[#2d6a4f]">{city}</span>
                </button>
              ))}
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

export { LOCATIONS };
