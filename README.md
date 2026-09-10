# Ouroboros Zeta: ACO assurance demo

A small Python demonstration of why passing available checks is not enough to authorize an engineering change, with a **versioned ACO exchange** interoperability contract (v1 and additive v1.1).

**All named systems are local mocks.** This example contains no production integrations, proprietary runtime, live AI agent, or real silicon signoff. Interfaces and decision rules were created for this demonstration.

## Quick start

Requires Python 3.8 or newer. No additional packages or accounts are needed.

```bash
python3 aco_simulated_stack.py
python3 aco_simulated_stack.py --self-test
python3 aco_simulated_stack.py --examples
python3 aco_simulated_stack.py --json
```

The default run prints adder scenarios plus ACO exchange examples. `--self-test` verifies the controls. `--examples` focuses on exchange packets. `--json` prints simulated calls and results to standard output. The program makes no network requests. Example JSON files are read as inputs; the demo does not write files during normal execution.

## What an ACO is

An Engineering Change Order (ECO) proposes an engineering modification. An **Agent Change Order (ACO)** (also Agentic Change Order) is the durable, versioned, evidence-backed governed state of that change.

Conceptually:

```text
one durable ACO identity
    many revisions
    exact source/design binding per revision
    participant-owned records
    append-oriented lifecycle history
    CI/PR merge-gate projection
```

**Where it begins:** an originator proposes a change, stated objective, and acceptance criteria against a concrete source binding.

**Where it ends:** lifecycle reaches a terminal state such as `MERGED` / `CLOSED`, or non-execution terminals such as `REJECTED`, `WITHDRAWN`, `SUPERSEDED`, `EXPIRED`, or `CLOSED_WITHOUT_EXECUTION`. This demo does not implement a production state machine; it records bounded transitions.

## Contract versions

| Version | Schema | Role |
| --- | --- | --- |
| **1.0** | [`schemas/aco_exchange_v1.schema.json`](schemas/aco_exchange_v1.schema.json) | Original snapshot interchange (proposal, evidence, assurance, CLEAR, optional ATLAS, KRISHNA, Zeta transition) |
| **1.1** | [`schemas/aco_exchange_v1_1.schema.json`](schemas/aco_exchange_v1_1.schema.json) | Additive: `revision`, `source_binding`, `ownership`, `lifecycle_state`, `transition_history`, `merge_gate`, explicit producers, `STALE` / `REANALYSIS_REQUIRED` |

v1 examples remain runnable. v1.1 demonstrates durable identity across commits without rewriting history.

The demo validates packets with small deterministic standard-library checks. It does **not** depend on `jsonschema`, `pydantic`, network clients, or external services.

### v1.1 semantic patch (gate honesty)

Still `schema_version: "1.1"`, with tightened runtime semantics (documented migration, not a silent meaning change of green fixtures):

- HorizonAX evaluates evidence freshness/status/binding and numeric `OBJECTIVE_THRESHOLD` values; labels alone cannot manufacture PASS.
- Release-authorizing evidence must have explicit `freshness: CURRENT`. `UNKNOWN`, missing, or null freshness is incomplete and HOLD (never normalized to CURRENT).
- Unsupported required criterion types derive `NOT_EVALUATED` / `UNSUPPORTED_REQUIRED_CRITERION` and block regardless of submitted SATISFIED.
- Declared HorizonAX `FAIL`/`INCOMPLETE` is preserved separately from evidence-derived assessment; disagreement with green checks records `ASSURANCE_STATUS_CONFLICT` and blocks. Declared `PASS` never overrides failed/stale/incomplete evidence.
- Serialized `horizonax_assurance` carries three distinct fields: `declared_status` (producer submission), `derived_status` (evidence assessment), and `status` (final effective status). `submitted_status` remains as a compatibility alias.
- v1.1 release requires `horizonax_assurance.bound_commit_sha` and matching evidence bindings to `source_binding.commit_sha`.
- Incoming `atlas_dispute.status=OPEN` is preserved and blocks execution/merge.
- `merge_gate` is derived only from current computed state (never imports a stale `MERGE_AUTHORIZED` reason onto a HOLD).
- v1 packets remain supported without commit-bound merge authorization.
- Toy class coverage may use successful class-labeled checks when evidence is non-empty (documented aggregation only). Empty evidence cannot authorize.
- Regression suite: `python -m unittest -v test_gate_regressions`

Positive-control baseline copy: [`examples/v1_1/aco2741_rev7_authorized.baseline.json`](examples/v1_1/aco2741_rev7_authorized.baseline.json).

## Participant ownership

