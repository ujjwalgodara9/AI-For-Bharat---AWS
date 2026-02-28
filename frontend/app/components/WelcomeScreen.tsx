"use client";

interface WelcomeScreenProps {
  language: string;
  onQuickAction: (message: string) => void;
}

export default function WelcomeScreen({ language, onQuickAction }: WelcomeScreenProps) {
  const isHindi = language === "hi";

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 py-8">
      {/* Logo */}
      <div className="w-20 h-20 bg-gradient-to-br from-[#2d6a4f] to-[#40916c] rounded-full flex items-center justify-center text-4xl shadow-lg mb-4">
        🌾
      </div>

      <h2 className="text-2xl font-bold text-[#2d6a4f] mb-1">MandiMitra</h2>
      <p className="text-sm text-gray-500 mb-6 text-center">
        {isHindi
          ? "AI-संचालित मंडी बाज़ार बुद्धिमत्ता — किसानों के लिए"
          : "AI-powered Mandi Market Intelligence — for Farmers"}
      </p>

      {/* Feature cards */}
      <div className="grid grid-cols-2 gap-3 w-full max-w-sm mb-4">
        <FeatureCard
          icon="💰"
          title={isHindi ? "लाइव भाव" : "Live Prices"}
          desc={isHindi ? "किसी भी फसल का भाव" : "Check any crop price"}
          onClick={() =>
            onQuickAction(
              isHindi
                ? "गेहूं का भाव बताओ मध्य प्रदेश में"
                : "What is wheat price in Madhya Pradesh?"
            )
          }
        />
        <FeatureCard
          icon="📍"
          title={isHindi ? "सबसे अच्छी मंडी" : "Best Mandi"}
          desc={isHindi ? "पास की मंडियां" : "Nearby mandis"}
          onClick={() =>
            onQuickAction(
              isHindi
                ? "मेरे पास की मंडियों में गेहूं कहाँ महंगा है?"
                : "Which nearby mandi has the best wheat price?"
            )
          }
        />
        <FeatureCard
          icon="🏪"
          title={isHindi ? "मंडी के सब भाव" : "All Mandi Prices"}
          desc={isHindi ? "एक मंडी की सब फसलें" : "All crops at a mandi"}
          onClick={() =>
            onQuickAction(
              isHindi
                ? "इंदौर मंडी में आज कौन कौन सी फसलों का भाव है?"
                : "What are all the commodity prices at Indore mandi today?"
            )
          }
        />
        <FeatureCard
          icon="⏳"
          title={isHindi ? "बेचें या रुकें" : "Sell or Hold"}
          desc={isHindi ? "AI सलाह" : "AI-powered advice"}
          onClick={() =>
            onQuickAction(
              isHindi
                ? "क्या अभी सोयाबीन बेचना चाहिए या रुकना चाहिए?"
                : "Should I sell soyabean now or wait?"
            )
          }
        />
      </div>

      {/* Browse options */}
      <div className="w-full max-w-sm mb-4">
        <p className="text-xs text-gray-400 px-1 mb-2 font-medium">
          {isHindi ? "या पूछें:" : "Or ask:"}
        </p>
        <div className="flex flex-wrap gap-2">
          <QuickChip
            label={isHindi ? "📋 Price Brief" : "📋 Price Brief"}
            onClick={() =>
              onQuickAction(
                isHindi
                  ? "गेहूं का price brief बनाओ negotiation के लिए"
                  : "Generate a price brief for wheat for negotiation"
              )
            }
          />
          <QuickChip
            label={isHindi ? "📊 MSP क्या है?" : "📊 What is MSP?"}
            onClick={() =>
              onQuickAction(
                isHindi
                  ? "गेहूं का MSP क्या है?"
                  : "What is the MSP for wheat?"
              )
            }
          />
          <QuickChip
            label={isHindi ? "🌾 कौन सी फसलें?" : "🌾 Which crops?"}
            onClick={() =>
              onQuickAction(
                isHindi
                  ? "कौन कौन सी फसलों का डाटा उपलब्ध है?"
                  : "Which commodities data is available?"
              )
            }
          />
          <QuickChip
            label={isHindi ? "🏪 कौन सी मंडियां?" : "🏪 Which mandis?"}
            onClick={() =>
              onQuickAction(
                isHindi
                  ? "कौन कौन सी मंडियों का डाटा है?"
                  : "Which mandis data is available?"
              )
            }
          />
        </div>
      </div>

      {/* Data source badge */}
      <div className="flex items-center gap-2 text-xs text-gray-400">
        <span className="w-2 h-2 bg-green-400 rounded-full" />
        {isHindi
          ? "डेटा स्रोत: Agmarknet (data.gov.in) — प्रतिदिन अपडेट"
          : "Data source: Agmarknet (data.gov.in) — Updated daily"}
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
}: {
  icon: string;
  title: string;
  desc: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="bg-white rounded-xl p-4 text-left shadow-sm border border-gray-100 hover:border-[#2d6a4f]/30 hover:shadow-md transition-all active:scale-[0.98]"
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
      className="bg-white border border-gray-200 text-gray-600 rounded-full px-3 py-1.5 text-xs hover:border-[#2d6a4f]/30 hover:text-[#2d6a4f] transition-all"
    >
      {label}
    </button>
  );
}
