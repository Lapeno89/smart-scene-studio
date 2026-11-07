import { describe, expect, it, vi } from "vitest";
import { SceneApi } from "./scene-api";
import type { HomeAssistant, SceneDefinition } from "../types";
const scene = {
  id: "scene-1",
  name: "Ocean Calm",
  kind: "static",
  category: "relax",
  favorite: false,
  palette: ["#168AAD"],
  targets: [],
  provenance: "builtin",
} as SceneDefinition;
function hass(callWS = vi.fn(), callService = vi.fn()): HomeAssistant {
  return { states: {}, callWS, callService };
}
describe("SceneApi", () => {
  it("uses authenticated scene list and detail websocket commands", async () => {
    const ws = vi
      .fn()
      .mockResolvedValueOnce({ scenes: [scene] })
      .mockResolvedValueOnce({ scene });
    const api = new SceneApi(hass(ws));
    await expect(api.listScenes()).resolves.toEqual({ scenes: [scene] });
    await expect(api.getScene(scene.id)).resolves.toEqual({ scene });
    expect(ws).toHaveBeenNthCalledWith(1, {
      type: "smart_scene_studio/scene/list",
    });
    expect(ws).toHaveBeenNthCalledWith(2, {
      type: "smart_scene_studio/scene/get",
      scene_id: scene.id,
    });
  });
  it("only calls apply_scene with a nonempty deduplicated explicit target list", async () => {
    const service = vi
      .fn()
      .mockResolvedValue({ response: { applied: ["light.desk"] } });
    const api = new SceneApi(hass(vi.fn(), service));
    await expect(
      api.applyScene(scene, ["light.desk", "light.desk"]),
    ).resolves.toEqual({
      applied: ["light.desk"],
      skipped: undefined,
      failed: undefined,
    });
    expect(service).toHaveBeenCalledWith(
      "smart_scene_studio",
      "apply_scene",
      { scene_id: "scene-1", entity_id: ["light.desk"] },
      undefined,
      false,
      true,
    );
    await expect(api.applyScene(scene, [])).rejects.toThrow(
      /at least one light/,
    );
    await expect(api.applyScene(scene, ["switch.desk"])).rejects.toThrow(
      /valid Home Assistant light/,
    );
    await expect(
      api.applyScene(
        scene,
        Array.from({ length: 65 }, (_, index) => `light.fixture_${index}`),
      ),
    ).rejects.toThrow(/no more than 64/);
  });
});
