import { test, expect } from "@playwright/test";

/**
 * VERINE live showcase (offline fixtures, no LLM required):
 * launcher → live war room → poll → signals/quorum/shadow/cascade → fork compare
 * → case file. Requires API (8000) + web (3000) running.
 */
test("live war room offline showcase", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Before the failure becomes obvious")).toBeVisible();
  await page.getByTestId("open-live").click();

  // War room loads the capability graph.
  await expect(page.getByTestId("graph-explorer")).toBeVisible();
  await expect(page.getByTestId("capability-pane")).toBeVisible();

  // Poll the offline connectors.
  await page.getByTestId("poll-button").click();

  // Three signals corroborate into one hypothesis with independent quorum.
  await expect(page.getByTestId("hypothesis-state")).toContainText("OPERATIONALLY_RELEVANT_HYPOTHESIS", { timeout: 60_000 });
  await expect(page.getByTestId("quorum")).toContainText("3 independent group");

  // Shadowgraph reveals an inferred shared dependency, review-required.
  await expect(page.getByTestId("shadow-pane")).toContainText("inferred, not confirmed");

  // Event tape shows the pipeline events.
  await expect(page.getByTestId("event-tape")).toContainText("signal_observed");
  await expect(page.getByTestId("event-tape")).toContainText("shadow_edge_created");

  // Cascade clock: interval language, never "will fail at T".
  await expect(page.getByTestId("cascade-pane")).toContainText("POSSIBLE capability-floor breach");
  await expect(page.getByTestId("cascade-pane")).not.toContainText("will fail");

  // Fork compare: no-action vs a reversible containment path.
  await page.getByTestId("tab-forks").click();
  await expect(page.getByTestId("fork-compare")).toBeVisible();
  await page.getByTestId("fork-no-action").click();
  await expect(page.getByTestId("fork-result").first()).toBeVisible({ timeout: 30_000 });

  // LLM tab is available but optional — shows the "no provider" guidance offline.
  await page.getByTestId("tab-llm").click();
  await expect(page.getByTestId("llm-pane")).toContainText("No AI provider configured");
});

test("external signals never claim confirmed internal impact", async ({ page }) => {
  await page.goto("/live");
  await page.getByTestId("poll-button").click();
  await expect(page.getByTestId("hypothesis-state")).toBeVisible({ timeout: 60_000 });
  await page.getByTestId("tab-evidence").click();
  const pane = page.getByTestId("evidence-pane");
  await expect(pane).toContainText("external_signal_only");
  // A CISA/NVD-style signal stays possible_exposure, not confirmed.
  await expect(pane).toContainText("possible_exposure");
});

test("AI provider key can be added, is masked, and deletes", async ({ page }) => {
  await page.goto("/providers");
  await page.getByTestId("add-openrouter").click();
  await page.getByTestId("key-input").fill("sk-or-e2e-testonly-abcd1234");
  await page.getByTestId("save-credential").click();
  const row = page.getByTestId("credential-row").first();
  await expect(row).toBeVisible({ timeout: 15_000 });
  // Masked, last four only — never the full key.
  await expect(row).toContainText("1234");
  await expect(row).not.toContainText("sk-or-e2e-testonly");
  await row.getByTestId("delete-credential").click();
});
