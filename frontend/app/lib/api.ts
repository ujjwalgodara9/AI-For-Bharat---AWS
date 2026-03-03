/**
 * MandiMitra API client
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3001/api";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  language?: string;
  agentTrace?: AgentTraceStep[];
  priceData?: PriceData;
}

export interface AgentTraceStep {
  type: "preprocessing" | "reasoning" | "tool_call" | "observation" | "model_output";
  step: string;
  input?: unknown;
  output?: string;
  metadata?: Record<string, unknown>;
}

export interface PriceData {
  commodity: string;
  mandis: MandiPrice[];
  trend?: TrendData;
  msp?: MspData;
}

export interface MandiPrice {
  mandi: string;
  modal_price: number;
  min_price: number;
  max_price: number;
  distance_km?: number;
  net_realization?: number;
  transport_cost_per_qtl?: number;
  date: string;
}

export interface TrendData {
  trend: "rising" | "falling" | "stable" | "no_data";
  change_pct: number;
  current_price: number;
  avg_price: number;
  volatility: "low" | "medium" | "high";
  data_points: number;
}

export interface MspData {
  commodity: string;
  msp: number | null;
  year: string;
  has_msp: boolean;
}

export interface ChatResponse {
  response: string;
  session_id: string;
  language: string;
  agent_trace: AgentTraceStep[];
  latency_seconds: number;
}

let sessionId: string | null = null;

function getSessionId(): string {
  if (!sessionId) {
    sessionId = `session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  }
  return sessionId;
}

export async function sendChatMessage(
  message: string,
  language: string = "hi"
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      language,
      session_id: getSessionId(),
    }),
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }

  return res.json();
}

export async function fetchPrices(
  commodity: string,
  state: string = "Madhya Pradesh",
  mandi?: string,
  days: number = 7
): Promise<PriceData> {
  const params = new URLSearchParams({ state, days: String(days) });
  if (mandi) params.set("mandi", mandi);

  const res = await fetch(
    `${API_BASE}/prices/${encodeURIComponent(commodity)}?${params}`
  );

  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export function resetSession(): void {
  sessionId = null;
}
