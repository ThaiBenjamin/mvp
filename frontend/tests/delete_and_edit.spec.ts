import { expect, test } from "@playwright/test";
import { addCard, signIn } from "./helpers";

test("user can delete a card via the trash button", async ({ page }) => {
  await signIn(page);

  const firstColumn = page.locator('[data-testid^="column-"]').first();
  const stamp = `Delete-me-${Date.now()}`;
  await addCard(firstColumn, stamp, "temp");

  const card = page.locator(`[data-testid^="card-"]`, { hasText: stamp });
  await expect(card).toBeVisible();

  await card.hover();
  const deleteBtn = card.getByRole("button", { name: new RegExp(`delete ${stamp}`, "i") });
  await expect(deleteBtn).toBeVisible();
  await deleteBtn.click();

  await expect(card).toHaveCount(0);
});

test("user can edit a card via the pencil button", async ({ page }) => {
  await signIn(page);

  const firstColumn = page.locator('[data-testid^="column-"]').first();
  const stamp = `Edit-me-${Date.now()}`;
  await addCard(firstColumn, stamp, "orig details");

  const card = page.locator(`[data-testid^="card-"]`, { hasText: stamp });
  await expect(card).toBeVisible();
  await card.hover();
  await card.getByRole("button", { name: new RegExp(`edit ${stamp}`, "i") }).click();

  const modal = page.getByTestId("card-edit-modal");
  await expect(modal).toBeVisible();

  const newTitle = `${stamp}-EDITED`;
  await modal.getByLabel(/title/i).fill(newTitle);
  await modal.getByLabel(/details/i).fill("new details");
  await modal.getByLabel(/priority/i).selectOption("high");
  await modal.getByRole("button", { name: /^save$/i }).click();

  const editedCard = page.locator(`[data-testid^="card-"]`, { hasText: newTitle });
  await expect(editedCard).toBeVisible();
  // Cleanup so re-runs don't pile up cards.
  await editedCard.hover();
  await editedCard.getByRole("button", { name: new RegExp(`delete ${newTitle}`, "i") }).click();
});
