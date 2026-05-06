import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BoardSidebar } from "@/components/BoardSidebar";
import type { BoardSummary } from "@/lib/kanban";

const sampleBoards: BoardSummary[] = [
  {
    id: 1,
    name: "First",
    position: 0,
    archived: false,
    version: 1,
    updatedAt: "2026-01-01",
  },
  {
    id: 2,
    name: "Second",
    position: 1,
    archived: false,
    version: 1,
    updatedAt: "2026-01-02",
  },
];

const noop = () => undefined;

describe("BoardSidebar", () => {
  it("renders all boards", () => {
    render(
      <BoardSidebar
        boards={sampleBoards}
        activeId={1}
        onSelect={noop}
        onCreate={noop}
        onRename={noop}
        onDelete={noop}
      />
    );
    expect(screen.getByText("First")).toBeInTheDocument();
    expect(screen.getByText("Second")).toBeInTheDocument();
  });

  it("invokes onSelect when a board is clicked", async () => {
    const onSelect = vi.fn();
    render(
      <BoardSidebar
        boards={sampleBoards}
        activeId={1}
        onSelect={onSelect}
        onCreate={noop}
        onRename={noop}
        onDelete={noop}
      />
    );
    await userEvent.click(screen.getByTestId("board-tab-2"));
    expect(onSelect).toHaveBeenCalledWith(2);
  });

  it("invokes onCreate after submitting the new-board form", async () => {
    const onCreate = vi.fn();
    render(
      <BoardSidebar
        boards={sampleBoards}
        activeId={1}
        onSelect={noop}
        onCreate={onCreate}
        onRename={noop}
        onDelete={noop}
      />
    );
    await userEvent.click(screen.getByLabelText(/create new board/i));
    await userEvent.type(screen.getByPlaceholderText(/board name/i), "Roadmap");
    await userEvent.click(screen.getByRole("button", { name: /create board/i }));
    expect(onCreate).toHaveBeenCalledWith("Roadmap");
  });

  it("disables delete on the only board", () => {
    render(
      <BoardSidebar
        boards={[sampleBoards[0]]}
        activeId={1}
        onSelect={noop}
        onCreate={noop}
        onRename={noop}
        onDelete={noop}
      />
    );
    const button = screen.getByRole("button", { name: /delete first/i });
    expect(button).toBeDisabled();
  });

  it("invokes onRename after submitting the rename form", async () => {
    const onRename = vi.fn();
    render(
      <BoardSidebar
        boards={sampleBoards}
        activeId={1}
        onSelect={noop}
        onCreate={noop}
        onRename={onRename}
        onDelete={noop}
      />
    );
    await userEvent.click(screen.getByRole("button", { name: /rename first/i }));
    const input = screen.getByDisplayValue("First");
    await userEvent.clear(input);
    await userEvent.type(input, "Inbox");
    await userEvent.click(screen.getByRole("button", { name: /save/i }));
    expect(onRename).toHaveBeenCalledWith(1, "Inbox");
  });
});
