"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ChatHeader from "./components/ChatHeader";
import ChatBubble from "./components/ChatBubble";
import ChatInput from "./components/ChatInput";
import QuickActions from "./components/QuickActions";
import TypingIndicator from "./components/TypingIndicator";
import WelcomeScreen from "./components/WelcomeScreen";
import LocationPicker from "./components/LocationPicker";
import type { ChatMessage, ChatResponse } from "./lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [language, setLanguage] = useState("hi");
  const [sessionId] = useState(
    () => `session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  );
  const [userLocation, setUserLocation] = useState<{
    latitude: number;
    longitude: number;
    accuracy?: number;
  } | null>(null);
  const [locationStatus, setLocationStatus] = useState<
    "pending" | "granted" | "denied" | "unavailable"
  >("pending");
  const [locationLabel, setLocationLabel] = useState("");
  const [showLocationPicker, setShowLocationPicker] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  // Request GPS location on mount
  useEffect(() => {
    if (!navigator.geolocation) {
      setLocationStatus("unavailable");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setUserLocation({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        });
        setLocationStatus("granted");
      },
      () => {
        setLocationStatus("denied");
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 }
    );
  }, []);

  const sendMessage = async (content: string) => {
    if (!content.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: `msg_${Date.now()}_user`,
      role: "user",
      content,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      let response: ChatResponse;

      if (API_BASE) {
        // Real API call — include location if available
        const payload: Record<string, unknown> = {
          message: content,
          language,
          session_id: sessionId,
        };
        if (userLocation) {
          payload.latitude = userLocation.latitude;
          payload.longitude = userLocation.longitude;
        }
        const res = await fetch(`${API_BASE}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!res.ok) throw new Error(`API error: ${res.status}`);
        response = await res.json();
      } else {
        // Demo mode — simulated response for testing without backend
        response = await simulateResponse(content, language);
      }

      const botMessage: ChatMessage = {
        id: `msg_${Date.now()}_bot`,
        role: "assistant",
        content: response.response,
        timestamp: new Date(),
        agentTrace: response.agent_trace,
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      const errorMessage: ChatMessage = {
        id: `msg_${Date.now()}_error`,
        role: "assistant",
        content:
          language === "hi"
            ? "माफ़ करें, कुछ गड़बड़ हो गई। कृपया दोबारा पूछें।"
            : "Sorry, something went wrong. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
      console.error("Chat error:", error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen max-w-lg mx-auto bg-[#f0f7f4] shadow-2xl">
      {/* Header */}
      <ChatHeader
        language={language}
        onLanguageChange={setLanguage}
        locationStatus={locationStatus}
        locationLabel={locationLabel}
        onRequestLocation={() => setShowLocationPicker(true)}
      />

      {/* Location Picker Modal */}
      <LocationPicker
        language={language}
        isOpen={showLocationPicker}
        onClose={() => setShowLocationPicker(false)}
        onSelectLocation={(loc) => {
          setUserLocation({ latitude: loc.latitude, longitude: loc.longitude });
          setLocationLabel(loc.label);
          setLocationStatus("granted");
          setShowLocationPicker(false);
        }}
      />

      {/* Chat area */}
      <div className="flex-1 overflow-y-auto chat-scroll">
        {messages.length === 0 ? (
          <WelcomeScreen language={language} onQuickAction={sendMessage} />
        ) : (
          <div className="py-4">
            {messages.map((msg) => (
              <ChatBubble key={msg.id} message={msg} />
            ))}
            {isLoading && <TypingIndicator />}
            <div ref={chatEndRef} />
          </div>
        )}
      </div>

      {/* Quick actions (show when few messages) */}
      {messages.length > 0 && messages.length <= 4 && !isLoading && (
        <QuickActions
          language={language}
          onAction={sendMessage}
          disabled={isLoading}
        />
      )}

      {/* Input */}
      <ChatInput onSend={sendMessage} disabled={isLoading} language={language} />
    </div>
  );
}

/**
 * Simulated response for demo/testing when backend is not connected.
 * This lets the frontend be demonstrated standalone.
 */
async function simulateResponse(
  message: string,
  language: string
): Promise<ChatResponse> {
  await new Promise((r) => setTimeout(r, 1500 + Math.random() * 1000));

  const lowerMsg = message.toLowerCase();
  const isHindi = language === "hi";

  // Detect intent from message
  if (
    lowerMsg.includes("भाव") ||
    lowerMsg.includes("price") ||
    lowerMsg.includes("rate") ||
    lowerMsg.includes("भाव बताओ")
  ) {
    return {
      response: isHindi
        ? `🌾 सोयाबीन — इंदौर मंडी
━━━━━━━━━━━━━━━━━━
📊 आज का भाव: ₹4,850/क्विंटल
📉 न्यूनतम: ₹4,200 | 📈 अधिकतम: ₹5,100
📋 MSP: ₹4,892/क्विंटल (MSP से ₹42 कम)

📈 7-दिन का रुझान: ▲ +2.3% (बढ़ रहा है)
📊 30-दिन औसत: ₹4,780/क्विंटल

आस-पास की मंडियां:
• देवास: ₹5,020 (38km) ← सबसे अच्छा
• उज्जैन: ₹4,700 (55km)
• रतलाम: ₹4,890 (130km)

📌 स्रोत: Agmarknet | 25-Feb-2026`
        : `🌾 Soyabean — Indore Mandi
━━━━━━━━━━━━━━━━━━
📊 Today's Price: ₹4,850/quintal
📉 Min: ₹4,200 | 📈 Max: ₹5,100
📋 MSP: ₹4,892/quintal (₹42 below MSP)

📈 7-Day Trend: ▲ +2.3% (rising)
📊 30-Day Avg: ₹4,780/quintal

Nearby Mandis:
• Dewas: ₹5,020 (38km) ← Best price
• Ujjain: ₹4,700 (55km)
• Ratlam: ₹4,890 (130km)

📌 Source: Agmarknet | 25-Feb-2026`,
      session_id: "demo",
      language,
      agent_trace: [
        {
          type: "preprocessing",
          step: "Intent Classification",
          output: "PRICE_CHECK — User wants commodity price at a specific mandi",
        },
        {
          type: "tool_call",
          step: "Tool Invocation",
          input: {
            action_group: "PriceIntelligence",
            function: "query_mandi_prices",
            parameters: { commodity: "Soyabean", state: "Madhya Pradesh", mandi: "Indore" },
          },
        },
        {
          type: "observation",
          step: "Tool Result",
          output: "Retrieved 7 price records. Modal: ₹4,850, Trend: +2.3% (7d)",
        },
        {
          type: "tool_call",
          step: "Tool Invocation",
          input: {
            action_group: "PriceIntelligence",
            function: "get_nearby_mandis",
            parameters: { latitude: 22.72, longitude: 75.86, radius_km: 150 },
          },
        },
        {
          type: "observation",
          step: "Tool Result",
          output: "Found 3 mandis within 150km: Dewas (₹5,020), Ujjain (₹4,700), Ratlam (₹4,890)",
        },
        {
          type: "reasoning",
          step: "Agent Reasoning",
          output: "Price is slightly below MSP. Trend is rising. Dewas offers ₹170 higher price at 38km distance.",
        },
      ],
      latency_seconds: 2.1,
    };
  }

  if (
    lowerMsg.includes("बेचूं") ||
    lowerMsg.includes("sell") ||
    lowerMsg.includes("hold") ||
    lowerMsg.includes("रुक")
  ) {
    return {
      response: isHindi
        ? `📊 सोयाबीन — बिक्री सलाह
━━━━━━━━━━━━━━━━━━

⏳ सलाह: 5-7 दिन रुकें (HOLD)
🎯 विश्वास स्तर: 82%

📝 कारण:
• भाव पिछले 7 दिन में 2.3% बढ़ा है
• सोयाबीन खराब नहीं होती (perishability: कम)
• मौसम सामान्य — कोई प्रतिकूल पूर्वानुमान नहीं
• अनुमानित भाव 5 दिन बाद: ₹4,920–₹5,050

💡 अगर अभी बेचना ज़रूरी है:
→ देवास मंडी (₹5,020/क्विंटल, 38km)
→ Net realization: ₹4,990/क्विंटल (transport ₹30 काटकर)
→ 50 क्विंटल पर कुल: ₹2,49,500

📌 स्रोत: Agmarknet + AI Analysis | 25-Feb-2026`
        : `📊 Soyabean — Sell Advisory
━━━━━━━━━━━━━━━━━━

⏳ Recommendation: HOLD for 5-7 days
🎯 Confidence: 82%

📝 Reasoning:
• Prices rose 2.3% in the last 7 days
• Soyabean is non-perishable (can store safely)
• Weather normal — no adverse forecast
• Expected price in 5 days: ₹4,920–₹5,050

💡 If you must sell now:
→ Dewas Mandi (₹5,020/quintal, 38km)
→ Net realization: ₹4,990/quintal (after ₹30 transport)
→ For 50 quintals: ₹2,49,500 total

📌 Source: Agmarknet + AI Analysis | 25-Feb-2026`,
      session_id: "demo",
      language,
      agent_trace: [
        {
          type: "preprocessing",
          step: "Intent Classification",
          output: "SELL_ADVISORY — User wants sell/hold recommendation",
        },
        {
          type: "reasoning",
          step: "Agent Reasoning",
          output: "Need price data + trend + perishability for sell recommendation. Routing to Price Intel → Sell Advisory.",
        },
        {
          type: "tool_call",
          step: "Tool Invocation",
          input: {
            action_group: "SellAdvisory",
            function: "get_sell_recommendation",
            parameters: { commodity: "Soyabean", state: "MP", quantity: 50 },
          },
        },
        {
          type: "observation",
          step: "Tool Result",
          output: "Trend: Rising +2.3%. Perishability: 2/10. Storage cost: ₹2/qtl/day. Best mandi: Dewas ₹5,020.",
        },
        {
          type: "reasoning",
          step: "Agent Reasoning",
          output: "Rising trend + low perishability + storage available → HOLD recommendation. Expected 3-4% appreciation in 5-7 days.",
        },
      ],
      latency_seconds: 3.4,
    };
  }

  if (
    lowerMsg.includes("brief") ||
    lowerMsg.includes("negotiate") ||
    lowerMsg.includes("पत्र")
  ) {
    return {
      response: isHindi
        ? `═══════════════════════════════════
  MandiMitra मूल्य पत्र (Price Brief)
  गेहूं — 25 Feb 2026
═══════════════════════════════════
  MSP (न्यूनतम समर्थन मूल्य): ₹2,275/क्विंटल
  आपकी मंडी (इंदौर):        ₹2,350/क्विंटल
  सबसे अच्छी मंडी (देवास):   ₹2,420 (38km)
  7-दिन का रुझान:            ▲ +1.8%
  उचित मूल्य अनुमान:        ₹2,350 — ₹2,450
───────────────────────────────────
  आस-पास की मंडियां:
  • देवास: ₹2,420 (38km)
  • उज्जैन: ₹2,310 (55km)
  • भोपाल: ₹2,380 (190km)
───────────────────────────────────
  स्रोत: Agmarknet | 25-Feb-2026
  MandiMitra — किसान का साथी
═══════════════════════════════════

💡 इस brief को WhatsApp पर share करें और मंडी में trader को दिखाएं।`
        : `═══════════════════════════════════
  MandiMitra Price Brief
  Wheat — 25 Feb 2026
═══════════════════════════════════
  MSP Reference:       ₹2,275/quintal
  Your Mandi (Indore): ₹2,350/quintal
  Best Nearby (Dewas): ₹2,420 (38km)
  7-Day Trend:         ▲ +1.8%
  Fair Price Range:    ₹2,350 — ₹2,450
───────────────────────────────────
  Nearby Mandis:
  • Dewas: ₹2,420 (38km)
  • Ujjain: ₹2,310 (55km)
  • Bhopal: ₹2,380 (190km)
───────────────────────────────────
  Source: Agmarknet | 25-Feb-2026
  MandiMitra — Farmer's Companion
═══════════════════════════════════

💡 Share this brief on WhatsApp and show it to the trader at the mandi.`,
      session_id: "demo",
      language,
      agent_trace: [
        {
          type: "preprocessing",
          step: "Intent Classification",
          output: "NEGOTIATION_PREP — User wants a price brief for mandi negotiation",
        },
        {
          type: "tool_call",
          step: "Tool Invocation",
          input: {
            action_group: "NegotiationPrep",
            function: "generate_price_brief",
            parameters: { commodity: "Wheat", mandi: "Indore" },
          },
        },
        {
          type: "observation",
          step: "Tool Result",
          output: "Generated price brief with MSP ₹2,275, modal ₹2,350, best nearby Dewas ₹2,420",
        },
      ],
      latency_seconds: 2.8,
    };
  }

  // Default response
  return {
    response: isHindi
      ? `नमस्ते! मैं MandiMitra हूँ — आपका AI मंडी सहायक। 🌾

मैं आपकी इन बातों में मदद कर सकता हूँ:
• 💰 मंडी भाव जानें (किसी भी फसल का)
• 📍 सबसे अच्छी मंडी खोजें (transport cost समेत)
• ⏳ बेचें या रुकें — AI सलाह लें
• 📋 Negotiation के लिए Price Brief बनाएं

कृपया अपनी फसल का नाम और मंडी बताएं!`
      : `Hello! I'm MandiMitra — your AI Mandi Assistant. 🌾

I can help you with:
• 💰 Check mandi prices (any commodity)
• 📍 Find the best mandi (including transport cost)
• ⏳ Sell or Hold — get AI-powered advice
• 📋 Generate a Price Brief for negotiation

Please tell me your commodity and mandi!`,
    session_id: "demo",
    language,
    agent_trace: [],
    latency_seconds: 0.5,
  };
}