No participant silently overwrites another participant's authoritative result.

| Record | Owner | Answers |
| --- | --- | --- |
| proposed change / objective / acceptance | **ORIGINATOR** | What is being changed, and what must be true? |
| `horizonax_assurance` + evidence | **HorizonAX** | Is the change technically acceptable against engineering intent and required assurance? |
| `clear_review` | **CLEAR** | Is the assurance *case* complete, current, bound, and policy-satisfying? |
| `atlas_dispute` | **ATLAS** | If disputed, what is the resolution? (optional) |
| `execution_gate` | **KRISHNA** | Is execution/merge authorized right now? |
| lifecycle / `transition_history` | **Zeta** | What transitions were recorded? |

CLEAR does **not** reimplement CDC/FIFO/STA. CLEAR evaluates policy completeness, evidence presence/currency, source binding, producer identity, acceptance criteria, and unresolved disputes.

HorizonAX does **not** decide merge authorization. KRISHNA does **not** perform semiconductor analysis. Zeta coordinates and records; it does not decide whether a CDC/FIFO property holds.

ATLAS remains optional: undisputed paths go CLEAR → KRISHNA.

## Source binding and stale assurance

An assurance or authorization is bound to an exact analyzed state, represented in v1.1 as `source_binding` (demo fields such as repository, branch, `commit_sha`, and representative fingerprints). These are teaching bindings, not a claim that every semiconductor flow uses exactly these artifacts.

**Invariant:** approval for source state A must not authorize source state B.

Demonstration (`ACO-2741`):

| Revision | Commit | Result |
| --- | --- | --- |
| 7 | `aaa1111…` | HorizonAX PASS, CLEAR APPROVED, KRISHNA PASS, merge gate PASS |
| 8 | `bbb2222…` | Prior PASS retained in history; assurance **STALE**; KRISHNA **HOLD**; merge gate **STALE** |

The earlier PASS is historical evidence. It is not erased, and it is not reusable for the new commit.

## Domain-aware policy (tiny, simulated)

For `change_class = ASYNC_FIFO_MODIFICATION`, the demo policy requires assurance classes `CDC`, `FIFO_SAFETY`, `FIFO_ORDERING`, and `TIMING` (with optional conditional classes documented in code).

CLEAR can detect that HorizonAX returned only CDC + TIMING and therefore mark the assurance case incomplete (`MISSING_REQUIRED_ASSURANCE_CLASS`) without implementing FIFO verification.

## PR / CI merge-gate projection

v1.1 includes a machine-readable `merge_gate` object intended for a future GitHub/GitLab/Jenkins required check:

```text
aco_id, revision, commit_sha, gate_status, reason_codes
```

`gate_status`: `PENDING` | `PASS` | `HOLD` | `DENY` | `STALE`

Merge is blocked when analysis is pending, required evidence is missing, a required property is violated, CLEAR requires changes, an ATLAS dispute is open, KRISHNA HOLDs/DENYs, or the source binding changed (stale authorization).

Only current binding + complete HorizonAX assurance + CLEAR APPROVED + dispute absent/resolved + KRISHNA PASS may project `PASS` / `MERGE_AUTHORIZED`.

**This repository does not integrate with GitHub.** The field is contract/demo behavior only.

## Likely production storage model (documented only)

| Store | Holds |
| --- | --- |
| Operational DB | ACO identity, current revision, lifecycle state, bindings, record IDs, indexes |
| Immutable object store | Proposal snapshots, evidence manifests, HorizonAX/CLEAR/ATLAS/KRISHNA/Zeta artifacts |
| Git / source control | Design state under change, exact commit identity, optional declarative policies |

**Filesystem folder movement is not the lifecycle authority.** This demo uses in-memory append-oriented history and JSON examples only — no SQLite, Postgres, S3, or similar.

## Authority boundaries (summary)

| Role | Demo responsibility |
| --- | --- |
| HorizonAX | Engineering assurance posture and evidence references |
| CLEAR | Assurance-case / policy review (not duplicate semiconductor verification) |
| ATLAS | Dispute resolution **only when a dispute exists** |
| KRISHNA | Machine execution/merge gate (PASS / HOLD / DENY) |
| Zeta | Lifecycle coordination and transition recording |

## What each example teaches

### Adder path (preserved)

