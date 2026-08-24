import { test, expect } from "@playwright/test";

/** N063: keyboard navigation and labeling basics. */
test("war room is keyboard-navigable with labeled controls", async ({ page }) => {
  await page.goto("/war-room");
  await expect(page.getByTestId("graph-explorer")).toBeVisible();

  // Controls are labeled selects/buttons, reachable and operable by keyboard.
  const incidentSelect = page.getByTestId("incident-select");
  await incidentSelect.focus();
  await expect(incidentSelect).toBeFocused();
  await incidentSelect.selectOption("inc_processor_latency");

  const launch = page.getByTestId("launch-button");
  await launch.focus();
  await expect(launch).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("capability-status")).toBeVisible({ timeout: 60_000 });

  // The timeline scrubber is an accessible range input with an aria-label.
  const scrubber = page.getByTestId("timeline-scrubber");
  await expect(scrubber).toHaveAttribute("aria-label", "Timeline scrubber");
  await scrubber.focus();
  await scrubber.press("ArrowRight");

  // Landmarks: header nav links have accessible names.
  await expect(page.getByRole("link", { name: "Case Files" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Evidence" })).toBeVisible();
});
