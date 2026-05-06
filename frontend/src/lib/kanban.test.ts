import { describe, it, expect } from "vitest";
import {
  moveCard,
  formatDueDate,
  isOverdue,
  PRIORITY_LABEL,
  PRIORITY_DOT,
  createId,
  type Column,
} from "@/lib/kanban";

describe("moveCard", () => {
  const baseColumns: Column[] = [
    { id: "col-a", title: "A", cardIds: ["card-1", "card-2"] },
    { id: "col-b", title: "B", cardIds: ["card-3"] },
  ];

  it("reorders cards in the same column", () => {
    const result = moveCard(baseColumns, "card-2", "card-1");
    expect(result[0].cardIds).toEqual(["card-2", "card-1"]);
  });

  it("moves cards to another column", () => {
    const result = moveCard(baseColumns, "card-2", "card-3");
    expect(result[0].cardIds).toEqual(["card-1"]);
    expect(result[1].cardIds).toEqual(["card-2", "card-3"]);
  });

  it("drops cards to the end of a column", () => {
    const result = moveCard(baseColumns, "card-1", "col-b");
    expect(result[0].cardIds).toEqual(["card-2"]);
    expect(result[1].cardIds).toEqual(["card-3", "card-1"]);
  });

  it("moves a card into an empty column", () => {
    const columns = [
      { id: "col-a", title: "A", cardIds: ["card-1"] },
      { id: "col-empty", title: "Empty", cardIds: [] },
    ];

    const result = moveCard(columns, "card-1", "col-empty");

    expect(result[0].cardIds).toEqual([]);
    expect(result[1].cardIds).toEqual(["card-1"]);
  });
});

describe("formatDueDate", () => {
  it("returns null for null input", () => {
    expect(formatDueDate(null)).toBeNull();
  });

  it("returns the input string when unparseable", () => {
    expect(formatDueDate("not-a-date")).toBe("not-a-date");
  });

  it("formats YYYY-MM-DD as a friendly month/day string", () => {
    const out = formatDueDate("2026-06-15");
    expect(out).toBeTruthy();
    expect(out).not.toBe("2026-06-15");
  });
});

describe("isOverdue", () => {
  it("returns false for null", () => {
    expect(isOverdue(null)).toBe(false);
  });

  it("returns true for a past date", () => {
    expect(isOverdue("2000-01-01")).toBe(true);
  });

  it("returns false for a far-future date", () => {
    expect(isOverdue("2099-12-31")).toBe(false);
  });

  it("returns false for unparseable input", () => {
    expect(isOverdue("nope")).toBe(false);
  });
});

describe("priority constants", () => {
  it("provides labels for every priority", () => {
    expect(PRIORITY_LABEL.low).toBe("Low");
    expect(PRIORITY_LABEL.medium).toBe("Medium");
    expect(PRIORITY_LABEL.high).toBe("High");
  });

  it("provides a dot color for every priority", () => {
    expect(PRIORITY_DOT.low).toBeTruthy();
    expect(PRIORITY_DOT.medium).toBeTruthy();
    expect(PRIORITY_DOT.high).toBeTruthy();
  });
});

describe("createId", () => {
  it("uses the supplied prefix", () => {
    expect(createId("card")).toMatch(/^card-/);
    expect(createId("col")).toMatch(/^col-/);
  });

  it("returns distinct ids on successive calls", () => {
    const a = createId("card");
    const b = createId("card");
    expect(a).not.toBe(b);
  });
});
