# ADR-0002: PaaS (Render) vs. Real IaC (Terraform + Cloud Run/Cloud SQL)

## Status

Accepted — 2026-07-05

## Context

Every repo in this org deploys to Render/Vercel PaaS ([ADR-005 in ai-architecture-portfolio](https://github.com/vpeetla-ai/ai-architecture-portfolio/blob/main/adr/ADR-005-reference-stack-free-tier.md)),
which is the right default for iteration speed and near-zero ops overhead — but it left the
whole org with zero evidence of real cloud infrastructure ownership (VPC design, container
orchestration, IAM, managed database provisioning), despite that being core Principal AI
Architect / MLOps territory. Phase C of the top-1% AI Architect program closes that gap with
genuinely operated infra, not just Terraform-on-paper.

## Decision

Added `deploy/terraform/gcp/`: Cloud Run (scale-to-zero) + Cloud SQL (Postgres, `db-f1-micro`,
no HA) + Artifact Registry + Secret Manager + a least-privilege runtime service account — a
real, alternative deploy path to `render.yaml`, not a replacement for it.

**When Render/Vercel PaaS is the right call:** fast iteration on a portfolio-stage service, no
dedicated ops capacity, traffic low enough that PaaS free/starter tiers cover it, and the team
doesn't need direct control over networking or IAM boundaries. This describes every repo in
this org today, including this one in its normal operating mode.

**When Terraform + Cloud Run/Cloud SQL earns its complexity:** when you need direct control
over IAM (least-privilege service accounts scoped per resource, not a shared platform
identity), network boundaries (VPC peering, private connectivity to other cloud resources), or
provider-specific managed services PaaS doesn't expose (Secret Manager rotation, Cloud SQL
IAM auth, VPC Service Controls). None of that was needed here — this was built specifically to
gain and demonstrate that operational capability, not because agent-finops's traffic or ops
needs outgrew Render.

## Consequences

### Positive
- Real, verified deploy: `terraform apply` created 19 real GCP resources, the live service
  correctly recorded usage and detected a budget breach against a real Cloud SQL-backed ledger,
  and `terraform destroy` cleanly removed all 19 — a genuine stand-up/verify/tear-down cycle,
  not a one-way demo.
- Found and fixed two real bugs only real deployment could surface: the Dockerfile didn't
  respect Cloud Run's injected `PORT` env var (now `${PORT:-8000}`), and the API key secret
  defaulted to the guessable placeholder string `"unset"` for a service whose Cloud Run IAM
  invoker is `allUsers` — now a real generated `random_password`.
- Documents a genuine engineering trade-off (when to reach for IaC vs. PaaS) rather than
  reflexively treating "more infrastructure" as inherently better.

### Negative
- Real, if temporary, cloud spend: Cloud SQL's `db-f1-micro` tier costs roughly $7–10/month
  while running. Mitigated by the stand-up/verify/tear-down operating model — this is not left
  running as a second production deployment of agent-finops.
- Cloud Run doesn't automatically roll a new revision when a referenced Secret Manager
  "latest" version changes underneath an otherwise-unchanged service spec — required an
  explicit `terraform apply -replace` to pick up the rotated API key. A real operational
  gotcha, not a design flaw in this Terraform, but worth remembering for any future secret
  rotation against this same stack.

## References
- `deploy/terraform/gcp/` (main.tf, variables.tf, outputs.tf, README.md)
- `render.yaml` (the PaaS path this doesn't replace)
- [ai-architecture-portfolio ADR-015](https://github.com/vpeetla-ai/ai-architecture-portfolio/blob/main/adr/ADR-015-real-aws-gcp-infra-phase-c.md)
