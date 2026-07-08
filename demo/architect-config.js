window.AGENT_FINOPS_API = window.AGENT_FINOPS_API || "https://agent-finops.onrender.com";
window.ARCHITECT_CONFIG = {
  tagline:
    "Agent FinOps metering: record token usage, enforce budgets per agent/tenant, and halt dispatch on breach — cost governance as a first-class layer.",
  metricsUrl: window.AGENT_FINOPS_API + "/v1/ops/metrics",
  metricsPath: "/v1/ops/metrics",
  metricLabels: { runs: "Usage events", entities: "Budgets configured", latency: "P95 latency" },
  layers: [
    { tier: "L1", name: "Metering API", role: "Usage + budget", components: ["POST /v1/usage", "Budget CRUD", "Breach flag"] },
    { tier: "L2", name: "Store", role: "Ledger", components: ["SQLite dev", "Postgres prod", "Per-scope totals"] },
    { tier: "L3", name: "Integration", role: "Fleet hook", components: ["VAP dispatch gate", "AegisAI finops panel", "Cloud snapshot script"] },
    { tier: "L4", name: "Ops", role: "SLO + security", components: ["/v1/ops/metrics", "Security scan CI", "SLO.md"] },
  ],
  tradeoffs: [
    { decision: "Per-agent budgets vs org-wide cap", gain: "Blast-radius isolation for runaway agents", trade: "More budget rows to manage" },
    { decision: "Estimate cost from list pricing", gain: "Works without provider billing API", trade: "Approximate vs invoice-true" },
    { decision: "API key on mutating routes", gain: "Prevents usage spam", trade: "Demo needs key in prod" },
    { decision: "SQLite default for portfolio", gain: "Zero DB setup", trade: "Metrics reset on ephemeral disk" },
  ],
};
