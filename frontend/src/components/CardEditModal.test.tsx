import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CardEditModal } from "@/components/CardEditModal";
import type { Card } from "@/lib/kanban";

const sampleCard: Card = {
  id: "card-1",
  title: "Sample",
  details: "Original details",
  priority: "medium",
  dueDate: null,
};

describe("CardEditModal", () => {
  it("renders nothing when card is null", () => {
    const { container } = render(
      <CardEditModal card={null} onClose={() => {}} onSave={() => {}} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("submits the edited card fields", async () => {
    const onSave = vi.fn();
    render(<CardEditModal card={sampleCard} onClose={() => {}} onSave={onSave} />);

    const titleInput = screen.getByLabelText(/title/i);
    await userEvent.clear(titleInput);
    await userEvent.type(titleInput, "New title");

    const priority = screen.getByLabelText(/priority/i);
    await userEvent.selectOptions(priority, "high");

    const due = screen.getByLabelText(/due date/i);
    await userEvent.type(due, "2026-12-01");

    await userEvent.click(screen.getByRole("button", { name: /^save$/i }));
    expect(onSave).toHaveBeenCalledWith("card-1", {
      title: "New title",
      details: "Original details",
      priority: "high",
      dueDate: "2026-12-01",
    });
  });

  it("closes on cancel", async () => {
    const onClose = vi.fn();
    render(<CardEditModal card={sampleCard} onClose={onClose} onSave={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onClose).toHaveBeenCalled();
  });
});
