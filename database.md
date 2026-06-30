# DATABASE.md

# ReForge Data Model

## Projects

Stores user projects.

Fields:

* id
* name
* owner
* created_at

---

## Repositories

Stores repository metadata.

Fields:

* url
* owner
* language
* stars
* forks
* last_commit
* license

---

## Heritage Reports

Stores Heritage Score results.

Fields:

* repository_id
* overall_score
* preservation_profile
* explanation

---

## Analysis Reports

Stores architecture and software understanding.

---

## Restoration Jobs

Tracks restoration progress.

States:

* Pending
* Running
* Failed
* Completed

---

## Agent Logs

Stores every agent action.

This creates a fully explainable audit trail.

---

## Evolution Plans

Stores AI recommendations without modifying source code.

---

## Artifacts

Stores:

* Build logs
* Screenshots
* Reports
* Generated diagrams
* Restored binaries
