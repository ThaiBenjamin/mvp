import { expect, type Locator, type Page } from "@playwright/test";

export const signIn = async (page: Page) => {
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

export const addCard = async (
  column: Locator,
  title: string,
  details: string,
): Promise<void> => {
  await column.getByRole("button", { name: /add a card/i }).click();
  await column.getByPlaceholder("Card title").fill(title);
  await column.getByPlaceholder("Details").fill(details);
  await column.getByRole("button", { name: /add card/i }).click();
};
