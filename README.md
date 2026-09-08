# Ouroboros Zeta: ACO assurance demo

A single-file Python demonstration of why passing available checks is not enough to authorize an engineering change.

**All named systems are local mocks.** This example contains no production integrations, proprietary runtime, live AI agent, or real silicon signoff. Interfaces and decision rules were created for this demonstration.

## Quick start

Requires Python 3.8 or newer. No additional packages or accounts are needed.

```bash
python3 aco_simulated_stack.py
python3 aco_simulated_stack.py --self-test
python3 aco_simulated_stack.py --json
```

The default run prints four scenarios. `--self-test` verifies the controls. `--json` prints the simulated calls and results to standard output. The program makes no network requests or file writes.

## From ECO to ACO

An Engineering Change Order (ECO) proposes an engineering modification. In this example, an Agent Change Order (ACO), also described as an Agentic Change Order, represents a change proposed through an agent-driven workflow.

The proposal here is scripted: use smaller cells in an eight-bit adder to reduce modeled area by 25%. The arithmetic remains correct for all 65,536 input pairs. Nominal timing also passes. A required slow-corner timing check is initially absent.

A naive gate releases because every available check is green. The simulated workflow holds because the required evidence is incomplete. When the slow-corner result is revealed, it fails.

**Proposal, technical evidence, and permission to execute are separate parts of the decision.**

## Simulated roles

`MockZetaRuntime` coordinates the following local components and stores snapshots of their outputs:

| Component | Behavior implemented in this example |
| --- | --- |
| Engineering verifier | Exhaustive untimed arithmetic check and synthetic delay calculations |
| `MockHorizonAX` | Fixed checklist identifying missing and failed engineering checks |
| `MockCLEAR` | Release recommendation based on checklist completeness and results |
| `MockATLAS` | Scripted handling of disagreement between a release request and the review |
| `MockKRISHNA` | Final local action gate requiring passing assurance and a local permission flag |

These roles illustrate a proposed integration. They do not document actual product APIs, internal algorithms, product ownership, or commercial availability. The HorizonAX mock does not implement the broader impact-analysis workflow described in the conceptual contribution acknowledged below.

## Expected results

| Scenario | HorizonAX mock | CLEAR mock | KRISHNA mock |
| --- | --- | --- | --- |
| Edited design; slow-corner evidence withheld | INCOMPLETE | HOLD | HOLD |
| Edited design; slow-corner failure revealed | FAIL | HOLD | HOLD |
| Original design; complete passing evidence | PASS | TOY_RELEASE | TOY_RELEASE |
| Original design; passing evidence but no local permission | PASS | TOY_RELEASE | HOLD |

In the first scenario, ATLAS handles a disagreement: the naive requester asks to release, while CLEAR recommends HOLD. Its fixed rule preserves HOLD. In the other scenarios, there is no review disagreement to resolve.

The synthetic timing budget is 1,000 ps. The edited design has +440 ps nominal slack and -120 ps slow-corner slack. The original design has +200 ps slow-corner slack. These are invented teaching values, not foundry or PDK measurements.

## What the checks establish

The self-test checks that green partial evidence can coexist with HOLD, a revealed failure remains held, the passing control can release, lack of local permission blocks release, and a directly supplied release disposition cannot bypass incomplete assurance through the mock execution method. It also checks call order. The scenario runner checks that later events preserve the earlier snapshots during the run.

This is a constructed example, not a benchmark of a production system. The permission flag is not authentication, and callers can modify this Python program. History is ordinary mutable in-memory data, not a tamper-evident or cryptographically authenticated log. TOY_RELEASE changes no chip design and performs no external action.

## Acknowledgments and conceptual contribution

We credit **Niraj Prasad of Caminosoft** for contributing the **Agent Change Order (ACO)** framing to this project and for articulating the associated workflow in which agent-proposed engineering changes undergo impact analysis and independent assurance before admission to an authoritative design. His contribution also described HorizonAX's proposed role in that workflow.

This acknowledgment recognizes his conceptual contribution to this project. It does not assert that the term or concept originated here globally, and it does not designate authorship of every implementation or ownership of the separately named systems.

This educational Python implementation was prepared by Deep Prasad with assistance from OpenAI Codex. The mock interfaces and simplified rules are specific to this demonstration.

The repository does not reproduce private correspondence, screenshots, or the original illustration. Attribution does not imply endorsement of this implementation by Niraj Prasad or Caminosoft.

## License and release status

Copyright (c) 2026 Quantum Generative Materials LLC.

This demo code and accompanying documentation are licensed under the MIT License. See [LICENSE](LICENSE).

Ouroboros Zeta is the project branding. Quantum Generative Materials LLC (QGM) is the licensor of this package. This branding does not represent an incorporated entity or transfer ownership of separately referenced systems.

The intended open-source package comprises this educational script and its accompanying documentation. No production CLEAR, KRISHNA, ATLAS, Zeta Point, or HorizonAX implementation is included. Referencing a system here does not license that separate system or establish a partnership.

MIT allows commercial reuse, modification, and redistribution subject to its notice requirements. The acknowledgment above is not an added license condition requiring downstream users to display a credit or logo. If mandatory downstream conceptual attribution is a project requirement, revisit the licensing choice before publication.

Official license references:

- [MIT License](https://opensource.org/license/mit)
- [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)

## Contributions

Useful contributions include additional synthetic failure cases, clearer explanations, and tests that distinguish incomplete evidence from failed evidence. Do not submit confidential implementation details, private correspondence, customer data, proprietary PDK data, or third-party code without appropriate rights.
