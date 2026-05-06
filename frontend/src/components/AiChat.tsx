"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import type { BoardData } from "@/lib/kanban";
import { api, type ChatMessage } from "@/lib/api";
import { EraserIcon, SendIcon, SparkleIcon } from "@/components/icons";

type AiChatProps = {
  onBoardUpdated: (nextBoard: BoardData) => void;
  boardId?: number;
};

export const AiChat = ({ onBoardUpdated, boardId }: AiChatProps) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setMessages([]);
    api
      .getChatHistory(boardId)
      .then((data) => setMessages(data.messages || []))
      .catch(() => {
        /* empty history is fine */
      });
  }, [boardId]);

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
      const data = await api.sendChat(trimmed, boardId);
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
      await api.resetChat(boardId);
      setMessages([]);
      setError(null);
    } catch {
      setError("Could not clear chat history. Please retry.");
    }
  };

  return (
    <aside
      className="flex h-[calc(100vh-2rem)] w-full flex-col rounded-2xl border border-[var(--stroke)] bg-white/95 shadow-[var(--shadow)] backdrop-blur lg:sticky lg:top-4"
      data-testid="ai-chat"
    >
      <header className="flex items-center justify-between gap-3 border-b border-[var(--stroke)] px-4 py-3">
        <div className="flex items-center gap-2.5">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-[rgba(32,157,215,0.12)] text-[var(--primary-blue)]">
            <SparkleIcon className="h-4 w-4" />
          </span>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
              Assistant
            </p>
            <p className="font-display text-sm font-semibold leading-tight text-[var(--navy-dark)]">
              Board Copilot
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={handleReset}
          aria-label="Clear chat history"
          title="Clear chat"
          className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-[var(--stroke)] text-[var(--gray-text)] transition hover:bg-[var(--surface)] hover:text-[var(--navy-dark)]"
        >
          <EraserIcon className="h-3.5 w-3.5" />
        </button>
      </header>

      <div
        ref={scrollRef}
        className="flex flex-1 flex-col gap-2.5 overflow-y-auto px-4 py-3"
      >
        {messages.length === 0 && (
          <p className="text-xs leading-6 text-[var(--gray-text)]">
            Ask the assistant to add, move, rename, or delete cards. For
            example: &ldquo;Move the analytics card to In Progress&rdquo;.
          </p>
        )}
        {messages.map((message, index) => (
          <div
            key={index}
            className={
              message.role === "user"
                ? "self-end max-w-[88%] rounded-2xl rounded-br-md bg-[var(--primary-blue)] px-3.5 py-2 text-xs leading-5 text-white"
                : "self-start max-w-[88%] rounded-2xl rounded-bl-md border border-[var(--stroke)] bg-[var(--surface)] px-3.5 py-2 text-xs leading-5 text-[var(--navy-dark)]"
            }
            data-testid={`chat-message-${message.role}`}
          >
            {message.content}
          </div>
        ))}
        {sending && (
          <div className="self-start max-w-[88%] rounded-2xl rounded-bl-md border border-[var(--stroke)] bg-[var(--surface)] px-3.5 py-2 text-xs italic text-[var(--gray-text)]">
            Thinking…
          </div>
        )}
      </div>

      {error && (
        <div className="mx-4 mb-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {error}
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="flex items-end gap-2 border-t border-[var(--stroke)] px-4 py-3"
      >
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          rows={2}
          placeholder="Ask the assistant…"
          className="flex-1 resize-none rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-xs leading-5 text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
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
          aria-label="Send message"
          className="inline-flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-[var(--secondary-purple)] text-white transition hover:brightness-110 disabled:opacity-50"
        >
          <SendIcon className="h-4 w-4" />
        </button>
      </form>
    </aside>
  );
};
