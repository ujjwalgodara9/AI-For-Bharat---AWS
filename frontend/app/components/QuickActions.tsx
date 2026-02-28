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

interface ActionItem {
  label: string;
  icon: string;
  query?: string;
  isSellHold?: boolean;
}

export default function QuickActions({ language, onAction, disabled, locationState, locationCity }: QuickActionsProps) {
  const isHindi = language === "hi";
  const loc = locationCity || locationState || "";
  const hasLoc = !!loc;
  const [showCommodityPicker, setShowCommodityPicker] = useState(false);

  const handleSellHold = (commodity: { en: string; hi: string }) => {
    setShowCommodityPicker(false);
    const name = isHindi ? commodity.hi : commodity.en;
    const query = isHindi
      ? `क्या अभी ${name} बेचना चाहिए या कुछ दिन रुकना चाहिए? शेल्फ लाइफ और कितने दिन रुक सकते हैं यह भी बताओ।`
      : `Should I sell my ${name} now or wait? Also tell me the shelf life and recommended hold time.`;
    onAction(query);
  };

  const actions: ActionItem[] = isHindi
    ? [
        { label: "भाव देखो", icon: "💰", query: hasLoc ? `सोयाबीन का भाव बताओ ${loc} में` : "सोयाबीन का भाव बताओ" },
        { label: "कहाँ बेचूं?", icon: "📍", query: hasLoc ? `${loc} के पास 20 क्विंटल गेहूं बेचने के लिए सबसे अच्छी मंडी?` : "मेरे पास 20 क्विंटल गेहूं है, सबसे अच्छी मंडी कौन सी है?" },
        { label: "बेचूं या रुकूं?", icon: "⏳", isSellHold: true },
        { label: "मौसम", icon: "🌤️", query: hasLoc ? `${loc} में अगले 5 दिन मौसम कैसा रहेगा? मंडी जाने में कोई दिक्कत?` : "मौसम कैसा रहेगा अगले 5 दिन?" },
        { label: "मंडी जानकारी", icon: "🏪", query: hasLoc ? `${loc} मंडी की पूरी जानकारी दो — कौन सी फसलें बिक रही हैं, भाव, और Agmarknet विवरण` : "मंडी की जानकारी दो — कौन सी फसलें बिक रही हैं और भाव क्या हैं?" },
      ]
    : [
        { label: "Check Price", icon: "💰", query: hasLoc ? `What is the current soyabean price in ${loc}?` : "What is the current soyabean price?" },
        { label: "Best Mandi", icon: "📍", query: hasLoc ? `Which mandi near ${loc} has the best wheat price? I have 20 quintals.` : "Which mandi has the best wheat price? I have 20 quintals." },
        { label: "Sell or Hold?", icon: "⏳", isSellHold: true },
        { label: "Weather", icon: "🌤️", query: hasLoc ? `What's the weather forecast for ${loc} for the next 5 days? Is it safe to go to mandi?` : "What's the weather forecast for the next 5 days?" },
        { label: "Mandi Info", icon: "🏪", query: hasLoc ? `Give me full information about ${loc} mandi — what commodities are traded, prices, and Agmarknet details` : "Give me mandi information — what commodities are available and their prices?" },
      ];

  return (
    <div className="px-4 py-2">
      {/* Commodity picker for Sell/Hold */}
      {showCommodityPicker && (
        <div className="mb-2 p-3 bg-white rounded-xl border border-[#2d6a4f]/20 shadow-sm">
          <p className="text-xs text-gray-500 mb-2 font-medium">
            {isHindi ? "कौन सी फसल के बारे में जानना है?" : "Which commodity?"}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {COMMODITY_OPTIONS.map((c) => (
              <button
                key={c.en}
                onClick={() => handleSellHold(c)}
                className="px-2.5 py-1 text-xs rounded-full border border-[#2d6a4f]/20 text-[#2d6a4f] hover:bg-[#2d6a4f]/10 transition-all"
              >
                {isHindi ? c.hi : c.en}
              </button>
            ))}
            <button
              onClick={() => setShowCommodityPicker(false)}
              className="px-2.5 py-1 text-xs rounded-full border border-gray-200 text-gray-400 hover:bg-gray-50"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex flex-wrap gap-2">
        {actions.map((action) => (
          <button
            key={action.label}
            onClick={() => {
              if (action.isSellHold) {
                setShowCommodityPicker(!showCommodityPicker);
              } else if (action.query) {
                onAction(action.query);
              }
            }}
            disabled={disabled}
            className="flex items-center gap-1.5 bg-white border border-[#2d6a4f]/20 text-[#2d6a4f] rounded-full px-3.5 py-2 text-sm font-medium hover:bg-[#2d6a4f]/5 hover:border-[#2d6a4f]/40 transition-all disabled:opacity-50 shadow-sm"
          >
            <span>{action.icon}</span>
            <span>{action.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
