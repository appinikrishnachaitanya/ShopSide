import { test, expect } from "@playwright/test";
test("two separate participants connect audio and can mute and leave", async ({
  browser,
}) => {
  const a = await browser.newContext({ permissions: ["microphone"] });
  const b = await browser.newContext({ permissions: ["microphone"] });
  const first = await a.newPage(),
    second = await b.newPage();
  await first.goto("http://localhost:3000");
  await first.getByLabel("Your name").fill("Voice A");
  await first.getByRole("button", { name: "Create your room" }).click();
  await expect(first.getByText("Connected", { exact: true })).toBeVisible();
  const id = new URL(first.url()).searchParams.get("room");
  const state = await (
    await first.request.get("http://localhost:3000/api/rooms/" + id)
  ).json();
  await second.goto("http://localhost:3000?invite=" + state.invite);
  await second.getByLabel("Your name").fill("Voice B");
  await second.getByRole("button", { name: "Join your friend" }).click();
  await first.getByRole("button", { name: "Join voice" }).click();
  await expect(
    first.getByText("Waiting for your friend to join…"),
  ).toBeVisible();
  await second.getByRole("button", { name: "Join voice" }).click();
  await expect(first.getByText("Voice connected")).toBeVisible({
    timeout: 20000,
  });
  await expect(second.getByText("Voice connected")).toBeVisible({
    timeout: 20000,
  });
  await first.getByRole("button", { name: "Mute", exact: true }).click();
  await expect(first.getByRole("button", { name: "Unmute" })).toBeVisible();
  await first.getByRole("button", { name: "Leave", exact: true }).click();
  await expect(second.getByText("Your friend left the call.")).toBeVisible();
  await a.close();
  await b.close();
});
