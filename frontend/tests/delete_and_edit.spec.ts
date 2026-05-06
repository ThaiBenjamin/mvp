import { expect, test, type Page } from "@playwright/test";

const signIn = async (page: Page) => {
  await page.goto("/");
  const loginTitle = page.getByRole("heading", { name: /Project Management/ });
  const boardTitle = page.getByRole("heading", { name: "Kanban Studio" }).first();
  await expect(loginTitle.or(boardTitle)).toBeVisible();
  if (await loginTitle.isVisible()) {
    await page.getByPlaceholder("user").fill("user");
    await page.getByPlaceholder("password").fill("password");
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(boardTitle).toBeVisible();
  }
};

test("user can delete a card via the trash button", async ({ page }) => {
  await signIn(page);

  // Add a card so we have a known target.
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  const stamp = `Delete-me-${Date.now()}`;
  await firstColumn.getByPlaceholder("Card title").fill(stamp);
  await firstColumn.getByPlaceholder("Details").fill("temp");
  await firstColumn.getByRole("button", { name: /add card/i }).click();

  const card = page.locator(`[data-testid^="card-"]`, { hasText: stamp });
  await expect(card).toBeVisible();

  // Hover to reveal the delete button.
  await card.hover();
  const deleteBtn = card.getByRole("button", { name: new RegExp(`delete ${stamp}`, "i") });
  await expect(deleteBtn).toBeVisible();
  await deleteBtn.click();

  await expect(card).toHaveCount(0);
});

test("user can edit a card via the pencil button", async ({ page }) => {
  await signIn(page);

  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  const stamp = `Edit-me-${Date.now()}`;
  await firstColumn.getByPlaceholder("Card title").fill(stamp);
  await firstColumn.getByPlaceholder("Details").fill("orig details");
  await firstColumn.getByRole("button", { name: /add card/i }).click();

  const card = page.locator(`[data-testid^="card-"]`, { hasText: stamp });
  await expect(card).toBeVisible();
  await card.hover();
  const editBtn = card.getByRole("button", { name: new RegExp(`edit ${stamp}`, "i") });
  await editBtn.click();

  const modal = page.getByTestId("card-edit-modal");
  await expect(modal).toBeVisible();

  const newTitle = `${stamp}-EDITED`;
  await modal.getByLabel(/title/i).fill(newTitle);
  await modal.getByLabel(/details/i).fill("new details");
  await modal.getByLabel(/priority/i).selectOption("high");
  await modal.getByRole("button", { name: /^save$/i }).click();

  await expect(page.locator(`[data-testid^="card-"]`, { hasText: newTitle })).toBeVisible();
  // Cleanup so re-runs don't pile up cards.
  const editedCard = page.locator(`[data-testid^="card-"]`, { hasText: newTitle });
  await editedCard.hover();
  await editedCard.getByRole("button", { name: new RegExp(`delete ${newTitle}`, "i") }).click();
});
