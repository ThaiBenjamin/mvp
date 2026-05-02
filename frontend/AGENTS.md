# Frontend Agent Documentation

## Purpose

This frontend is a working Kanban board demo intended to become the user-facing app for the Project Management MVP.

- Renders a single Kanban board with five columns.
- Supports renaming columns, adding cards, deleting cards, and drag-and-drop card movement.
- Uses a local client-side state model; there is no backend persistence yet.

## Project structure

- `src/app/page.tsx`
  - App entry point for the Next.js page.
  - Imports and renders the `KanbanBoard` component.

- `src/lib/kanban.ts`
  - Defines `Card`, `Column`, and `BoardData` types.
  - Holds the `initialData` demo board.
  - Includes `moveCard` helper for drag/drop logic.
  - Includes `createId` helper for new cards.

- `src/components/KanbanBoard.tsx`
  - Main board container component.
  - Manages board state and active drag overlay state.
  - Uses `@dnd-kit/core` for drag-and-drop.
  - Handles column renaming, card creation, and card deletion.

- `src/components/KanbanColumn.tsx`
  - Renders a single column as a droppable area.
  - Displays column title, card count, card list, and add-card UI.

- `src/components/KanbanCard.tsx`
  - Renders a single draggable card.
  - Includes a remove button to delete the card.

- `src/components/NewCardForm.tsx`
  - Collapsible form for creating new cards.
  - Validates title input before submitting.

- `src/components/KanbanCardPreview.tsx`
  - Displayed inside the drag overlay while a card is being moved.

## Styling

- Tailwind CSS is used for styling.
- Global CSS is in `src/app/globals.css`.
- The current visual theme matches the project design language.

## Tests

- `tests/kanban.spec.ts`
  - Validates the board loads successfully.
  - Tests adding a new card to a column.
  - Tests dragging a card between columns.

## Notes

- The current frontend is a demo-only implementation.
- The next phase should integrate this UI with the backend API and persistence layer.