| Scenario | Objective | HorizonAX | CLEAR | ATLAS | KRISHNA |
| --- | --- | --- | --- | --- | --- |
| Slow-corner evidence withheld | area ECO | INCOMPLETE | CHANGES_REQUIRED | invoked | HOLD |
| Slow-corner failure revealed | area ECO | FAIL | CHANGES_REQUIRED | not invoked | HOLD |
| Original design; complete evidence | control | PASS | APPROVED | not invoked | PASS |
| Complete evidence; no local permission | control | PASS | APPROVED | not invoked | HOLD |
| Arithmetic+timing pass; area `<= 70` fails at 75 | modeled area | FAIL | CHANGES_REQUIRED | not invoked | HOLD |

### ACO exchange packets

| File | Lesson |
| --- | --- |
| [`examples/cdc_fifo_pass.json`](examples/cdc_fifo_pass.json) | v1 good CDC/FIFO repair → PASS |
| [`examples/cdc_fifo_hold.json`](examples/cdc_fifo_hold.json) | v1 CDC looks fixed / FIFO violated → HOLD |
| [`examples/area_goal_hold.json`](examples/area_goal_hold.json) | v1 verification PASS ≠ objective met → HOLD |
| [`examples/v1_1/aco2741_rev7_authorized.json`](examples/v1_1/aco2741_rev7_authorized.json) | v1.1 commit A authorized |
| [`examples/v1_1/aco2741_rev8_stale.json`](examples/v1_1/aco2741_rev8_stale.json) | v1.1 commit B → prior PASS stale → HOLD |
| [`examples/v1_1/policy_missing_fifo.json`](examples/v1_1/policy_missing_fifo.json) | CLEAR detects missing required assurance class → HOLD |

## Simulated roles

`MockZetaRuntime` coordinates local mocks and stores snapshots of their outputs. Recommendation is not authorization. An old PASS for a different commit is not authorization.

## Repository layout

```text
aco_simulated_stack.py
schemas/aco_exchange_v1.schema.json
schemas/aco_exchange_v1_1.schema.json
examples/cdc_fifo_pass.json
examples/cdc_fifo_hold.json
examples/area_goal_hold.json
examples/v1_1/aco2741_rev7_authorized.json
examples/v1_1/aco2741_rev8_stale.json
examples/v1_1/policy_missing_fifo.json
README.md
LICENSE
.gitignore
```

## What the checks establish

The self-test covers cases A–H from the v1 demo plus:

- I. previously authorized ACO becomes STALE after source commit changes → HOLD until re-analysis; prior PASS preserved in history
- J. CLEAR detects missing required assurance class via domain policy → CHANGES_REQUIRED / HOLD

This is a constructed educational example, not a production system. History is ordinary in-memory data, not tamper-evident. PASS / APPROVED changes no chip design. CDC/FIFO/area values are synthetic teaching data, not production HorizonAX outputs.

## Acknowledgments and conceptual contribution

We credit **Niraj Prasad of Caminosoft** for contributing the **Agent Change Order (ACO)** framing to this project and for articulating the associated workflow in which agent-proposed engineering changes undergo impact analysis and independent assurance before admission to an authoritative design. His contribution also described HorizonAX's proposed role in that workflow.

This acknowledgment recognizes his conceptual contribution to this project. It does not assert that the term or concept originated here globally, and it does not designate authorship of every implementation or ownership of the separately named systems.

This educational Python implementation was prepared by Deep Prasad with assistance from OpenAI Codex. The mock interfaces and simplified rules are specific to this demonstration.

The repository does not reproduce private correspondence, screenshots, or the original illustration. Attribution does not imply endorsement of this implementation by Niraj Prasad or Caminosoft.

## License and release status

Copyright (c) 2026 Quantum Generative Materials LLC.

This demo code and accompanying documentation are licensed under the MIT License. See [LICENSE](LICENSE).

Ouroboros Zeta is the project branding. Quantum Generative Materials LLC (QGM) is the licensor of this package. This branding does not represent an incorporated entity or transfer ownership of separately referenced systems.

The intended open-source package comprises this educational script, the demo ACO exchange schemas/examples, and accompanying documentation. No production CLEAR, KRISHNA, ATLAS, Zeta Point, or HorizonAX implementation is included. Referencing a system here does not license that separate system or establish a partnership.

MIT allows commercial reuse, modification, and redistribution subject to its notice requirements. The acknowledgment above is not an added license condition requiring downstream users to display a credit or logo. If mandatory downstream conceptual attribution is a project requirement, revisit the licensing choice before publication.

Official license references:

- [MIT License](https://opensource.org/license/mit)
- [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)

## Contributions

Useful contributions include additional synthetic failure cases, clearer explanations, and tests that distinguish incomplete evidence from failed evidence. Do not submit confidential implementation details, private correspondence, customer data, proprietary PDK data, or third-party code without appropriate rights.
