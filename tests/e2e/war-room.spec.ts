import { test, expect } from "@playwright/test";

/**
 * Happy path (N064): capability -> compound incident -> simulation ->
 * containment -> case file export/replay, without touching a terminal.
 * Requires the API (port 8000) and web app (port 3000) to be running.
 */
test("compound payment crisis demo end-to-end", async ({ page }) => {
  // Landing page: capability visible, war room reachable.
  await page.goto("/");
  await expect(page.getByText("Digital Payments Authorization")).toBeVisible();
  await expect(page.getByText(/Synthetic war room/i)).toBeVisible();
  await page.getByTestId("open-war-room").click();

  // War room loads the graph.
  await expect(page.getByTestId("graph-explorer")).toBeVisible();
  await expect(page.getByTestId("status-pane")).toContainText("Inject an incident");

  // Choose the compound incident and run.
  await page.getByTestId("incident-select").selectOption("inc_compound_payment_crisis");
  await page.getByTestId("launch-button").click();

  // Results: status badge, timeline, containment.
  await expect(page.getByTestId("capability-status")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId("timeline")).toBeVisible();
  await expect(page.getByTestId("containment-planner")).toBeVisible();
  await expect(page.getByTestId("status-pane")).toContainText("Time to floor");

  // Timeline scrubber changes displayed time.
  const scrubber = page.getByTestId("timeline-scrubber");
  await scrubber.focus();
  await scrubber.press("End");
  await expect(page.getByTestId("timeline")).not.toContainText("t = 0m");

  // Pathways tab shows rule-linked impacts.
  await page.getByTestId("tab-pathways").click();
  await expect(page.getByTestId("pathways-panel")).toContainText("cap_digital_payments_authorization");

  // Disagreement tab shows at least two models and reasons.
  await page.getByTestId("tab-disagreement").click();
  await expect(page.getByTestId("disagreement-panel")).toContainText("deterministic_propagation_v1");
  await expect(page.getByTestId("disagreement-panel")).toContainText("likely reasons");

  // Unknowns tab shows uncertainty components.
  await page.getByTestId("tab-unknowns").click();
  await expect(page.getByTestId("unknowns-panel")).toContainText("epistemic");

  // Containment recompute with tighter budget still returns a result.
  await page.getByTestId("budget-slider").fill("15000");
  await page.getByTestId("recompute-containment").click();
  await expect(page.getByTestId("containment-planner")).toContainText("No action (baseline)", { timeout: 30_000 });

  // Case file: export exists, replay verifies hashes.
  await page.getByTestId("tab-case").click();
  await expect(page.getByTestId("case-export")).toContainText("run hash: sha256:");
  const downloadPromise = page.waitForEvent("download");
  await page.getByTestId("export-json").click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/^case_.*\.json$/);
  await page.getByTestId("verify-replay").click();
  await expect(page.getByTestId("replay-verdict")).toContainText("Replay hash matches", { timeout: 60_000 });
});

test("incomplete topology raises unknowns", async ({ page }) => {
  await page.goto("/war-room");
  await page.getByTestId("incident-select").selectOption("inc_compound_payment_crisis");
  await page.getByTestId("topology-select").selectOption("incomplete");
  await page.getByTestId("launch-button").click();
  await expect(page.getByTestId("capability-status")).toBeVisible({ timeout: 60_000 });
  await page.getByTestId("tab-unknowns").click();
  await expect(page.getByTestId("unknowns-panel")).toContainText("undisclosed_dependencies");
  await expect(page.getByTestId("unknowns-panel")).toContainText("hidden from models");
});
