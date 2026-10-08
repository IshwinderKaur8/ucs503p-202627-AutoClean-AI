import { useCallback, useEffect, useRef, useState } from "react";

// The Web Speech API's SpeechRecognition interface isn't part of TS's
// standard DOM lib (it's non-standard / webkit-prefixed in most browsers),
// so we declare the minimal shape we actually use.
interface SpeechRecognitionResultLike {
  0: { transcript: string };
}
interface SpeechRecognitionEventLike extends Event {
  results: ArrayLike<SpeechRecognitionResultLike>;
}
interface SpeechRecognitionLike extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
}

type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

function getRecognitionCtor(): SpeechRecognitionCtor | null {
  const w = window as unknown as { SpeechRecognition?: SpeechRecognitionCtor; webkitSpeechRecognition?: SpeechRecognitionCtor };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

interface UseVoiceOptions {
  onResult: (transcript: string) => void;
}

export function useVoice({ onResult }: UseVoiceOptions) {
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  const isRecognitionSupported = getRecognitionCtor() !== null;
  const isSynthesisSupported = typeof window !== "undefined" && "speechSynthesis" in window;

  useEffect(() => {
    const Ctor = getRecognitionCtor();
    if (!Ctor) return;
    const recognition = new Ctor();
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript;
      if (transcript) onResult(transcript);
    };
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    recognitionRef.current = recognition;
    return () => {
      recognition.onresult = null;
      recognition.onend = null;
      recognition.onerror = null;
    };
  }, [onResult]);

  const startListening = useCallback(() => {
    if (!recognitionRef.current) return;
    setListening(true);
    recognitionRef.current.start();
  }, []);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
    setListening(false);
  }, []);

  const speak = useCallback(
    (text: string) => {
      if (!isSynthesisSupported) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.02;
      window.speechSynthesis.speak(utterance);
    },
    [isSynthesisSupported]
  );

  const cancelSpeak = useCallback(() => {
    if (isSynthesisSupported) window.speechSynthesis.cancel();
  }, [isSynthesisSupported]);

  return { isRecognitionSupported, isSynthesisSupported, listening, startListening, stopListening, speak, cancelSpeak };
}
