import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData } from "@/lib/kanban";

const getFirstColumn = () => screen.getAllByTestId(/column-/i)[0];

const createFetchResponse = (payload: unknown) =>
  Promise.resolve({ ok: true, json: async () => payload });

describe("KanbanBoard", () => {
  const fetchMock = vi.fn();
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
    let currentBoard = structuredClone(initialData);

    fetchMock.mockImplementation(async (input: string, init?: RequestInit) => {
      if (input === "/api/board") {
        return createFetchResponse(currentBoard);
      }

      if (input === "/api/board/actions") {
        const requestBody = init?.body ? JSON.parse(init.body as string) : {};
        const action = requestBody.action;
        const payload = requestBody.payload || {};

        if (action === "rename_column") {
          currentBoard = {
            ...currentBoard,
            columns: currentBoard.columns.map((column) =>
              column.id === payload.column_id
                ? { ...column, title: payload.title }
                : column
            ),
          };
        }

        if (action === "add_card") {
          const cardId = payload.card_id;
          currentBoard = {
            ...currentBoard,
            cards: {
              ...currentBoard.cards,
              [cardId]: {
                id: cardId,
                title: payload.title,
                details: payload.details,
              },
            },
            columns: currentBoard.columns.map((column) =>
              column.id === payload.column_id
                ? { ...column, cardIds: [...column.cardIds, cardId] }
                : column
            ),
          };
        }

        if (action === "delete_card") {
          currentBoard = {
            ...currentBoard,
            cards: Object.fromEntries(
              Object.entries(currentBoard.cards).filter(
                ([id]) => id !== payload.card_id
              )
            ),
            columns: currentBoard.columns.map((column) =>
              column.id === payload.column_id
                ? {
                    ...column,
                    cardIds: column.cardIds.filter(
                      (id) => id !== payload.card_id
                    ),
                  }
                : column
            ),
          };
        }

        return createFetchResponse(currentBoard);
      }

      return Promise.resolve({ ok: false, json: async () => ({}) });
    });

    Object.defineProperty(globalThis, "fetch", {
      writable: true,
      value: fetchMock,
    });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders five columns", async () => {
    render(<KanbanBoard />);
    await waitFor(() => expect(screen.getAllByTestId(/column-/i)).toHaveLength(5));
  });

  it("renames a column and sends an action request", async () => {
    render(<KanbanBoard />);

    await waitFor(() => expect(screen.getAllByTestId(/column-/i)).toHaveLength(5));

    const column = getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");

    await waitFor(() => {
      const actionCalls = fetchMock.mock.calls.filter(
        ([url]) => url === "/api/board/actions"
      );
      expect(actionCalls.length).toBeGreaterThanOrEqual(1);
    });

    const actionCalls = fetchMock.mock.calls.filter(
      ([url]) => url === "/api/board/actions"
    );
    const actionRequest = actionCalls[actionCalls.length - 1][1];
    expect(actionRequest.method).toBe("POST");
    expect(JSON.parse(actionRequest.body)).toMatchObject({
      action: "rename_column",
      payload: {
        column_id: initialData.columns[0].id,
        title: "New Name",
      },
    });

    expect(input).toHaveValue("New Name");
  });

  it("adds and removes a card", async () => {
    render(<KanbanBoard />);
    await waitFor(() => expect(screen.getAllByTestId(/column-/i)).toHaveLength(5));

    const column = getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(within(column).getByText("New card")).toBeInTheDocument();

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await userEvent.click(deleteButton);

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });
});
