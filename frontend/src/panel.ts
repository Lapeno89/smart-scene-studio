import { LitElement, css, html, nothing } from "lit";
import type { PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { SceneApi } from "./api/scene-api";
import { languageOf, translate } from "./i18n";
import type { HomeAssistant, SceneDefinition } from "./types";
@customElement("smart-scene-studio-panel")
export class SmartSceneStudioPanel extends LitElement {
  @property({ attribute: false }) hass?: HomeAssistant;
  @property({ attribute: false }) narrow = false;
  @property({ attribute: false }) route?: unknown;
  @property({ attribute: false }) panel?: unknown;
  @state() private scenes: SceneDefinition[] = [];
  @state() private selected?: SceneDefinition;
  @state() private query = "";
  @state() private category = "";
  @state() private favoritesOnly = false;
  @state() private targets = new Set<string>();
  @state() private loading = true;
  @state() private error = "";
  @state() private pending = false;
  @state() private confirm = false;
  @state() private applying = false;
  @state() private result = "";
  private initialized = false;
  private requestGeneration = 0;
  static styles = css`
    :host {
      display: block;
      color: var(--primary-text-color);
      background: var(--primary-background-color);
      min-height: 100%;
    }
    * {
      box-sizing: border-box;
    }
    main {
      max-width: 1440px;
      margin: auto;
      padding: 24px;
    }
    .toolbar,
    .actions {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 12px;
      margin: 16px 0;
    }
    input,
    select,
    button {
      font: inherit;
      color: inherit;
    }
    input[type="search"],
    select,
    button {
      min-height: 44px;
      padding: 8px 12px;
      border: 1px solid var(--divider-color);
      border-radius: 8px;
      background: var(--card-background-color);
    }
    input[type="search"] {
      flex: 1 1 220px;
    }
    button {
      cursor: pointer;
    }
    button:focus-visible,
    input:focus-visible,
    select:focus-visible {
      outline: 3px solid var(--primary-color);
      outline-offset: 2px;
    }
    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1.5fr) minmax(280px, 0.8fr);
      gap: 18px;
      align-items: start;
    }
    .gallery {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(min(100%, 210px), 1fr));
      gap: 12px;
    }
    .card {
      padding: 0;
      overflow: hidden;
      text-align: left;
    }
    .card[aria-pressed="true"] {
      border: 2px solid var(--primary-color);
    }
    .palette {
      display: flex;
      min-height: 72px;
    }
    .color {
      flex: 1;
    }
    .copy {
      padding: 12px;
      display: grid;
      gap: 4px;
    }
    .panel {
      padding: 16px;
      border: 1px solid var(--divider-color);
      border-radius: 12px;
      background: var(--card-background-color);
    }
    .panel + .panel {
      margin-top: 12px;
    }
    .lights {
      max-height: 300px;
      overflow: auto;
    }
    .light {
      display: flex;
      gap: 8px;
      align-items: center;
      min-height: 42px;
    }
    .subtle {
      color: var(--secondary-text-color);
    }
    .notice,
    .error,
    .success {
      padding: 12px;
      border-radius: 8px;
    }
    .notice {
      background: var(--warning-color, #f9a825);
    }
    .error {
      background: var(--error-color, #b3261e);
      color: white;
    }
    .success {
      background: var(--success-color, #2e7d32);
      color: white;
    }
    .primary {
      background: var(--primary-color);
    }
    dialog {
      color: var(--primary-text-color);
      background: var(--card-background-color);
      border-radius: 12px;
    }
    @media (max-width: 800px) {
      .layout {
        grid-template-columns: 1fr;
      }
    }
    @media (prefers-reduced-motion: reduce) {
      *,
      *::before,
      *::after {
        animation: none !important;
        transition: none !important;
      }
    }
  `;
  private t(key: Parameters<typeof translate>[0]): string {
    return translate(key, languageOf(this.hass?.language, this.hass?.locale));
  }
  protected updated(changed: PropertyValues<this>): void {
    if (changed.has("hass") && this.hass && !this.initialized) {
      this.initialized = true;
      void this.refresh();
    }
  }
  private async refresh(): Promise<void> {
    if (!this.hass) return;
    const generation = ++this.requestGeneration;
    this.loading = true;
    this.error = "";
    try {
      const r = await new SceneApi(this.hass).listScenes();
      if (generation !== this.requestGeneration) return;
      this.scenes = r.scenes;
      this.pending = r.entity_sync?.status === "pending";
      if (this.selected)
        this.selected = this.scenes.find(
          (scene) => scene.id === this.selected?.id,
        );
      if (!this.selected && this.scenes.length)
        await this.select(this.scenes[0]!);
    } catch (e) {
      if (generation === this.requestGeneration)
        this.error = e instanceof Error ? e.message : this.t("loadError");
    } finally {
      if (generation === this.requestGeneration) this.loading = false;
    }
  }
  private async select(scene: SceneDefinition): Promise<void> {
    this.selected = scene;
    this.targets = new Set();
    this.confirm = false;
    try {
      const r = await new SceneApi(this.hass!).getScene(scene.id);
      if (this.selected?.id === scene.id) this.selected = r.scene;
    } catch {
      /* List response remains usable. */
    }
    if (this.selected?.id === scene.id)
      this.targets = new Set(
        (this.selected.targets ?? [])
          .filter((x) => x.enabled !== false && this.available(x.entity_id))
          .map((x) => x.entity_id),
      );
  }
  private available(id: string): boolean {
    const s = this.hass?.states[id]?.state;
    return Boolean(s && s !== "unknown" && s !== "unavailable");
  }
  private get lights() {
    return Object.values(this.hass?.states ?? {}).filter((s) =>
      s.entity_id.startsWith("light."),
    );
  }
  private get categories() {
    return [
      ...new Set(this.scenes.map((s) => s.category).filter(Boolean)),
    ].sort();
  }
  private get filtered() {
    const q = this.query.trim().toLocaleLowerCase();
    return this.scenes.filter(
      (s) =>
        (!q || `${s.name} ${s.category}`.toLocaleLowerCase().includes(q)) &&
        (!this.category || s.category === this.category) &&
        (!this.favoritesOnly || s.favorite),
    );
  }
  private async apply() {
    if (
      !this.hass?.user ||
      !this.selected ||
      !this.targets.size ||
      this.applying
    )
      return;
    this.applying = true;
    this.confirm = false;
    this.error = "";
    try {
      const r = await new SceneApi(this.hass).applyScene(this.selected, [
        ...this.targets,
      ]);
      this.result = this.t("applySummary")
        .replace("{applied}", String(r?.applied?.length ?? 0))
        .replace("{skipped}", String(r?.skipped?.length ?? 0))
        .replace("{failed}", String(r?.failed?.length ?? 0));
    } catch (e) {
      this.error = e instanceof Error ? e.message : this.t("applyError");
    } finally {
      this.applying = false;
    }
  }
  private palette(s: SceneDefinition) {
    return html`<div class="palette" role="img" aria-label=${this.t("palette")}>
      ${s.palette
        .filter((c) => /^#[0-9a-f]{6}$/i.test(c))
        .map(
          (c) =>
            html`<span class="color" style=${`background-color:${c}`}></span>`,
        )}
    </div>`;
  }
  private origin(s: SceneDefinition) {
    return this.t(
      s.provenance === "builtin"
        ? "builtin"
        : s.provenance === "hue_import"
          ? "hueImport"
          : "user",
    );
  }
  private card(s: SceneDefinition) {
    return html`<button
      class="card"
      aria-pressed=${this.selected?.id === s.id}
      @click=${() => void this.select(s)}
    >
      ${this.palette(s)}<span class="copy"
        ><strong>${s.name}</strong
        ><span class="subtle">${s.category} · ${this.origin(s)}</span></span
      >
    </button>`;
  }
  private details() {
    const s = this.selected;
    if (!s)
      return html`<section class="panel">
        <p>${this.t("noScenes")}</p>
      </section>`;
    const assigned = s.targets ?? [];
    const missing = assigned.filter((t) => !this.hass?.states[t.entity_id]);
    const unavailable = assigned.filter((t) =>
      ["unknown", "unavailable"].includes(
        this.hass?.states[t.entity_id]?.state ?? "",
      ),
    );
    return html`<section class="panel">
        <h2>${this.t("details")}</h2>
        ${this.palette(s)}
        <p><strong>${s.name}</strong></p>
        <p class="subtle">${s.category} · ${this.origin(s)}</p>
        <dl>
          ${s.brightness_pct !== undefined
            ? html`<dt>${this.t("brightness")}</dt>
                <dd>${s.brightness_pct}%</dd>`
            : nothing}${s.transition !== undefined
            ? html`<dt>${this.t("transition")}</dt>
                <dd>${s.transition}s</dd>`
            : nothing}${s.white_temperature_kelvin != null
            ? html`<dt>${this.t("whiteTemperature")}</dt>
                <dd>${s.white_temperature_kelvin} K</dd>`
            : nothing}
        </dl>
        <h2>${this.t("savedTargets")}</h2>
        ${assigned.length
          ? html`<ul>
              ${assigned.map((t) => html`<li>${t.entity_id}</li>`)}
            </ul>`
          : html`<p class="subtle">${this.t("noLights")}</p>`}${missing.length
          ? html`<p class="notice">
              ${this.t("missingTargets")}:
              ${missing.map((t) => t.entity_id).join(", ")}
            </p>`
          : nothing}${unavailable.length
          ? html`<p class="notice">
              ${this.t("unavailable")}:
              ${unavailable.map((t) => t.entity_id).join(", ")}
            </p>`
          : nothing}${s.source?.unmapped_light_ids?.length
          ? html`<p class="notice">
              ${this.t("unmappedHue")}:
              ${s.source.unmapped_light_ids.join(", ")}
            </p>`
          : nothing}${s.source?.unsupported_features?.length
          ? html`<p class="notice">
              ${this.t("unsupportedFeatures")}:
              ${s.source.unsupported_features.join(", ")}
            </p>`
          : nothing}
      </section>
      <section class="panel">
        <h2>${this.t("targets")}</h2>
        ${this.lights.length
          ? html`<div class="lights">
              ${this.lights.map((l) => {
                const off = ["unknown", "unavailable"].includes(l.state);
                const modes = l.attributes.supported_color_modes;
                const unsupported =
                  s.palette.length > 0 &&
                  !(
                    Array.isArray(modes) &&
                    modes.some((m) =>
                      ["xy", "rgb", "hs", "rgbw", "rgbww"].includes(String(m)),
                    )
                  );
                return html`<label class="light"
                  ><input
                    type="checkbox"
                    .checked=${this.targets.has(l.entity_id)}
                    .disabled=${off}
                    @change=${(e: Event) => {
                      const n = new Set(this.targets);
                      const checked = (e.currentTarget as HTMLInputElement)
                        .checked;
                      if (checked) n.add(l.entity_id);
                      else n.delete(l.entity_id);
                      this.targets = n;
                    }}
                  /><span
                    >${String(l.attributes.friendly_name ?? l.entity_id)}
                    <small
                      >${l.entity_id}${off
                        ? ` · ${this.t("unavailable")}`
                        : ""}${unsupported
                        ? ` · ${this.t("unsupported")}`
                        : ""}</small
                    ></span
                  ></label
                >`;
              })}
            </div>`
          : html`<p>${this.t("noLights")}</p>`}${this.hass?.user
          ? html`<div class="actions">
              <button
                class="primary"
                ?disabled=${!this.targets.size || this.applying}
                @click=${() => {
                  this.confirm = true;
                }}
              >
                ${this.t("apply")}
              </button>
            </div>`
          : nothing}${this.error
          ? html`<p class="error" role="alert">${this.error}</p>`
          : nothing}${this.result
          ? html`<p class="success" role="status">${this.result}</p>`
          : nothing}
      </section>
      ${this.confirm
        ? html`<dialog open>
            <h2>${this.t("applyConfirmTitle")}</h2>
            <p>${this.t("applyConfirmBody")}</p>
            <p>${[...this.targets].join(", ")}</p>
            <button @click=${() => void this.apply()}>
              ${this.t("confirmApply")}</button
            ><button
              @click=${() => {
                this.confirm = false;
              }}
            >
              ${this.t("cancel")}
            </button>
          </dialog>`
        : nothing}`;
  }
  render() {
    return html`<main>
      <h1>${this.t("title")}</h1>
      ${this.pending
        ? html`<p class="notice" role="status">
            ${this.t("entitySyncPending")}
          </p>`
        : nothing}
      <div class="toolbar">
        <input
          type="search"
          aria-label=${this.t("search")}
          placeholder=${this.t("search")}
          .value=${this.query}
          @input=${(e: Event) => {
            this.query = (e.currentTarget as HTMLInputElement).value;
          }}
        /><label
          >${this.t("category")}
          <select
            .value=${this.category}
            @change=${(e: Event) => {
              this.category = (e.currentTarget as HTMLSelectElement).value;
            }}
          >
            <option value="">${this.t("allCategories")}</option>
            ${this.categories.map(
              (c) => html`<option value=${c}>${c}</option>`,
            )}
          </select></label
        >
        <label
          ><input
            type="checkbox"
            .checked=${this.favoritesOnly}
            @change=${(e: Event) => {
              this.favoritesOnly = (
                e.currentTarget as HTMLInputElement
              ).checked;
            }}
          />${this.t("favoritesOnly")}</label
        ><button @click=${() => void this.refresh()}>
          ${this.t("refresh")}
        </button>
      </div>
      ${this.loading
        ? html`<p role="status">${this.t("loading")}</p>`
        : nothing}${this.error && !this.selected
        ? html`<div class="error" role="alert">
            <p>${this.t("loadError")}</p>
            <button @click=${() => void this.refresh()}>
              ${this.t("retry")}
            </button>
          </div>`
        : nothing}
      <div class="layout">
        <section class="gallery" aria-label=${this.t("title")}>
          ${this.filtered.map((s) => this.card(s))}${!this.loading &&
          !this.filtered.length
            ? html`<p>${this.t("noScenes")}</p>`
            : nothing}
        </section>
        <aside>${this.details()}</aside>
      </div>
    </main>`;
  }
}
