# CAHMA Arena — final elimination pitch

## One sentence

CAHMA turns limited edge AI compute into an auditable scheduling resource: policy protects critical cameras, while learned utility decides where the remaining expensive inference is worth spending.

## Five-minute delivery

### 0:00–0:40 — Problem

“AI has made camera analytics more capable, but also more expensive in RAM, VRAM and compute. A site with dozens of feeds cannot run its strongest model everywhere continuously. Round robin is cheap but blind: it spends the same compute on an empty corridor and a rapidly changing safety-critical entrance.”

### 0:40–1:10 — Product and novelty

“CAHMA is a policy-protected compute orchestrator, not another detector. Every camera runs a cheap observer. Safety commitments, operator overrides and minimum service are resolved first. Then a router ranks the eligible camera–model calls, and only the winner receives the shared production inference slot. Every allocation produces an explanation receipt.”

The key distinction is the combination of:

1. policy constraints that cannot be displaced by a learned score;
2. value-aware allocation of the remaining compute;
3. a warmed resident model pool and admission control; and
4. deterministic, inspectable receipts and starvation protection.

### 1:10–3:20 — Live demonstration

1. Show the three feeds and their `SAFETY`, `PRIORITY` and `ADAPTIVE` modes.
2. Point to adaptive utility and final rank as separate values: the model proposes value; the scheduler makes the governed decision.
3. Show the policy hierarchy and explain why safety is a constraint rather than a score.
4. Show one warmed resident service, one load event, `0.2 FPS` protected demand and `12 FPS` profiled capacity.
5. Activate Camera B’s override. Explain that an already-due safety dispatch may still win that instant. Release the override.
6. Open the latest decision receipt and read the selected route, class, reason, model and rank.
7. Show the frozen evidence table.

### 3:20–4:20 — Verifiable evidence

“On a deterministic, leakage-safe, simulated replay holdout of 192 windows, every policy received exactly 192 expensive calls. The learned person router captured 92.7979 proxy utility, versus 68.7085 for round robin and 69.5939 for confidence-only: improvements of 35.06% and 33.34%. It captured 85.59% of the non-deployable oracle. Ten-thousand-sample bootstrap intervals for the absolute gains were entirely positive: 18.31 to 29.86 over round robin, and 17.93 to 28.58 over confidence-only.”

Immediately add: “This metric is Nano-to-Tiny teacher-disagreement proxy utility, not detector ground-truth accuracy. It validates the learned person router. The live v2 heterogeneous policy layer currently uses an explicitly labelled deterministic baseline.”

### 4:20–5:00 — Feasibility and close

“CAHMA sits between existing camera analytics and existing production models. It does not require replacing a detector or sending raw video to the cloud. The prototype already demonstrates local observation, protected scheduling, resident inference, capacity admission, overrides, fairness and receipts. The next validation expands the learned router across multiple production tasks. CAHMA’s promise is simple: when compute is scarce, spend it where it has the highest governed value—and be able to prove why.”

## Exact evidence table

| Equal-budget policy | Calls | Proxy utility |
|---|---:|---:|
| Round robin | 192 | 68.7085 |
| Confidence only | 192 | 69.5939 |
| Learned person router | 192 | 92.7979 |
| Non-deployable oracle | 192 | 108.4205 |

- Learned versus round robin: `+35.06%`; absolute 95% bootstrap interval `[18.31, 29.86]`.
- Learned versus confidence-only: `+33.34%`; absolute 95% bootstrap interval `[17.93, 28.58]`.
- Oracle utility captured: `85.59%`.
- Holdout records: `1,962`; replay windows: `192`; seed: `20260902`.
- Router SHA-256: `a098669583c43b93796f0d0fed1d1581183bada5c3852def14cbe74239dc8509`.
- Dataset SHA-256: `919ee82e7ad9d28d0de4042f8afe505948e96a80536e9a9a1fe95af4e02ad16e`.

## Never claim

- Do not call the system production-ready.
- Do not call proxy utility accuracy, mAP, incident prevention or compute savings.
- Do not say the live v2 selector is the trained heterogeneous SAGE model.
- Do not claim multiple trained task models; the current demo uses person detection.
- Do not call the videos live deployment footage.
