import { themes } from "@/themes";

describe("Themes", () => {
  it("has dark theme", () => {
    expect(themes.dark).toBeDefined();
  });

  it("has light theme", () => {
    expect(themes.light).toBeDefined();
  });

  it("dark theme has expected color properties", () => {
    const dark = themes.dark;
    expect(dark.name).toBe("dark");
    expect(dark.colors).toBeDefined();
    expect(dark.colors.bg).toBeDefined();
    expect(dark.colors.bgSurface).toBeDefined();
    expect(dark.colors.bgCard).toBeDefined();
    expect(dark.colors.text).toBeDefined();
    expect(dark.colors.primary).toBeDefined();
    expect(dark.colors.success).toBeDefined();
    expect(dark.colors.warning).toBeDefined();
    expect(dark.colors.error).toBeDefined();
    expect(dark.colors.info).toBeDefined();
  });

  it("light theme has expected color properties", () => {
    const light = themes.light;
    expect(light.name).toBe("light");
    expect(light.colors).toBeDefined();
    expect(light.colors.bg).toBeDefined();
    expect(light.colors.bgSurface).toBeDefined();
    expect(light.colors.bgCard).toBeDefined();
    expect(light.colors.text).toBeDefined();
    expect(light.colors.primary).toBeDefined();
    expect(light.colors.success).toBeDefined();
    expect(light.colors.warning).toBeDefined();
    expect(light.colors.error).toBeDefined();
    expect(light.colors.info).toBeDefined();
  });

  it("both themes have same color keys", () => {
    const darkKeys = Object.keys(themes.dark.colors).sort();
    const lightKeys = Object.keys(themes.light.colors).sort();
    expect(darkKeys).toEqual(lightKeys);
  });

  it("themes use hex color values", () => {
    const hexRegex = /^#[0-9a-fA-F]{6}$/;
    Object.values(themes.dark.colors).forEach((color) => {
      expect(color).toMatch(hexRegex);
    });
    Object.values(themes.light.colors).forEach((color) => {
      expect(color).toMatch(hexRegex);
    });
  });
});
