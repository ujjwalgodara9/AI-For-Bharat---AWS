/**
 * MandiMitra — Voice input using Web Speech API
 * Supports Hindi and English speech recognition.
 */

type SpeechCallback = (transcript: string) => void;
type ErrorCallback = (error: string) => void;

interface SpeechRecognitionEvent {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionErrorEvent {
  error: string;
  message?: string;
}

let recognition: SpeechRecognition | null = null;

export function isVoiceSupported(): boolean {
  return typeof window !== "undefined" &&
    ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);
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

  const SpeechRecognition =
    window.SpeechRecognition || (window as unknown as { webkitSpeechRecognition: typeof window.SpeechRecognition }).webkitSpeechRecognition;
  recognition = new SpeechRecognition();

  recognition.lang = language === "hi" ? "hi-IN" : "en-IN";
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  recognition.onresult = (event: SpeechRecognitionEvent) => {
    const transcript = event.results[0][0].transcript;
    onResult(transcript);
  };

  recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
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
