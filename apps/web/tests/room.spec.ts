import { test, expect } from "@playwright/test";
test("desktop and mobile share persisted room", async ({ browser }) => {
  const testBase = process.env.SHOPSIDE_TEST_URL || "http://localhost:3000";
  const a = await browser.newContext({
    permissions: ["clipboard-read", "clipboard-write"],
  });
  const b = await browser.newContext({ viewport: { width: 375, height: 812 } });
  const first = await a.newPage(),
    second = await b.newPage();
  await first.goto(testBase);
  await first.getByLabel("Your name").fill("Krishna");
  await first.getByRole("button", { name: "Create your room" }).click();
  await expect(first.getByText("Connected", { exact: true })).toBeVisible();
  const roomId = new URL(first.url()).searchParams.get("room");
  const state = await (
    await first.request.get(testBase + "/api/rooms/" + roomId)
  ).json();
  await second.goto(testBase + "?invite=" + state.invite);
  await second.getByLabel("Your name").fill("Priya");
  await second.getByRole("button", { name: "Join your friend" }).click();
  await expect(second.getByText("Connected", { exact: true })).toBeVisible();
  await expect(first.getByText(/Krishna & Priya/)).toBeVisible();
  await first
    .getByRole("button", { name: /Quiet Hours.*Look at this/ })
    .click();
  await expect(second.locator(".stage h2")).toHaveText("Quiet Hours");
  await second.getByRole("button", { name: /Like ·/ }).click();
  await expect(
    first.getByRole("button", { name: /Like · Priya/ }),
  ).toBeVisible();
  await first.reload();
  await second.reload();
  await expect(first.locator(".stage h2")).toHaveText("Quiet Hours");
  await expect(
    second.getByRole("button", { name: /Like · Priya/ }),
  ).toBeVisible();
  expect(
    await second.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await expect(first.getByText(/Krishna & Priya/)).toBeVisible();
  await first
    .getByRole("button", { name: "Save to Together", exact: true })
    .click();
  await expect(second.getByText("1 saved to your shortlist")).toBeVisible();
  await second
    .getByRole("button", { name: /Sunday Studio.*Look at this/ })
    .click();
  await expect(first.locator(".stage h2")).toHaveText("Sunday Studio");
  await second
    .getByRole("button", { name: "Save to Together", exact: true })
    .click();
  await expect(first.getByText("2 saved to your shortlist")).toBeVisible();
  await first.getByRole("button", { name: "Compare picks" }).click();
  await expect(
    first.locator(".board").getByText("Sunday Studio", { exact: true }),
  ).toBeVisible();
  await expect(
    second.locator(".board").getByText("Quiet Hours", { exact: true }),
  ).toBeVisible();
  await second.getByLabel("Message everyone").fill("Comfort matters to me");
  await second
    .getByRole("button", { name: "Send message", exact: true })
    .click();
  await expect(
    first.getByText("Comfort matters to me", { exact: true }),
  ).toBeVisible();
  await first.reload();
  await second.reload();
  await expect(first.getByText("2 saved to your shortlist")).toBeVisible();
  await expect(
    second.locator(".board").getByText("Quiet Hours", { exact: true }),
  ).toBeVisible();
  await expect(
    second.getByText("Comfort matters to me", { exact: true }),
  ).toBeVisible();
  await first
    .getByRole("button", { name: /Quiet Hours.*Look at this/ })
    .click();
  await expect(second.locator(".stage h2")).toHaveText("Quiet Hours");
  await first.getByLabel("Product variant").selectOption("midnight");
  await first.getByLabel("Product quantity").fill("2");
  await first.getByRole("button", { name: "Add to cart" }).click();
  await second.locator(".cart-details summary").click();
  await expect(
    second.getByText("Quiet Hours · midnight", { exact: true }),
  ).toBeVisible();
  await expect(first.locator(".cart-details")).toHaveAttribute("open", "");
  await expect(first.getByText("Added to your shared cart.")).toBeVisible();
  await first.getByLabel("Quantity 2 midnight").fill("3");
  await first.getByRole("button", { name: "Update quantity" }).click();
  await expect(second.getByLabel("Quantity 2 midnight")).toHaveValue("3");
  await expect(first.locator(".cart-count")).toHaveText("3");
  await first.getByLabel("Quantity 2 midnight").fill("2");
  await first.getByRole("button", { name: "Update quantity" }).click();
  await expect(second.getByLabel("Quantity 2 midnight")).toHaveValue("2");
  await first
    .getByRole("button", { name: "Review exact quote", exact: true })
    .click();
  await expect(first.getByText("Total $198.00 USD")).toBeVisible();
  await expect(
    second.getByRole("button", { name: "Krishna handles checkout" }),
  ).toBeDisabled();
  await first.getByRole("button", { name: "Cancel unused quote" }).click();
  await first.screenshot({ path: "/tmp/shopside-desktop.png", fullPage: true });
  await second.screenshot({ path: "/tmp/shopside-mobile.png", fullPage: true });
  await a.close();
  await b.close();
});
