"use client";

import { useEffect, useMemo, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
  type UniqueIdentifier,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { createId, initialData, moveCard, type BoardData } from "@/lib/kanban";

const findColumnId = (columns: BoardData["columns"], id: string) => {
  if (columns.some((column) => column.id === id)) {
    return id;
  }

  return columns.find((column) => column.cardIds.includes(id))?.id ?? null;
};

export const resolveDragOverColumnId = (
  over: { id: UniqueIdentifier; data?: { current?: { columnId?: string } } } | null
): string | null => {
  if (!over) {
    return null;
  }

  return over.data?.current?.columnId ?? String(over.id);
};

export const getTargetDetails = (
  columns: BoardData["columns"],
  overId: string
): { columnId: string; index: number } | null => {
  const columnId = findColumnId(columns, overId);
  if (!columnId) {
    return null;
  }

  const targetColumn = columns.find((column) => column.id === columnId);
  if (!targetColumn) {
    return null;
  }

  const overIsColumn = targetColumn.id === overId;
  if (overIsColumn) {
    return { columnId, index: targetColumn.cardIds.length };
  }

  const targetIndex = targetColumn.cardIds.indexOf(overId);
  return {
    columnId,
    index: targetIndex === -1 ? targetColumn.cardIds.length : targetIndex,
  };
};

export const KanbanBoard = () => {
  const [board, setBoard] = useState<BoardData>(() => initialData);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [loadingBoard, setLoadingBoard] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    const loadBoard = async () => {
      try {
        const response = await fetch("/api/board");
        if (!response.ok) {
          setLoadError("Unable to load board from server. Using local board state.");
          return;
        }

        const data = (await response.json()) as BoardData;
        setBoard(data);
      } catch {
        setLoadError("Unable to load board from server. Using local board state.");
      } finally {
        setLoadingBoard(false);
      }
    };

    loadBoard();
  }, []);

  const sendBoardAction = async (
    action: string,
    payload: Record<string, unknown>,
    optimisticBoard: BoardData
  ) => {
    setBoard(optimisticBoard);
    setSaveError(null);

    try {
      const response = await fetch("/api/board/actions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, payload }),
      });

      if (!response.ok) {
        throw new Error("Save failed");
      }

      const updatedBoard = (await response.json()) as BoardData;
      setBoard(updatedBoard);
    } catch {
      setSaveError("Unable to save board changes. Refresh to retry.");
    }
  };

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const cardsById = useMemo(() => board.cards, [board.cards]);

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!over || active.id === over.id) {
      return;
    }

    const overColumnId = resolveDragOverColumnId(over);
    if (!overColumnId) {
      return;
    }

    const nextColumns = moveCard(
      board.columns,
      active.id as string,
      overColumnId
    );
    const targetDetails = getTargetDetails(board.columns, overColumnId);
    const nextBoard = { ...board, columns: nextColumns };

    if (!targetDetails) {
      setBoard(nextBoard);
      return;
    }

    sendBoardAction(
      "move_card",
      {
        card_id: active.id as string,
        target_column_id: targetDetails.columnId,
        target_index: targetDetails.index,
      },
      nextBoard
    );
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    const nextBoard = {
      ...board,
      columns: board.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    };

    sendBoardAction("rename_column", { column_id: columnId, title }, nextBoard);
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    const id = createId("card");
    const nextBoard = {
      ...board,
      cards: {
        ...board.cards,
        [id]: { id, title, details: details || "No details yet." },
      },
      columns: board.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: [...column.cardIds, id] }
          : column
      ),
    };

    sendBoardAction(
      "add_card",
      {
        column_id: columnId,
        title,
        details: details || "No details yet.",
        card_id: id,
      },
      nextBoard
    );
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    const nextBoard = {
      ...board,
      cards: Object.fromEntries(
        Object.entries(board.cards).filter(([id]) => id !== cardId)
      ),
      columns: board.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: column.cardIds.filter((id) => id !== cardId) }
          : column
      ),
    };

    sendBoardAction(
      "delete_card",
      { column_id: columnId, card_id: cardId },
      nextBoard
    );
  };

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  if (loadingBoard) {
    return (
      <div className="min-h-screen bg-slate-50 px-6 py-16">
        <div className="mx-auto max-w-xl rounded-[32px] border border-[var(--stroke)] bg-white p-10 shadow-[var(--shadow)]">
          <p className="text-sm text-[var(--gray-text)]">Loading your board...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Keep momentum visible. Rename columns, drag cards between stages,
                and capture quick notes without getting buried in settings.
              </p>
            </div>
            <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                Focus
              </p>
              <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                One board. Five columns. Zero clutter.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column) => (
              <div
                key={column.id}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
          </div>
          {(loadError || saveError) && (
            <div className="grid gap-3">
              {loadError && (
                <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {loadError}
                </div>
              )}
              {saveError && (
                <div className="rounded-2xl border border-orange-200 bg-orange-50 px-4 py-3 text-sm text-orange-700">
                  {saveError}
                </div>
              )}
            </div>
          )}
        </header>

        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <section className="grid gap-6 lg:grid-cols-5">
            {board.columns.map((column) => (
              <KanbanColumn
                key={column.id}
                column={column}
                cards={column.cardIds.map((cardId) => board.cards[cardId])}
                onRename={handleRenameColumn}
                onAddCard={handleAddCard}
                onDeleteCard={handleDeleteCard}
              />
            ))}
          </section>
          <DragOverlay>
            {activeCard ? (
              <div className="w-[260px]">
                <KanbanCardPreview card={activeCard} />
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </main>
    </div>
  );
};
