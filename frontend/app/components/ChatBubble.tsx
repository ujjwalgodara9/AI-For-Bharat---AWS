"use client";

import { useState } from "react";
import type { ChatMessage, AgentTraceStep } from "../lib/api";

interface ChatBubbleProps {
  message: ChatMessage;
}

export default function ChatBubble({ message }: ChatBubbleProps) {
  const [showTrace, setShowTrace] = useState(false);
  const isUser = message.role === "user";

  const handleWhatsAppShare = () => {
    const text = encodeURIComponent(
      `${message.content}\n\n— MandiMitra (AI Mandi Assistant)`
    );
    window.open(`https://wa.me/?text=${text}`, "_blank");
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
  };

  return (
    <div
      className={`message-enter flex ${isUser ? "justify-end" : "justify-start"} mb-3 px-3`}
    >
      <div className={`max-w-[85%] ${isUser ? "order-1" : "order-1"}`}>
        {/* Avatar for bot */}
        {!isUser && (
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm">🌾</span>
            <span className="text-xs font-medium text-[#2d6a4f]">MandiMitra</span>
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

        {/* Action buttons for bot messages */}
        {!isUser && (
          <div className="flex items-center gap-2 mt-1.5">
            {/* Timestamp */}
            <span className="text-[10px] text-gray-400">
              {message.timestamp.toLocaleTimeString("en-IN", {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>

            {/* Copy button */}
            <button
              onClick={handleCopy}
              className="text-[10px] text-gray-400 hover:text-gray-600 transition-colors"
              title="Copy"
            >
              Copy
            </button>

            {/* WhatsApp share */}
            <button
              onClick={handleWhatsAppShare}
              className="flex items-center gap-0.5 text-[10px] text-green-600 hover:text-green-700 font-medium transition-colors"
              title="Share on WhatsApp"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
              </svg>
              Share
            </button>
          </div>
        )}

        {/* Timestamp for user messages */}
        {isUser && (
          <div className="text-[10px] text-gray-400 mt-1 text-right">
            {message.timestamp.toLocaleTimeString("en-IN", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </div>
        )}

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
