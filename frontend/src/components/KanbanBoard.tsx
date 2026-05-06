"use client";

import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
  type UniqueIdentifier,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { AiChat } from "@/components/AiChat";
import { CardEditModal } from "@/components/CardEditModal";
import { PlusIcon, XIcon } from "@/components/icons";
import {
  createId,
  moveCard,
  type BoardData,
  type Card,
  type Priority,
} from "@/lib/kanban";
import { buildCollisionDetection, findColumnId } from "@/lib/dnd";
import { api, type BoardAction } from "@/lib/api";

type KanbanBoardProps = {
  boardId?: number;
};

export const KanbanBoard = ({ boardId }: KanbanBoardProps = {}) => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [editingCard, setEditingCard] = useState<Card | null>(null);
  const [creatingColumn, setCreatingColumn] = useState(false);
  const [newColumnName, setNewColumnName] = useState("");
  const dragSourceColumnRef = useRef<string | null>(null);
  const lastOverIdRef = useRef<UniqueIdentifier | null>(null);
  const boardRef = useRef<BoardData | null>(null);
  boardRef.current = board;

  const reloadBoard = async () => {
    try {
      const data = boardId
        ? await api.getBoardState(boardId)
        : await api.getBoard();
      const next: BoardData = { columns: data.columns, cards: data.cards };
      setBoard(next);
      setLoadError(null);
    } catch {
      setLoadError("Unable to load board from server. Please retry.");
    }
  };

  useEffect(() => {
    setBoard(null);
    reloadBoard();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [boardId]);

  const sendBoardAction = async (action: BoardAction, optimisticBoard: BoardData) => {
    setBoard(optimisticBoard);
    setSaveError(null);
    try {
      const updatedBoard = boardId
        ? await api.postBoardAction(boardId, action)
        : await fetch("/api/board/actions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(action),
          }).then((r) => {
            if (!r.ok) throw new Error("save failed");
            return r.json() as Promise<BoardData>;
          });
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

  const cardsById = useMemo(() => board?.cards ?? {}, [board]);
  const columns = useMemo(() => board?.columns ?? [], [board]);

  const collisionDetection = useMemo(
    () => buildCollisionDetection(columns, lastOverIdRef),
    [columns]
  );

  const handleDragStart = (event: DragStartEvent) => {
    if (!board) return;
    const activeId = event.active.id as string;
    setActiveCardId(activeId);
    dragSourceColumnRef.current = findColumnId(board.columns, activeId);
    lastOverIdRef.current = null;
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { active, over } = event;
    if (!over) return;

    const activeId = active.id as string;
    const overId = String(over.id);
    if (activeId === overId) return;

    setBoard((prev) => {
      if (!prev) return prev;
      const activeColumn = findColumnId(prev.columns, activeId);
      const overColumn = findColumnId(prev.columns, overId);
      if (!activeColumn || !overColumn || activeColumn === overColumn) return prev;

      const fromCol = prev.columns.find((c) => c.id === activeColumn);
      const toCol = prev.columns.find((c) => c.id === overColumn);
      if (!fromCol || !toCol) return prev;

      const remaining = fromCol.cardIds.filter((id) => id !== activeId);
      const overIsColumn = toCol.id === overId;
      const insertAt = overIsColumn
        ? toCol.cardIds.length
        : (() => {
            const idx = toCol.cardIds.indexOf(overId);
            return idx === -1 ? toCol.cardIds.length : idx;
          })();

      const updatedTo = [...toCol.cardIds];
      updatedTo.splice(insertAt, 0, activeId);

      if (
        toCol.cardIds[insertAt] === activeId &&
        !fromCol.cardIds.includes(activeId)
      ) {
        return prev;
      }

      return {
        ...prev,
        columns: prev.columns.map((column) => {
          if (column.id === activeColumn) return { ...column, cardIds: remaining };
          if (column.id === overColumn) return { ...column, cardIds: updatedTo };
          return column;
        }),
      };
    });
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    const activeId = active.id as string;
    const sourceColumnId = dragSourceColumnRef.current;
    setActiveCardId(null);
    dragSourceColumnRef.current = null;
    lastOverIdRef.current = null;

    if (!over) return;
    const currentBoard = boardRef.current;
    if (!currentBoard) return;

    const finalColumnId = findColumnId(currentBoard.columns, activeId);
    if (!finalColumnId) return;
    const finalColumn = currentBoard.columns.find((c) => c.id === finalColumnId);
    if (!finalColumn) return;
    const finalIndex = finalColumn.cardIds.indexOf(activeId);

    if (finalColumnId === sourceColumnId) {
      const overId = String(over.id);
      if (overId !== activeId && finalColumn.cardIds.includes(overId)) {
        const nextColumns = moveCard(currentBoard.columns, activeId, overId);
        const reordered = nextColumns.find((c) => c.id === finalColumnId);
        if (!reordered) return;
        const reorderedIndex = reordered.cardIds.indexOf(activeId);
        if (reorderedIndex === finalIndex) return;
        const nextBoard = { ...currentBoard, columns: nextColumns };
        sendBoardAction(
          {
            action: "move_card",
            payload: {
              card_id: activeId,
              target_column_id: finalColumnId,
              target_index: reorderedIndex,
            },
          },
          nextBoard
        );
      }
      return;
    }

    sendBoardAction(
      {
        action: "move_card",
        payload: {
          card_id: activeId,
          target_column_id: finalColumnId,
          target_index: finalIndex,
        },
      },
      currentBoard
    );
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    if (!board) return;
    const nextBoard = {
      ...board,
      columns: board.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    };
    sendBoardAction(
      { action: "rename_column", payload: { column_id: columnId, title } },
      nextBoard
    );
  };

  const handleAddCard = (
    columnId: string,
    title: string,
    details: string,
    priority: Priority,
    dueDate: string | null
  ) => {
    if (!board) return;
    const id = createId("card");
    const nextBoard = {
      ...board,
      cards: {
        ...board.cards,
        [id]: {
          id,
          title,
          details: details || "No details yet.",
          priority,
          dueDate,
        },
      },
      columns: board.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: [...column.cardIds, id] }
          : column
      ),
    };
    sendBoardAction(
      {
        action: "add_card",
        payload: {
          column_id: columnId,
          title,
          details: details || "No details yet.",
          card_id: id,
          priority,
          dueDate,
        },
      },
      nextBoard
    );
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    if (!board) return;
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
      { action: "delete_card", payload: { card_id: cardId } },
      nextBoard
    );
  };

  const handleDeleteColumn = (columnId: string) => {
    if (!board) return;
    const target = board.columns.find((c) => c.id === columnId);
    if (!target) return;
    if (target.cardIds.length > 0) {
      setSaveError("Move or delete the cards in this column before deleting it.");
      return;
    }
    const nextBoard = {
      ...board,
      columns: board.columns.filter((c) => c.id !== columnId),
    };
    sendBoardAction(
      { action: "delete_column", payload: { column_id: columnId } },
      nextBoard
    );
  };

  const handleAddColumn = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!board || !newColumnName.trim()) return;
    const newId = createId("col");
    const trimmed = newColumnName.trim();
    const nextBoard = {
      ...board,
      columns: [...board.columns, { id: newId, title: trimmed, cardIds: [] }],
    };
    sendBoardAction(
      { action: "add_column", payload: { title: trimmed, column_id: newId } },
      nextBoard
    );
    setNewColumnName("");
    setCreatingColumn(false);
  };

  const handleEditCard = (
    cardId: string,
    fields: { title: string; details: string; priority: Priority; dueDate: string | null }
  ) => {
    if (!board) return;
    const existing = board.cards[cardId];
    if (!existing) return;
    const nextBoard = {
      ...board,
      cards: { ...board.cards, [cardId]: { ...existing, ...fields } },
    };
    sendBoardAction(
      {
        action: "update_card",
        payload: {
          card_id: cardId,
          title: fields.title,
          details: fields.details,
          priority: fields.priority,
          dueDate: fields.dueDate,
        },
      },
      nextBoard
    );
    setEditingCard(null);
  };

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  if (!board) {
    if (loadError) {
      return (
        <div className="flex flex-col gap-4">
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {loadError}
          </div>
          <button
            type="button"
            onClick={reloadBoard}
            className="self-start rounded-full bg-[var(--primary-blue)] px-4 py-2 text-sm font-semibold text-white"
          >
            Retry
          </button>
        </div>
      );
    }
    return <p className="text-sm text-[var(--gray-text)]">Loading your board...</p>;
  }

  return (
    <div className="flex flex-col gap-4">
      {saveError && (
        <div className="rounded-xl border border-orange-200 bg-orange-50 px-4 py-2.5 text-sm text-orange-700">
          {saveError}
        </div>
      )}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
        <DndContext
          sensors={sensors}
          collisionDetection={collisionDetection}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDragEnd={handleDragEnd}
        >
          <section className="flex min-w-0 flex-1 flex-wrap content-start gap-3">
            {board.columns.map((column) => (
              <div key={column.id} className="min-w-[260px] flex-1 sm:max-w-[340px]">
                <KanbanColumn
                  column={column}
                  cards={column.cardIds.map((cardId) => board.cards[cardId])}
                  onRename={handleRenameColumn}
                  onAddCard={handleAddCard}
                  onDeleteCard={handleDeleteCard}
                  onEditCard={setEditingCard}
                  onDeleteColumn={handleDeleteColumn}
                  canDeleteColumn={board.columns.length > 1}
                />
              </div>
            ))}
            <div className="min-w-[220px] flex-1 sm:max-w-[260px]">
              {creatingColumn ? (
                <form
                  onSubmit={handleAddColumn}
                  className="flex flex-col gap-2 rounded-2xl border border-dashed border-[var(--stroke)] bg-white/80 p-3"
                >
                  <input
                    value={newColumnName}
                    onChange={(event) => setNewColumnName(event.target.value)}
                    placeholder="Column title"
                    autoFocus
                    className="w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm font-medium text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
                    required
                  />
                  <div className="flex gap-2">
                    <button
                      type="submit"
                      className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-full bg-[var(--secondary-purple)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:brightness-110"
                    >
                      <PlusIcon className="h-3.5 w-3.5" />
                      Add column
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setCreatingColumn(false);
                        setNewColumnName("");
                      }}
                      aria-label="Cancel"
                      className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-[var(--stroke)] text-[var(--gray-text)] hover:text-[var(--navy-dark)]"
                    >
                      <XIcon className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </form>
              ) : (
                <button
                  type="button"
                  onClick={() => setCreatingColumn(true)}
                  className="flex h-full min-h-[120px] w-full items-center justify-center gap-1.5 rounded-2xl border border-dashed border-[var(--stroke)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--primary-blue)] transition hover:border-[var(--primary-blue)] hover:bg-[var(--surface)]"
                >
                  <PlusIcon className="h-3.5 w-3.5" />
                  Add column
                </button>
              )}
            </div>
          </section>
          <DragOverlay>
            {activeCard ? (
              <div className="w-[240px]">
                <KanbanCardPreview card={activeCard} />
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
        <div className="w-full lg:w-[320px] lg:flex-shrink-0">
          <AiChat
            boardId={boardId}
            onBoardUpdated={(next) =>
              setBoard({ columns: next.columns, cards: next.cards })
            }
          />
        </div>
      </div>
      <CardEditModal
        card={editingCard}
        onClose={() => setEditingCard(null)}
        onSave={handleEditCard}
      />
    </div>
  );
};
