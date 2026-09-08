# Ouroboros Zeta: ACO assurance demo

A small Python demonstration of why passing available checks is not enough to authorize an engineering change, now with a **versioned ACO exchange v1** interoperability contract.

**All named systems are local mocks.** This example contains no production integrations, proprietary runtime, live AI agent, or real silicon signoff. Interfaces and decision rules were created for this demonstration.

## Quick start

Requires Python 3.8 or newer. No additional packages or accounts are needed.

```bash
python3 aco_simulated_stack.py
python3 aco_simulated_stack.py --self-test
python3 aco_simulated_stack.py --examples
python3 aco_simulated_stack.py --json
```

The default run prints the adder scenarios plus ACO exchange examples. `--self-test` verifies the controls. `--examples` focuses on the CDC/FIFO and area-objective packets. `--json` prints simulated calls and results to standard output. The program makes no network requests. Example JSON files are read as inputs; the demo does not write files during normal execution.

## From ECO to ACO exchange v1

An Engineering Change Order (ECO) proposes an engineering modification. An Agent Change Order (ACO), also described as an Agentic Change Order, represents a change proposed through an agent-driven workflow.

This repository keeps the original educational adder workflow and makes the **interchange contract** explicit:

```text
versioned ACO object
        ↓
same mock workflow
        ↓
versioned disposition
```

The contract lives in [`schemas/aco_exchange_v1.schema.json`](schemas/aco_exchange_v1.schema.json). It separates identity/schema version, proposed change, stated objective, acceptance criteria, evidence, HorizonAX assurance, CLEAR review, optional ATLAS dispute, KRISHNA execution gate, and Zeta transition recording.

The demo validates packets with small deterministic standard-library checks. It does **not** depend on `jsonschema`, `pydantic`, network clients, or external services. The schema file is the documented interoperability contract.

## Authority boundaries

| Role | Demo responsibility |
| --- | --- |
| HorizonAX | Engineering impact / assurance posture and evidence references |
| CLEAR | Reviews the decision and acceptance posture |
| ATLAS | Handles a dispute **only when one exists** (not a happy-path requirement) |
| KRISHNA | Gates execution; may PASS or HOLD |
| Zeta | Coordinates and records workflow transitions/outcomes |

Zeta does not decide whether a CDC/FIFO property holds. HorizonAX does not decide whether an ACO is authorized to execute. A technically successful check is not automatic proof that the stated engineering objective was achieved. Missing evidence remains distinguishable from failed evidence.

## What each example teaches

### Adder path (preserved)

Scripted proposal: use smaller cells in an eight-bit adder. Arithmetic remains correct for all 65,536 input pairs. Nominal timing can pass while required slow-corner evidence is missing or failing.

| Scenario | Objective | HorizonAX | CLEAR | ATLAS | KRISHNA |
| --- | --- | --- | --- | --- | --- |
| Slow-corner evidence withheld | area reduction | INCOMPLETE | CHANGES_REQUIRED | invoked (naive approve vs review) | HOLD |
| Slow-corner failure revealed | area reduction | FAIL | CHANGES_REQUIRED | not required | HOLD |
| Original design; complete evidence | control | PASS | APPROVED | not invoked | PASS |
| Complete evidence; no local permission | control | PASS | APPROVED | not invoked | HOLD |
| Arithmetic+timing pass; area `<= 70` fails at 75 | modeled area | FAIL | CHANGES_REQUIRED | not invoked | HOLD |

### ACO exchange packets (`examples/`)

| File | Lesson |
| --- | --- |
| [`cdc_fifo_pass.json`](examples/cdc_fifo_pass.json) | CDC/FIFO repair with required properties satisfied → acceptance SATISFIED, CLEAR APPROVED, ATLAS not invoked, KRISHNA PASS |
| [`cdc_fifo_hold.json`](examples/cdc_fifo_hold.json) | Structural CDC can look fixed while `fifo_no_overflow` is PROPERTY_VIOLATED → acceptance NOT_SATISFIED, KRISHNA HOLD. Fixing the original finding is not proof the change is acceptable. A 2-FF synchronizer alone is not presented as a universal pulse/control fix. |
| [`area_goal_hold.json`](examples/area_goal_hold.json) | Reuses the synthetic adder model: arithmetic and timing PASS, but stated modeled-area objective `<= 70` fails at observed 75 → KRISHNA HOLD |

