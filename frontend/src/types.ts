export interface TargetAssignment {
  entity_id: string;
  enabled?: boolean;
  state?: "on" | "off";
  color_mode?: string;
  color_index?: number;
  brightness_pct?: number;
  transition?: number;
  color?: string;
  color_temp_kelvin?: number;
}

export interface SceneDefinition {
  id: string;
  name: string;
  kind: string;
  category: string;
  favorite: boolean;
  palette: string[];
  targets: TargetAssignment[];
  brightness_pct?: number;
  transition?: number;
  white_temperature_kelvin?: number | null;
  provenance: "builtin" | "user" | "hue_import";
  source?: {
    provider?: string;
    unmapped_light_ids?: string[];
    missing_light_ids?: string[];
    unsupported_features?: string[];
  };
}

export interface LightState {
  entity_id: string;
  state: string;
  attributes: Record<string, unknown>;
}

export interface SceneListResponse {
  scenes: SceneDefinition[];
  entity_sync?: { status: "complete" | "pending"; message?: string };
}

export interface SceneGetResponse {
  scene: SceneDefinition;
  entity_sync?: { status: "complete" | "pending"; message?: string };
}

export interface ApplyResult {
  applied?: string[];
  skipped?: string[];
  failed?: string[];
}

export interface HomeAssistant {
  states: Record<string, LightState>;
  user?: { is_admin?: boolean };
  language?: string;
  locale?: { language?: string };
  callWS<T = unknown>(message: Record<string, unknown>): Promise<T>;
  callService(
    domain: string,
    service: string,
    serviceData?: Record<string, unknown>,
    target?: Record<string, unknown>,
    notifyOnError?: boolean,
    returnResponse?: boolean,
  ): Promise<unknown>;
}
