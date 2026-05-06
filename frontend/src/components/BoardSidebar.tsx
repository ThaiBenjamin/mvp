"use client";

import { FormEvent, useState } from "react";
import clsx from "clsx";
import type { BoardSummary } from "@/lib/kanban";
import { LayoutIcon, PencilIcon, PlusIcon, TrashIcon, XIcon } from "@/components/icons";

type BoardSidebarProps = {
  boards: BoardSummary[];
  activeId: number | null;
  onSelect: (id: number) => void;
  onCreate: (name: string) => Promise<void> | void;
  onRename: (id: number, name: string) => Promise<void> | void;
  onDelete: (id: number) => Promise<void> | void;
};

export const BoardSidebar = ({
  boards,
  activeId,
  onSelect,
  onCreate,
  onRename,
  onDelete,
}: BoardSidebarProps) => {
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!newName.trim()) return;
    await onCreate(newName.trim());
    setNewName("");
    setCreating(false);
  };

  const handleRename = async (event: FormEvent<HTMLFormElement>, id: number) => {
    event.preventDefault();
    if (!editName.trim()) return;
    await onRename(id, editName.trim());
    setEditingId(null);
    setEditName("");
  };

  return (
    <aside
      className="flex w-full flex-col gap-2 rounded-2xl border border-[var(--stroke)] bg-white/95 p-3 shadow-[var(--shadow)] backdrop-blur lg:w-[240px]"
      data-testid="board-sidebar"
    >
      <header className="flex items-center justify-between px-1 pt-1">
        <span className="text-[10px] font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
          Boards
        </span>
        <button
          type="button"
          onClick={() => setCreating((c) => !c)}
          aria-label={creating ? "Cancel new board" : "Create new board"}
          className="inline-flex h-7 w-7 items-center justify-center rounded-full text-[var(--gray-text)] hover:bg-[var(--surface)] hover:text-[var(--primary-blue)]"
        >
          {creating ? <XIcon className="h-3.5 w-3.5" /> : <PlusIcon className="h-3.5 w-3.5" />}
        </button>
      </header>

      {creating && (
        <form onSubmit={handleCreate} className="flex flex-col gap-2 px-1">
          <input
            value={newName}
            onChange={(event) => setNewName(event.target.value)}
            placeholder="Board name"
            autoFocus
            className="w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm font-medium text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
            required
          />
          <button
            type="submit"
            className="rounded-full bg-[var(--secondary-purple)] px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-white transition hover:brightness-110"
          >
            Create board
          </button>
        </form>
      )}

      <ul className="flex flex-col gap-1">
        {boards.map((board) => {
          const isActive = board.id === activeId;
          const isEditing = editingId === board.id;
          if (isEditing) {
            return (
              <li key={board.id} className="px-1">
                <form
                  onSubmit={(event) => handleRename(event, board.id)}
                  className="flex items-center gap-1"
                >
                  <input
                    value={editName}
                    onChange={(event) => setEditName(event.target.value)}
                    autoFocus
                    className="flex-1 rounded-lg border border-[var(--stroke)] bg-white px-2 py-1.5 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
                    required
                  />
                  <button
                    type="submit"
                    className="rounded-full bg-[var(--primary-blue)] px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-white"
                  >
                    Save
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditingId(null)}
                    aria-label="Cancel rename"
                    className="inline-flex h-6 w-6 items-center justify-center rounded-full text-[var(--gray-text)] hover:bg-[var(--surface)]"
                  >
                    <XIcon className="h-3 w-3" />
                  </button>
                </form>
              </li>
            );
          }
          return (
            <li key={board.id} className="group">
              <div
                className={clsx(
                  "flex items-center gap-2 rounded-xl px-2 py-1.5 text-sm",
                  isActive
                    ? "bg-[var(--primary-blue)]/10 text-[var(--navy-dark)]"
                    : "text-[var(--gray-text)] hover:bg-[var(--surface)] hover:text-[var(--navy-dark)]"
                )}
              >
                <button
                  type="button"
                  onClick={() => onSelect(board.id)}
                  className="flex flex-1 items-center gap-2 truncate text-left font-medium"
                  data-testid={`board-tab-${board.id}`}
                >
                  <LayoutIcon
                    className={clsx(
                      "h-3.5 w-3.5 flex-shrink-0",
                      isActive ? "text-[var(--primary-blue)]" : "text-[var(--gray-text)]"
                    )}
                  />
                  <span className="truncate">{board.name}</span>
                </button>
                <div className="flex items-center gap-0.5 opacity-0 transition group-hover:opacity-100 focus-within:opacity-100">
                  <button
                    type="button"
                    aria-label={`Rename ${board.name}`}
                    onClick={() => {
                      setEditingId(board.id);
                      setEditName(board.name);
                    }}
                    className="inline-flex h-6 w-6 items-center justify-center rounded-full text-[var(--gray-text)] hover:bg-white hover:text-[var(--primary-blue)]"
                  >
                    <PencilIcon className="h-3 w-3" />
                  </button>
                  <button
                    type="button"
                    aria-label={`Delete ${board.name}`}
                    onClick={() => onDelete(board.id)}
                    disabled={boards.length <= 1}
                    className="inline-flex h-6 w-6 items-center justify-center rounded-full text-[var(--gray-text)] hover:bg-white hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-30"
                  >
                    <TrashIcon className="h-3 w-3" />
                  </button>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </aside>
  );
};
