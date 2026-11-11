import { afterEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import {
  setupSteps,
  readTour,
  saveTour,
  tourEvent,
  SetupTour,
} from "./setup-tour";
import App from "./App";

const store = new Map<string, string>();
afterEach(() => {
  vi.unstubAllGlobals();
  store.clear();
});
function storage() {
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => store.set(key, value),
  });
}

describe("self-contained setup tour", () => {
  it("resumes only bounded progress, without persisting provider or conversation data", () => {
    storage();
    expect(readTour()).toBeNull();
    saveTour(true, 3);
    expect(readTour()).toEqual({ open: true, step: 3 });
    expect([...store.values()]).toEqual(['{"open":true,"step":3}']);
    for (const value of [
      '{"open":true,"step":99}',
      '{"open":true,"step":-1}',
      '{"open":true,"step":1,"key":"secret"}',
      "invalid",
    ]) {
      store.set("omr:setup-tour:v1", value);
      expect(readTour()).toBeNull();
    }
  });
  it("navigates through real setup controls without saving, consenting or generating", async () => {
    const navigate = vi.fn();
    const steps = setupSteps(navigate);
    expect(steps).toHaveLength(5);
    expect(steps.map((step) => step.target)).toEqual([
      '[data-tour="providers"]',
      '[data-tour="decider"]',
      '[data-tour="profiles"]',
      '[data-tour="client"]',
      '[data-tour="inspector"]',
    ]);
    for (const step of steps) await step.before?.({} as never);
    expect(navigate.mock.calls.map(([page]) => page)).toEqual([
      "Fournisseurs",
      "Profils & règles",
      "Profils & règles",
      "État",
      "Inspecteur",
    ]);
    const copy = steps
      .map((step) => renderToStaticMarkup(<>{step.content}</>))
      .join(" ");
    expect(copy).toContain("Jev");
    expect(copy).toContain("oh-my-pi");
    expect(copy).not.toMatch(/configuration vérifiée|économies garanties/i);
  });
  it("pauses on missing controls and never silently advances a required step", () => {
    expect(
      tourEvent({
        type: "error:target_not_found",
        index: 2,
        status: "running",
      }),
    ).toEqual({ open: false, step: 2, failed: true });
    expect(
      tourEvent({ type: "tour:end", index: 4, status: "finished" }),
    ).toEqual({ open: false, step: 4, failed: false });
    expect(
      tourEvent({ type: "tour:end", index: 1, status: "skipped" }),
    ).toEqual({ open: false, step: 1, failed: false });
    expect(tourEvent({ type: "tooltip", index: 1, status: "running" })).toEqual(
      { open: true, step: 1, failed: false },
    );
  });
  it("renders a replay action before any engine connection and does not perform native effects", () => {
    expect(renderToStaticMarkup(<App />)).toContain("Visite guidée");
    expect(
      renderToStaticMarkup(
        <SetupTour navigate={() => {}} close={() => {}} initialStep={0} />,
      ),
    ).not.toContain("configuration vérifiée");
  });
});
