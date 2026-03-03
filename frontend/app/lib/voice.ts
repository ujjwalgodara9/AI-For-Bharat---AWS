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

  let hasError = false;

  recognition.onerror = (event: any) => {
    hasError = true;
    if (event.error === "not-allowed" || event.error === "service-not-allowed") {
      onError("Microphone permission denied. Please allow microphone access and use HTTPS.");
    } else if (event.error === "no-speech") {
      onError("No speech detected. Please try again and speak clearly.");
    } else if (event.error !== "aborted") {
      onError(`Voice error: ${event.error}`);
    }
  };

  recognition.onend = () => {
    // Only show "no speech" if we didn't already get a result or an error
    if (!hasResult && !hasError) {
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

function getEnglishIndiaVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
  return (
    voices.find((v) => v.name === "Rishi") ||
    voices.find((v) => v.name === "Veena") ||
    voices.find((v) => v.lang === "en-IN") ||
    voices.find((v) => v.name.toLowerCase().includes("india")) ||
    voices.find((v) => v.lang.startsWith("en")) ||
    null
  );
}

function getPreferredVoice(language: string): SpeechSynthesisVoice | null {
  const voices = window.speechSynthesis.getVoices();
  if (voices.length === 0) return null;

  if (language === "hi") {
    const hiVoice =
      voices.find((v) => v.name === "Lekha") ||
      voices.find((v) => v.lang === "hi-IN") ||
      voices.find((v) => v.lang.startsWith("hi")) ||
      null;
    return hiVoice ?? getEnglishIndiaVoice(voices);
  } else {
    return getEnglishIndiaVoice(voices);
  }
}

export function speak(text: string, language: string, onEnd?: () => void): void {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();

  const doSpeak = () => {
    const utterance = new SpeechSynthesisUtterance(text);
    const voice = getPreferredVoice(language);

    if (voice) {
      utterance.voice = voice;
      utterance.lang = voice.lang;
      utterance.rate = voice.lang.startsWith("hi") ? 0.82 : 0.88;
      utterance.pitch = voice.lang.startsWith("hi") ? 1.1 : 1.0;
    }
    utterance.volume = 1.0;

    if (onEnd) {
      utterance.onend = onEnd;
      utterance.onerror = onEnd;
    }

    window.speechSynthesis.speak(utterance);
  };

  const voices = window.speechSynthesis.getVoices();
  if (voices.length === 0) {
    const handler = () => {
      window.speechSynthesis.removeEventListener("voiceschanged", handler);
      doSpeak();
    };
    window.speechSynthesis.addEventListener("voiceschanged", handler);
    setTimeout(() => {
      window.speechSynthesis.removeEventListener("voiceschanged", handler);
      doSpeak();
    }, 500);
  } else {
    doSpeak();
  }
}

export function stopSpeaking(): void {
  if (typeof window !== "undefined" && window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
}

export function isSpeakingSupported(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}
