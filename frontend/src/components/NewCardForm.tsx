import { useState, type FormEvent } from "react";
import { PlusIcon, XIcon } from "@/components/icons";
import type { Priority } from "@/lib/kanban";

const initialFormState = {
  title: "",
  details: "",
  priority: "medium" as Priority,
  dueDate: "",
};

type NewCardFormProps = {
  onAdd: (
    title: string,
    details: string,
    priority: Priority,
    dueDate: string | null
  ) => void;
};

export const NewCardForm = ({ onAdd }: NewCardFormProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [formState, setFormState] = useState(initialFormState);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!formState.title.trim()) {
      return;
    }
    onAdd(
      formState.title.trim(),
      formState.details.trim(),
      formState.priority,
      formState.dueDate || null
    );
    setFormState(initialFormState);
    setIsOpen(false);
  };

  return (
    <div className="mt-3">
      {isOpen ? (
        <form onSubmit={handleSubmit} className="space-y-2">
          <input
            value={formState.title}
            onChange={(event) =>
              setFormState((prev) => ({ ...prev, title: event.target.value }))
            }
            placeholder="Card title"
            className="w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm font-medium text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
            required
          />
          <textarea
            value={formState.details}
            onChange={(event) =>
              setFormState((prev) => ({ ...prev, details: event.target.value }))
            }
            placeholder="Details"
            rows={2}
            className="w-full resize-none rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--gray-text)] outline-none transition focus:border-[var(--primary-blue)]"
          />
          <div className="grid grid-cols-2 gap-2">
            <select
              value={formState.priority}
              onChange={(event) =>
                setFormState((prev) => ({
                  ...prev,
                  priority: event.target.value as Priority,
                }))
              }
              aria-label="Priority"
              className="w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-xs text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
            <input
              type="date"
              value={formState.dueDate}
              onChange={(event) =>
                setFormState((prev) => ({ ...prev, dueDate: event.target.value }))
              }
              aria-label="Due date"
              className="w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-xs text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
            />
          </div>
          <div className="flex items-center gap-2">
            <button
              type="submit"
              className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-full bg-[var(--secondary-purple)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:brightness-110"
            >
              <PlusIcon className="h-3.5 w-3.5" />
              Add card
            </button>
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                setFormState(initialFormState);
              }}
              aria-label="Cancel"
              className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-[var(--stroke)] text-[var(--gray-text)] transition hover:text-[var(--navy-dark)]"
            >
              <XIcon className="h-3.5 w-3.5" />
            </button>
          </div>
        </form>
      ) : (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="inline-flex w-full items-center justify-center gap-1.5 rounded-full border border-dashed border-[var(--stroke)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--primary-blue)] transition hover:border-[var(--primary-blue)] hover:bg-[var(--surface)]"
        >
          <PlusIcon className="h-3.5 w-3.5" />
          Add a card
        </button>
      )}
    </div>
  );
};
