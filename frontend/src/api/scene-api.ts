import type {
  ApplyResult,
  HomeAssistant,
  SceneDefinition,
  SceneGetResponse,
  SceneListResponse,
} from "../types";

const DOMAIN = "smart_scene_studio";

export class SceneApi {
  constructor(private readonly hass: HomeAssistant) {}

  async listScenes(): Promise<SceneListResponse> {
    const result = await this.hass.callWS<SceneListResponse>({
      type: `${DOMAIN}/scene/list`,
    });
    if (!result || !Array.isArray(result.scenes)) {
      throw new Error("The scene service returned an invalid list response.");
    }
    return result;
  }

  async getScene(sceneId: string): Promise<SceneGetResponse> {
    return this.hass.callWS<SceneGetResponse>({
      type: `${DOMAIN}/scene/get`,
      scene_id: sceneId,
    });
  }

  async applyScene(
    scene: SceneDefinition,
    entityIds: string[],
  ): Promise<ApplyResult | null> {
    const selected = [...new Set(entityIds)];
    if (selected.some((entityId) => !/^light\.[a-z0-9_]+$/.test(entityId))) {
      throw new Error("Select only valid Home Assistant light entities.");
    }
    if (selected.length === 0) {
      throw new Error("Select at least one light before applying a scene.");
    }
    if (selected.length > 64) {
      throw new Error("Select no more than 64 lights before applying a scene.");
    }
    const result = await this.hass.callService(
      DOMAIN,
      "apply_scene",
      { scene_id: scene.id, entity_id: selected },
      undefined,
      false,
      true,
    );
    return readApplyResult(result);
  }
}

function readApplyResult(value: unknown): ApplyResult | null {
  if (!value || typeof value !== "object") return null;
  const response = "response" in value ? value.response : value;
  if (!response || typeof response !== "object") return null;
  const result = response as Record<string, unknown>;
  return {
    applied: stringArray(result.applied),
    skipped: stringArray(result.skipped),
    failed: stringArray(result.failed),
  };
}

function stringArray(value: unknown): string[] | undefined {
  return Array.isArray(value) && value.every((item) => typeof item === "string")
    ? value
    : undefined;
}
