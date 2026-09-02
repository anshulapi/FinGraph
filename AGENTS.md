# FinGraph Repository Guidance

## Product scope

FinGraph is the Razorpay AI Buildathon Track 1 project (AI Growth & Agentic Commerce). The product specification in `docs/fingraph-mvp-plan.md` is the source of truth for product scope and requirements.

ReelGraph is FinGraph's architectural inspiration: FinGraph applies the same graph-orchestration substrate to merchant growth. The buildathon MVP is one real, end-to-end vertical slice, not the complete long-term AI OS for commerce.

Do not implement roadmap features unless they are explicitly requested.

## Required MVP flow

The implemented flow must preserve this order:

```text
Merchant Goal
  → Data Agent
  → Opportunity Agent
  → Strategy Agent
  → Policy/Risk Gate
  → Human Approval
  → Execution Agent
  → Razorpay Test API
  → Outcome + Audit Log
```

Real Razorpay **TEST MODE** APIs are mandatory for the MVP. Do not substitute preloaded data, mocked end-to-end integrations, or live-mode Razorpay APIs for the required real test-mode calls.

## Financial safety and execution

- Financial actions must be explainable, bounded, and gated.
- The policy/risk gate must be deterministic and capable of blocking an action. It must enforce at least one hard rule, such as an action allowlist or spend cap.
- Human approval must occur after the policy/risk gate and before any execution.
- Execution may occur only after a policy pass and explicit human approval.
- Capture outcomes and an audit log for every meaningful step, including inputs, decisions, reasoning, timestamps, and Razorpay test API responses.

## Security

- Never commit, print, log, expose, or otherwise disclose credentials, API keys, tokens, or secrets.
- Keep secrets in local environment configuration that is excluded from version control.

## Engineering practice

- Work milestone-by-milestone; do not skip ahead to polish or roadmap work.
- Every meaningful implementation requires tests appropriate to the change.
- Current milestone: **Razorpay Test Mode connectivity only**. Do not build application functionality beyond establishing and validating this connectivity unless explicitly requested.
