"use client";

import { useState } from "react";
import type { ChatMessage, AgentTraceStep } from "../lib/api";
import { isTTSSupported, speakText, stopSpeaking } from "../lib/tts";

interface ChatBubbleProps {
  message: ChatMessage;
  language: string;
  speakingMessageId: string | null;
  onSpeakingChange: (messageId: string | null) => void;
}

export default function ChatBubble({
  message,
  language,
  speakingMessageId,
  onSpeakingChange,
}: ChatBubbleProps) {
  const [showTrace, setShowTrace] = useState(false);
  const isUser = message.role === "user";
  const isSpeakingThis = !isUser && speakingMessageId === message.id;
  const canSpeak = !isUser && isTTSSupported();

  const handleSpeakClick = () => {
    if (!canSpeak) return;

    if (isSpeakingThis) {
      stopSpeaking();
      onSpeakingChange(null);
      return;
    }

    onSpeakingChange(message.id);
    speakText({
      text: message.content,
      lang: language === "hi" ? "hi-IN" : "en-IN",
      onEnd: () => onSpeakingChange(null),
      onError: () => onSpeakingChange(null),
    });
  };

  return (
    <div
      className={`message-enter flex ${isUser ? "justify-end" : "justify-start"} mb-3 px-3`}
    >
      <div className={`max-w-[85%] ${isUser ? "order-1" : "order-1"}`}>
        {/* Avatar for bot */}
        {!isUser && (
          <div className="flex items-center justify-between gap-2 mb-1">
            <div className="flex items-center gap-2">
              <span className="text-sm">🌾</span>
              <span className="text-xs font-medium text-[#2d6a4f]">MandiMitra</span>
            </div>

            <button
              type="button"
              onClick={handleSpeakClick}
              disabled={!canSpeak}
              aria-label={
                isSpeakingThis
                  ? language === "hi"
                    ? "रोकें (Stop speaking)"
                    : "Stop speaking"
                  : language === "hi"
                    ? "सुनाएँ (Speak aloud)"
                    : "Speak aloud"
              }
              className={`text-xs px-2 py-1 rounded-full border transition-colors ${
                canSpeak
                  ? isSpeakingThis
                    ? "bg-[#2d6a4f] text-white border-[#2d6a4f]"
                    : "bg-white text-[#2d6a4f] border-[#2d6a4f]/30 hover:bg-[#2d6a4f]/5"
                  : "bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed"
              }`}
              title={
                canSpeak
                  ? isSpeakingThis
                    ? language === "hi"
                      ? "रोकें"
                      : "Stop"
                    : language === "hi"
                      ? "सुनाएँ"
                      : "Speak"
                  : language === "hi"
                    ? "यह ब्राउज़र Text-to-Speech सपोर्ट नहीं करता"
                    : "Text-to-Speech not supported in this browser"
              }
            >
              {isSpeakingThis ? "⏹" : "🔊"}
            </button>
          </div>
        )}

        {/* Message bubble */}
        <div
          className={`rounded-2xl px-4 py-2.5 text-[15px] leading-relaxed shadow-sm ${
            isUser
              ? "bg-[#2d6a4f] text-white rounded-br-sm"
              : "bg-white text-gray-800 rounded-bl-sm border border-gray-100"
          }`}
        >
          {/* Render message with line breaks */}
          {message.content.split("\n").map((line, i) => (
            <span key={i}>
              {line}
              {i < message.content.split("\n").length - 1 && <br />}
            </span>
          ))}
        </div>

        {/* Timestamp */}
        <div
          className={`text-[10px] text-gray-400 mt-1 ${
            isUser ? "text-right" : "text-left"
          }`}
        >
          {message.timestamp.toLocaleTimeString("en-IN", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>

        {/* Agent Trace (expandable) */}
        {!isUser && message.agentTrace && message.agentTrace.length > 0 && (
          <div className="mt-2">
            <button
              onClick={() => setShowTrace(!showTrace)}
              className="text-xs text-[#2d6a4f] hover:text-[#40916c] font-medium flex items-center gap-1"
            >
              <span className={`transform transition-transform ${showTrace ? "rotate-90" : ""}`}>
                ▶
              </span>
              How MandiMitra Reasoned ({message.agentTrace.length} steps)
            </button>

            {showTrace && (
              <div className="mt-2 bg-gray-50 rounded-lg p-3 border border-gray-200 text-xs">
                {message.agentTrace.map((step, i) => (
                  <TraceStep key={i} step={step} index={i} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function TraceStep({ step, index }: { step: AgentTraceStep; index: number }) {
  const icons: Record<string, string> = {
    preprocessing: "🧠",
    reasoning: "💭",
    tool_call: "🔧",
    observation: "📊",
  };

  return (
    <div className="flex items-start gap-2 py-1.5 border-b border-gray-100 last:border-0">
      <span className="text-sm">{icons[step.type] || "📋"}</span>
      <div>
        <span className="font-medium text-gray-700">
          Step {index + 1}: {step.step}
        </span>
        {step.output && (
          <p className="text-gray-500 mt-0.5 line-clamp-2">{step.output}</p>
        )}
        {step.input != null && typeof step.input === "object" ? (
          <p className="text-gray-400 mt-0.5">
            {String(JSON.stringify(step.input)).slice(0, 100)}
            {String(JSON.stringify(step.input)).length > 100 ? "..." : ""}
          </p>
        ) : null}
      </div>
    </div>
  );
}
