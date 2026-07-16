/**
 * Agent FinOps glass-box center column — honest metering step replay.
 *
 * Phases are built only from real API responses the product script already
 * received (budget_usd, cost_usd, total_cost_usd, breached). No invented
 * latency or cost figures.
 */
(function () {
  const PHASE_META = [
    { id: "budget_set", label: "Set budget", detail: "PUT /v1/budget" },
    { id: "usage_price", label: "Price tokens", detail: "canonical table" },
    { id: "usage_record", label: "Record usage", detail: "POST /v1/usage" },
    { id: "budget_compare", label: "Compare budget", detail: "total vs cap" },
    { id: "breach_signal", label: "Breach signal", detail: "halt dispatch" },
  ];

  const els = {
    pipeline: () => document.getElementById("gbPipeline"),
    gate: () => document.getElementById("gbGate"),
    log: () => document.getElementById("gbEventLog"),
    ops: () => document.getElementById("gbOpsStrip"),
    badge: () => document.getElementById("gbSourceBadge"),
    bars: () => document.getElementById("gbCostBars"),
  };

  let timer = null;
  let activeId = null;
  let done = new Set();

  function setBadge(source) {
    const b = els.badge();
    if (!b) return;
    b.className = "gb-source-badge";
    if (source === "live") {
      b.classList.add("live");
      b.textContent = "live API";
    } else if (source === "fallback") {
      b.classList.add("fallback");
      b.textContent = "demo_fallback";
    } else {
      b.textContent = "awaiting run";
    }
  }

  function setGate(text) {
    const g = els.gate();
    if (g) g.textContent = text;
  }

  function clearLog() {
    const log = els.log();
    if (log) log.innerHTML = "";
  }

  function appendLog(line) {
    const log = els.log();
    if (!log) return;
    if (log.querySelector(".muted")) log.innerHTML = "";
    const row = document.createElement("div");
    row.className = "ev-live";
    row.textContent = line;
    log.appendChild(row);
    log.scrollTop = log.scrollHeight;
  }

  function setOps({ steps, total, budget, breached }) {
    const ops = els.ops();
    if (!ops) return;
    ops.innerHTML =
      "<span><strong>steps</strong> " +
      (steps ?? "—") +
      "</span><span><strong>total</strong> " +
      (total ?? "n/a") +
      "</span><span><strong>budget</strong> " +
      (budget ?? "n/a") +
      "</span><span><strong>breached</strong> " +
      (breached == null ? "—" : breached ? "yes" : "no") +
      "</span>";
  }

  function renderCostBars(total, budget) {
    const root = els.bars();
    if (!root) return;
    if (total == null && budget == null) {
      root.hidden = true;
      root.innerHTML = "";
      return;
    }
    root.hidden = false;
    const t = Number(total || 0);
    const b = Number(budget || 0);
    const max = Math.max(t, b, 0.0001);
    const over = b > 0 && t > b;
    root.innerHTML =
      '<div class="gb-wf-row"><span class="gb-wf-label">Spend</span>' +
      '<div class="gb-wf-track"><div class="gb-wf-bar filled' +
      (over ? " over" : "") +
      '" style="width:' +
      Math.min(100, (t / max) * 100) +
      '%"></div>' +
      (b > 0
        ? '<div class="gb-wf-budget" style="left:' + Math.min(100, (b / max) * 100) + '%" title="budget"></div>'
        : "") +
      '</div><span class="gb-wf-ms' +
      (over ? " over" : "") +
      '">$' +
      t.toFixed(4) +
      "</span></div>" +
      (b > 0
        ? '<div class="gb-wf-row"><span class="gb-wf-label">Budget</span>' +
          '<div class="gb-wf-track"><div class="gb-wf-bar filled budget" style="width:' +
          Math.min(100, (b / max) * 100) +
          '%"></div></div>' +
          '<span class="gb-wf-ms">$' +
          b.toFixed(4) +
          "</span></div>"
        : "");
  }

  function renderNodes(activePhases) {
    const root = els.pipeline();
    if (!root) return;
    const activeSet = new Set((activePhases || []).map((p) => p.id));
    root.innerHTML = PHASE_META.map((p, i) => {
      const used = activeSet.has(p.id);
      const cls =
        activeId === p.id ? " gb-active" : done.has(p.id) ? " gb-done" : used ? "" : " gb-skipped";
      const step = (activePhases || []).find((s) => s.id === p.id);
      const note = step && step.note ? "<em>" + step.note + "</em>" : "<em>—</em>";
      return (
        '<div class="gb-agent-node' +
        cls +
        '" data-phase-id="' +
        p.id +
        '">' +
        '<span class="gb-agent-idx">' +
        String(i + 1).padStart(2, "0") +
        "</span>" +
        "<div><strong>" +
        p.label +
        "</strong><small>" +
        p.detail +
        "</small></div>" +
        note +
        "</div>"
      );
    }).join('<span class="gb-agent-arrow" aria-hidden="true">→</span>');
  }

  function highlight(id) {
    activeId = id;
    document.querySelectorAll(".gb-agent-node").forEach((n) => {
      const pid = n.getAttribute("data-phase-id");
      n.classList.toggle("gb-active", pid === activeId);
      n.classList.toggle("gb-done", done.has(pid) && pid !== activeId);
    });
  }

  function clearTimer() {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
  }

  function replay(steps, meta) {
    clearTimer();
    done = new Set();
    activeId = null;
    clearLog();
    const phases = steps || [];
    renderNodes(phases);
    setBadge(meta.source || "live");
    setOps({
      steps: phases.length,
      total: meta.total,
      budget: meta.budget,
      breached: meta.breached,
    });
    renderCostBars(meta.totalUsd, meta.budgetUsd);

    if (!phases.length) {
      setGate("No metering steps to replay.");
      return;
    }

    let i = 0;
    let prev = null;
    const tick = () => {
      if (i >= phases.length) {
        if (prev) done.add(prev);
        activeId = null;
        highlight(null);
        setGate(
          meta.breached
            ? "Budget breached — callers must halt further paid dispatch."
            : "Metering complete — spend still within budget."
        );
        if (typeof window.AgentFinopsRefreshMetrics === "function") {
          window.AgentFinopsRefreshMetrics();
        }
        return;
      }
      const p = phases[i];
      if (prev) done.add(prev);
      highlight(p.id);
      prev = p.id;
      setGate(p.label + " — " + (p.message || p.note || ""));
      appendLog("▸ " + p.id + (p.note ? " · " + p.note : "") + (p.message ? " — " + p.message : ""));
      i += 1;
      timer = setTimeout(tick, 380);
    };
    tick();
  }

  /** Build honest steps from a single usage response. */
  function stepsFromUsage(data) {
    const steps = [];
    const cost = data.cost_usd != null ? Number(data.cost_usd) : null;
    const total = data.total_cost_usd != null ? Number(data.total_cost_usd) : null;
    const budget = data.budget_usd != null ? Number(data.budget_usd) : null;
    if (cost != null) {
      steps.push({
        id: "usage_price",
        label: "Price tokens",
        note: "$" + cost.toFixed(4),
        message: "Canonical pricing table → cost_usd",
      });
    }
    steps.push({
      id: "usage_record",
      label: "Record usage",
      note: total != null ? "$" + total.toFixed(4) + " total" : "recorded",
      message: "Ledger updated for " + (data.scope_value || "scope"),
    });
    if (budget != null && total != null) {
      steps.push({
        id: "budget_compare",
        label: "Compare budget",
        note: "$" + total.toFixed(4) + " / $" + budget.toFixed(4),
        message: "Running total vs scope budget",
      });
    }
    if (data.breached) {
      steps.push({
        id: "breach_signal",
        label: "Breach signal",
        note: "breached=true",
        message: "Caller must halt paid dispatch",
      });
    }
    return steps;
  }

  window.GlassBox = {
    reset() {
      clearTimer();
      done = new Set();
      activeId = null;
      const root = els.pipeline();
      if (root) {
        root.innerHTML = PHASE_META.map((p, i) => {
          return (
            '<div class="gb-agent-node" data-phase-id="' +
            p.id +
            '">' +
            '<span class="gb-agent-idx">' +
            String(i + 1).padStart(2, "0") +
            "</span>" +
            "<div><strong>" +
            p.label +
            "</strong><small>" +
            p.detail +
            "</small></div><em>—</em></div>"
          );
        }).join('<span class="gb-agent-arrow" aria-hidden="true">→</span>');
      }
      clearLog();
      const log = els.log();
      if (log) {
        log.innerHTML =
          '<div class="muted" style="font-style: italic">No steps yet — run a metering action to replay the pipeline.</div>';
      }
      setBadge("idle");
      setGate(
        "Trigger a budget breach (or record usage) — center replay uses only fields returned by the API (cost_usd, total_cost_usd, budget_usd, breached)."
      );
      setOps({});
      renderCostBars(null, null);
    },

    /** Replay a caller-built sequence of honest steps from live API responses. */
    replaySteps(steps, meta) {
      replay(steps || [], {
        source: "live",
        total: meta && meta.totalUsd != null ? "$" + Number(meta.totalUsd).toFixed(4) : "n/a",
        budget: meta && meta.budgetUsd != null ? "$" + Number(meta.budgetUsd).toFixed(4) : "n/a",
        breached: meta ? !!meta.breached : null,
        totalUsd: meta && meta.totalUsd,
        budgetUsd: meta && meta.budgetUsd,
      });
    },

    onUsageResult(data) {
      const steps = stepsFromUsage(data || {});
      this.replaySteps(steps, {
        totalUsd: data.total_cost_usd,
        budgetUsd: data.budget_usd,
        breached: data.breached,
      });
    },

    onBudgetSet(data) {
      this.replaySteps(
        [
          {
            id: "budget_set",
            label: "Set budget",
            note: data.budget_usd != null ? "$" + Number(data.budget_usd).toFixed(4) : "set",
            message: "Budget configured for " + (data.scope_value || "scope"),
          },
        ],
        { budgetUsd: data.budget_usd, totalUsd: null, breached: false }
      );
    },

    onBudgetCheck(data) {
      const steps = [
        {
          id: "budget_compare",
          label: "Compare budget",
          note:
            data.total_cost_usd != null && data.budget_usd != null
              ? "$" + Number(data.total_cost_usd).toFixed(4) + " / $" + Number(data.budget_usd).toFixed(4)
              : "checked",
          message: data.breached ? "Already over budget" : "Within budget",
        },
      ];
      if (data.breached) {
        steps.push({
          id: "breach_signal",
          label: "Breach signal",
          note: "breached=true",
          message: "Caller must halt paid dispatch",
        });
      }
      this.replaySteps(steps, {
        totalUsd: data.total_cost_usd,
        budgetUsd: data.budget_usd,
        breached: data.breached,
      });
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => window.GlassBox.reset());
  } else {
    window.GlassBox.reset();
  }
})();
