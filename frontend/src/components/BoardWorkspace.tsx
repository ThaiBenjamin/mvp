"use client";

import { useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { BoardSidebar } from "@/components/BoardSidebar";
import { api } from "@/lib/api";
import type { BoardSummary } from "@/lib/kanban";

const STORAGE_KEY = "pm:active_board_id";

const readStoredId = (): number | null => {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  const num = Number(raw);
  return Number.isFinite(num) ? num : null;
};

const writeStoredId = (id: number | null) => {
  if (typeof window === "undefined") return;
  if (id == null) {
    window.localStorage.removeItem(STORAGE_KEY);
  } else {
    window.localStorage.setItem(STORAGE_KEY, String(id));
  }
};

export const BoardWorkspace = () => {
  const [boards, setBoards] = useState<BoardSummary[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const applyBoards = (
    incoming: BoardSummary[],
    preferredId?: number | null
  ) => {
    const ids = incoming.map((b) => b.id);
    const stored = preferredId ?? readStoredId();
    let next: number | null;
    if (stored != null && ids.includes(stored)) {
      next = stored;
    } else if (incoming.length > 0) {
      next = incoming[0].id;
    } else {
      next = null;
    }
    setBoards(incoming);
    setActiveId(next);
    writeStoredId(next);
    setLoadError(null);
  };

  const refreshBoards = (preferredId?: number | null) =>
    api
      .listBoards()
      .then((data) => applyBoards(data.boards, preferredId))
      .catch(() => setLoadError("Unable to load boards. Please retry."));

  useEffect(() => {
    api
      .listBoards()
      .then((data) => applyBoards(data.boards))
      .catch(() => setLoadError("Unable to load boards. Please retry."));
  }, []);

  const handleSelect = (id: number) => {
    setActiveId(id);
    writeStoredId(id);
  };

  const handleCreate = async (name: string) => {
    const created = await api.createBoard(name);
    await refreshBoards(created.id);
  };

  const handleRename = async (id: number, name: string) => {
    await api.renameBoard(id, name);
    await refreshBoards(id);
  };

  const handleDelete = async (id: number) => {
    if (boards.length <= 1) return;
    const confirmed = window.confirm("Delete this board? This cannot be undone.");
    if (!confirmed) return;
    await api.deleteBoard(id);
    const remaining = boards.filter((b) => b.id !== id);
    const nextId = remaining[0]?.id ?? null;
    await refreshBoards(nextId);
  };

  if (loadError) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        {loadError}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
      <div className="lg:sticky lg:top-4 lg:self-start">
        <BoardSidebar
          boards={boards}
          activeId={activeId}
          onSelect={handleSelect}
          onCreate={handleCreate}
          onRename={handleRename}
          onDelete={handleDelete}
        />
      </div>
      <div className="min-w-0 flex-1">
        {activeId != null ? (
          <KanbanBoard key={activeId} boardId={activeId} />
        ) : (
          <p className="text-sm text-[var(--gray-text)]">
            Create a board to get started.
          </p>
        )}
      </div>
    </div>
  );
};
