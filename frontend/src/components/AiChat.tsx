"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import type { BoardData } from "@/lib/kanban";
import { api, type ChatMessage } from "@/lib/api";

type AiChatProps = {
  onBoardUpdated: (nextBoard: BoardData) => void;
};

export const AiChat = ({ onBoardUpdated }: AiChatProps) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    api
      .getChatHistory()
      .then((data) => setMessages(data.messages || []))
      .catch(() => {
        /* empty history is fine */
      });
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (el && typeof el.scrollTo === "function") {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  }, [messages, sending]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || sending) return;

    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setInput("");
    setSending(true);
    setError(null);

    try {
      const data = await api.sendChat(trimmed);
      setMessages((prev) => [...prev, { role: "assistant", content: data.message }]);
      if (data.boardUpdated && data.board) {
        onBoardUpdated(data.board);
      }
    } catch {
      setError("The assistant is unavailable right now. Please try again.");
    } finally {
      setSending(false);
    }
  };

  const handleReset = async () => {
    try {
      await api.resetChat();
      setMessages([]);
      setError(null);
    } catch {
      setError("Could not clear chat history. Please retry.");
    }
  };

  return (
    <aside
      className="flex h-[calc(100vh-2rem)] w-full flex-col rounded-3xl border border-[var(--stroke)] bg-white/90 shadow-[var(--shadow)] backdrop-blur lg:sticky lg:top-4"
      data-testid="ai-chat"
    >
      <header className="flex items-center justify-between gap-3 border-b border-[var(--stroke)] px-5 py-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
            Assistant
          </p>
          <p className="font-display text-lg font-semibold text-[var(--navy-dark)]">
            Board Copilot
          </p>
        </div>
        <button
          type="button"
          onClick={handleReset}
          className="rounded-full border border-[var(--stroke)] px-3 py-1 text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)] transition hover:bg-[var(--surface)]"
        >
          Clear
        </button>
      </header>

      <div
        ref={scrollRef}
        className="flex flex-1 flex-col gap-3 overflow-y-auto px-5 py-4"
      >
        {messages.length === 0 && (
          <p className="text-sm leading-6 text-[var(--gray-text)]">
            Ask the assistant to add, move, rename, or delete cards. For
            example: &ldquo;Move the analytics card to In Progress&rdquo;.
          </p>
        )}
        {messages.map((message, index) => (
          <div
            key={index}
            className={
              message.role === "user"
                ? "self-end max-w-[85%] rounded-2xl bg-[var(--primary-blue)] px-4 py-2 text-sm text-white"
                : "self-start max-w-[85%] rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-2 text-sm text-[var(--navy-dark)]"
            }
            data-testid={`chat-message-${message.role}`}
          >
            {message.content}
          </div>
        ))}
        {sending && (
          <div className="self-start max-w-[85%] rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-2 text-sm italic text-[var(--gray-text)]">
            Thinking…
          </div>
        )}
      </div>

      {error && (
        <div className="mx-5 mb-2 rounded-2xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {error}
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="flex items-end gap-2 border-t border-[var(--stroke)] px-5 py-4"
      >
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          rows={2}
          placeholder="Ask the assistant…"
          className="flex-1 resize-none rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className="rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-sm font-semibold text-white transition hover:brightness-110 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </aside>
  );
};
