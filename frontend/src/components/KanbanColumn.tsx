import clsx from "clsx";
import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import type { Card, Column, Priority } from "@/lib/kanban";
import { KanbanCard } from "@/components/KanbanCard";
import { NewCardForm } from "@/components/NewCardForm";
import { TrashIcon } from "@/components/icons";

type KanbanColumnProps = {
  column: Column;
  cards: Card[];
  onRename: (columnId: string, title: string) => void;
  onAddCard: (
    columnId: string,
    title: string,
    details: string,
    priority: Priority,
    dueDate: string | null
  ) => void;
  onDeleteCard: (columnId: string, cardId: string) => void;
  onEditCard: (card: Card) => void;
  onDeleteColumn: (columnId: string) => void;
  canDeleteColumn: boolean;
};

export const KanbanColumn = ({
  column,
  cards,
  onRename,
  onAddCard,
  onDeleteCard,
  onEditCard,
  onDeleteColumn,
  canDeleteColumn,
}: KanbanColumnProps) => {
  const { setNodeRef, isOver } = useDroppable({
    id: column.id,
    data: { columnId: column.id },
  });

  const canDelete = canDeleteColumn && cards.length === 0;

  return (
    <section
      ref={setNodeRef}
      className={clsx(
        "flex min-h-[420px] flex-col rounded-2xl border border-[var(--stroke)] bg-[var(--surface-strong)] p-3 shadow-[0_8px_22px_rgba(3,33,71,0.06)] transition",
        isOver && "border-[var(--accent-yellow)]"
      )}
      data-testid={`column-${column.id}`}
    >
      <header className="group mb-2 flex items-center gap-2 px-1">
        <span className="h-1.5 w-1.5 flex-shrink-0 rounded-full bg-[var(--accent-yellow)]" />
        <input
          value={column.title}
          onChange={(event) => onRename(column.id, event.target.value)}
          className="min-w-0 flex-1 bg-transparent font-display text-sm font-semibold tracking-wide text-[var(--navy-dark)] outline-none"
          aria-label="Column title"
        />
        <span className="flex-shrink-0 rounded-full bg-[var(--surface)] px-2 py-0.5 text-[10px] font-semibold tabular-nums text-[var(--gray-text)]">
          {cards.length}
        </span>
        <button
          type="button"
          onClick={() => onDeleteColumn(column.id)}
          disabled={!canDelete}
          aria-label={`Delete column ${column.title}`}
          title={
            canDeleteColumn
              ? cards.length === 0
                ? "Delete column"
                : "Move all cards out before deleting"
              : "Cannot delete the only column"
          }
          className="inline-flex h-6 w-6 items-center justify-center rounded-full text-[var(--gray-text)] opacity-0 transition group-hover:opacity-100 hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-30"
        >
          <TrashIcon className="h-3 w-3" />
        </button>
      </header>
      <div
        className={clsx(
          "flex flex-1 flex-col gap-2 rounded-xl p-1 transition",
          isOver && "bg-[rgba(236,173,10,0.08)]"
        )}
      >
        <SortableContext items={column.cardIds} strategy={verticalListSortingStrategy}>
          {cards.map((card) => (
            <KanbanCard
              key={card.id}
              card={card}
              onDelete={(cardId) => onDeleteCard(column.id, cardId)}
              onEdit={onEditCard}
            />
          ))}
        </SortableContext>
        {cards.length === 0 && (
          <div className="flex flex-1 items-center justify-center rounded-xl border border-dashed border-[var(--stroke)] px-3 py-6 text-center text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
            Drop a card here
          </div>
        )}
      </div>
      <NewCardForm
        onAdd={(title, details, priority, dueDate) =>
          onAddCard(column.id, title, details, priority, dueDate)
        }
      />
    </section>
  );
};
