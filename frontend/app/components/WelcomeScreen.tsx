"use client";

import { useState } from "react";

interface WelcomeScreenProps {
  language: string;
  onQuickAction: (message: string) => void;
  locationState?: string;
  locationCity?: string;
  locationLabel?: string;
}

const CROP_OPTIONS = [
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
  { en: "Garlic", hi: "लहसुन" },
  { en: "Bajra", hi: "बाजरा" },
];

export default function WelcomeScreen({ language, onQuickAction, locationState, locationCity, locationLabel }: WelcomeScreenProps) {
  const isHindi = language === "hi";
  const loc = locationCity || locationState || "";
  const hasLocation = !!loc;

  // Which feature card's crop picker is active
  const [activePicker, setActivePicker] = useState<string | null>(null);

  const handleCropSelect = (card: string, crop: { en: string; hi: string }) => {
    const name = isHindi ? crop.hi : crop.en;
    setActivePicker(null);

    switch (card) {
      case "price":
        onQuickAction(
          isHindi
            ? (hasLocation ? `${name} का भाव बताओ ${loc} में` : `${name} का भाव बताओ`)
            : (hasLocation ? `What is the current ${name} price in ${loc}?` : `What is the current ${name} price?`)
        );
        break;
      case "bestMandi":
        onQuickAction(
          isHindi
            ? (hasLocation ? `${loc} के पास ${name} के लिए सबसे अच्छी मंडी कौन सी है?` : `${name} के लिए सबसे अच्छी मंडी कौन सी है?`)
            : (hasLocation ? `Which mandi near ${loc} has the best ${name} price?` : `Which mandi has the best ${name} price?`)
        );
        break;
      case "sellHold":
        onQuickAction(
          isHindi
            ? `क्या अभी ${name} बेचना चाहिए या कुछ दिन रुकना चाहिए? शेल्फ लाइफ और कितने दिन रुक सकते हैं यह भी बताओ।`
            : `Should I sell my ${name} now or wait? Also tell me the shelf life and recommended hold time.`
        );
        break;
      case "priceBrief":
        onQuickAction(
          isHindi
            ? (hasLocation ? `${loc} में ${name} का price brief बनाओ negotiation के लिए` : `${name} का price brief बनाओ negotiation के लिए`)
            : (hasLocation ? `Generate a price brief for ${name} in ${loc}` : `Generate a price brief for ${name} for negotiation`)
        );
        break;
      case "msp":
        onQuickAction(
          isHindi ? `${name} का MSP क्या है?` : `What is the MSP for ${name}?`
        );
        break;
    }
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 py-8">
      {/* Logo */}
      <div className="w-20 h-20 bg-gradient-to-br from-[#2d6a4f] to-[#40916c] rounded-full flex items-center justify-center text-4xl shadow-lg mb-4">
        🌾
      </div>

      <h2 className="text-2xl font-bold text-[#2d6a4f] mb-1">MandiMitra</h2>
      <p className="text-sm text-gray-500 mb-2 text-center">
        {isHindi
          ? "AI-संचालित मंडी बाज़ार बुद्धिमत्ता — किसानों के लिए"
          : "AI-powered Mandi Market Intelligence — for Farmers"}
      </p>

      {/* Show selected location */}
      {locationLabel && (
        <p className="text-xs text-[#2d6a4f] bg-green-50 border border-green-200 rounded-full px-3 py-1 mb-4">
          📍 {locationLabel}
        </p>
      )}

      {/* Crop Picker Popup (shared for all cards) */}
      {activePicker && (
        <div className="w-full max-w-sm mb-3 p-3 bg-white rounded-xl border border-[#2d6a4f]/20 shadow-md animate-in">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-gray-500 font-medium">
              {isHindi ? "कौन सी फसल?" : "Which crop?"}
            </p>
            <button
              onClick={() => setActivePicker(null)}
              className="text-gray-400 hover:text-gray-600 text-sm"
            >
              ✕
            </button>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {CROP_OPTIONS.map((c) => (
              <button
                key={c.en}
                onClick={() => handleCropSelect(activePicker, c)}
                className="px-3 py-1.5 text-xs rounded-full border border-[#2d6a4f]/20 text-[#2d6a4f] hover:bg-[#2d6a4f] hover:text-white transition-all"
              >
                {isHindi ? c.hi : c.en}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Feature cards */}
      <div className="grid grid-cols-2 gap-3 w-full max-w-sm mb-4">
        <FeatureCard
          icon="💰"
          title={isHindi ? "लाइव भाव" : "Live Prices"}
          desc={isHindi ? (hasLocation ? `${loc} में भाव` : "किसी भी फसल का भाव") : (hasLocation ? `Prices in ${loc}` : "Check any crop price")}
          onClick={() => setActivePicker("price")}
          active={activePicker === "price"}
        />
        <FeatureCard
          icon="📍"
          title={isHindi ? "सबसे अच्छी मंडी" : "Best Mandi"}
          desc={isHindi ? (hasLocation ? `${loc} के पास` : "पास की मंडियां") : (hasLocation ? `Near ${loc}` : "Nearby mandis")}
          onClick={() => setActivePicker("bestMandi")}
          active={activePicker === "bestMandi"}
        />
        <FeatureCard
          icon="🏪"
          title={isHindi ? "मंडी जानकारी" : "Mandi Info"}
          desc={isHindi ? "मंडी प्रोफ़ाइल देखें" : "Market profile & details"}
          onClick={() =>
            onQuickAction(
              isHindi
                ? (hasLocation ? `${loc} मंडी की पूरी जानकारी दो — कौन सी फसलें बिक रही हैं, भाव, और Agmarknet विवरण` : "मंडी की जानकारी दो — कौन सी फसलें बिक रही हैं और भाव क्या हैं?")
                : (hasLocation ? `Give me full information about ${loc} mandi — what commodities are traded, prices, and Agmarknet details` : "Give me mandi information — what commodities are available and their prices?")
            )
          }
        />
        <FeatureCard
          icon="⏳"
          title={isHindi ? "बेचें या रुकें" : "Sell or Hold"}
          desc={isHindi ? "शेल्फ लाइफ + AI सलाह" : "Shelf life + AI advice"}
          onClick={() => setActivePicker("sellHold")}
          active={activePicker === "sellHold"}
        />
      </div>

      {/* Browse options */}
      <div className="w-full max-w-sm mb-4">
        <p className="text-xs text-gray-400 px-1 mb-2 font-medium">
          {isHindi ? "और जानें:" : "Explore:"}
        </p>
        <div className="flex flex-wrap gap-2">
          <QuickChip
            label={isHindi ? "📋 Price Brief" : "📋 Price Brief"}
            onClick={() => setActivePicker("priceBrief")}
          />
          <QuickChip
            label={isHindi ? "📊 MSP जानें" : "📊 Check MSP"}
            onClick={() => setActivePicker("msp")}
          />
          <QuickChip
            label={isHindi ? "🌤️ मौसम" : "🌤️ Weather"}
            onClick={() =>
              onQuickAction(
                isHindi
                  ? (hasLocation ? `${loc} में अगले 5 दिन मौसम कैसा रहेगा?` : "अगले 5 दिन मौसम कैसा रहेगा?")
                  : (hasLocation ? `What's the weather forecast for ${loc} for the next 5 days?` : "What's the weather forecast for the next 5 days?")
              )
            }
          />
          <QuickChip
            label={isHindi ? "🌾 फसलें देखें" : "🌾 View Crops"}
            onClick={() =>
              onQuickAction(
                isHindi
                  ? (locationState ? `${locationState} में कौन कौन सी फसलों का डाटा उपलब्ध है?` : "कौन कौन सी फसलों का डाटा उपलब्ध है?")
                  : (locationState ? `Which commodities data is available in ${locationState}?` : "Which commodities data is available?")
              )
            }
          />
          <QuickChip
            label={isHindi ? "🏪 मंडियां देखें" : "🏪 View Mandis"}
            onClick={() =>
              onQuickAction(
                isHindi
                  ? (locationState ? `${locationState} में कौन कौन सी मंडियों का डाटा है?` : "कौन कौन सी मंडियों का डाटा है?")
                  : (locationState ? `Which mandis are available in ${locationState}?` : "Which mandis data is available?")
              )
            }
          />
        </div>
      </div>

      {/* Data source badge */}
      <div className="flex items-center gap-2 text-xs text-gray-400">
        <span className="w-2 h-2 bg-green-400 rounded-full" />
        {isHindi
          ? "डेटा स्रोत: Agmarknet (data.gov.in) — प्रतिदिन शाम 5:30 बजे अपडेट"
          : "Data source: Agmarknet (data.gov.in) — Updated daily by 9:30 PM IST"}
      </div>

      {/* Powered by */}
      <p className="text-[10px] text-gray-300 mt-4">
        Powered by Amazon Bedrock Agents + Amazon Nova AI
      </p>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  desc,
  onClick,
  active,
}: {
  icon: string;
  title: string;
  desc: string;
  onClick: () => void;
  active?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`bg-white rounded-xl p-4 text-left shadow-sm border transition-all active:scale-[0.98] ${
        active
          ? "border-[#2d6a4f] shadow-md ring-1 ring-[#2d6a4f]/20"
          : "border-gray-100 hover:border-[#2d6a4f]/30 hover:shadow-md"
      }`}
    >
      <span className="text-2xl">{icon}</span>
      <h3 className="text-sm font-semibold text-gray-800 mt-2">{title}</h3>
      <p className="text-[11px] text-gray-400 mt-0.5">{desc}</p>
    </button>
  );
}

function QuickChip({
  label,
  onClick,
}: {
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="bg-white border border-gray-200 text-gray-600 rounded-full px-3 py-1.5 text-xs hover:border-[#2d6a4f]/30 hover:text-[#2d6a4f] transition-all active:scale-[0.97]"
    >
      {label}
    </button>
  );
}
