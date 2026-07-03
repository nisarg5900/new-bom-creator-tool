# New BOM Creator Tool

An improved BOM Creator for ERPNext — closing the gaps in the built-in
*Multi-level BOM Creator* tool while keeping the generated BOMs 100% standard.

> Verified against **ERPNext 16.21.1**. License: **GPLv3** (matches ERPNext).

---

## Design target: mergeable **and** standalone

The app is built as a stack of small, focused changes to the **existing**
`BOM Creator` — not as a parallel replacement doctype. Every change is designed
so it can be shipped two ways:

1. **Standalone app** — installed on any ERPNext v16 site; overrides the
   built-in BOM Creator via Frappe hooks (`override_doctype_class`,
   `override_whitelisted_methods`, `doctype_js`, bundle override). No fork.
2. **Upstream PR against `frappe/erpnext`** — each hooks-override maps ~1:1
   onto an edit of the corresponding core file.

Discipline that keeps both viable:

- **One fix = one self-contained unit = one potential PR.** Small focused PRs
  merge; monolithic rewrites do not. Even if the whole vision isn't accepted,
  individual wins land.
- **License GPLv3 from commit 1.** ERPNext is GPLv3; anything else is
  unmergeable.
- **ERPNext conventions** (ruff/eslint/prettier, `FrappeTestCase`, no new
  heavy deps).
- **Quarantine app-only concerns** (install hooks, workspace card, any
  branding) in a thin, obviously-droppable layer.
- **Engage the community first.** Forum post → issues → PRs — do not build
  first and hope.

## Two-layer workflow

Same building surface, two conceptual passes users can iterate on
independently:

- **Layer 1 — Structure.** FG + qty + UOM; the component tree; sub-assembly vs
  raw materials; per-line qty & UOM with correct conversion; reuse an
  existing sub-assembly's default BOM.
- **Layer 2 — Detail.** Operations/routing, by-products / secondary items,
  scrap / process loss, QC, warehouses, alternates, active/default control.

Structure first, detail second. Layers are two toolbars over the same tree,
not modal steps.

**Positioning against direct BOM creation:** primary path, not exclusive. The
standard BOM form stays available for trivial BOMs, quick edits, and platform
flows (Work Orders, subcontracting, MRP, Data Import). Entry points from the
BOM list / new-BOM form make the tool the natural default without blocking
the form.

## What's wrong with the built-in BOM Creator

Verified against source. Full detail with code references and upstream-issue
de-duplication in [`docs/UPSTREAM_ISSUES.md`](docs/UPSTREAM_ISSUES.md).

| # | Gap | Type | Upstream status |
|---|-----|------|-----------------|
| 1 | Line UOM / conversion factor hardcoded to stock UOM & factor `1` | Feature | **Not filed** — we draft it |
| 2 | Output is always submitted; no Draft option | Feature | **Not filed** — we draft it |
| 3 | Every generated BOM forced to `is_default`, silently superseding existing defaults | Feature | **Not filed** — we draft it |
| 4 | Sub-assembly RM not fetched from an existing default BOM | Feature | Exists: [#42932](https://github.com/frappe/erpnext/issues/42932) |
| 5 | Cannot reuse / link an existing BOM as an explodable node | Feature | Exists: [#38438](https://github.com/frappe/erpnext/issues/38438) |
| 6 | Cannot import an existing submitted BOM back into the tool for editing | Feature | Adjacent: [#38395](https://github.com/frappe/erpnext/issues/38395) |
| 7 | No entry point from the BOM list / new-BOM form | Feature | **Not filed** — we draft it |
| 8 | Tree view is cluttered; no level-based grouping/collapse | UX | **Not filed** — we draft it |
| 9 | Dead fields: client writes to non-existent `bom_no`; header `default_warehouse` never consumed | Bug | **Not filed** — we draft it |
| — | Operations/routing costing surface missing | Feature | Exists: [#44094](https://github.com/frappe/erpnext/issues/44094), [#40529](https://github.com/frappe/erpnext/issues/40529), [#48154](https://github.com/frappe/erpnext/issues/48154) |

## Engagement plan (sequenced)

1. **Forum post** on `discuss.frappe.io` — [`docs/FORUM_POST.md`](docs/FORUM_POST.md) —
   list the gaps, ask if others hit them, ask maintainers if PRs would be
   welcome, invite feature suggestions we haven't listed.
2. **Per-fix GitHub issues** — [`docs/UPSTREAM_ISSUES.md`](docs/UPSTREAM_ISSUES.md) —
   filed separately (per ERPNext CONTRIBUTING), each with a *willing to PR* offer.
3. **Build the standalone app**, phase by phase — [`PHASED_PLAN.md`](PHASED_PLAN.md).
4. **Open PRs** as each phase completes, smallest first (dead-field bugs →
   UOM → …).

## Environment

| Item | Value |
|------|-------|
| Frappe / ERPNext | v16 / 16.21.1 |
| Frappe app module | `new_bom_creator` |
| Dedicated test site | `bomcreator.localhost` (to be created — see plan) |
| License | GPLv3 |

> **Isolation:** one dedicated test site per app; never shared with unrelated
> apps.

## Status

Planning. No app code yet — this repo currently holds the phased plan, the
forum-post draft, and the upstream-issue drafts. Frappe Cloud deployment is
**out of scope** until explicitly confirmed.
