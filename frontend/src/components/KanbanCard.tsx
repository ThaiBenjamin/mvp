import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import {
  formatDueDate,
  isOverdue,
  PRIORITY_DOT,
  PRIORITY_LABEL,
  type Card,
} from "@/lib/kanban";
import { CalendarIcon, PencilIcon, TrashIcon } from "@/components/icons";

type KanbanCardProps = {
  card: Card;
  onDelete: (cardId: string) => void;
  onEdit: (card: Card) => void;
};

const iconBtnBase =
  "inline-flex h-7 w-7 items-center justify-center rounded-full bg-white/80 text-[var(--gray-text)] shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary-blue)]";

export const KanbanCard = ({ card, onDelete, onEdit }: KanbanCardProps) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const due = formatDueDate(card.dueDate);
  const overdue = isOverdue(card.dueDate);

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={clsx(
        "group relative rounded-2xl border border-transparent bg-white px-4 py-3.5 shadow-[0_8px_18px_rgba(3,33,71,0.06)]",
        "transition-all duration-150 hover:shadow-[0_12px_26px_rgba(3,33,71,0.1)]",
        isDragging && "opacity-60 shadow-[0_18px_32px_rgba(3,33,71,0.16)]"
      )}
      {...attributes}
      {...listeners}
      data-testid={`card-${card.id}`}
    >
      <div className="pr-14">
        <h4 className="font-display text-sm font-semibold leading-snug text-[var(--navy-dark)]">
          {card.title}
        </h4>
        <p className="mt-1.5 text-xs leading-5 text-[var(--gray-text)]">
          {card.details}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] font-semibold uppercase tracking-wide">
          <span
            className="inline-flex items-center gap-1.5 rounded-full bg-[var(--surface)] px-2 py-0.5 text-[var(--gray-text)]"
            data-testid={`card-${card.id}-priority`}
          >
            <span className={clsx("h-1.5 w-1.5 rounded-full", PRIORITY_DOT[card.priority])} />
            {PRIORITY_LABEL[card.priority]}
          </span>
          {due && (
            <span
              className={clsx(
                "inline-flex items-center gap-1 rounded-full px-2 py-0.5",
                overdue
                  ? "bg-red-50 text-red-600"
                  : "bg-[var(--surface)] text-[var(--gray-text)]"
              )}
              data-testid={`card-${card.id}-due`}
            >
              <CalendarIcon className="h-3 w-3" />
              {due}
            </span>
          )}
        </div>
      </div>
      <div className="absolute right-2 top-2 flex flex-col gap-1 opacity-60 transition group-hover:opacity-100 focus-within:opacity-100">
        <button
          type="button"
          onPointerDown={(event) => event.stopPropagation()}
          onClick={(event) => {
            event.stopPropagation();
            onEdit(card);
          }}
          className={clsx(iconBtnBase, "hover:bg-[var(--surface)] hover:text-[var(--primary-blue)]")}
          aria-label={`Edit ${card.title}`}
        >
          <PencilIcon className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onPointerDown={(event) => event.stopPropagation()}
          onClick={(event) => {
            event.stopPropagation();
            onDelete(card.id);
          }}
          className={clsx(iconBtnBase, "hover:bg-red-50 hover:text-red-600")}
          aria-label={`Delete ${card.title}`}
        >
          <TrashIcon className="h-4 w-4" />
        </button>
      </div>
    </article>
  );
};
