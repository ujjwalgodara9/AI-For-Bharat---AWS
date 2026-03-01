"use client";

import { useState } from "react";

interface QuickActionsProps {
  language: string;
  onAction: (message: string) => void;
  disabled: boolean;
  locationState?: string;
  locationCity?: string;
}

const COMMODITY_OPTIONS = [
  { en: "Wheat", hi: "गेहूं" },
  { en: "Soyabean", hi: "सोयाबीन" },
  { en: "Onion", hi: "प्याज" },
  { en: "Tomato", hi: "टमाटर" },
  { en: "Potato", hi: "आलू" },
  { en: "Chana", hi: "चना" },
  { en: "Mustard", hi: "सरसों" },
  { en: "Cotton", hi: "कपास" },
  { en: "Maize", hi: "मक्का" },
  { en: "Rice", hi: "धान" },
];

type PickerMode = "price" | "bestMandi" | "sellHold" | null;

export default function QuickActions({ language, onAction, disabled, locationState, locationCity }: QuickActionsProps) {
  const isHindi = language === "hi";
  const loc = locationCity || locationState || "";
  const hasLoc = !!loc;
  const [pickerMode, setPickerMode] = useState<PickerMode>(null);

  const handleCropSelect = (commodity: { en: string; hi: string }) => {
    const name = isHindi ? commodity.hi : commodity.en;
    const mode = pickerMode;
    setPickerMode(null);

    switch (mode) {
      case "price":
        onAction(
          isHindi
            ? (hasLoc ? `${name} का भाव बताओ ${loc} में` : `${name} का भाव बताओ`)
            : (hasLoc ? `What is the current ${name} price in ${loc}?` : `What is the current ${name} price?`)
        );
        break;
      case "bestMandi":
        onAction(
          isHindi
            ? (hasLoc ? `${loc} के पास ${name} बेचने के लिए सबसे अच्छी मंडी कौन सी है?` : `${name} बेचने के लिए सबसे अच्छी मंडी कौन सी है?`)
            : (hasLoc ? `Which mandi near ${loc} has the best ${name} price?` : `Which mandi has the best ${name} price?`)
        );
        break;
      case "sellHold":
        onAction(
          isHindi
            ? `क्या अभी ${name} बेचना चाहिए या कुछ दिन रुकना चाहिए? शेल्फ लाइफ और कितने दिन रुक सकते हैं यह भी बताओ।`
            : `Should I sell my ${name} now or wait? Also tell me the shelf life and recommended hold time.`
        );
        break;
    }
  };

  const togglePicker = (mode: PickerMode) => {
    setPickerMode(pickerMode === mode ? null : mode);
  };

  const pickerLabel = (): string => {
    switch (pickerMode) {
      case "price": return isHindi ? "किस फसल का भाव देखना है?" : "Which crop's price?";
      case "bestMandi": return isHindi ? "किस फसल के लिए मंडी खोजें?" : "Find best mandi for which crop?";
      case "sellHold": return isHindi ? "किस फसल के बारे में सलाह चाहिए?" : "Get sell/hold advice for which crop?";
      default: return "";
    }
  };

  return (
    <div className="px-4 py-2">
      {/* Commodity picker */}
      {pickerMode && (
        <div className="mb-2 p-3 bg-white rounded-xl border border-[#2d6a4f]/20 shadow-sm animate-in">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-gray-500 font-medium">
              {pickerLabel()}
            </p>
            <button
              onClick={() => setPickerMode(null)}
              className="text-gray-400 hover:text-gray-600 text-sm"
            >
              ✕
            </button>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {COMMODITY_OPTIONS.map((c) => (
              <button
                key={c.en}
                onClick={() => handleCropSelect(c)}
                className="px-2.5 py-1.5 text-xs rounded-full border border-[#2d6a4f]/20 text-[#2d6a4f] hover:bg-[#2d6a4f] hover:text-white transition-all"
              >
                {isHindi ? c.hi : c.en}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex flex-wrap gap-2">
        <ActionButton
          icon="💰"
          label={isHindi ? "भाव देखो" : "Check Price"}
          onClick={() => togglePicker("price")}
          active={pickerMode === "price"}
          disabled={disabled}
        />
        <ActionButton
          icon="📍"
          label={isHindi ? "कहाँ बेचूं?" : "Best Mandi"}
          onClick={() => togglePicker("bestMandi")}
          active={pickerMode === "bestMandi"}
          disabled={disabled}
        />
        <ActionButton
          icon="⏳"
          label={isHindi ? "बेचूं या रुकूं?" : "Sell or Hold?"}
          onClick={() => togglePicker("sellHold")}
          active={pickerMode === "sellHold"}
          disabled={disabled}
        />
        <ActionButton
          icon="🌤️"
          label={isHindi ? "मौसम" : "Weather"}
          onClick={() => onAction(
            isHindi
              ? (hasLoc ? `${loc} में अगले 5 दिन मौसम कैसा रहेगा? मंडी जाने में कोई दिक्कत?` : "मौसम कैसा रहेगा अगले 5 दिन?")
              : (hasLoc ? `What's the weather forecast for ${loc} for the next 5 days?` : "What's the weather forecast for the next 5 days?")
          )}
          disabled={disabled}
        />
        <ActionButton
          icon="🏪"
          label={isHindi ? "मंडी जानकारी" : "Mandi Info"}
          onClick={() => onAction(
            isHindi
              ? (hasLoc ? `${loc} मंडी की पूरी जानकारी दो — कौन सी फसलें बिक रही हैं, भाव, और Agmarknet विवरण` : "मंडी की जानकारी दो — कौन सी फसलें बिक रही हैं और भाव क्या हैं?")
              : (hasLoc ? `Give me full information about ${loc} mandi — all commodities, prices, and Agmarknet details` : "Give me mandi information — what commodities are available and their prices?")
          )}
          disabled={disabled}
        />
      </div>
    </div>
  );
}

function ActionButton({
  icon,
  label,
  onClick,
  active,
  disabled,
}: {
  icon: string;
  label: string;
  onClick: () => void;
  active?: boolean;
  disabled: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center gap-1.5 rounded-full px-3.5 py-2 text-sm font-medium transition-all disabled:opacity-50 shadow-sm ${
        active
          ? "bg-[#2d6a4f] text-white border border-[#2d6a4f]"
          : "bg-white border border-[#2d6a4f]/20 text-[#2d6a4f] hover:bg-[#2d6a4f]/5 hover:border-[#2d6a4f]/40"
      }`}
    >
      <span>{icon}</span>
      <span>{label}</span>
    </button>
  );
}
