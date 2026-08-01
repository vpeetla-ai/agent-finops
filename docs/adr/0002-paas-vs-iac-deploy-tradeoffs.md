# ADR-0002: PaaS (Render) vs. Real IaC (Terraform + Cloud Run/Cloud SQL)

## Status

Accepted — 2026-07-05

## In one breath (panel)

I'd keep Render for day-to-day and prove Cloud Run + Cloud SQL with apply → real breach against a real ledger → destroy — IaC for IAM/network control, not as a second always-on prod.

## Context

Org default is Render/Vercel ([portfolio ADR-005](https://github.com/vpeetla-ai/ai-architecture-portfolio/blob/main/adr/ADR-005-reference-stack-free-tier.md)). Right for speed; left zero *operated* GCP evidence (IAM, managed DB, Artifact Registry, Secret Manager).

What I refused: claiming free-tier Render meets enterprise availability SLOs, or leaving Terraform as paper-only.

## Decision

Added `deploy/terraform/gcp/`: Cloud Run (scale-to-zero) + Cloud SQL (`db-f1-micro`, no HA) + Artifact Registry + Secret Manager + least-privilege runtime SA. Alternative to `render.yaml`, not a replacement.

**PaaS wins** for portfolio-stage traffic and iteration. **Terraform earns it** when you need scoped IAM, private connectivity, or provider controls PaaS hides. Built to demonstrate that capability — traffic did not force the move.

## Consequences

### Positive

- Verified: 19 GCP resources, real usage + budget breach on Cloud SQL-backed ledger, clean destroy
- Deploy-only bugs fixed: `PORT` binding for Cloud Run; API key no longer default `"unset"` on `allUsers` invoker
- Trade-off documented — more infra ≠ automatically better

### Negative

- Temporary Cloud SQL spend (~$7–10/mo while up) — stand-up/verify/tear-down, not a second permanent prod
- Secret "latest" rotation doesn't auto-roll Cloud Run — needed explicit replace; operational gotcha, not a design flex

## References

- `deploy/terraform/gcp/`
- `render.yaml`
- [ai-architecture-portfolio ADR-015](https://github.com/vpeetla-ai/ai-architecture-portfolio/blob/main/adr/ADR-015-real-aws-gcp-infra-phase-c.md)
