"use client";

import { useEffect, useMemo, useRef, useState } from "react";
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
import { createId, moveCard, type BoardData } from "@/lib/kanban";
import { buildCollisionDetection, findColumnId } from "@/lib/dnd";
import { api, type BoardAction } from "@/lib/api";

export const KanbanBoard = () => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const dragSourceColumnRef = useRef<string | null>(null);
  const lastOverIdRef = useRef<UniqueIdentifier | null>(null);
  const boardRef = useRef<BoardData | null>(null);
  boardRef.current = board;

  const reloadBoard = async () => {
    try {
      const data = await api.getBoard();
      setBoard(data);
      setLoadError(null);
    } catch {
      setLoadError("Unable to load board from server. Please retry.");
    }
  };

  useEffect(() => {
    reloadBoard();
  }, []);

  const sendBoardAction = async (action: BoardAction, optimisticBoard: BoardData) => {
    setBoard(optimisticBoard);
    setSaveError(null);
    try {
      const updatedBoard = await api.postBoardAction(action);
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
  const columns = board?.columns ?? [];

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

      // No-op short-circuit: if the active card is already at insertAt in the
      // target column and removed from the source, return prev to avoid an
      // unnecessary re-render.
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

  const handleAddCard = (columnId: string, title: string, details: string) => {
    if (!board) return;
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
      {
        action: "add_card",
        payload: {
          column_id: columnId,
          title,
          details: details || "No details yet.",
          card_id: id,
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
    <div className="flex flex-col gap-6">
      {saveError && (
        <div className="rounded-2xl border border-orange-200 bg-orange-50 px-4 py-3 text-sm text-orange-700">
          {saveError}
        </div>
      )}
      <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
        <DndContext
          sensors={sensors}
          collisionDetection={collisionDetection}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDragEnd={handleDragEnd}
        >
          <section className="grid flex-1 gap-6 sm:grid-cols-2 lg:grid-cols-5">
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
        <div className="w-full lg:w-[360px] lg:flex-shrink-0">
          <AiChat onBoardUpdated={setBoard} />
        </div>
      </div>
    </div>
  );
};
