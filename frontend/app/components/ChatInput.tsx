"use client";

import { useState, useRef, useEffect } from "react";
import { isVoiceSupported, startListening, stopListening } from "../lib/voice";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled: boolean;
  language: string;
}

export default function ChatInput({ onSend, disabled, language }: ChatInputProps) {
  const [input, setInput] = useState("");
  const [isListening, setIsListening] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const voiceSupported = typeof window !== "undefined" && isVoiceSupported();
  const isHindi = language === "hi";

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 120) + "px";
    }
  }, [input]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInput("");
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleVoice = () => {
    if (isListening) {
      stopListening();
      setIsListening(false);
      return;
    }

    setIsListening(true);
    startListening(
      language,
      (transcript) => {
        setInput((prev) => (prev ? prev + " " + transcript : transcript));
        setIsListening(false);
      },
      (error) => {
        console.error(error);
        setIsListening(false);
      }
    );
  };

  return (
    <div className="border-t border-gray-200 bg-white px-3 py-2">
      {/* Voice hint when input is empty */}
      {voiceSupported && !input && !disabled && (
        <div className="text-center mb-1.5">
          <button
            onClick={handleVoice}
            className={`text-xs px-3 py-1 rounded-full transition-all ${
              isListening
                ? "bg-red-50 text-red-600 font-medium"
                : "text-gray-400 hover:text-[#2d6a4f] hover:bg-green-50"
            }`}
          >
            {isListening
              ? (isHindi ? "🎤 सुन रहे हैं... (रोकने के लिए दबाएं)" : "🎤 Listening... (tap to stop)")
              : (isHindi ? "🎤 हिंदी में बोलकर पूछें" : "🎤 Tap to speak in Hindi")}
          </button>
        </div>
      )}

      <div className="flex items-end gap-2 max-w-3xl mx-auto">
        {/* Voice button */}
        {voiceSupported && (
          <button
            onClick={handleVoice}
            disabled={disabled}
            className={`relative flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center transition-all ${
              isListening
                ? "bg-red-500 text-white voice-pulse shadow-lg shadow-red-200"
                : "bg-[#2d6a4f]/10 text-[#2d6a4f] hover:bg-[#2d6a4f]/20"
            } disabled:opacity-50`}
            title={isHindi ? "बोलकर पूछें" : "Speak your query"}
          >
            <span className="text-lg">🎤</span>
          </button>
        )}

        {/* Text input */}
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={
            isHindi
              ? "अपना सवाल पूछें..."
              : "Ask your question..."
          }
          rows={1}
          className="flex-1 resize-none rounded-2xl border border-gray-200 px-4 py-2.5 text-[15px] focus:outline-none focus:border-[#2d6a4f] focus:ring-1 focus:ring-[#2d6a4f]/20 disabled:opacity-50 bg-gray-50"
        />

        {/* Send button */}
        <button
          onClick={handleSend}
          disabled={disabled || !input.trim()}
          className="flex-shrink-0 w-10 h-10 bg-[#2d6a4f] text-white rounded-full flex items-center justify-center hover:bg-[#40916c] transition-colors disabled:opacity-50 disabled:hover:bg-[#2d6a4f]"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
          </svg>
        </button>
      </div>
    </div>
  );
}
