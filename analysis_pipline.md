# ANALYSIS_PIPELINE.md

# ReForge Analysis Pipeline

Every repository processed by ReForge follows the same pipeline.

## Stage 1 — Repository Discovery

**Goal:** Collect metadata without downloading the full project.

Collect:

* Repository metadata
* Stars, forks, watchers
* License
* Contributors
* Last activity
* Releases
* Languages
* README

**Output:** Repository Profile

---

## Stage 2 — Heritage Evaluation

**Goal:** Determine whether the project deserves preservation.

Runs the ReForge Heritage Score.

Outputs:

* Heritage Score (0–100)
* Preservation Profile
* Worth Preserving? (Yes/No)

If the repository is not worth preserving, analysis stops unless the user forces continuation.

---

## Stage 3 — Software Understanding

**Goal:** Understand the software before changing it.

Analyze:

* Project structure
* Entry points
* Dependencies
* Frameworks
* Build system
* Documentation

**Output:** Software Overview

---

## Stage 4 — Architecture Reconstruction

**Goal:** Recover the software's design.

Generate:

* Module graph
* Dependency graph
* Data flow
* Component relationships

---

## Stage 5 — Restoration Planning

**Goal:** Produce a restoration strategy.

Identify:

* Missing dependencies
* Deprecated libraries
* Build failures
* Compatibility issues
* Estimated restoration effort

No code is modified.

---

## Stage 6 — Restoration

**Goal:** Restore a working version whenever feasible.

Possible actions:

* Dependency replacement
* Build fixes
* Configuration updates
* Runtime fixes

All modifications are logged.

---

## Stage 7 — Evolution Planning

**Goal:** Suggest future improvements.

Examples:

* Framework upgrades
* Performance improvements
* Security improvements
* New capabilities

Suggestions preserve the project's identity.

---

## Final Output

Every analysis produces:

* Repository Summary
* Heritage Score
* Preservation Profile
* Architecture Report
* Restoration Plan
* Evolution Report
* Complete Audit Log
