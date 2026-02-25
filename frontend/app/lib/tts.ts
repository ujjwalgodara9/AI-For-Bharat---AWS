/**
 * MandiMitra — Text-to-Speech using Web Speech Synthesis API
 * Speaks bot responses in Hindi/English based on current toggle.
 */

export function isTTSSupported(): boolean {
  if (typeof window === "undefined") return false;
  return "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
}

let activeUtterance: SpeechSynthesisUtterance | null = null;

function pickVoice(targetLang: string): SpeechSynthesisVoice | undefined {
  const voices = window.speechSynthesis.getVoices?.() ?? [];
  if (voices.length === 0) return undefined;

  const normalized = targetLang.toLowerCase();
  const exact = voices.find((v) => v.lang?.toLowerCase() === normalized);
  if (exact) return exact;

  const prefix = normalized.split("-")[0];
  return voices.find((v) => v.lang?.toLowerCase().startsWith(prefix));
}

export function stopSpeaking(): void {
  if (!isTTSSupported()) return;
  window.speechSynthesis.cancel();
  activeUtterance = null;
}

export function speakText(params: {
  text: string;
  lang: string;
  onEnd?: () => void;
  onError?: () => void;
}): void {
  if (!isTTSSupported()) return;

  const text = params.text.trim();
  if (!text) return;

  // Ensure only one utterance is active at a time.
  stopSpeaking();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = params.lang;

  // Trigger voice list hydration in some browsers, then pick best match.
  window.speechSynthesis.getVoices?.();
  const voice = pickVoice(params.lang);
  if (voice) utterance.voice = voice;

  utterance.onend = () => {
    if (activeUtterance === utterance) activeUtterance = null;
    params.onEnd?.();
  };
  utterance.onerror = () => {
    if (activeUtterance === utterance) activeUtterance = null;
    params.onError?.();
  };

  activeUtterance = utterance;
  window.speechSynthesis.speak(utterance);
}

