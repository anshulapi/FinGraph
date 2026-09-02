# FinGraph — Razorpay AI Buildathon (Track 01: AI Growth & Agentic Commerce)

Deadline: applications close **September 5**. Deliverables: public GitHub repo, 5-min pitch video, architecture walkthrough.

---

## 1. Why this scope, in one paragraph (for your README / pitch intro)

FinGraph is the same graph-orchestration substrate that powers ReelGraph, applied to a second vertical: merchant growth instead of creative generation. The full architecture (goal interface → dynamic agent graph → opportunity/strategy/experiment layers → policy gate → human approval → execution → outcome monitor → memory) is the long-term "AI OS for commerce" vision. For this buildathon, one vertical slice of that graph is built fully real against Razorpay test-mode APIs — not simulated end to end.

---

## 2. MVP architecture — what's real vs. what's roadmap

| # | Node | Build for real? | What "real" means here |
|---|------|------------------|--------------------------|
| 1 | Merchant goal | Input only | A goal string / config, e.g. "grow AOV via cross-sell" |
| 2 | Data agent | ✅ Real | Pulls actual merchant order/customer data via Razorpay **test-mode** API — no preloaded CSV |
| 3 | Opportunity agent | ✅ Real | Identifies a genuine upsell/cross-sell candidate from that real data |
| 4 | Strategy agent | ✅ Real | Drafts a bounded action + written reasoning (this reasoning is what goes in the audit log) |
| 5 | Policy / risk gate | ✅ Real | Enforces a spend cap / action allowlist; must actually **block** something in the demo |
| 6 | Human approval | ✅ Real | One-click approve/deny step, visible in the demo |
| 7 | Execution agent | ✅ Real | Calls a real Razorpay test-mode endpoint (payment link / order / catalog update) and shows the response |
| 8 | Outcome + audit log | ✅ Real | Queryable log (JSON/SQLite is fine) of every agent's input → decision → reasoning, timestamped |

Everything beyond this (Customer/Transaction/Product agent split, Experiment agent, full Merchant Memory loop, multi-track dynamic graph) stays in the **architecture diagram and pitch as roadmap**, not in the working demo. Say so explicitly rather than implying it's all built — panels reward honesty about scope here (Track 4's language: "one cherry-picked match proves nothing" signals they penalize overclaiming across all tracks).

---

## 3. Progress checklist

### Core build (must all be true before you touch polish)
- [ ] Data agent authenticates and pulls real records from Razorpay test-mode APIs
- [ ] Opportunity agent runs on that real data (not a fixture) and produces a candidate
- [ ] Strategy agent outputs a structured action + reasoning trace
- [ ] Policy/risk gate has at least one hard rule (spend cap or allowlist) that can actually trigger
- [ ] Human approval step is wired into the flow (even a simple CLI/UI prompt is fine)
- [ ] Execution agent makes a real Razorpay test-mode API call and the response is captured
- [ ] Audit log records every step (agent, input, output, reasoning, timestamp) and can be printed/viewed
- [ ] One deliberately failing case is captured and handled gracefully (e.g., gate blocks an over-cap offer, or a failed API call triggers a retry/fallback)

### Packaging
- [ ] Public GitHub repo, clean README explaining the ReelGraph → FinGraph lineage in the first paragraph
- [ ] Architecture diagram in the repo: full vision graph + a clear callout of which nodes are "built" vs "roadmap"
- [ ] 5-minute pitch video: demo the real loop running live first, vision/roadmap talk kept to ~30–45 seconds
- [ ] Audit trail and the one blocked/failed case are both shown on-screen in the video, not just described

### Nice-to-have if time allows
- [ ] Mock AI-buyer agent that queries an agent-readable catalog and completes a test-mode transaction (covers the "transactable by an AI buyer" half of the track brief)
- [ ] Simple dashboard/UI over the audit log instead of raw JSON

---

## 4. Why this approach should land well with the panel

- **Matches the track's explicit bar** ("every money action explainable, bounded and gated... show the audit trail and one failure handled gracefully") point for point — you're not guessing at what they want, you're building exactly the checklist they published.
- **Uses real Razorpay test-mode APIs**, which the brief requires by name — this alone separates a "build" from a "concept video," and a lot of submissions will skip real integration under time pressure.
- **ReelGraph lineage gives narrative credibility.** Framing FinGraph as a second vertical on a proven orchestration substrate reads as "I've shipped this pattern before," not "I invented a graph to fit the brief this week."
- **Scoped honesty beats false breadth.** A judge skimming many repos in a short window trusts a small, fully-working loop with a real audit log far more than a large diagram with three working nodes and ten aspirational ones.
- **The gated failure case is a differentiator.** Most growth-agent demos show the happy path only. Showing the policy gate actually blocking something, live, is a concrete, memorable "aha" moment for a 5-minute video.
