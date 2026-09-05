# FinGraph

### Bounded Agentic Growth Infrastructure for Razorpay

FinGraph is an agentic commerce system designed to help merchants discover growth opportunities from their payment data and safely turn those opportunities into bounded, explainable actions.

The core principle is simple:

> **AI should be able to propose growth actions, but it should never be allowed to move money without evidence, policy controls, and explicit approval.**

FinGraph currently demonstrates this principle end-to-end using **Razorpay Test Mode APIs**.

---

## The Problem

AI agents can identify opportunities faster than traditional merchant dashboards, but giving an AI agent direct access to payment infrastructure creates a fundamental problem:

**What happens when an agent makes the wrong decision?**

A production-grade agentic commerce system needs more than an LLM.

It needs:

* real payment data
* opportunity detection
* bounded actions
* deterministic risk controls
* explainability
* human approval
* safe execution
* failure handling
* auditability

FinGraph is built around this control loop.

---

# What FinGraph Does Today

The current MVP implements a complete vertical slice:

```text
Razorpay Test Mode
       │
       ▼
   Order Data
       │
       ▼
Opportunity Detection
       │
       ▼
Strategy Generation
       │
       ▼
 Policy / Risk Gate
       │
       ├──────────────► BLOCK
       │
       ▼
 Human Approval
       │
       ├──────────────► REJECT
       │
       ▼
Bounded Execution
       │
       ▼
Razorpay Payment Link
       │
       ▼
Execution Result
       │
       ▼
Persistent Audit Trail
```

The system currently focuses on one concrete growth action:

> **Detect an unusually high-value order and propose a bounded Razorpay Payment Link action.**

The action is never executed directly by the strategy layer.

---

# Why This Architecture Matters

FinGraph separates **reasoning from authority**.

The system can reason:

> "This order is significantly above the merchant's normal order-value baseline."

But reasoning alone does not grant execution authority.

The proposed action must pass through:

```text
Opportunity
    ↓
Strategy
    ↓
Policy
    ↓
Human Approval
    ↓
Execution
```

This creates a safety boundary between an intelligent recommendation and a real financial action.

---

# Current MVP

## 1. Real Razorpay Data

FinGraph connects to Razorpay using Test Mode credentials and retrieves real order data.

The system normalizes provider responses into internal typed models rather than allowing provider-specific JSON to leak through the entire application.

---

## 2. Deterministic Opportunity Detection

The current MVP detects high-value order opportunities using a same-currency median baseline.

For each currency:

```text
baseline = median(order amounts)
```

An order becomes an opportunity when it is sufficiently above that baseline.

The current signal is intentionally conservative.

FinGraph does **not** pretend that order-level data provides customer-level or product-level intelligence.

That limitation is explicitly represented in the strategy confidence model.

---

## 3. Bounded Strategy Generation

An opportunity produces a typed strategy.

The current executable action is:

```text
create_payment_link
```

The strategy contains:

* action type
* amount
* currency
* reference ID
* description
* reasoning
* expected outcome
* confidence
* confidence rationale

The strategy layer proposes an action.

**It does not execute it.**

---

## 4. Deterministic Policy / Risk Gate

Every proposed action passes through a deterministic policy layer.

The current policy verifies:

* action type is allowlisted
* amount matches the observed opportunity
* currency matches the opportunity
* reference ID matches the source order
* description is valid
* amount is positive
* opportunity uplift remains below the configured risk ceiling

A policy decision is either:

```text
ALLOW
```

or:

```text
BLOCK
```

A blocked strategy cannot proceed to human approval or execution.

### Real blocking behavior

The MVP has been tested with an extreme high-value order that exceeded the configured uplift threshold.

FinGraph returned:

```text
BLOCK
maximum_uplift_ratio_exceeded
```

This is an actual policy decision, not a UI-only warning.

---

# 5. Human Approval Gate

An `ALLOW` decision still does not execute automatically.

A human must explicitly choose:

```text
APPROVE
```

or:

```text
REJECT
```

A `BLOCK` decision cannot enter the approval stage.

This creates a deliberate authority boundary:

```text
AI proposes
     ↓
Policy constrains
     ↓
Human authorizes
     ↓
System executes
```

---

# 6. Real Razorpay Test Mode Execution

After approval, FinGraph executes the bounded action against Razorpay Test Mode.

