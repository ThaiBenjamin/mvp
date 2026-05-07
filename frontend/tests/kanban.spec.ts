import { expect, test, type Locator, type Page } from "@playwright/test";
import { addCard, signIn } from "./helpers";

// dnd-kit's PointerSensor has a 6px activation distance and updates `over`
// only on pointermove. Playwright's `Locator.dragTo` performs a single-step
// mouse.move which does not give dnd-kit enough events to track the pointer
// across multiple droppables. This helper performs an explicit multi-step
// drag that mimics a real user.
const dragCardTo = async (page: Page, source: Locator, target: Locator) => {
  // Make sure both endpoints are in the viewport before measuring; otherwise
  // boundingBox returns coordinates outside the viewport and the synthetic
  // pointer events go nowhere.
  await source.scrollIntoViewIfNeeded();
  await target.scrollIntoViewIfNeeded();

  const viewport = page.viewportSize();
  const viewportH = viewport?.height ?? 720;

  const sourceBox = await source.boundingBox();
  const targetBox = await target.boundingBox();
  if (!sourceBox || !targetBox) {
    throw new Error("Drag source or target has no bounding box");
  }

  const clampY = (box: { y: number; height: number }) => {
    const bottom = Math.min(box.y + box.height, viewportH - 4);
    const top = Math.max(box.y, 4);
    return (top + bottom) / 2;
  };

  const sx = sourceBox.x + sourceBox.width / 2;
  const sy = clampY(sourceBox);
  const tx = targetBox.x + targetBox.width / 2;
  const ty = clampY(targetBox);

  await page.mouse.move(sx, sy);
  await page.mouse.down();
  // Nudge past dnd-kit's 6px activation distance, then traverse to the target.
  await page.mouse.move(sx + 8, sy + 8, { steps: 1 });
  await page.mouse.move(tx, ty, { steps: 8 });
  await page.waitForTimeout(50);
  await page.mouse.up();
};

test("loads the kanban board", async ({ page }) => {
  await signIn(page);
  await expect(page.getByRole("heading", { name: "Kanban Studio" }).first()).toBeVisible();
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
});

test("adds a card to a column", async ({ page }) => {
  await signIn(page);
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await addCard(firstColumn, "Playwright card", "Added via e2e.");
  await expect(firstColumn.getByText("Playwright card")).toBeVisible();
});

test("allows login and logout", async ({ page }) => {
  await page.goto("/");

  await page.getByPlaceholder("user").fill("user");
  await page.getByPlaceholder("password").fill("password");
  await page.getByRole("button", { name: /sign in/i }).click();

  await expect(page.getByRole("heading", { name: "Kanban Studio" }).first()).toBeVisible();
  await page.getByRole("button", { name: /log out/i }).click();

  await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
});

test("persists board changes across logout and login", async ({ page }) => {
  await signIn(page);
  const cardTitle = `Persistence card ${Date.now()}`;

  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await addCard(firstColumn, cardTitle, "Saved across sessions.");

  await expect(firstColumn.getByText(cardTitle)).toBeVisible();
  await page.getByRole("button", { name: /log out/i }).click();
  await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();

  await signIn(page);
  await expect(page.getByText(cardTitle)).toBeVisible();
});

test("moves a card into an empty column", async ({ page }) => {
  await signIn(page);

  // Move the only card from Discovery into Backlog to create an empty column.
  await dragCardTo(
    page,
    page.getByTestId("card-card-3"),
    page.getByTestId("column-col-backlog")
  );

  await expect(
    page.getByTestId("column-col-discovery").getByText("Drop a card here")
  ).toBeVisible();

  // Drag another card into the newly emptied Discovery column.
  await dragCardTo(
    page,
    page.getByTestId("card-card-1"),
    page.getByTestId("column-col-discovery")
  );

  await expect(
    page.getByTestId("column-col-discovery").getByText("Align roadmap themes")
  ).toBeVisible();
});
