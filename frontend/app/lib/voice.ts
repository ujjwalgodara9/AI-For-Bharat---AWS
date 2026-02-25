/**
 * MandiMitra — Voice input using Web Speech API
 * Supports Hindi and English speech recognition.
 */

type SpeechCallback = (transcript: string) => void;
type ErrorCallback = (error: string) => void;

/* eslint-disable @typescript-eslint/no-explicit-any */
let recognition: any = null;

export function isVoiceSupported(): boolean {
  if (typeof window === "undefined") return false;
  return "SpeechRecognition" in window || "webkitSpeechRecognition" in window;
}

export function startListening(
  language: string,
  onResult: SpeechCallback,
  onError: ErrorCallback
): void {
  if (!isVoiceSupported()) {
    onError("Voice input is not supported in this browser");
    return;
  }

  const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
  recognition = new SR();

  recognition.lang = language === "hi" ? "hi-IN" : "en-IN";
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  recognition.onresult = (event: any) => {
    const transcript: string = event.results[0][0].transcript;
    onResult(transcript);
  };

  recognition.onerror = (event: any) => {
    if (event.error !== "aborted") {
      onError(`Voice error: ${event.error}`);
    }
  };

  recognition.start();
}

export function stopListening(): void {
  if (recognition) {
    recognition.stop();
    recognition = null;
  }
}
