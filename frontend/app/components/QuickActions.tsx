"use client";

interface QuickActionsProps {
  language: string;
  onAction: (message: string) => void;
  disabled: boolean;
  locationState?: string;
  locationCity?: string;
}

export default function QuickActions({ language, onAction, disabled, locationState, locationCity }: QuickActionsProps) {
  const isHindi = language === "hi";
  const loc = locationCity || locationState || "";
  const hasLoc = !!loc;

  const actions = isHindi
    ? [
        { label: "भाव देखो", icon: "💰", query: hasLoc ? `सोयाबीन का भाव बताओ ${loc} में` : "सोयाबीन का भाव बताओ" },
        { label: "कहाँ बेचूं?", icon: "📍", query: hasLoc ? `${loc} के पास 20 क्विंटल गेहूं बेचने के लिए सबसे अच्छी मंडी?` : "मेरे पास 20 क्विंटल गेहूं है, सबसे अच्छी मंडी कौन सी है?" },
        { label: "बेचूं या रुकूं?", icon: "⏳", query: "क्या अभी सोयाबीन बेचना चाहिए या कुछ दिन रुकना चाहिए?" },
        { label: "मंडी के भाव", icon: "🏪", query: hasLoc ? `${loc} की मंडी में सब फसलों के भाव बताओ` : "मेरे पास की मंडी में सब फसलों के भाव बताओ" },
      ]
    : [
        { label: "Check Price", icon: "💰", query: hasLoc ? `What is the current soyabean price in ${loc}?` : "What is the current soyabean price?" },
        { label: "Best Mandi", icon: "📍", query: hasLoc ? `Which mandi near ${loc} has the best wheat price? I have 20 quintals.` : "Which mandi has the best wheat price? I have 20 quintals." },
        { label: "Sell or Hold?", icon: "⏳", query: "Should I sell my soyabean now or wait a few days?" },
        { label: "Mandi Prices", icon: "🏪", query: hasLoc ? `Show all commodity prices at ${loc} mandi` : "Show all commodity prices at the nearest mandi" },
      ];

  return (
    <div className="flex flex-wrap gap-2 px-4 py-3">
      {actions.map((action) => (
        <button
          key={action.label}
          onClick={() => onAction(action.query)}
          disabled={disabled}
          className="flex items-center gap-1.5 bg-white border border-[#2d6a4f]/20 text-[#2d6a4f] rounded-full px-3.5 py-2 text-sm font-medium hover:bg-[#2d6a4f]/5 hover:border-[#2d6a4f]/40 transition-all disabled:opacity-50 shadow-sm"
        >
          <span>{action.icon}</span>
          <span>{action.label}</span>
        </button>
      ))}
    </div>
  );
}