The current action creates a Standard Payment Link through Razorpay's Payment Links API.

Razorpay's API accepts the payment amount in the smallest currency unit and requires a unique `reference_id`; the API returns the created Payment Link ID and hosted short URL.

FinGraph captures and normalizes:

* execution status
* action
* provider ID
* provider URL
* provider status
* error information
* execution timestamp

The current MVP has successfully executed this complete path against Razorpay Test Mode.

**No live money is moved by the demo.**

Razorpay Test Mode is designed for simulated payment testing rather than real-money transactions.

---

# 7. Failure Handling

The system explicitly handles failures instead of assuming every agent action succeeds.

Examples include:

```text
Invalid / missing configuration
        ↓
503

Razorpay authentication failure
        ↓
502

Razorpay API failure
        ↓
502

Provider/network failure during execution
        ↓
FAILED execution result
```

This allows the agentic pipeline to fail safely instead of silently claiming that an action succeeded.

---

# 8. Persistent Audit Trail

FinGraph stores important pipeline events in SQLite.

The audit trail records information such as:

* timestamp
* pipeline stage
* event type
* inputs
* decision
* reasoning
* outputs

The current system exposes the audit trail through:

```text
GET /api/audit-log
```

The goal is to make every consequential action explainable after the fact.

---

# Architecture

```text
                    ┌──────────────────────┐
                    │   Razorpay Test API  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    Data Layer        │
                    │ Orders + Normalizer  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Opportunity Detector │
                    │   Deterministic      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Strategy Generator   │
                    │ Bounded Action       │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Policy / Risk Gate   │
                    │  ALLOW / BLOCK       │
                    └───────┬───────┬──────┘
                            │       │
                         BLOCK     ALLOW
                            │       │
                            │       ▼
                            │  ┌───────────────┐
                            │  │ Human Approval│
                            │  │ APPROVE/REJECT│
                            │  └───────┬───────┘
                            │          │
                            │          ▼
                            │  ┌───────────────┐
                            │  │   Execution   │
                            │  └───────┬───────┘
                            │          │
                            │          ▼
                            │  ┌───────────────┐
                            │  │ Razorpay API  │
                            │  └───────────────┘
                            │
                            └───────────────┐
                                            ▼
                                   ┌────────────────┐
                                   │  Audit Trail   │
                                   └────────────────┘
```

---

# Repository Structure

```text
fingraph/
│
├── app/
│   ├── approvals.py       # Human approval domain logic
│   ├── audit.py           # Persistent SQLite audit trail
│   ├── config.py          # Environment/configuration
│   ├── execution.py       # Approved action execution
│   ├── main.py            # FastAPI application and API routes
│   ├── models.py          # Pydantic domain models
│   ├── opportunities.py   # Opportunity detection
│   ├── policy.py          # Deterministic policy/risk gate
│   ├── razorpay.py        # Razorpay API client
│   └── strategies.py      # Strategy generation
│
├── tests/
│   ├── test_api.py
│   ├── test_approvals.py
│   ├── test_audit.py
│   ├── test_config.py
│   ├── test_execution.py
│   ├── test_opportunities.py
│   ├── test_policy.py
│   ├── test_razorpay.py
│   └── test_strategies.py
│
├── docs/
│   └── fingraph-mvp-plan.md
│
├── .env.example
├── .gitignore
├── AGENTS.md
├── pyproject.toml
└── README.md
```

---

# Running FinGraph

## Requirements

* Python 3.9+
* Razorpay Test Mode API credentials
* Git

## 1. Clone

```bash
git clone <YOUR_REPOSITORY_URL>
cd fingraph
```

## 2. Create virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -e ".[dev]"
```

## 4. Configure Razorpay Test Mode

Create `.env`:

```env
RAZORPAY_KEY_ID=your_test_key_id
RAZORPAY_KEY_SECRET=your_test_key_secret
```

**Never commit `.env`.**

Only use Razorpay Test Mode credentials for the demo.

---

# Run Tests

```bash
python -m pytest
```

Current MVP test suite:

```text
68 passed
```

The tests cover:

* Razorpay client behavior
* configuration
* opportunity detection
* strategy generation
* policy decisions
* human approval
* execution
* API behavior
* audit persistence
* provider failure handling

---

# Start the API

```bash
set -a
source .env
set +a

python -m uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

FastAPI documentation:

