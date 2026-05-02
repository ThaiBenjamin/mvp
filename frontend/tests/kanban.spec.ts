import { expect, test } from "@playwright/test";

const signIn = async (page: any) => {
  await page.goto("/");
  const loginTitle = page.getByRole("heading", { name: "Project Management MVP" });
  if (await loginTitle.isVisible()) {
    await page.getByPlaceholder("user").fill("user");
    await page.getByPlaceholder("password").fill("password");
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page.getByRole("heading", { name: "Kanban Studio" }).first()).toBeVisible();
  }
};

test("loads the kanban board", async ({ page }) => {
  await signIn(page);
  await expect(page.getByRole("heading", { name: "Kanban Studio" }).first()).toBeVisible();
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
});

test("adds a card to a column", async ({ page }) => {
  await signIn(page);
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Playwright card");
  await firstColumn.getByPlaceholder("Details").fill("Added via e2e.");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
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
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill(cardTitle);
  await firstColumn.getByPlaceholder("Details").fill("Saved across sessions.");
  await firstColumn.getByRole("button", { name: /add card/i }).click();

  await expect(firstColumn.getByText(cardTitle)).toBeVisible();
  await page.getByRole("button", { name: /log out/i }).click();
  await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();

  await signIn(page);
  await expect(page.getByText(cardTitle)).toBeVisible();
});
