import { test, expect } from "@playwright/test";

test("a real agent request from the second participant updates both boards", async ({
  browser,
}) => {
  test.skip(
    process.env.SHOPSIDE_LIVE_AGENT !== "1",
    "Requires configured Vertex AI and Channel3",
  );
  test.setTimeout(80000);
  const url = process.env.SHOPSIDE_TEST_URL || "http://localhost:3000";
  const a = await browser.newContext(),
    b = await browser.newContext({ viewport: { width: 375, height: 812 } });
  const first = await a.newPage(),
    second = await b.newPage();
  await first.goto(url);
  await first.getByLabel("Your name").fill("Krishna");
  await first.getByRole("button", { name: "Create your room" }).click();
  await expect(first.getByText("Connected", { exact: true })).toBeVisible();
  const roomId = new URL(first.url()).searchParams.get("room");
  const room = await (
    await first.request.get(url + "/api/rooms/" + roomId)
  ).json();
  await second.goto(url + "?invite=" + room.invite);
  await second.getByLabel("Your name").fill("Priya");
  await second.getByRole("button", { name: "Join your friend" }).click();
  await expect(first.getByText(/Krishna & Priya/)).toBeVisible();
  await second
    .locator("details")
    .filter({ hasText: "Room priorities" })
    .locator("summary")
    .click();
  await second
    .getByLabel("Your shopping preference")
    .fill("Comfort matters for long calls");
  await second.getByLabel("Your shopping preference").blur();
  await expect(
    first
      .locator(".recommendations")
      .getByText("Priya: Comfort matters for long calls", { exact: true }),
  ).toBeVisible();
  await second.getByLabel("Message target").selectOption("agent");
  await second
    .getByLabel("Message everyone")
    .fill(
      "Call discover_products once for wireless headphones under $150, then update_decision_board using the first two Channel3 product IDs returned. Summarize only what is known.",
    );
  await second.getByRole("button", { name: "Send message" }).click();
  await expect(
    first.locator(".messages").getByText("ShopSide", { exact: true }),
  ).toBeVisible({ timeout: 60000 });
  const firstState = await (
    await first.request.get(url + "/api/rooms/" + roomId)
  ).json();
  const secondState = await (
    await second.request.get(url + "/api/rooms/" + roomId)
  ).json();
  expect(firstState.activity.map((x: any) => x.tool)).toContain(
    "discover_products",
  );
  expect(firstState.activity.map((x: any) => x.tool)).toContain(
    "update_decision_board",
  );
  expect(
    firstState.messages.some(
      (message: any) =>
        message.actor === "Priya" && message.text.includes("discover_products"),
    ),
  ).toBeTruthy();
  expect(
    firstState.messages.some((message: any) => message.actor === "ShopSide"),
  ).toBeTruthy();
  expect(firstState.comparison).toHaveLength(2);
  expect(
    firstState.comparison.every((id: string) => id.startsWith("channel3:")),
  ).toBeTruthy();
  expect(secondState.comparison).toEqual(firstState.comparison);
  await expect(first.locator(".board .ag-row")).toHaveCount(2);
  await expect(second.locator(".board .ag-row")).toHaveCount(2);
  await second.reload();
  await expect(second.locator(".board .ag-row")).toHaveCount(2);
  await a.close();
  await b.close();
});