```text
http://127.0.0.1:8000/docs
```

---

# Core API Endpoints

| Endpoint                    | Purpose                             |
| --------------------------- | ----------------------------------- |
| `GET /api/razorpay/orders`  | Retrieve normalized Razorpay orders |
| `GET /api/opportunities`    | Detect growth opportunities         |
| `GET /api/strategies`       | Generate bounded action strategies  |
| `GET /api/policy-decisions` | Evaluate strategies against policy  |
| `POST /api/approvals`       | Approve or reject an allowed action |
| `POST /api/executions`      | Execute an approved action          |
| `GET /api/audit-log`        | Inspect persistent audit events     |

---

# Example End-to-End Flow

### 1. Discover orders

```http
GET /api/razorpay/orders
```

### 2. Detect opportunity

```http
GET /api/opportunities
```

### 3. Generate strategy

```http
GET /api/strategies
```

### 4. Evaluate policy

```http
GET /api/policy-decisions
```

Possible result:

```json
{
  "decision": "ALLOW"
}
```

or:

```json
{
  "decision": "BLOCK"
}
```

### 5. Human approval

```http
POST /api/approvals
```

with:

```json
{
  "action": "APPROVE",
  "approver": "demo-reviewer",
  "reason": "Reviewed and approved the bounded action."
}
```

### 6. Execute

```http
POST /api/executions
```

The execution layer then calls Razorpay Test Mode.

### 7. Inspect the audit trail

```http
GET /api/audit-log
```

---

# What Is Intentionally Not in the MVP?

FinGraph deliberately does **not** pretend to already be a fully autonomous merchant operating system.

The current MVP uses a narrow order-level signal because that is the evidence actually available in the implemented system.

It does not currently claim to have:

* customer-level intelligence
* product-level intelligence
* complete transaction intelligence
* autonomous experimentation
* unrestricted LLM execution
* automatic spending authority
* self-modifying policies
* production payment execution
* fully autonomous merchant operations

These are future stages of the architecture.

---

# Future Roadmap

The MVP is designed as the first vertical slice of a much larger agentic commerce architecture.

## Phase 1 — Multi-Agent Merchant Intelligence

Expand the current order-level pipeline into specialized agents:

```text
                    Merchant
                       │
              ┌────────┴────────┐
              ▼                 ▼
        Customer Agent     Transaction Agent
              │                 │
              └────────┬────────┘
                       ▼
                 Product Agent
                       │
                       ▼
              Opportunity Agent
```

These agents would build a richer merchant context instead of relying only on order value.

Potential signals:

* customer purchase history
* repeat purchase behavior
* product relationships
* transaction patterns
* order frequency
* customer/product segments

---

## Phase 2 — Merchant Memory

Introduce persistent merchant memory.

Instead of treating every API request as an isolated calculation:

```text
Current Data
     +
Historical Data
     +
Previous Decisions
     +
Previous Experiments
     ↓
Merchant Memory
```

The system could remember:

* successful strategies
* rejected strategies
* previous policy decisions
* merchant preferences
* experiment outcomes
* seasonal patterns
* historical baselines

This allows future decisions to become context-aware rather than stateless.

---

## Phase 3 — Agentic Strategy Generation

Introduce an LLM reasoning layer behind strict typed contracts.

The LLM would **not** receive unrestricted execution authority.

Instead:

```text
LLM
 ↓
Structured Strategy
 ↓
Schema Validation
 ↓
Policy Engine
 ↓
Human Approval
 ↓
Execution
```

The model can become better at generating strategies while the deterministic policy layer remains the final safety boundary.

---

## Phase 4 — Experiment Agent

Introduce controlled experimentation.

For example:

```text
Opportunity
     ↓
Strategy A ─────┐
                ├── Experiment
Strategy B ─────┘
                │
                ▼
          Measure Outcome
                │
                ▼
          Select Winner
```

The system could eventually learn which growth actions work for different merchant contexts.

Experiments would remain:

* bounded
* measurable
* reversible where possible
* policy controlled
* auditable

---

## Phase 5 — Agentic Commerce Graph

The long-term architecture evolves from a linear pipeline into a dynamic graph:

