import { expect, test } from "@playwright/test";

test("login page loads and shows the form", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await expect(page.getByLabel("Email")).toBeVisible();
  await expect(page.getByLabel("Password")).toBeVisible();
});

test("unauthenticated visit to / redirects to /login", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
});

test("login page links to signup", async ({ page }) => {
  await page.goto("/login");
  const signup = page.getByRole("link", { name: /create an organisation/i });
  await expect(signup).toBeVisible();
});
