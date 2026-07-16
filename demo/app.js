/* Product panel logic — meters usage and drives GlassBox from real API JSON only. */
(function () {
  const $ = (id) => document.getElementById(id);
  const apiDefault = window.AGENT_FINOPS_API || "https://agent-finops-api.onrender.com";
  $("apiBase").value = apiDefault;
  $("apiUrl").textContent = apiDefault;

  function headers() {
    const h = { "Content-Type": "application/json" };
    const key = $("apiKey").value.trim();
    if (key) h["X-API-Key"] = key;
    return h;
  }

  function apiBase() {
    return $("apiBase").value.replace(/\/$/, "");
  }

  function renderOps(data) {
    const extra = data.extra || {};
    const cards = [
      ["Usage events", data.total_runs ?? "—"],
      ["Total cost (USD)", extra.total_cost_usd != null ? "$" + Number(extra.total_cost_usd).toFixed(4) : "—"],
      ["Budgets configured", data.active_entities ?? "—"],
      ["Success rate", (data.success_rate_pct ?? "—") + (data.success_rate_pct != null ? "%" : "")],
    ];
    $("opsCards").innerHTML = cards
      .map(
        ([label, value]) =>
          `<div class="gb-ops-card"><p class="muted">${label}</p><p class="gb-ops-value">${value}</p></div>`
      )
      .join("");
  }

  async function loadOps() {
    try {
      const res = await fetch(apiBase() + "/v1/ops/metrics", { cache: "no-store" });
      if (res.ok) renderOps(await res.json());
    } catch (_) {
      $("opsCards").innerHTML = '<p class="muted">API waking from idle — retry in a moment.</p>';
    }
  }

  $("record").addEventListener("click", async () => {
    const body = {
      scope_type: "agent",
      scope_value: $("scopeValue").value,
      provider: "openai",
      model: "gpt-4o-mini",
      prompt_tokens: Number($("promptTokens").value),
      completion_tokens: Number($("completionTokens").value),
    };
    try {
      const res = await fetch(`${apiBase()}/v1/usage`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      $("output").innerHTML = data.breached
        ? `<span style="color:#dc2626;font-weight:600">BUDGET BREACHED</span>\n${JSON.stringify(data, null, 2)}`
        : JSON.stringify(data, null, 2);
      if (window.GlassBox) window.GlassBox.onUsageResult(data);
      loadOps();
    } catch (err) {
      $("output").textContent = "Error: " + err.message;
    }
  });

  $("setBudget").addEventListener("click", async () => {
    const scope = $("scopeValue").value;
    try {
      const res = await fetch(`${apiBase()}/v1/budget/agent/${encodeURIComponent(scope)}`, {
        method: "PUT",
        headers: headers(),
        body: JSON.stringify({ budget_usd: 1.0 }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      $("output").textContent = JSON.stringify(data, null, 2);
      if (window.GlassBox) window.GlassBox.onBudgetSet(data);
      loadOps();
    } catch (err) {
      $("output").textContent = "Error: " + err.message;
    }
  });

  $("checkBudget").addEventListener("click", async () => {
    const scope = $("scopeValue").value;
    try {
      const res = await fetch(`${apiBase()}/v1/budget/agent/${encodeURIComponent(scope)}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      $("output").textContent = JSON.stringify(data, null, 2);
      if (window.GlassBox) window.GlassBox.onBudgetCheck(data);
    } catch (err) {
      $("output").textContent = "Error: " + err.message;
    }
  });

  $("triggerBreach").addEventListener("click", async () => {
    const scope = $("scopeValue").value || "demo-agent";
    const log = [];
    const steps = [];
    let last = null;
    try {
      $("output").textContent = "Setting $0.01 budget…";
      let res = await fetch(`${apiBase()}/v1/budget/agent/${encodeURIComponent(scope)}`, {
        method: "PUT",
        headers: headers(),
        body: JSON.stringify({ budget_usd: 0.01 }),
      });
      let data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      log.push("Budget set to $0.01");
      steps.push({
        id: "budget_set",
        label: "Set budget",
        note: "$0.0100",
        message: "Tiny budget for breach demo",
      });

      for (let i = 1; i <= 8; i++) {
        res = await fetch(`${apiBase()}/v1/usage`, {
          method: "POST",
          headers: headers(),
          body: JSON.stringify({
            scope_type: "agent",
            scope_value: scope,
            provider: "openai",
            model: "gpt-4o-mini",
            prompt_tokens: 4000,
            completion_tokens: 1000,
          }),
        });
        data = await res.json();
        if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
        last = data;
        log.push(`Usage #${i}: $${Number(data.total_cost_usd || 0).toFixed(4)} breached=${!!data.breached}`);

        if (i === 1 && data.cost_usd != null) {
          steps.push({
            id: "usage_price",
            label: "Price tokens",
            note: "$" + Number(data.cost_usd).toFixed(4),
            message: "Canonical pricing table",
          });
        }
        steps.push({
          id: "usage_record",
          label: "Record usage",
          note: "#" + i + " · $" + Number(data.total_cost_usd || 0).toFixed(4),
          message: "Ledger event " + i,
        });

        if (data.breached) {
          steps.push({
            id: "budget_compare",
            label: "Compare budget",
            note:
              "$" +
              Number(data.total_cost_usd || 0).toFixed(4) +
              " / $" +
              Number(data.budget_usd || 0.01).toFixed(4),
            message: "Total exceeded scope budget",
          });
          steps.push({
            id: "breach_signal",
            label: "Breach signal",
            note: "breached=true",
            message: "Caller must halt paid dispatch",
          });
          // Deduplicate repeated usage_record ids for highlight — keep sequence as-is for log honesty
          // but GlassBox highlight uses id; collapse duplicates for node state by replaying unique final path
          const replay = [
            steps[0],
            steps.find((s) => s.id === "usage_price"),
            {
              id: "usage_record",
              label: "Record usage",
              note: i + " events · $" + Number(data.total_cost_usd || 0).toFixed(4),
              message: "Accumulated until breach",
            },
            steps[steps.length - 2],
            steps[steps.length - 1],
          ].filter(Boolean);

          $("output").innerHTML =
            `<span style="color:#dc2626;font-weight:600">BUDGET BREACHED</span>\n` +
            log.join("\n") +
            "\n\n" +
            JSON.stringify(data, null, 2);
          if (window.GlassBox) {
            window.GlassBox.replaySteps(replay, {
              totalUsd: data.total_cost_usd,
              budgetUsd: data.budget_usd,
              breached: true,
            });
          }
          loadOps();
          return;
        }
      }
      $("output").textContent = log.join("\n") + "\n\nNo breach yet — raise token counts and retry.";
      if (window.GlassBox && last) window.GlassBox.onUsageResult(last);
      loadOps();
    } catch (err) {
      $("output").textContent = "Error: " + err.message;
    }
  });

  loadOps();
})();