```text
                   ┌──────────────┐
                   │ Merchant     │
                   │ Context     │
                   └──────┬───────┘
                          │
        ┌─────────────────┼──────────────────┐
        ▼                 ▼                  ▼
 Customer Agent    Transaction Agent   Product Agent
        │                 │                  │
        └─────────────────┼──────────────────┘
                          ▼
                 Opportunity Agent
                          │
                          ▼
                  Strategy Agent
                          │
                          ▼
                  Policy Engine
                          │
                  ┌───────┴───────┐
                  ▼               ▼
               BLOCK           APPROVAL
                                  │
                                  ▼
                             Execution
                                  │
                                  ▼
                              Outcome
                                  │
                                  ▼
                           Merchant Memory
                                  │
                                  └──────► Future Decisions
```

The key transition is:

```text
Pipeline
   ↓
Orchestrated Agents
   ↓
Adaptive Agent Graph
   ↓
Learning Commerce System
```

---

# Long-Term Vision

FinGraph is ultimately intended to evolve into a **merchant growth operating layer**.

Instead of asking a merchant to manually inspect dashboards and decide what to do next:

```text
Dashboard
   ↓
Human discovers opportunity
   ↓
Human decides strategy
   ↓
Human executes
```

the future system becomes:

```text
Merchant Data
      ↓
AI understands context
      ↓
AI discovers opportunity
      ↓
AI proposes strategy
      ↓
Policy constrains action
      ↓
Human or merchant-defined autonomy approves
      ↓
Razorpay executes
      ↓
System measures outcome
      ↓
Memory improves future decisions
```

The objective is not simply **"let AI control payments."**

The objective is:

> **Build a trustworthy execution layer where AI can create measurable merchant growth while every consequential action remains bounded, explainable, controllable, and auditable.**

---

# Design Principles

FinGraph follows several principles that will remain constant as the system becomes more autonomous.

### 1. Intelligence and authority are separate

An agent can recommend an action without being authorized to execute it.

### 2. Every financial action is bounded

Execution parameters are typed and constrained.

### 3. Policy is deterministic

Critical safety rules should not depend on whether an LLM happens to make the right decision.

### 4. Humans remain in the loop

The current MVP requires explicit approval before execution.

Future versions may introduce merchant-configured autonomy levels, but those permissions will still be policy controlled.

### 5. Everything important is auditable

A consequential decision should be explainable after it happens.

### 6. Failure is a first-class outcome

An agentic system should be designed to fail safely.

### 7. Start narrow, then expand

The MVP intentionally proves one complete vertical slice before expanding into a larger multi-agent system.

---

# Security

Never commit credentials.

```text
.env
```

is ignored by Git.

Use only Razorpay Test Mode credentials during development and demonstrations.

The project does not require live payment credentials to demonstrate the MVP.

---

# Razorpay Integration

FinGraph uses Razorpay APIs for both merchant data retrieval and bounded execution.

The current execution path uses the Standard Payment Links API:

```text
POST /v1/payment_links
```

Razorpay documents Payment Links as API-created URLs that can be used to collect payments, with APIs available for creation, retrieval, updating, cancellation, and related operations.

For the MVP, execution remains in Test Mode.

---

# Project Status

### Current

```text
[████████████████████] MVP vertical slice complete
```

Implemented:

* [x] Razorpay Test Mode integration
* [x] Real order ingestion
* [x] Opportunity detection
* [x] Typed strategy generation
* [x] Deterministic policy gate
* [x] Real blocking behavior
* [x] Human approval
* [x] Human rejection
* [x] Bounded Payment Link execution
* [x] Razorpay Test Mode execution
* [x] Failure handling
* [x] Persistent audit trail
* [x] Automated tests

### Next

* [ ] Unified orchestration layer
* [ ] Run-level audit correlation
* [ ] Customer Agent
* [ ] Transaction Agent
* [ ] Product Agent
* [ ] Merchant Memory
* [ ] LLM strategy generation behind typed contracts
* [ ] Experiment Agent
* [ ] Outcome measurement
* [ ] Dynamic agent graph
* [ ] Merchant-configured autonomy

---

# The Core Thesis

FinGraph is built around one idea:

> **The future of agentic commerce is not an AI that can blindly execute payments. It is an AI system that can understand merchant context, identify opportunities, propose bounded actions, prove why those actions are safe, obtain the required authority, execute through payment infrastructure, and learn from the outcome.**

The current MVP proves the foundation of that architecture with a real Razorpay Test Mode execution path.
