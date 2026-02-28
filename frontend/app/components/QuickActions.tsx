"use client";

interface QuickActionsProps {
  language: string;
  onAction: (message: string) => void;
  disabled: boolean;
}

const ACTIONS_HI = [
  { label: "भाव देखो", icon: "💰", query: "सोयाबीन का भाव बताओ" },
  { label: "कहाँ बेचूं?", icon: "📍", query: "मेरे पास 20 क्विंटल गेहूं है, सबसे अच्छी मंडी कौन सी है?" },
  { label: "बेचूं या रुकूं?", icon: "⏳", query: "क्या अभी सोयाबीन बेचना चाहिए या कुछ दिन रुकना चाहिए?" },
  { label: "मंडी के भाव", icon: "🏪", query: "इंदौर मंडी में सब फसलों के भाव बताओ" },
];

const ACTIONS_EN = [
  { label: "Check Price", icon: "💰", query: "What is the current soyabean price?" },
  { label: "Best Mandi", icon: "📍", query: "Which mandi has the best wheat price? I have 20 quintals." },
  { label: "Sell or Hold?", icon: "⏳", query: "Should I sell my soyabean now or wait a few days?" },
  { label: "Mandi Prices", icon: "🏪", query: "Show all commodity prices at Indore mandi" },
];

export default function QuickActions({ language, onAction, disabled }: QuickActionsProps) {
  const actions = language === "hi" ? ACTIONS_HI : ACTIONS_EN;

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
