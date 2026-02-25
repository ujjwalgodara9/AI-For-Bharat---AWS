"use client";

export default function TypingIndicator() {
  return (
    <div className="flex justify-start mb-3 px-3 message-enter">
      <div className="max-w-[85%]">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm">🌾</span>
          <span className="text-xs font-medium text-[#2d6a4f]">MandiMitra</span>
        </div>
        <div className="bg-white rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm border border-gray-100">
          <div className="flex gap-1.5 items-center">
            <span className="typing-dot w-2 h-2 bg-[#2d6a4f] rounded-full inline-block" />
            <span className="typing-dot w-2 h-2 bg-[#2d6a4f] rounded-full inline-block" />
            <span className="typing-dot w-2 h-2 bg-[#2d6a4f] rounded-full inline-block" />
            <span className="text-xs text-gray-400 ml-2">सोच रहा हूँ...</span>
          </div>
        </div>
      </div>
    </div>
  );
}
