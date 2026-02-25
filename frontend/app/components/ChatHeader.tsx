"use client";

interface ChatHeaderProps {
  language: string;
  onLanguageChange: (lang: string) => void;
}

export default function ChatHeader({ language, onLanguageChange }: ChatHeaderProps) {
  return (
    <header className="bg-gradient-to-r from-[#2d6a4f] to-[#40916c] text-white px-4 py-3 flex items-center justify-between shadow-lg">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center text-xl">
          🌾
        </div>
        <div>
          <h1 className="text-lg font-bold leading-tight">MandiMitra</h1>
          <p className="text-xs text-green-200 leading-tight">
            {language === "hi" ? "किसान का साथी — AI मंडी सहायक" : "Farmer's Companion — AI Mandi Assistant"}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {/* Language Toggle */}
        <button
          onClick={() => onLanguageChange(language === "hi" ? "en" : "hi")}
          className="bg-white/20 hover:bg-white/30 transition-colors px-3 py-1.5 rounded-full text-sm font-medium"
        >
          {language === "hi" ? "EN" : "हिं"}
        </button>

        {/* Online indicator */}
        <div className="flex items-center gap-1 text-xs text-green-200">
          <span className="w-2 h-2 bg-green-300 rounded-full animate-pulse" />
          Live
        </div>
      </div>
    </header>
  );
}
