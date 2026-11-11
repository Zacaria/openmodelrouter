import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ControlsFixture } from "./controls.fixture";
import { Select } from "./ui";

describe("shared form rendering", () => {
  it("retains labels, restrictions and shared button variants", () => {
    const fixture = renderToStaticMarkup(<ControlsFixture />);
    expect(fixture).toContain('data-slot="input"');
    expect(fixture).toContain('spellCheck="false"');
    expect(fixture).toContain('autoCapitalize="none"');
    expect(fixture).toContain('class="button secondary"');
    expect(fixture).toContain('role="combobox"');
    expect(fixture).toContain('name="transport" value="http"');
    expect(fixture).toMatch(/readonly=""/i);
    expect(fixture).toContain('role="switch"');
  });

  it("renders the empty choice without leaking internal encoding into form data", () => {
    const markup = renderToStaticMarkup(
      <Select
        name="baseline"
        value=""
        onValueChange={() => {}}
        options={[
          { value: "", label: "Aucune référence" },
          { value: "value:", label: "Autre choix" },
        ]}
      />,
    );
    expect(markup).toContain('type="hidden" name="baseline" value=""');
    expect(markup).toContain("Aucune référence");
    expect(markup).toContain('type="button"');
  });
});
