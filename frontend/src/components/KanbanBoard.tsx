"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  getFirstCollision,
  pointerWithin,
  rectIntersection,
  type CollisionDetection,
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
  type UniqueIdentifier,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { AiChat } from "@/components/AiChat";
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

const isColumnId = (columns: BoardData["columns"], id: UniqueIdentifier) =>
  columns.some((column) => column.id === id);

// Multi-container kanban collision detection (adapted from the dnd-kit
// MultipleContainers example). Pointer-first so empty columns win when the
// cursor is over them, then drill down to the nearest card inside the column
// so within-column reordering still works.
export const buildCollisionDetection = (
  columns: BoardData["columns"],
  lastOverIdRef: { current: UniqueIdentifier | null }
): CollisionDetection => (args) => {
  const filtered = {
    ...args,
    droppableContainers: args.droppableContainers.filter(
      (container) => container.id !== args.active?.id
    ),
  };

  const pointerCollisions = pointerWithin(filtered);
  const intersections =
    pointerCollisions.length > 0 ? pointerCollisions : rectIntersection(filtered);
  let overId = getFirstCollision(intersections, "id");

  if (overId == null) {
    overId = getFirstCollision(closestCorners(filtered), "id") ?? null;
  }

  if (overId != null && isColumnId(columns, overId)) {
    const column = columns.find((c) => c.id === overId);
    if (column && column.cardIds.length > 0) {
      const cardSet = new Set<UniqueIdentifier>(column.cardIds);
      const inner = closestCorners({
        ...filtered,
        droppableContainers: filtered.droppableContainers.filter(
          (container) => container.id !== overId && cardSet.has(container.id)
        ),
      });
      const innerId = getFirstCollision(inner, "id");
      if (innerId != null) overId = innerId;
    }
  }

  if (overId == null) {
    return lastOverIdRef.current ? [{ id: lastOverIdRef.current }] : [];
  }

  lastOverIdRef.current = overId;
  return [{ id: overId }];
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
  const dragSourceColumnRef = useRef<string | null>(null);
  const lastOverIdRef = useRef<UniqueIdentifier | null>(null);
  const boardRef = useRef<BoardData>(board);
  boardRef.current = board;

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

  const collisionDetection = useMemo(
    () => buildCollisionDetection(board.columns, lastOverIdRef),
    [board.columns]
  );

  const handleDragStart = (event: DragStartEvent) => {
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
          "move_card",
          {
            card_id: activeId,
            target_column_id: finalColumnId,
            target_index: reorderedIndex,
          },
          nextBoard
        );
      }
      return;
    }

    sendBoardAction(
      "move_card",
      {
        card_id: activeId,
        target_column_id: finalColumnId,
        target_index: finalIndex,
      },
      currentBoard
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
      <p className="text-sm text-[var(--gray-text)]">Loading your board...</p>
    );
  }

  return (
    <div className="flex flex-col gap-6">
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
