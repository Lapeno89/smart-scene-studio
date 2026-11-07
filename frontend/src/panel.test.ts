import { afterEach, describe, expect, it, vi } from "vitest";
import "./panel";
import type { HomeAssistant, SceneDefinition } from "./types";
const scene: SceneDefinition = {
  id: "scene-1",
  name: "Ocean Calm",
  kind: "static",
  category: "relax",
  favorite: false,
  palette: ["#168AAD", "#76C893"],
  targets: [],
  provenance: "builtin",
};
const savedScene: SceneDefinition = {
  ...scene,
  id: "scene-2",
  name: "Desk Glow",
  category: "focus",
  provenance: "user",
};
const hueScene: SceneDefinition = {
  ...scene,
  id: "scene-3",
  name: "Reading",
  category: "reading",
  favorite: true,
  provenance: "hue_import",
  source: { provider: "hue_v2", unmapped_light_ids: ["hue-light-1"] },
};
function createPanel(admin = true) {
  const websocket = vi.fn(async (message: Record<string, unknown>) =>
    (message.type as string).endsWith("/list")
      ? {
          scenes: [scene, savedScene, hueScene],
          entity_sync: { status: "pending" },
        }
      : {
          scene:
            message.scene_id === hueScene.id
              ? hueScene
              : message.scene_id === savedScene.id
                ? savedScene
                : scene,
        },
  );
  const callWS = websocket as unknown as HomeAssistant["callWS"];
  const callService = admin
    ? vi.fn().mockResolvedValue({
        response: { applied: ["light.desk"], skipped: [], failed: [] },
      })
    : vi.fn().mockRejectedValue(new Error("Permission denied for light.desk"));
  const hass: HomeAssistant = {
    states: {
      "light.desk": {
        entity_id: "light.desk",
        state: "off",
        attributes: { friendly_name: "Desk", supported_color_modes: ["xy"] },
      },
    },
    user: { is_admin: admin },
    language: "en",
    callWS,
    callService,
  };
  const panel = document.createElement(
    "smart-scene-studio-panel",
  ) as import("./panel").SmartSceneStudioPanel;
  panel.hass = hass;
  document.body.append(panel);
  return { panel, hass, callWS: websocket, callService };
}
async function settle(panel: HTMLElement) {
  await (panel as HTMLElement & { updateComplete: Promise<boolean> })
    .updateComplete;
  await new Promise((resolve) => setTimeout(resolve, 0));
  await (panel as HTMLElement & { updateComplete: Promise<boolean> })
    .updateComplete;
}
afterEach(() => {
  document.body.replaceChildren();
});
describe("Smart Scene Studio panel", () => {
  it("loads a scene gallery, palette, filters, details and saved synchronization status", async () => {
    const { panel } = createPanel();
    await settle(panel);
    expect(panel.shadowRoot?.querySelector(".card strong")?.textContent).toBe(
      "Ocean Calm",
    );
    expect(
      panel.shadowRoot?.querySelectorAll(".card:first-child .color"),
    ).toHaveLength(2);
    expect(panel.shadowRoot?.textContent).toContain("Scenes are saved");
    expect(panel.shadowRoot?.textContent).toContain("Desk Glow");
    expect(panel.shadowRoot?.textContent).toContain("Hue import");
    const category = panel.shadowRoot?.querySelector(
      "select",
    ) as HTMLSelectElement;
    category.value = "focus";
    category.dispatchEvent(new Event("change"));
    await settle(panel);
    expect(panel.shadowRoot?.querySelectorAll(".card")).toHaveLength(1);
    category.value = "";
    category.dispatchEvent(new Event("change"));
    const favorite = panel.shadowRoot?.querySelector(
      'input[type="checkbox"]',
    ) as HTMLInputElement;
    favorite.checked = true;
    favorite.dispatchEvent(new Event("change"));
    await settle(panel);
    expect(panel.shadowRoot?.querySelectorAll(".card")).toHaveLength(1);
    expect(panel.shadowRoot?.querySelector(".card strong")?.textContent).toBe(
      "Reading",
    );
    favorite.checked = false;
    favorite.dispatchEvent(new Event("change"));
    const search = panel.shadowRoot?.querySelector(
      'input[type="search"]',
    ) as HTMLInputElement;
    search.value = "no-match";
    search.dispatchEvent(new Event("input"));
    await settle(panel);
    expect(panel.shadowRoot?.textContent).toContain("No scenes match");
  });
  it("does not apply until the user selects a light and confirms", async () => {
    const { panel, callService } = createPanel();
    await settle(panel);
    expect(callService).not.toHaveBeenCalled();
    const checkbox = panel.shadowRoot?.querySelector(
      '.light input[type="checkbox"]',
    ) as HTMLInputElement;
    checkbox.checked = true;
    checkbox.dispatchEvent(new Event("change"));
    await settle(panel);
    panel.shadowRoot
      ?.querySelector(".primary")
      ?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await settle(panel);
    expect(callService).not.toHaveBeenCalled();
    const confirm = [
      ...(panel.shadowRoot?.querySelectorAll("button") ?? []),
    ].find((button) => button.textContent?.includes("Confirm apply"));
    confirm?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    confirm?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await settle(panel);
    expect(callService).toHaveBeenCalledTimes(1);
  });
  it("reflects HA light availability updates without refetching scenes", async () => {
    const { panel, hass, callWS } = createPanel();
    await settle(panel);
    const requestCount = callWS.mock.calls.length;
    panel.hass = {
      ...hass,
      states: {
        "light.desk": { ...hass.states["light.desk"]!, state: "unavailable" },
      },
    };
    await settle(panel);
    expect(callWS).toHaveBeenCalledTimes(requestCount);
    expect(
      (
        panel.shadowRoot?.querySelector(
          '.light input[type="checkbox"]',
        ) as HTMLInputElement
      ).disabled,
    ).toBe(true);
  });
  it("surfaces backend per-light authorization failures for a non-administrator", async () => {
    const { panel, callService } = createPanel(false);
    await settle(panel);
    expect(panel.shadowRoot?.querySelector(".primary")).not.toBeNull();
    const checkbox = panel.shadowRoot?.querySelector(
      '.light input[type="checkbox"]',
    ) as HTMLInputElement;
    checkbox.checked = true;
    checkbox.dispatchEvent(new Event("change"));
    await settle(panel);
    panel.shadowRoot
      ?.querySelector(".primary")
      ?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await settle(panel);
    const confirm = [
      ...(panel.shadowRoot?.querySelectorAll("button") ?? []),
    ].find((button) => button.textContent?.includes("Confirm apply"));
    confirm?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await settle(panel);
    expect(
      panel.shadowRoot?.querySelector('[role="alert"]')?.textContent,
    ).toContain("Permission denied");
    expect(callService).toHaveBeenCalledTimes(1);
  });
});
