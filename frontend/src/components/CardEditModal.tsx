"use client";

import { FormEvent, useState } from "react";
import { XIcon } from "@/components/icons";
import type { Card, Priority } from "@/lib/kanban";

type CardEditModalProps = {
  card: Card | null;
  onClose: () => void;
  onSave: (
    cardId: string,
    fields: { title: string; details: string; priority: Priority; dueDate: string | null }
  ) => void;
};

export const CardEditModal = ({ card, onClose, onSave }: CardEditModalProps) => {
  if (!card) return null;
  return (
    <CardEditModalInner key={card.id} card={card} onClose={onClose} onSave={onSave} />
  );
};

const CardEditModalInner = ({
  card,
  onClose,
  onSave,
}: CardEditModalProps & { card: Card }) => {
  const [title, setTitle] = useState(card.title);
  const [details, setDetails] = useState(card.details);
  const [priority, setPriority] = useState<Priority>(card.priority);
  const [dueDate, setDueDate] = useState<string>(card.dueDate ?? "");

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!title.trim()) return;
    onSave(card.id, {
      title: title.trim(),
      details: details.trim(),
      priority,
      dueDate: dueDate || null,
    });
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      role="dialog"
      aria-modal="true"
      aria-label="Edit card"
      onClick={onClose}
      data-testid="card-edit-modal"
    >
      <div
        className="w-full max-w-md rounded-2xl border border-[var(--stroke)] bg-white p-6 shadow-[var(--shadow)]"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-display text-lg font-semibold text-[var(--navy-dark)]">
            Edit card
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="inline-flex h-8 w-8 items-center justify-center rounded-full text-[var(--gray-text)] hover:bg-[var(--surface)]"
          >
            <XIcon className="h-4 w-4" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <label className="space-y-1 text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)]">
            Title
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              className="w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm font-medium text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
              required
            />
          </label>
          <label className="space-y-1 text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)]">
            Details
            <textarea
              value={details}
              onChange={(event) => setDetails(event.target.value)}
              rows={3}
              className="w-full resize-none rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-1 text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)]">
              Priority
              <select
                value={priority}
                onChange={(event) => setPriority(event.target.value as Priority)}
                className="w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </label>
            <label className="space-y-1 text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)]">
              Due date
              <input
                type="date"
                value={dueDate}
                onChange={(event) => setDueDate(event.target.value)}
                className="w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
              />
            </label>
          </div>
          <div className="mt-2 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--navy-dark)] hover:bg-[var(--surface)]"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:brightness-110"
            >
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
