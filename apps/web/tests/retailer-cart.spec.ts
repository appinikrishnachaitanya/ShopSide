import { test, expect } from "@playwright/test";
test("live retailer item is visible in both carts and cannot enter sandbox checkout", async ({
  browser,
}) => {
  test.skip(
    process.env.SHOPSIDE_LIVE_CART !== "1",
    "Requires live Channel3 credentials",
  );
  const url = process.env.SHOPSIDE_TEST_URL || "http://localhost:3000";
  const a = await browser.newContext(),
    b = await browser.newContext({ viewport: { width: 375, height: 812 } });
  const first = await a.newPage(),
    second = await b.newPage();
  await first.goto(url);
  await first.getByLabel("Your name").fill("Shopper A");
  await first.getByRole("button", { name: "Create your shopping room" }).click();
  await expect(first.getByText("Connected", { exact: true })).toBeVisible();
  const id = new URL(first.url()).searchParams.get("room");
  const room = await (await first.request.get(url + "/api/rooms/" + id)).json();
  await second.goto(url + "?invite=" + room.invite);
  await second.getByLabel("Your name").fill("Shopper B");
  await second.getByRole("button", { name: "Join your friend" }).click();
  await expect(first.getByText(/Shopper A & Shopper B/)).toBeVisible();
  await first.getByLabel("Live product search").fill("wireless headphones");
  await first.getByRole("button", { name: "Search Channel3" }).click();
  const card = first
    .locator('.live-product:has(button:not([disabled]):text-is("Add to cart"))')
    .first();
  await expect(card).toBeVisible({ timeout: 30000 });
  const productName = await card.locator("h3").innerText();
  await card.getByRole("button", { name: "Add to cart", exact: true }).click();
  await expect(
    first.getByText(
      "Added to your shared cart. This item is purchased at the retailer.",
    ),
  ).toBeVisible();
  await expect(first.locator(".cart-details")).toHaveAttribute("open", "");
  await expect(
    first
      .getByRole("region", { name: "Retailer items" })
      .getByText(productName, { exact: true }),
  ).toBeVisible();
  await second.locator(".cart-details summary").click();
  await expect(
    second
      .getByRole("region", { name: "Retailer items" })
      .getByText(productName, { exact: true }),
  ).toBeVisible();
  await expect(
    first.getByRole("button", { name: "Review sandbox checkout" }),
  ).toBeDisabled();
  await first.reload();
  await first.locator(".cart-details summary").click();
  await expect(
    first
      .getByRole("region", { name: "Retailer items" })
      .getByText(productName, { exact: true }),
  ).toBeVisible();
  await a.close();
  await b.close();
});
