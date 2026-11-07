const N = globalThis, W = N.ShadowRoot && (N.ShadyCSS === void 0 || N.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, F = /* @__PURE__ */ Symbol(), J = /* @__PURE__ */ new WeakMap();
let at = class {
  constructor(t, s, i) {
    if (this._$cssResult$ = !0, i !== F) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = t, this.t = s;
  }
  get styleSheet() {
    let t = this.o;
    const s = this.t;
    if (W && t === void 0) {
      const i = s !== void 0 && s.length === 1;
      i && (t = J.get(s)), t === void 0 && ((this.o = t = new CSSStyleSheet()).replaceSync(this.cssText), i && J.set(s, t));
    }
    return t;
  }
  toString() {
    return this.cssText;
  }
};
const ut = (e) => new at(typeof e == "string" ? e : e + "", void 0, F), gt = (e, ...t) => {
  const s = e.length === 1 ? e[0] : t.reduce((i, r, n) => i + ((o) => {
    if (o._$cssResult$ === !0) return o.cssText;
    if (typeof o == "number") return o;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + o + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(r) + e[n + 1], e[0]);
  return new at(s, e, F);
}, $t = (e, t) => {
  if (W) e.adoptedStyleSheets = t.map((s) => s instanceof CSSStyleSheet ? s : s.styleSheet);
  else for (const s of t) {
    const i = document.createElement("style"), r = N.litNonce;
    r !== void 0 && i.setAttribute("nonce", r), i.textContent = s.cssText, e.appendChild(i);
  }
}, Q = W ? (e) => e : (e) => e instanceof CSSStyleSheet ? ((t) => {
  let s = "";
  for (const i of t.cssRules) s += i.cssText;
  return ut(s);
})(e) : e;
const { is: ft, defineProperty: yt, getOwnPropertyDescriptor: mt, getOwnPropertyNames: _t, getOwnPropertySymbols: vt, getPrototypeOf: bt } = Object, R = globalThis, X = R.trustedTypes, At = X ? X.emptyScript : "", St = R.reactiveElementPolyfillSupport, C = (e, t) => e, z = { toAttribute(e, t) {
  switch (t) {
    case Boolean:
      e = e ? At : null;
      break;
    case Object:
    case Array:
      e = e == null ? e : JSON.stringify(e);
  }
  return e;
}, fromAttribute(e, t) {
  let s = e;
  switch (t) {
    case Boolean:
      s = e !== null;
      break;
    case Number:
      s = e === null ? null : Number(e);
      break;
    case Object:
    case Array:
      try {
        s = JSON.parse(e);
      } catch {
        s = null;
      }
  }
  return s;
} }, V = (e, t) => !ft(e, t), Y = { attribute: !0, type: String, converter: z, reflect: !1, useDefault: !1, hasChanged: V };
Symbol.metadata ??= /* @__PURE__ */ Symbol("metadata"), R.litPropertyMetadata ??= /* @__PURE__ */ new WeakMap();
let S = class extends HTMLElement {
  static addInitializer(t) {
    this._$Ei(), (this.l ??= []).push(t);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(t, s = Y) {
    if (s.state && (s.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(t) && ((s = Object.create(s)).wrapped = !0), this.elementProperties.set(t, s), !s.noAccessor) {
      const i = /* @__PURE__ */ Symbol(), r = this.getPropertyDescriptor(t, i, s);
      r !== void 0 && yt(this.prototype, t, r);
    }
  }
  static getPropertyDescriptor(t, s, i) {
    const { get: r, set: n } = mt(this.prototype, t) ?? { get() {
      return this[s];
    }, set(o) {
      this[s] = o;
    } };
    return { get: r, set(o) {
      const h = r?.call(this);
      n?.call(this, o), this.requestUpdate(t, h, i);
    }, configurable: !0, enumerable: !0 };
  }
  static getPropertyOptions(t) {
    return this.elementProperties.get(t) ?? Y;
  }
  static _$Ei() {
    if (this.hasOwnProperty(C("elementProperties"))) return;
    const t = bt(this);
    t.finalize(), t.l !== void 0 && (this.l = [...t.l]), this.elementProperties = new Map(t.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(C("finalized"))) return;
    if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(C("properties"))) {
      const s = this.properties, i = [..._t(s), ...vt(s)];
      for (const r of i) this.createProperty(r, s[r]);
    }
    const t = this[Symbol.metadata];
    if (t !== null) {
      const s = litPropertyMetadata.get(t);
      if (s !== void 0) for (const [i, r] of s) this.elementProperties.set(i, r);
    }
    this._$Eh = /* @__PURE__ */ new Map();
    for (const [s, i] of this.elementProperties) {
      const r = this._$Eu(s, i);
      r !== void 0 && this._$Eh.set(r, s);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(t) {
    const s = [];
    if (Array.isArray(t)) {
      const i = new Set(t.flat(1 / 0).reverse());
      for (const r of i) s.unshift(Q(r));
    } else t !== void 0 && s.push(Q(t));
    return s;
  }
  static _$Eu(t, s) {
    const i = s.attribute;
    return i === !1 ? void 0 : typeof i == "string" ? i : typeof t == "string" ? t.toLowerCase() : void 0;
  }
  constructor() {
    super(), this._$Ep = void 0, this.isUpdatePending = !1, this.hasUpdated = !1, this._$Em = null, this._$Ev();
  }
  _$Ev() {
    this._$ES = new Promise((t) => this.enableUpdating = t), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), this.constructor.l?.forEach((t) => t(this));
  }
  addController(t) {
    (this._$EO ??= /* @__PURE__ */ new Set()).add(t), this.renderRoot !== void 0 && this.isConnected && t.hostConnected?.();
  }
  removeController(t) {
    this._$EO?.delete(t);
  }
  _$E_() {
    const t = /* @__PURE__ */ new Map(), s = this.constructor.elementProperties;
    for (const i of s.keys()) this.hasOwnProperty(i) && (t.set(i, this[i]), delete this[i]);
    t.size > 0 && (this._$Ep = t);
  }
  createRenderRoot() {
    const t = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
    return $t(t, this.constructor.elementStyles), t;
  }
  connectedCallback() {
    this.renderRoot ??= this.createRenderRoot(), this.enableUpdating(!0), this._$EO?.forEach((t) => t.hostConnected?.());
  }
  enableUpdating(t) {
  }
  disconnectedCallback() {
    this._$EO?.forEach((t) => t.hostDisconnected?.());
  }
  attributeChangedCallback(t, s, i) {
    this._$AK(t, i);
  }
  _$ET(t, s) {
    const i = this.constructor.elementProperties.get(t), r = this.constructor._$Eu(t, i);
    if (r !== void 0 && i.reflect === !0) {
      const n = (i.converter?.toAttribute !== void 0 ? i.converter : z).toAttribute(s, i.type);
      this._$Em = t, n == null ? this.removeAttribute(r) : this.setAttribute(r, n), this._$Em = null;
    }
  }
  _$AK(t, s) {
    const i = this.constructor, r = i._$Eh.get(t);
    if (r !== void 0 && this._$Em !== r) {
      const n = i.getPropertyOptions(r), o = typeof n.converter == "function" ? { fromAttribute: n.converter } : n.converter?.fromAttribute !== void 0 ? n.converter : z;
      this._$Em = r;
      const h = o.fromAttribute(s, n.type);
      this[r] = h ?? this._$Ej?.get(r) ?? h, this._$Em = null;
    }
  }
  requestUpdate(t, s, i, r = !1, n) {
    if (t !== void 0) {
      const o = this.constructor;
      if (r === !1 && (n = this[t]), i ??= o.getPropertyOptions(t), !((i.hasChanged ?? V)(n, s) || i.useDefault && i.reflect && n === this._$Ej?.get(t) && !this.hasAttribute(o._$Eu(t, i)))) return;
      this.C(t, s, i);
    }
    this.isUpdatePending === !1 && (this._$ES = this._$EP());
  }
  C(t, s, { useDefault: i, reflect: r, wrapped: n }, o) {
    i && !(this._$Ej ??= /* @__PURE__ */ new Map()).has(t) && (this._$Ej.set(t, o ?? s ?? this[t]), n !== !0 || o !== void 0) || (this._$AL.has(t) || (this.hasUpdated || i || (s = void 0), this._$AL.set(t, s)), r === !0 && this._$Em !== t && (this._$Eq ??= /* @__PURE__ */ new Set()).add(t));
  }
  async _$EP() {
    this.isUpdatePending = !0;
    try {
      await this._$ES;
    } catch (s) {
      Promise.reject(s);
    }
    const t = this.scheduleUpdate();
    return t != null && await t, !this.isUpdatePending;
  }
  scheduleUpdate() {
    return this.performUpdate();
  }
  performUpdate() {
    if (!this.isUpdatePending) return;
    if (!this.hasUpdated) {
      if (this.renderRoot ??= this.createRenderRoot(), this._$Ep) {
        for (const [r, n] of this._$Ep) this[r] = n;
        this._$Ep = void 0;
      }
      const i = this.constructor.elementProperties;
      if (i.size > 0) for (const [r, n] of i) {
        const { wrapped: o } = n, h = this[r];
        o !== !0 || this._$AL.has(r) || h === void 0 || this.C(r, void 0, n, h);
      }
    }
    let t = !1;
    const s = this._$AL;
    try {
      t = this.shouldUpdate(s), t ? (this.willUpdate(s), this._$EO?.forEach((i) => i.hostUpdate?.()), this.update(s)) : this._$EM();
    } catch (i) {
      throw t = !1, this._$EM(), i;
    }
    t && this._$AE(s);
  }
  willUpdate(t) {
  }
  _$AE(t) {
    this._$EO?.forEach((s) => s.hostUpdated?.()), this.hasUpdated || (this.hasUpdated = !0, this.firstUpdated(t)), this.updated(t);
  }
  _$EM() {
    this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = !1;
  }
  get updateComplete() {
    return this.getUpdateComplete();
  }
  getUpdateComplete() {
    return this._$ES;
  }
  shouldUpdate(t) {
    return !0;
  }
  update(t) {
    this._$Eq &&= this._$Eq.forEach((s) => this._$ET(s, this[s])), this._$EM();
  }
  updated(t) {
  }
  firstUpdated(t) {
  }
};
S.elementStyles = [], S.shadowRootOptions = { mode: "open" }, S[C("elementProperties")] = /* @__PURE__ */ new Map(), S[C("finalized")] = /* @__PURE__ */ new Map(), St?.({ ReactiveElement: S }), (R.reactiveElementVersions ??= []).push("2.1.2");
const G = globalThis, tt = (e) => e, L = G.trustedTypes, et = L ? L.createPolicy("lit-html", { createHTML: (e) => e }) : void 0, lt = "$lit$", _ = `lit$${Math.random().toFixed(9).slice(2)}$`, ht = "?" + _, wt = `<${ht}>`, A = document, O = () => A.createComment(""), T = (e) => e === null || typeof e != "object" && typeof e != "function", K = Array.isArray, Et = (e) => K(e) || typeof e?.[Symbol.iterator] == "function", I = `[ 	
\f\r]`, x = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, st = /-->/g, it = />/g, v = RegExp(`>|${I}(?:([^\\s"'>=/]+)(${I}*=${I}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g"), rt = /'/g, nt = /"/g, ct = /^(?:script|style|textarea|title)$/i, xt = (e) => (t, ...s) => ({ _$litType$: e, strings: t, values: s }), c = xt(1), w = /* @__PURE__ */ Symbol.for("lit-noChange"), l = /* @__PURE__ */ Symbol.for("lit-nothing"), ot = /* @__PURE__ */ new WeakMap(), b = A.createTreeWalker(A, 129);
function pt(e, t) {
  if (!K(e) || !e.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return et !== void 0 ? et.createHTML(t) : t;
}
const Ct = (e, t) => {
  const s = e.length - 1, i = [];
  let r, n = t === 2 ? "<svg>" : t === 3 ? "<math>" : "", o = x;
  for (let h = 0; h < s; h++) {
    const a = e[h];
    let d, g, p = -1, y = 0;
    for (; y < a.length && (o.lastIndex = y, g = o.exec(a), g !== null); ) y = o.lastIndex, o === x ? g[1] === "!--" ? o = st : g[1] !== void 0 ? o = it : g[2] !== void 0 ? (ct.test(g[2]) && (r = RegExp("</" + g[2], "g")), o = v) : g[3] !== void 0 && (o = v) : o === v ? g[0] === ">" ? (o = r ?? x, p = -1) : g[1] === void 0 ? p = -2 : (p = o.lastIndex - g[2].length, d = g[1], o = g[3] === void 0 ? v : g[3] === '"' ? nt : rt) : o === nt || o === rt ? o = v : o === st || o === it ? o = x : (o = v, r = void 0);
    const m = o === v && e[h + 1].startsWith("/>") ? " " : "";
    n += o === x ? a + wt : p >= 0 ? (i.push(d), a.slice(0, p) + lt + a.slice(p) + _ + m) : a + _ + (p === -2 ? h : m);
  }
  return [pt(e, n + (e[s] || "<?>") + (t === 2 ? "</svg>" : t === 3 ? "</math>" : "")), i];
};
class k {
  constructor({ strings: t, _$litType$: s }, i) {
    let r;
    this.parts = [];
    let n = 0, o = 0;
    const h = t.length - 1, a = this.parts, [d, g] = Ct(t, s);
    if (this.el = k.createElement(d, i), b.currentNode = this.el.content, s === 2 || s === 3) {
      const p = this.el.content.firstChild;
      p.replaceWith(...p.childNodes);
    }
    for (; (r = b.nextNode()) !== null && a.length < h; ) {
      if (r.nodeType === 1) {
        if (r.hasAttributes()) for (const p of r.getAttributeNames()) if (p.endsWith(lt)) {
          const y = g[o++], m = r.getAttribute(p).split(_), M = /([.?@])?(.*)/.exec(y);
          a.push({ type: 1, index: n, name: M[2], strings: m, ctor: M[1] === "." ? Ot : M[1] === "?" ? Tt : M[1] === "@" ? kt : j }), r.removeAttribute(p);
        } else p.startsWith(_) && (a.push({ type: 6, index: n }), r.removeAttribute(p));
        if (ct.test(r.tagName)) {
          const p = r.textContent.split(_), y = p.length - 1;
          if (y > 0) {
            r.textContent = L ? L.emptyScript : "";
            for (let m = 0; m < y; m++) r.append(p[m], O()), b.nextNode(), a.push({ type: 2, index: ++n });
            r.append(p[y], O());
          }
        }
      } else if (r.nodeType === 8) if (r.data === ht) a.push({ type: 2, index: n });
      else {
        let p = -1;
        for (; (p = r.data.indexOf(_, p + 1)) !== -1; ) a.push({ type: 7, index: n }), p += _.length - 1;
      }
      n++;
    }
  }
  static createElement(t, s) {
    const i = A.createElement("template");
    return i.innerHTML = t, i;
  }
}
function E(e, t, s = e, i) {
  if (t === w) return t;
  let r = i !== void 0 ? s._$Co?.[i] : s._$Cl;
  const n = T(t) ? void 0 : t._$litDirective$;
  return r?.constructor !== n && (r?._$AO?.(!1), n === void 0 ? r = void 0 : (r = new n(e), r._$AT(e, s, i)), i !== void 0 ? (s._$Co ??= [])[i] = r : s._$Cl = r), r !== void 0 && (t = E(e, r._$AS(e, t.values), r, i)), t;
}
class Pt {
  constructor(t, s) {
    this._$AV = [], this._$AN = void 0, this._$AD = t, this._$AM = s;
  }
  get parentNode() {
    return this._$AM.parentNode;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  u(t) {
    const { el: { content: s }, parts: i } = this._$AD, r = (t?.creationScope ?? A).importNode(s, !0);
    b.currentNode = r;
    let n = b.nextNode(), o = 0, h = 0, a = i[0];
    for (; a !== void 0; ) {
      if (o === a.index) {
        let d;
        a.type === 2 ? d = new U(n, n.nextSibling, this, t) : a.type === 1 ? d = new a.ctor(n, a.name, a.strings, this, t) : a.type === 6 && (d = new Ut(n, this, t)), this._$AV.push(d), a = i[++h];
      }
      o !== a?.index && (n = b.nextNode(), o++);
    }
    return b.currentNode = A, r;
  }
  p(t) {
    let s = 0;
    for (const i of this._$AV) i !== void 0 && (i.strings !== void 0 ? (i._$AI(t, i, s), s += i.strings.length - 2) : i._$AI(t[s])), s++;
  }
}
class U {
  get _$AU() {
    return this._$AM?._$AU ?? this._$Cv;
  }
  constructor(t, s, i, r) {
    this.type = 2, this._$AH = l, this._$AN = void 0, this._$AA = t, this._$AB = s, this._$AM = i, this.options = r, this._$Cv = r?.isConnected ?? !0;
  }
  get parentNode() {
    let t = this._$AA.parentNode;
    const s = this._$AM;
    return s !== void 0 && t?.nodeType === 11 && (t = s.parentNode), t;
  }
  get startNode() {
    return this._$AA;
  }
  get endNode() {
    return this._$AB;
  }
  _$AI(t, s = this) {
    t = E(this, t, s), T(t) ? t === l || t == null || t === "" ? (this._$AH !== l && this._$AR(), this._$AH = l) : t !== this._$AH && t !== w && this._(t) : t._$litType$ !== void 0 ? this.$(t) : t.nodeType !== void 0 ? this.T(t) : Et(t) ? this.k(t) : this._(t);
  }
  O(t) {
    return this._$AA.parentNode.insertBefore(t, this._$AB);
  }
  T(t) {
    this._$AH !== t && (this._$AR(), this._$AH = this.O(t));
  }
  _(t) {
    this._$AH !== l && T(this._$AH) ? this._$AA.nextSibling.data = t : this.T(A.createTextNode(t)), this._$AH = t;
  }
  $(t) {
    const { values: s, _$litType$: i } = t, r = typeof i == "number" ? this._$AC(t) : (i.el === void 0 && (i.el = k.createElement(pt(i.h, i.h[0]), this.options)), i);
    if (this._$AH?._$AD === r) this._$AH.p(s);
    else {
      const n = new Pt(r, this), o = n.u(this.options);
      n.p(s), this.T(o), this._$AH = n;
    }
  }
  _$AC(t) {
    let s = ot.get(t.strings);
    return s === void 0 && ot.set(t.strings, s = new k(t)), s;
  }
  k(t) {
    K(this._$AH) || (this._$AH = [], this._$AR());
    const s = this._$AH;
    let i, r = 0;
    for (const n of t) r === s.length ? s.push(i = new U(this.O(O()), this.O(O()), this, this.options)) : i = s[r], i._$AI(n), r++;
    r < s.length && (this._$AR(i && i._$AB.nextSibling, r), s.length = r);
  }
  _$AR(t = this._$AA.nextSibling, s) {
    for (this._$AP?.(!1, !0, s); t !== this._$AB; ) {
      const i = tt(t).nextSibling;
      tt(t).remove(), t = i;
    }
  }
  setConnected(t) {
    this._$AM === void 0 && (this._$Cv = t, this._$AP?.(t));
  }
}
class j {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(t, s, i, r, n) {
    this.type = 1, this._$AH = l, this._$AN = void 0, this.element = t, this.name = s, this._$AM = r, this.options = n, i.length > 2 || i[0] !== "" || i[1] !== "" ? (this._$AH = Array(i.length - 1).fill(new String()), this.strings = i) : this._$AH = l;
  }
  _$AI(t, s = this, i, r) {
    const n = this.strings;
    let o = !1;
    if (n === void 0) t = E(this, t, s, 0), o = !T(t) || t !== this._$AH && t !== w, o && (this._$AH = t);
    else {
      const h = t;
      let a, d;
      for (t = n[0], a = 0; a < n.length - 1; a++) d = E(this, h[i + a], s, a), d === w && (d = this._$AH[a]), o ||= !T(d) || d !== this._$AH[a], d === l ? t = l : t !== l && (t += (d ?? "") + n[a + 1]), this._$AH[a] = d;
    }
    o && !r && this.j(t);
  }
  j(t) {
    t === l ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, t ?? "");
  }
}
class Ot extends j {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(t) {
    this.element[this.name] = t === l ? void 0 : t;
  }
}
class Tt extends j {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(t) {
    this.element.toggleAttribute(this.name, !!t && t !== l);
  }
}
class kt extends j {
  constructor(t, s, i, r, n) {
    super(t, s, i, r, n), this.type = 5;
  }
  _$AI(t, s = this) {
    if ((t = E(this, t, s, 0) ?? l) === w) return;
    const i = this._$AH, r = t === l && i !== l || t.capture !== i.capture || t.once !== i.once || t.passive !== i.passive, n = t !== l && (i === l || r);
    r && this.element.removeEventListener(this.name, this, i), n && this.element.addEventListener(this.name, this, t), this._$AH = t;
  }
  handleEvent(t) {
    typeof this._$AH == "function" ? this._$AH.call(this.options?.host ?? this.element, t) : this._$AH.handleEvent(t);
  }
}
class Ut {
  constructor(t, s, i) {
    this.element = t, this.type = 6, this._$AN = void 0, this._$AM = s, this.options = i;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(t) {
    E(this, t);
  }
}
const Ht = G.litHtmlPolyfillSupport;
Ht?.(k, U), (G.litHtmlVersions ??= []).push("3.3.3");
const Mt = (e, t, s) => {
  const i = s?.renderBefore ?? t;
  let r = i._$litPart$;
  if (r === void 0) {
    const n = s?.renderBefore ?? null;
    i._$litPart$ = r = new U(t.insertBefore(O(), n), n, void 0, s ?? {});
  }
  return r._$AI(e), r;
};
const Z = globalThis;
class P extends S {
  constructor() {
    super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
  }
  createRenderRoot() {
    const t = super.createRenderRoot();
    return this.renderOptions.renderBefore ??= t.firstChild, t;
  }
  update(t) {
    const s = this.render();
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(t), this._$Do = Mt(s, this.renderRoot, this.renderOptions);
  }
  connectedCallback() {
    super.connectedCallback(), this._$Do?.setConnected(!0);
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this._$Do?.setConnected(!1);
  }
  render() {
    return w;
  }
}
P._$litElement$ = !0, P.finalized = !0, Z.litElementHydrateSupport?.({ LitElement: P });
const Nt = Z.litElementPolyfillSupport;
Nt?.({ LitElement: P });
(Z.litElementVersions ??= []).push("4.2.2");
const zt = (e) => (t, s) => {
  s !== void 0 ? s.addInitializer(() => {
    customElements.define(e, t);
  }) : customElements.define(e, t);
};
const Lt = { attribute: !0, type: String, converter: z, reflect: !1, hasChanged: V }, Rt = (e = Lt, t, s) => {
  const { kind: i, metadata: r } = s;
  let n = globalThis.litPropertyMetadata.get(r);
  if (n === void 0 && globalThis.litPropertyMetadata.set(r, n = /* @__PURE__ */ new Map()), i === "setter" && ((e = Object.create(e)).wrapped = !0), n.set(s.name, e), i === "accessor") {
    const { name: o } = s;
    return { set(h) {
      const a = t.get.call(this);
      t.set.call(this, h), this.requestUpdate(o, a, e, !0, h);
    }, init(h) {
      return h !== void 0 && this.C(o, void 0, e, h), h;
    } };
  }
  if (i === "setter") {
    const { name: o } = s;
    return function(h) {
      const a = this[o];
      t.call(this, h), this.requestUpdate(o, a, e, !0, h);
    };
  }
  throw Error("Unsupported decorator location: " + i);
};
function H(e) {
  return (t, s) => typeof s == "object" ? Rt(e, t, s) : ((i, r, n) => {
    const o = r.hasOwnProperty(n);
    return r.constructor.createProperty(n, i), o ? Object.getOwnPropertyDescriptor(r, n) : void 0;
  })(e, t, s);
}
function f(e) {
  return H({ ...e, state: !0, attribute: !1 });
}
const D = "smart_scene_studio";
class q {
  constructor(t) {
    this.hass = t;
  }
  async listScenes() {
    const t = await this.hass.callWS({
      type: `${D}/scene/list`
    });
    if (!t || !Array.isArray(t.scenes))
      throw new Error("The scene service returned an invalid list response.");
    return t;
  }
  async getScene(t) {
    return this.hass.callWS({
      type: `${D}/scene/get`,
      scene_id: t
    });
  }
  async applyScene(t, s) {
    const i = [...new Set(s)];
    if (i.some((n) => !/^light\.[a-z0-9_]+$/.test(n)))
      throw new Error("Select only valid Home Assistant light entities.");
    if (i.length === 0)
      throw new Error("Select at least one light before applying a scene.");
    if (i.length > 64)
      throw new Error("Select no more than 64 lights before applying a scene.");
    const r = await this.hass.callService(
      D,
      "apply_scene",
      { scene_id: t.id, entity_id: i },
      void 0,
      !1,
      !0
    );
    return jt(r);
  }
}
function jt(e) {
  if (!e || typeof e != "object") return null;
  const t = "response" in e ? e.response : e;
  if (!t || typeof t != "object") return null;
  const s = t;
  return {
    applied: B(s.applied),
    skipped: B(s.skipped),
    failed: B(s.failed)
  };
}
function B(e) {
  return Array.isArray(e) && e.every((t) => typeof t == "string") ? e : void 0;
}
const dt = {
  title: "Smart Scene Studio",
  search: "Search scenes",
  category: "Category",
  allCategories: "All categories",
  favoritesOnly: "Favorites only",
  refresh: "Refresh scenes",
  loading: "Loading scenes…",
  loadError: "Scenes could not be loaded.",
  retry: "Try again",
  noScenes: "No scenes match these filters.",
  noLights: "No light entities are available.",
  details: "Scene details",
  palette: "Palette preview",
  targets: "Choose lights",
  savedTargets: "Saved targets",
  missingTargets: "Missing saved lights",
  unavailable: "Unavailable",
  unsupported: "Color mode may not be supported",
  unmappedHue: "Unmapped Hue lights",
  unsupportedFeatures: "Features not reproduced",
  entitySyncPending: "Scenes are saved, but native scene entities need synchronization.",
  apply: "Apply to lights",
  confirmApply: "Confirm apply",
  cancel: "Cancel",
  applyConfirmTitle: "Apply this scene?",
  applyConfirmBody: "This sends a light command to the selected lights.",
  selectLight: "Select at least one available light to apply this scene.",
  applying: "Applying scene…",
  applyError: "The scene could not be applied. Check your Home Assistant permissions and try again.",
  applySummary: "Applied: {applied}; skipped: {skipped}; failed: {failed}.",
  builtin: "Built-in",
  user: "My scene",
  hueImport: "Hue import",
  favorite: "Favorite",
  brightness: "Brightness",
  transition: "Transition",
  whiteTemperature: "White temperature",
  adminOnly: "Only administrators can manage scenes."
}, It = {
  title: "Smart Scene Studio",
  search: "Cerca scene",
  category: "Categoria",
  allCategories: "Tutte le categorie",
  favoritesOnly: "Solo preferite",
  refresh: "Aggiorna scene",
  loading: "Caricamento scene…",
  loadError: "Impossibile caricare le scene.",
  retry: "Riprova",
  noScenes: "Nessuna scena corrisponde ai filtri.",
  noLights: "Nessuna lampada disponibile.",
  details: "Dettagli scena",
  palette: "Anteprima palette",
  targets: "Scegli lampade",
  savedTargets: "Lampade assegnate",
  missingTargets: "Lampade assegnate mancanti",
  unavailable: "Non disponibile",
  unsupported: "La modalità colore potrebbe non essere supportata",
  unmappedHue: "Lampade Hue non associate",
  unsupportedFeatures: "Funzioni non riprodotte",
  entitySyncPending: "Scene salvate, ma la sincronizzazione delle scene native è in sospeso.",
  apply: "Applica alle lampade",
  confirmApply: "Conferma applicazione",
  cancel: "Annulla",
  applyConfirmTitle: "Applicare questa scena?",
  applyConfirmBody: "Invierà un comando alle lampade selezionate.",
  selectLight: "Seleziona almeno una lampada disponibile.",
  applying: "Applicazione scena…",
  applyError: "Impossibile applicare la scena. Controlla i permessi Home Assistant e riprova.",
  applySummary: "Applicate: {applied}; ignorate: {skipped}; non riuscite: {failed}.",
  builtin: "Integrata",
  user: "La mia scena",
  hueImport: "Importazione Hue",
  favorite: "Preferita",
  brightness: "Luminosità",
  transition: "Transizione",
  whiteTemperature: "Temperatura del bianco",
  adminOnly: "Solo gli amministratori possono gestire le scene."
}, Dt = { en: dt, it: It };
function qt(e, t = "en", s) {
  const i = t.toLowerCase().split(/[-_]/)[0] ?? "en";
  let r = (Dt[i] ?? dt)[e];
  for (const [n, o] of Object.entries({}))
    r = r.replaceAll(`{${n}}`, String(o));
  return r;
}
function Bt(e, t) {
  return t?.language ?? e ?? "en";
}
var Wt = Object.defineProperty, Ft = Object.getOwnPropertyDescriptor, $ = (e, t, s, i) => {
  for (var r = i > 1 ? void 0 : i ? Ft(t, s) : t, n = e.length - 1, o; n >= 0; n--)
    (o = e[n]) && (r = (i ? o(t, s, r) : o(r)) || r);
  return i && r && Wt(t, s, r), r;
};
let u = class extends P {
  constructor() {
    super(...arguments), this.narrow = !1, this.scenes = [], this.query = "", this.category = "", this.favoritesOnly = !1, this.targets = /* @__PURE__ */ new Set(), this.loading = !0, this.error = "", this.pending = !1, this.confirm = !1, this.applying = !1, this.result = "", this.initialized = !1, this.requestGeneration = 0;
  }
  t(e) {
    return qt(e, Bt(this.hass?.language, this.hass?.locale));
  }
  updated(e) {
    e.has("hass") && this.hass && !this.initialized && (this.initialized = !0, this.refresh());
  }
  async refresh() {
    if (!this.hass) return;
    const e = ++this.requestGeneration;
    this.loading = !0, this.error = "";
    try {
      const t = await new q(this.hass).listScenes();
      if (e !== this.requestGeneration) return;
      this.scenes = t.scenes, this.pending = t.entity_sync?.status === "pending", this.selected && (this.selected = this.scenes.find(
        (s) => s.id === this.selected?.id
      )), !this.selected && this.scenes.length && await this.select(this.scenes[0]);
    } catch (t) {
      e === this.requestGeneration && (this.error = t instanceof Error ? t.message : this.t("loadError"));
    } finally {
      e === this.requestGeneration && (this.loading = !1);
    }
  }
  async select(e) {
    this.selected = e, this.targets = /* @__PURE__ */ new Set(), this.confirm = !1;
    try {
      const t = await new q(this.hass).getScene(e.id);
      this.selected?.id === e.id && (this.selected = t.scene);
    } catch {
    }
    this.selected?.id === e.id && (this.targets = new Set(
      (this.selected.targets ?? []).filter((t) => t.enabled !== !1 && this.available(t.entity_id)).map((t) => t.entity_id)
    ));
  }
  available(e) {
    const t = this.hass?.states[e]?.state;
    return !!(t && t !== "unknown" && t !== "unavailable");
  }
  get lights() {
    return Object.values(this.hass?.states ?? {}).filter(
      (e) => e.entity_id.startsWith("light.")
    );
  }
  get categories() {
    return [
      ...new Set(this.scenes.map((e) => e.category).filter(Boolean))
    ].sort();
  }
  get filtered() {
    const e = this.query.trim().toLocaleLowerCase();
    return this.scenes.filter(
      (t) => (!e || `${t.name} ${t.category}`.toLocaleLowerCase().includes(e)) && (!this.category || t.category === this.category) && (!this.favoritesOnly || t.favorite)
    );
  }
  async apply() {
    if (!(!this.hass?.user || !this.selected || !this.targets.size || this.applying)) {
      this.applying = !0, this.confirm = !1, this.error = "";
      try {
        const e = await new q(this.hass).applyScene(this.selected, [
          ...this.targets
        ]);
        this.result = this.t("applySummary").replace("{applied}", String(e?.applied?.length ?? 0)).replace("{skipped}", String(e?.skipped?.length ?? 0)).replace("{failed}", String(e?.failed?.length ?? 0));
      } catch (e) {
        this.error = e instanceof Error ? e.message : this.t("applyError");
      } finally {
        this.applying = !1;
      }
    }
  }
  palette(e) {
    return c`<div class="palette" role="img" aria-label=${this.t("palette")}>
      ${e.palette.filter((t) => /^#[0-9a-f]{6}$/i.test(t)).map(
      (t) => c`<span class="color" style=${`background-color:${t}`}></span>`
    )}
    </div>`;
  }
  origin(e) {
    return this.t(
      e.provenance === "builtin" ? "builtin" : e.provenance === "hue_import" ? "hueImport" : "user"
    );
  }
  card(e) {
    return c`<button
      class="card"
      aria-pressed=${this.selected?.id === e.id}
      @click=${() => {
      this.select(e);
    }}
    >
      ${this.palette(e)}<span class="copy"
        ><strong>${e.name}</strong
        ><span class="subtle">${e.category} · ${this.origin(e)}</span></span
      >
    </button>`;
  }
  details() {
    const e = this.selected;
    if (!e)
      return c`<section class="panel">
        <p>${this.t("noScenes")}</p>
      </section>`;
    const t = e.targets ?? [], s = t.filter((r) => !this.hass?.states[r.entity_id]), i = t.filter(
      (r) => ["unknown", "unavailable"].includes(
        this.hass?.states[r.entity_id]?.state ?? ""
      )
    );
    return c`<section class="panel">
        <h2>${this.t("details")}</h2>
        ${this.palette(e)}
        <p><strong>${e.name}</strong></p>
        <p class="subtle">${e.category} · ${this.origin(e)}</p>
        <dl>
          ${e.brightness_pct !== void 0 ? c`<dt>${this.t("brightness")}</dt>
                <dd>${e.brightness_pct}%</dd>` : l}${e.transition !== void 0 ? c`<dt>${this.t("transition")}</dt>
                <dd>${e.transition}s</dd>` : l}${e.white_temperature_kelvin != null ? c`<dt>${this.t("whiteTemperature")}</dt>
                <dd>${e.white_temperature_kelvin} K</dd>` : l}
        </dl>
        <h2>${this.t("savedTargets")}</h2>
        ${t.length ? c`<ul>
              ${t.map((r) => c`<li>${r.entity_id}</li>`)}
            </ul>` : c`<p class="subtle">${this.t("noLights")}</p>`}${s.length ? c`<p class="notice">
              ${this.t("missingTargets")}:
              ${s.map((r) => r.entity_id).join(", ")}
            </p>` : l}${i.length ? c`<p class="notice">
              ${this.t("unavailable")}:
              ${i.map((r) => r.entity_id).join(", ")}
            </p>` : l}${e.source?.unmapped_light_ids?.length ? c`<p class="notice">
              ${this.t("unmappedHue")}:
              ${e.source.unmapped_light_ids.join(", ")}
            </p>` : l}${e.source?.unsupported_features?.length ? c`<p class="notice">
              ${this.t("unsupportedFeatures")}:
              ${e.source.unsupported_features.join(", ")}
            </p>` : l}
      </section>
      <section class="panel">
        <h2>${this.t("targets")}</h2>
        ${this.lights.length ? c`<div class="lights">
              ${this.lights.map((r) => {
      const n = ["unknown", "unavailable"].includes(r.state), o = r.attributes.supported_color_modes, h = e.palette.length > 0 && !(Array.isArray(o) && o.some(
        (a) => ["xy", "rgb", "hs", "rgbw", "rgbww"].includes(String(a))
      ));
      return c`<label class="light"
                  ><input
                    type="checkbox"
                    .checked=${this.targets.has(r.entity_id)}
                    .disabled=${n}
                    @change=${(a) => {
        const d = new Set(this.targets);
        a.currentTarget.checked ? d.add(r.entity_id) : d.delete(r.entity_id), this.targets = d;
      }}
                  /><span
                    >${String(r.attributes.friendly_name ?? r.entity_id)}
                    <small
                      >${r.entity_id}${n ? ` · ${this.t("unavailable")}` : ""}${h ? ` · ${this.t("unsupported")}` : ""}</small
                    ></span
                  ></label
                >`;
    })}
            </div>` : c`<p>${this.t("noLights")}</p>`}${this.hass?.user ? c`<div class="actions">
              <button
                class="primary"
                ?disabled=${!this.targets.size || this.applying}
                @click=${() => {
      this.confirm = !0;
    }}
              >
                ${this.t("apply")}
              </button>
            </div>` : l}${this.error ? c`<p class="error" role="alert">${this.error}</p>` : l}${this.result ? c`<p class="success" role="status">${this.result}</p>` : l}
      </section>
      ${this.confirm ? c`<dialog open>
            <h2>${this.t("applyConfirmTitle")}</h2>
            <p>${this.t("applyConfirmBody")}</p>
            <p>${[...this.targets].join(", ")}</p>
            <button @click=${() => {
      this.apply();
    }}>
              ${this.t("confirmApply")}</button
            ><button
              @click=${() => {
      this.confirm = !1;
    }}
            >
              ${this.t("cancel")}
            </button>
          </dialog>` : l}`;
  }
  render() {
    return c`<main>
      <h1>${this.t("title")}</h1>
      ${this.pending ? c`<p class="notice" role="status">
            ${this.t("entitySyncPending")}
          </p>` : l}
      <div class="toolbar">
        <input
          type="search"
          aria-label=${this.t("search")}
          placeholder=${this.t("search")}
          .value=${this.query}
          @input=${(e) => {
      this.query = e.currentTarget.value;
    }}
        /><label
          >${this.t("category")}
          <select
            .value=${this.category}
            @change=${(e) => {
      this.category = e.currentTarget.value;
    }}
          >
            <option value="">${this.t("allCategories")}</option>
            ${this.categories.map(
      (e) => c`<option value=${e}>${e}</option>`
    )}
          </select></label
        >
        <label
          ><input
            type="checkbox"
            .checked=${this.favoritesOnly}
            @change=${(e) => {
      this.favoritesOnly = e.currentTarget.checked;
    }}
          />${this.t("favoritesOnly")}</label
        ><button @click=${() => {
      this.refresh();
    }}>
          ${this.t("refresh")}
        </button>
      </div>
      ${this.loading ? c`<p role="status">${this.t("loading")}</p>` : l}${this.error && !this.selected ? c`<div class="error" role="alert">
            <p>${this.t("loadError")}</p>
            <button @click=${() => {
      this.refresh();
    }}>
              ${this.t("retry")}
            </button>
          </div>` : l}
      <div class="layout">
        <section class="gallery" aria-label=${this.t("title")}>
          ${this.filtered.map((e) => this.card(e))}${!this.loading && !this.filtered.length ? c`<p>${this.t("noScenes")}</p>` : l}
        </section>
        <aside>${this.details()}</aside>
      </div>
    </main>`;
  }
};
u.styles = gt`
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
$([
  H({ attribute: !1 })
], u.prototype, "hass", 2);
$([
  H({ attribute: !1 })
], u.prototype, "narrow", 2);
$([
  H({ attribute: !1 })
], u.prototype, "route", 2);
$([
  H({ attribute: !1 })
], u.prototype, "panel", 2);
$([
  f()
], u.prototype, "scenes", 2);
$([
  f()
], u.prototype, "selected", 2);
$([
  f()
], u.prototype, "query", 2);
$([
  f()
], u.prototype, "category", 2);
$([
  f()
], u.prototype, "favoritesOnly", 2);
$([
  f()
], u.prototype, "targets", 2);
$([
  f()
], u.prototype, "loading", 2);
$([
  f()
], u.prototype, "error", 2);
$([
  f()
], u.prototype, "pending", 2);
$([
  f()
], u.prototype, "confirm", 2);
$([
  f()
], u.prototype, "applying", 2);
$([
  f()
], u.prototype, "result", 2);
u = $([
  zt("smart-scene-studio-panel")
], u);
export {
  u as SmartSceneStudioPanel
};