## Simulated roles

`MockZetaRuntime` coordinates the following local components and stores snapshots of their outputs:

| Component | Behavior implemented in this example |
| --- | --- |
| Engineering verifier | Exhaustive untimed arithmetic check and synthetic delay / area calculations |
| `MockHorizonAX` | Checklist / packet assurance identifying missing and failed required items |
| `MockCLEAR` | APPROVED vs CHANGES_REQUIRED from assurance completeness and results |
| `MockATLAS` | Invoked only on disagreement between a release request and CLEAR |
| `MockKRISHNA` | Final local gate requiring APPROVED review, PASS assurance, and a local permission flag |

These roles illustrate a proposed integration. They do not document actual product APIs, internal algorithms, product ownership, or commercial availability.

## Repository layout

```text
aco_simulated_stack.py          # demo runner + mocks + self-test
schemas/aco_exchange_v1.schema.json
examples/cdc_fifo_pass.json
examples/cdc_fifo_hold.json
examples/area_goal_hold.json
README.md
LICENSE
```

## What the checks establish

The self-test checks that green partial evidence can coexist with HOLD, a revealed failure remains held, the passing control can release when locally permitted, lack of local permission blocks release, a directly supplied APPROVED disposition cannot bypass incomplete assurance, CDC/FIFO good and bad repairs behave as above, area-objective failure holds despite verification PASS, happy-path packets do not require ATLAS, and later events preserve earlier history snapshots.

This is a constructed example, not a benchmark of a production system. The permission flag is not authentication, and callers can modify this Python program. History is ordinary mutable in-memory data, not a tamper-evident or cryptographically authenticated log. PASS / APPROVED changes no chip design and performs no external action. CDC/FIFO and area figures are synthetic teaching values, not foundry, PDK, or production HorizonAX outputs.

## Acknowledgments and conceptual contribution

We credit **Niraj Prasad of Caminosoft** for contributing the **Agent Change Order (ACO)** framing to this project and for articulating the associated workflow in which agent-proposed engineering changes undergo impact analysis and independent assurance before admission to an authoritative design. His contribution also described HorizonAX's proposed role in that workflow.

This acknowledgment recognizes his conceptual contribution to this project. It does not assert that the term or concept originated here globally, and it does not designate authorship of every implementation or ownership of the separately named systems.

This educational Python implementation was prepared by Deep Prasad with assistance from OpenAI Codex. The mock interfaces and simplified rules are specific to this demonstration.

The repository does not reproduce private correspondence, screenshots, or the original illustration. Attribution does not imply endorsement of this implementation by Niraj Prasad or Caminosoft.

## License and release status

Copyright (c) 2026 Quantum Generative Materials LLC.

This demo code and accompanying documentation are licensed under the MIT License. See [LICENSE](LICENSE).

Ouroboros Zeta is the project branding. Quantum Generative Materials LLC (QGM) is the licensor of this package. This branding does not represent an incorporated entity or transfer ownership of separately referenced systems.

The intended open-source package comprises this educational script, the demo ACO exchange schema/examples, and accompanying documentation. No production CLEAR, KRISHNA, ATLAS, Zeta Point, or HorizonAX implementation is included. Referencing a system here does not license that separate system or establish a partnership.

MIT allows commercial reuse, modification, and redistribution subject to its notice requirements. The acknowledgment above is not an added license condition requiring downstream users to display a credit or logo. If mandatory downstream conceptual attribution is a project requirement, revisit the licensing choice before publication.

Official license references:

- [MIT License](https://opensource.org/license/mit)
- [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)

## Contributions

Useful contributions include additional synthetic failure cases, clearer explanations, and tests that distinguish incomplete evidence from failed evidence. Do not submit confidential implementation details, private correspondence, customer data, proprietary PDK data, or third-party code without appropriate rights.
