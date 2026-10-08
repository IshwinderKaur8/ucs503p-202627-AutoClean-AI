import { useCallback, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { ChatMessage } from "../types";
import { sendChatMessage } from "../api/client";
import { useVoice } from "../hooks/useVoice";

interface Props {
  selectedId: string | null;
  selectedName: string | null;
}

export default function ChatAssistant({ selectedId, selectedName }: Props) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [voiceReplies, setVoiceReplies] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!selectedId || !text.trim() || sending) return;
      const userMsg: ChatMessage = { role: "user", text };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setSending(true);
      try {
        const reply = await sendChatMessage(selectedId, text);
        const assistantMsg: ChatMessage = {
          role: "assistant",
          text: reply.reply,
          recommendations: reply.recommendations ?? undefined,
        };
        setMessages((prev) => [...prev, assistantMsg]);
        if (voiceReplies) speak(reply.reply);
      } catch (e) {
        setMessages((prev) => [...prev, { role: "assistant", text: `Sorry, something went wrong: ${String(e)}` }]);
      } finally {
        setSending(false);
        setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [selectedId, sending, voiceReplies]
  );

  const handleVoiceResult = useCallback(
    (transcript: string) => {
      void sendMessage(transcript);
    },
    [sendMessage]
  );

  const { isRecognitionSupported, isSynthesisSupported, listening, startListening, stopListening, speak } = useVoice({
    onResult: handleVoiceResult,
  });

  return (
    <>
      <motion.button
        className="chat-fab"
        onClick={() => setOpen((o) => !o)}
        whileHover={{ scale: 1.08 }}
        whileTap={{ scale: 0.95 }}
        aria-label="Open assistant chat"
      >
        {open ? "✕" : "💬"}
      </motion.button>

      <AnimatePresence>
        {open && (
          <motion.div
            className="chat-drawer"
            initial={{ opacity: 0, y: 24, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.96 }}
            transition={{ duration: 0.2 }}
          >
            <div className="chat-header">
              <div>
                <strong>Data Assistant</strong>
                <div className="dataset-tag">{selectedName ? `Talking about: ${selectedName}` : "No dataset selected"}</div>
              </div>
              <button className="chat-close-btn" onClick={() => setOpen(false)}>
                close
              </button>
            </div>

            <div className="chat-messages">
              {messages.length === 0 && (
                <div className="chat-empty-hint">
                  {selectedId
                    ? 'Ask me things like "what algorithm should I use?", "is my data clean?", or "any outliers?"'
                    : "Select a dataset first, then ask me anything about it."}
                </div>
              )}
              {messages.map((m, i) => (
                <div key={i} className={`chat-message ${m.role}`}>
                  {m.text}
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            <div className="chat-input-row">
              {isRecognitionSupported && (
                <button
                  className={`chat-icon-btn ${listening ? "active listening" : ""}`}
                  onClick={() => (listening ? stopListening() : startListening())}
                  disabled={!selectedId}
                  title="Speak your question"
                  type="button"
                >
                  🎤
                </button>
              )}
              {isSynthesisSupported && (
                <button
                  className={`chat-icon-btn ${voiceReplies ? "active" : ""}`}
                  onClick={() => setVoiceReplies((v) => !v)}
                  title="Read replies aloud"
                  type="button"
                >
                  🔊
                </button>
              )}
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void sendMessage(input);
                }}
                placeholder={selectedId ? "Ask about this dataset..." : "Select a dataset first"}
                disabled={!selectedId || sending}
              />
              <button
                className="chat-send-btn"
                onClick={() => void sendMessage(input)}
                disabled={!selectedId || !input.trim() || sending}
                type="button"
              >
                ➤
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
