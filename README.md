# New BOM Creator Tool

An improved, wizard-style builder for creating and editing **standard ERPNext
BOM documents** — closing the gaps in ERPNext's built-in *BOM Creator*.

> Verified against **ERPNext 16.21.1**. Licensed **GPL-3.0-or-later** (matching
> ERPNext, so any part can be offered upstream).

---

## Strategy: dual-target — upstreamable *and* standalone

This is designed from day one to serve two delivery targets from one codebase:

1. **Standalone app** — installs on top of ERPNext and adds the improvements by
   overriding the existing BOM Creator through ERPNext's own hooks.
2. **Upstream-mergeable** — each improvement is a small, self-contained change
   shaped so it maps cleanly onto ERPNext's real BOM Creator files and can be
   offered as a PR.

**Guiding rule: one fix = one self-contained unit = one potential PR.** Even if
the whole vision isn't merged, individual wins (e.g. the UOM fix) can still land.

## Design decisions

- **Improve the *existing* BOM Creator — don't build a parallel tool.**
  Maintainers accept improvements to what already exists; a second competing
  doctype invites "why not just improve BOM Creator?". The standalone app
  achieves this via override hooks (see below).
- **Complementary primary path, not a replacement and not exclusive.** BOM stays
  the single source of truth; direct BOM creation still works (Work Orders,
  subcontracting, MRP and the API depend on it). Exclusivity, if ever wanted,
  is an org-level deployment choice — never baked into the app.
- **Two-layer flow.** *Layer 1 — Structure:* map the multi-level skeleton
  (items, qty, UOM, which nodes are sub-assemblies, reuse of existing BOMs).
  *Layer 2 — Detail:* decorate each node (operations, by-products, scrap/process
  loss, QC, warehouses, alternatives, costing) before generating.
- **Generates 100% standard BOM documents** — indistinguishable from hand-made
  ones; nothing downstream needs to change.

## Gaps addressed

Verified against source (`erpnext/manufacturing/doctype/bom_creator/`). Brief,
template-ready drafts and the duplicate-check live in
[`docs/UPSTREAM_ISSUES.md`](docs/UPSTREAM_ISSUES.md).

| # | Gap | Type | Upstream status |
|---|-----|------|-----------------|
| 1 | Line UOM / conversion factor locked to stock UOM & factor `1` (needs **no** schema change) | Feature | Not filed |
| 2 | Output always submitted; no Draft option | Feature | Not filed |
| 3 | Every generated BOM forced to `is_default`, silently superseding existing defaults | Feature | Not filed |
| 4 | Sub-assembly raw materials not fetched from an existing default BOM | Feature | [#42932](https://github.com/frappe/erpnext/issues/42932) |
| 5 | Cannot reuse / link an existing BOM as an explodable node | Feature | [#38438](https://github.com/frappe/erpnext/issues/38438) |
| 6 | Cannot import an existing submitted BOM back into the tool for editing | Feature | Adjacent: [#38395](https://github.com/frappe/erpnext/issues/38395) |
| 7 | No entry point from the BOM list / new-BOM form | Feature | Not filed |
| 8 | Tree view cluttered; no level-based grouping/collapse | UX | Not filed |
| 9 | Dead fields: client writes non-existent `bom_no`; `default_warehouse` never consumed | Bug | Not filed |
| — | Operations/routing costing surface missing | Feature | [#44094](https://github.com/frappe/erpnext/issues/44094), [#40529](https://github.com/frappe/erpnext/issues/40529), [#48154](https://github.com/frappe/erpnext/issues/48154) |

## How it's built (standalone mode)

The app injects into the existing BOM Creator without forking erpnext:

- `override_doctype_class` — extend the BOM Creator controller.
- `override_whitelisted_methods` — fix `add_item` / `add_sub_assembly` /
  `create_bom` (UOM/conversion, draft, default control, reuse).
- `doctype_js` / bundle override — the improved tree UI and dialogs.
- BOM listview / form hooks — the missing entry points.

Each override is organized to mirror the upstream file it changes, so the merge
diff stays small.

## Upstream engagement

Forum-first, per ERPNext's contribution guidelines:

1. Gauge maintainer appetite on the community forum — draft in
   [`docs/FORUM_POST.md`](docs/FORUM_POST.md).
2. File the concrete, **brief**, separately-scoped issues (cross-linked to each
   other and to related existing issues), each offering a PR —
   [`docs/UPSTREAM_ISSUES.md`](docs/UPSTREAM_ISSUES.md).
3. Green signal = a maintainer says "PR welcome"; silence = build standalone
   anyway, keeping every change merge-shaped.

## Environment

| Item | Value |
|------|-------|
| Target | Frappe/ERPNext **v16** (16.21.1) on a bench with ERPNext installed |
| Frappe app module | `new_bom_creator` |
| Approach | override + extend the existing `BOM Creator` doctype |
| Dedicated local test site | e.g. `bomcreator.localhost` (frappe + erpnext + this app only) |
| License | GPL-3.0-or-later |

## Status

Planning. No app code yet — this repo holds the phased plan, the upstream-issue
drafts, and the forum post. The phase-by-phase detail in
[`PHASED_PLAN.md`](PHASED_PLAN.md) is being revised to the agreed
"improve existing BOM Creator + two-layer" direction. Frappe Cloud deployment is
out of scope.
