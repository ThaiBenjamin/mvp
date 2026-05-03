import { describe, expect, it } from "vitest";
import { getTargetDetails, resolveDragOverColumnId } from "./KanbanBoard";

describe("resolveDragOverColumnId", () => {
  it("returns the explicit columnId from droppable metadata when provided", () => {
    const over = {
      id: "placeholder-1",
      data: { current: { columnId: "col-empty" } },
    };

    expect(resolveDragOverColumnId(over)).toBe("col-empty");
  });

  it("falls back to the over id when metadata is missing", () => {
    const over = { id: "col-backlog" };

    expect(resolveDragOverColumnId(over)).toBe("col-backlog");
  });
});

describe("getTargetDetails", () => {
  it("returns index 0 for an empty column target", () => {
    const columns = [
      { id: "col-source", title: "Source", cardIds: ["card-1"] },
      { id: "col-empty", title: "Empty", cardIds: [] },
    ];

    expect(getTargetDetails(columns, "col-empty")).toEqual({
      columnId: "col-empty",
      index: 0,
    });
  });

  it("returns the proper index when targeting an existing card", () => {
    const columns = [
      { id: "col-source", title: "Source", cardIds: ["card-1"] },
      { id: "col-target", title: "Target", cardIds: ["card-2", "card-3"] },
    ];

    expect(getTargetDetails(columns, "card-3")).toEqual({
      columnId: "col-target",
      index: 1,
    });
  });
});
