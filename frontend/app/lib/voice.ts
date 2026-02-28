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

  let hasResult = false;

  recognition.onresult = (event: any) => {
    hasResult = true;
    const transcript: string = event.results[0][0].transcript;
    if (transcript && transcript.trim()) {
      onResult(transcript.trim());
    }
  };

  recognition.onerror = (event: any) => {
    if (event.error === "not-allowed" || event.error === "service-not-allowed") {
      onError("Microphone permission denied. Please allow microphone access in your browser settings.");
    } else if (event.error === "no-speech") {
      onError("No speech detected. Please try again and speak clearly.");
    } else if (event.error !== "aborted") {
      onError(`Voice error: ${event.error}`);
    }
  };

  recognition.onend = () => {
    if (!hasResult) {
      // Recognition ended without any result - notify user
      onError("No speech detected. Please tap the mic and speak clearly.");
    }
    recognition = null;
  };

  try {
    recognition.start();
  } catch {
    onError("Could not start voice input. Please try again.");
    recognition = null;
  }
}

export function stopListening(): void {
  if (recognition) {
    recognition.stop();
    recognition = null;
  }
}
