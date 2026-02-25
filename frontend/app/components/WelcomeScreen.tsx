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
      <div className="grid grid-cols-2 gap-3 w-full max-w-sm mb-6">
        <FeatureCard
          icon="💰"
          title={isHindi ? "लाइव भाव" : "Live Prices"}
          desc={isHindi ? "500+ मंडियों के भाव" : "Prices from 500+ mandis"}
          onClick={() =>
            onQuickAction(
              isHindi
                ? "इंदौर मंडी में सोयाबीन का आज का भाव बताओ"
                : "What is soyabean price in Indore today?"
            )
          }
        />
        <FeatureCard
          icon="📍"
          title={isHindi ? "सबसे अच्छी मंडी" : "Best Mandi"}
          desc={isHindi ? "Transport cost समेत" : "Including transport cost"}
          onClick={() =>
            onQuickAction(
              isHindi
                ? "इंदौर के पास गेहूं के लिए सबसे अच्छी मंडी कौन सी है?"
                : "Which is the best mandi for wheat near Indore?"
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
                ? "क्या अभी प्याज बेचना चाहिए?"
                : "Should I sell onion now or wait?"
            )
          }
        />
        <FeatureCard
          icon="📋"
          title={isHindi ? "मूल्य पत्र" : "Price Brief"}
          desc={isHindi ? "मंडी में negotiate करें" : "Negotiate at mandi"}
          onClick={() =>
            onQuickAction(
              isHindi
                ? "गेहूं का price brief बनाओ इंदौर मंडी के लिए"
                : "Generate price brief for wheat at Indore mandi"
            )
          }
        />
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
        Powered by Amazon Bedrock Agents + Claude AI
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
