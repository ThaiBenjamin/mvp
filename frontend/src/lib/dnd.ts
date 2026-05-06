import {
  closestCorners,
  getFirstCollision,
  pointerWithin,
  rectIntersection,
  type CollisionDetection,
  type UniqueIdentifier,
} from "@dnd-kit/core";
import type { BoardData } from "@/lib/kanban";

export const findColumnId = (
  columns: BoardData["columns"],
  id: string
): string | null => {
  if (columns.some((column) => column.id === id)) return id;
  return columns.find((column) => column.cardIds.includes(id))?.id ?? null;
};

const isColumnId = (columns: BoardData["columns"], id: UniqueIdentifier) =>
  columns.some((column) => column.id === id);

/**
 * Multi-container collision detection (dnd-kit MultipleContainers pattern).
 *
 * - Filters the active draggable's own droppable so a card can never be
 *   reported as dropped onto itself.
 * - Pointer-first: if the cursor is inside a droppable rect, prefer those
 *   matches so empty columns win.
 * - When the winner is a column with cards, drill down to the closest card
 *   inside it for accurate insert positioning.
 * - `lastOverIdRef` is sticky: if collision detection briefly returns
 *   nothing, keep the last known target so onDragEnd has something to
 *   commit.
 */
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
