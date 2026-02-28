"use client";

import { useState } from "react";

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
    },
  },
  "Gujarat": {
    lat: 23.02, lon: 72.57,
    cities: {
      "Ahmedabad": { lat: 23.02, lon: 72.57 },
      "Rajkot": { lat: 22.30, lon: 70.80 },
      "Surat": { lat: 21.17, lon: 72.83 },
      "Junagadh": { lat: 21.52, lon: 70.46 },
    },
  },
  "Punjab": {
    lat: 30.73, lon: 76.78,
    cities: {
      "Ludhiana": { lat: 30.90, lon: 75.86 },
      "Amritsar": { lat: 31.63, lon: 74.87 },
      "Jalandhar": { lat: 31.33, lon: 75.58 },
      "Patiala": { lat: 30.34, lon: 76.39 },
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
    },
  },
  "Haryana": {
    lat: 29.06, lon: 76.09,
    cities: {
      "Karnal": { lat: 29.69, lon: 76.99 },
      "Hisar": { lat: 29.15, lon: 75.72 },
      "Sirsa": { lat: 29.53, lon: 75.03 },
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
  const isHindi = language === "hi";

  if (!isOpen) return null;

  const states = Object.keys(LOCATIONS);

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end sm:items-center justify-center">
      <div className="bg-white rounded-t-2xl sm:rounded-2xl w-full max-w-lg max-h-[80vh] overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="bg-gradient-to-r from-[#2d6a4f] to-[#40916c] text-white px-4 py-3 flex items-center justify-between">
          <h3 className="font-bold">
            {isHindi ? "अपनी लोकेशन चुनें" : "Select Your Location"}
          </h3>
          <button onClick={onClose} className="text-white/80 hover:text-white text-xl">
            &times;
          </button>
        </div>

        {/* GPS option */}
        <button
          onClick={() => {
            if (navigator.geolocation) {
              navigator.geolocation.getCurrentPosition(
                (pos) => {
                  onSelectLocation({
                    latitude: pos.coords.latitude,
                    longitude: pos.coords.longitude,
                    label: isHindi ? "GPS लोकेशन" : "GPS Location",
                    state: "",
                  });
                  onClose();
                },
                () => alert(isHindi ? "GPS उपलब्ध नहीं है" : "GPS not available"),
                { enableHighAccuracy: true, timeout: 10000 }
              );
            }
          }}
          className="w-full px-4 py-3 flex items-center gap-3 border-b hover:bg-green-50 transition-colors"
        >
          <span className="text-2xl">📡</span>
          <div className="text-left">
            <p className="font-semibold text-[#2d6a4f]">
              {isHindi ? "GPS से पता लगाएं" : "Detect via GPS"}
            </p>
            <p className="text-xs text-gray-500">
              {isHindi ? "अपना सटीक स्थान उपयोग करें" : "Use your exact location"}
            </p>
          </div>
        </button>

        {/* State/City list */}
        <div className="overflow-y-auto max-h-[60vh] p-2">
          {!selectedState ? (
            // Show states
            <div className="space-y-1">
              <p className="text-xs text-gray-400 px-2 py-1 font-medium uppercase">
                {isHindi ? "राज्य चुनें" : "Select State"}
              </p>
              {states.map((state) => (
                <button
                  key={state}
                  onClick={() => setSelectedState(state)}
                  className="w-full text-left px-3 py-2.5 rounded-lg hover:bg-green-50 transition-colors flex items-center justify-between"
                >
                  <span className="text-sm font-medium text-gray-700">{state}</span>
                  <span className="text-gray-400 text-xs">&#9654;</span>
                </button>
              ))}
            </div>
          ) : (
            // Show cities for selected state
            <div className="space-y-1">
              <button
                onClick={() => setSelectedState("")}
                className="text-xs text-[#2d6a4f] px-2 py-1 font-medium flex items-center gap-1"
              >
                &#9664; {isHindi ? "वापस" : "Back"}
              </button>
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
                  {selectedState} ({isHindi ? "पूरा राज्य" : "Entire state"})
                </span>
              </button>
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
                  className="w-full text-left px-3 py-2.5 rounded-lg hover:bg-green-50 transition-colors"
                >
                  <span className="text-sm text-gray-700">{city}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export { LOCATIONS };
