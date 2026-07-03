# New BOM Creator Tool

An independent Frappe app that provides an improved, wizard-style builder for
creating and editing **standard ERPNext BOM documents** — closing the gaps in
ERPNext's built-in *BOM Creator* tool.

> Verified against **ERPNext 16.21.1** (bench `~/frappe-bench-v16`).

---

## The core design decision: supporting tool, not a replacement

ERPNext's built-in BOM Creator is architecturally a **generator**: its
`create_bom()` method does `frappe.new_doc("BOM")`, populates a small subset of
fields, and submits a real BOM. The `BOM` doctype stays the single source of
truth for MRP, Work Orders, and costing.

**This app follows the same philosophy.** It is a better *front-end* for
building BOMs — it does **not** replace the BOM doctype and does **not** fork
`erpnext`. It generates and edits standard `BOM` records through a controlled
routine that fixes the gaps the core tool leaves open.

Rationale:

1. **Upgrade-safe** — no patching of erpnext core; we depend on it, not fork it.
2. **Interoperable** — BOMs we create are indistinguishable from hand-made ones;
   Work Orders, costing, and reports all keep working.
3. **Matches intent** — the core team already treats BOM Creator as a wizard;
   we extend that idea instead of inventing a parallel source of truth.

## What's wrong with the built-in BOM Creator

Verified against source (`erpnext/manufacturing/doctype/bom_creator/`). Full
detail with code references and upstream-issue de-duplication lives in
[`docs/UPSTREAM_ISSUES.md`](docs/UPSTREAM_ISSUES.md).

| # | Gap | Type | Upstream status |
|---|-----|------|-----------------|
| 1 | Line UOM / conversion factor hardcoded to stock UOM & factor `1` | Feature | **Not filed** — we draft it |
| 2 | Output is always submitted; no Draft option | Feature | **Not filed** — we draft it |
| 3 | Every generated BOM forced to `is_default`, silently superseding existing defaults (incl. sub-assemblies) | Feature | **Not filed** — we draft it |
| 4 | Sub-assembly raw materials not fetched from an existing default BOM | Feature | Exists: [#42932](https://github.com/frappe/erpnext/issues/42932) |
| 5 | Cannot reuse / link an existing BOM as an explodable node | Feature | Exists: [#38438](https://github.com/frappe/erpnext/issues/38438) |
| 6 | Cannot import an existing submitted BOM back into the tool for editing | Feature | Adjacent: [#38395](https://github.com/frappe/erpnext/issues/38395) |
| 7 | No entry point from the BOM list / new-BOM form | Feature | **Not filed** — we draft it |
| 8 | Tree view is cluttered; no level-based grouping/collapse | UX | **Not filed** — we draft it |
| 9 | Dead fields: client writes to non-existent `bom_no`; `default_warehouse` never consumed | Bug | **Not filed** — we draft it |
| — | Operations/routing costing surface missing | Feature | Exists: [#44094](https://github.com/frappe/erpnext/issues/44094), [#40529](https://github.com/frappe/erpnext/issues/40529), [#48154](https://github.com/frappe/erpnext/issues/48154) |

## How this app addresses them

A parallel **BOM Builder** doctype + custom tree page that generates standard
BOMs, adding: editable line UOM with correct conversion-factor lookup, a
Draft/Submit + default/active toggle with a supersede preview, sub-assembly BOM
reuse, import-existing-BOM-for-editing, a legible level-grouped tree, and
non-invasive entry points from the BOM list.

See [`PHASED_PLAN.md`](PHASED_PLAN.md) for the build sequence and test gates.

## Environment

| Item | Value |
|------|-------|
| Bench | `~/frappe-bench-v16` (WSL Ubuntu-24.04) |
| Frappe / ERPNext | v16 / 16.21.1 |
| Frappe app module | `new_bom_creator` |
| Dedicated test site | `bomcreator.localhost` (to be created — see plan) |
| Field / DocType prefix | `nbc_` / `BOM Builder` |

> **Isolation:** this app gets its **own dedicated test site** and is never
> installed alongside unrelated apps (one dedicated site per app).

## Status

Planning. No app code yet — this repo currently holds the phased plan and the
upstream-issue drafts. Frappe Cloud deployment is **out of scope** until
explicitly confirmed.
