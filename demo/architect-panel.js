/** Compact architecture rail for the glass-box left column.
 * Mounts into #gb-rail when present; otherwise falls back to tabbed workbench.
 */
(function () {
  const cfg = window.ARCHITECT_CONFIG;
  if (!cfg) return;

  function el(tag, cls, html) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  }

  function normalize(data) {
    return {
      total_runs: data.total_runs ?? data.sample_size ?? data.total ?? 0,
      success_rate_pct: data.success_rate_pct ?? 100 - (data.failure_rate_pct || 0),
      p95_latency_ms: data.p95_latency_ms ?? data.p95_node_latency_ms ?? data.p95_ms ?? null,
      active_entities: data.active_entities ?? data.invited_users ?? 0,
      extra_cost: data.extra && data.extra.total_cost_usd,
    };
  }

  function renderRailMetrics(root, data) {
    root.innerHTML = "";
    const labels = cfg.metricLabels || {};
    const grid = el("div", "gb-metrics");
    [
      [labels.runs || "Runs", data.total_runs],
      ["Success", data.success_rate_pct + "%"],
      [labels.latency || "P95", data.p95_latency_ms != null ? data.p95_latency_ms + "ms" : "—"],
      [labels.entities || "Entities", data.active_entities],
    ].forEach(([label, value]) => {
      const card = el("div", "gb-metric");
      card.innerHTML = "<span>" + label + "</span><strong>" + value + "</strong>";
      grid.appendChild(card);
    });
    root.appendChild(grid);
    if (data.extra_cost != null) {
      root.appendChild(
        el("p", "muted", "Ledger total · $" + Number(data.extra_cost).toFixed(4))
      );
    }
  }

  function renderRailMetricsFailed(root, retry) {
    root.innerHTML = "";
    const wrap = el("div", "gb-metrics-failed");
    wrap.appendChild(el("p", "muted", "API waking (~30s)…"));
    const btn = el("button", "secondary", "Retry");
    btn.type = "button";
    btn.addEventListener("click", retry);
    wrap.appendChild(btn);
    root.appendChild(wrap);
  }

  function buildCompactRail() {
    const root = el("div", "gb-rail-inner");

    root.appendChild(el("h2", "gb-rail-title", "Stack"));
    const stack = el("div", "gb-stack");
    (cfg.layers || []).forEach((layer) => {
      const row = el("div", "gb-stack-layer");
      row.appendChild(el("div", "gb-stack-tier", layer.tier));
      row.appendChild(el("div", "gb-stack-name", layer.name));
      row.appendChild(el("div", "gb-stack-role", layer.role));
      stack.appendChild(row);
    });
    root.appendChild(stack);

    root.appendChild(el("h2", "gb-rail-title", "Live metrics"));
    const metricsSlot = el("div", "gb-metrics-slot");
    metricsSlot.appendChild(el("p", "muted", "Loading…"));
    root.appendChild(metricsSlot);

    function loadMetrics() {
      if (!cfg.metricsUrl) {
        metricsSlot.innerHTML = "";
        metricsSlot.appendChild(el("p", "muted", "No metrics URL."));
        return;
      }
      metricsSlot.innerHTML = "";
      metricsSlot.appendChild(el("p", "muted", "Loading…"));
      fetch(cfg.metricsUrl, { cache: "no-store" })
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
        .then((data) => renderRailMetrics(metricsSlot, normalize(data)))
        .catch(() => renderRailMetricsFailed(metricsSlot, loadMetrics));
    }
    loadMetrics();
    window.AgentFinopsRefreshMetrics = loadMetrics;

    root.appendChild(el("h2", "gb-rail-title", "Tradeoffs"));
    (cfg.tradeoffs || []).slice(0, 3).forEach((t) => {
      const card = el("div", "gb-tradeoff");
      card.innerHTML = "<strong>" + t.decision + "</strong><p>" + t.gain + "</p>";
      root.appendChild(card);
    });

    const links = [].concat(cfg.adrLinks || [], cfg.docsLinks || []).slice(0, 4);
    if (links.length) {
      root.appendChild(el("h2", "gb-rail-title", "ADRs & docs"));
      const ul = el("ul", "gb-adr-links");
      links.forEach((link) => {
        const li = document.createElement("li");
        const a = document.createElement("a");
        a.href = link.href;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        a.textContent = link.title + " →";
        li.appendChild(a);
        ul.appendChild(li);
      });
      root.appendChild(ul);
    }

    return root;
  }

  /* Legacy tabbed panel (fallback if #gb-rail missing) */
  function renderLayers(root) {
    const stack = el("div", "arch-layers");
    (cfg.layers || []).forEach((layer) => {
      const row = el("div", "arch-layer");
      row.appendChild(el("span", "arch-tier", layer.tier));
      const mid = el("div", "arch-mid");
      mid.appendChild(el("strong", "ao-layer-name", layer.name));
      mid.appendChild(el("span", "muted", layer.role));
      row.appendChild(mid);
      const chips = el("div", "arch-chips");
      (layer.components || []).forEach((c) => chips.appendChild(el("span", "arch-chip", c)));
      row.appendChild(chips);
      stack.appendChild(row);
    });
    root.appendChild(stack);
  }

  function renderTradeoffs(root) {
    const grid = el("div", "arch-tradeoffs");
    (cfg.tradeoffs || []).forEach((t) => {
      const card = el("div", "arch-tradeoff");
      card.innerHTML =
        '<strong class="ao-trade-title">' +
        t.decision +
        '</strong><p><span class="gain">Gain</span> — ' +
        t.gain +
        "</p><p><span class=\"trade\">Trade</span> — " +
        t.trade +
        "</p>";
      grid.appendChild(card);
    });
    root.appendChild(grid);
  }

  function renderDocLinks(root) {
    const links = [].concat(cfg.adrLinks || [], cfg.docsLinks || []);
    if (!links.length) return;
    const wrap = el("div", "");
    wrap.id = "ao-adrs";
    wrap.appendChild(el("h2", "ao-title", "Architecture record"));
    const ul = el("ul", "arch-doc-links");
    links.forEach((link) => {
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.href = link.href;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = link.title + " →";
      li.appendChild(a);
      ul.appendChild(li);
    });
    wrap.appendChild(ul);
    root.appendChild(wrap);
  }

  function renderMetrics(root, data) {
    root.innerHTML = "";
    const labels = cfg.metricLabels || {};
    const grid = el("div", "arch-metrics");
    [
      [labels.runs || "Runs", data.total_runs],
      ["Success rate", data.success_rate_pct + "%"],
      [labels.latency || "P95", data.p95_latency_ms != null ? data.p95_latency_ms + "ms" : "—"],
      [labels.entities || "Entities", data.active_entities],
    ].forEach(([label, value]) => {
      const card = el("div", "arch-metric");
      card.innerHTML = "<span>" + label + "</span><strong>" + value + "</strong>";
      grid.appendChild(card);
    });
    root.appendChild(grid);
  }

  function renderMetricsFailed(root, retry) {
    root.innerHTML = "";
    const wrap = el("div", "ao-metrics-failed");
    wrap.appendChild(el("p", "muted", "Metrics unavailable — API may be waking (~30s)."));
    const btn = el("button", "secondary", "Retry");
    btn.type = "button";
    btn.addEventListener("click", retry);
    wrap.appendChild(btn);
    root.appendChild(wrap);
  }

  function buildArchitecturePanel() {
    const panel = el("section", "panel architect-panel workbench-arch-panel");
    panel.hidden = true;
    const stack = el("div", "");
    stack.id = "ao-stack";
    stack.appendChild(el("h2", "ao-title", "How the system is wired"));
    stack.appendChild(el("p", "lede", cfg.tagline));
    renderLayers(stack);
    panel.appendChild(stack);
    const trade = el("div", "");
    trade.id = "ao-tradeoffs";
    trade.appendChild(el("h2", "ao-title", "Principal tradeoffs"));
    renderTradeoffs(trade);
    panel.appendChild(trade);
    renderDocLinks(panel);
    const metricsWrap = el("div", "");
    metricsWrap.id = "ao-metrics";
    metricsWrap.appendChild(el("h2", "ao-title", "Production metrics"));
    const metricsSlot = el("div", "arch-metrics-slot");
    metricsSlot.appendChild(el("p", "muted", "Loading live metrics…"));
    metricsWrap.appendChild(metricsSlot);
    panel.appendChild(metricsWrap);
    function loadMetrics() {
      if (!cfg.metricsUrl) return;
      fetch(cfg.metricsUrl, { cache: "no-store" })
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
        .then((data) => renderMetrics(metricsSlot, normalize(data)))
        .catch(() => renderMetricsFailed(metricsSlot, loadMetrics));
    }
    loadMetrics();
    return panel;
  }

  function mountTabsFallback() {
    const productRoot = document.getElementById("workbench-product");
    const main = document.querySelector("main.shell, main") || document.body;
    if (!main || !productRoot) return;
    const tabs = el("nav", "workbench-tabs");
    const btnProduct = el("button", "workbench-tab is-active", "");
    btnProduct.type = "button";
    btnProduct.innerHTML =
      '<span class="workbench-tab__label">Live product</span><span class="workbench-tab__hint">Run the demo</span>';
    const btnArch = el("button", "workbench-tab", "");
    btnArch.type = "button";
    btnArch.innerHTML =
      '<span class="workbench-tab__label">Architecture & metrics</span><span class="workbench-tab__hint">Stack, tradeoffs, SLOs</span>';
    tabs.appendChild(btnProduct);
    tabs.appendChild(btnArch);
    const archPanel = buildArchitecturePanel();
    main.insertBefore(tabs, main.firstChild);
    main.appendChild(archPanel);
    function show(tab) {
      const isProduct = tab === "product";
      productRoot.hidden = !isProduct;
      archPanel.hidden = isProduct;
      btnProduct.classList.toggle("is-active", isProduct);
      btnArch.classList.toggle("is-active", !isProduct);
    }
    btnProduct.addEventListener("click", () => show("product"));
    btnArch.addEventListener("click", () => show("architecture"));
    show("product");
  }

  function mount() {
    const rail = document.getElementById("gb-rail");
    if (rail) {
      rail.innerHTML = "";
      rail.appendChild(buildCompactRail());
      return;
    }
    mountTabsFallback();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
})();
