# New BOM Creator Tool — Phased Development Plan

Verified against **ERPNext 16.21.1** (v16 bench with ERPNext installed).

This plan builds `new_bom_creator` — a GPL-3.0 app that **improves the existing
ERPNext BOM Creator** so it can generate and edit standard `BOM` documents
without the current gaps. Dual-target: shippable standalone **and** shaped so
each change can be offered upstream as a PR. It does not fork erpnext core.

> **Revision note:** the phase detail below predates two decisions now agreed and
> is being revised to match them: (a) **improve the existing BOM Creator via
> override hooks** rather than a parallel `BOM Builder` doctype, and (b) a
> **two-layer** flow (Layer 1 structure → Layer 2 detail). The architecture and
> conventions sections already reflect the new direction; individual phases will
> be restructured next.

---

## Architecture at a glance

```
┌─────────────────────────────────────────────────────────────┐
│  new_bom_creator (this app)   depends on → erpnext           │
│                                                              │
│  Overrides the existing BOM Creator (no fork), via hooks:    │
│   • override_doctype_class ........ extend the controller    │
│   • override_whitelisted_methods .. add_item / add_sub_...   │
│   • doctype_js / bundle override .. improved tree + dialogs  │
│   • BOM listview / form hooks ..... missing entry points     │
│                                                              │
│  Layer 1 (structure)  →  Layer 2 (detail)  →  standard BOM   │
└─────────────────────────────────────────────────────────────┘
```

**Key principle:** every improvement is a small, self-contained change to BOM
Creator's real behaviour — **one fix = one unit = one potential upstream PR** —
and the output is always a 100%-standard `BOM`.

**Why improve BOM Creator instead of a parallel doctype?** For upstream-merge
viability. Maintainers accept improvements to the tool that exists; a second
competing doctype invites rejection. In standalone mode we express those
improvements through erpnext's override hooks, so each override maps ~1:1 onto an
edit of BOM Creator's upstream files and the merge diff stays small.

---

## Conventions

- **App module:** `new_bom_creator`  •  **License:** GPL-3.0-or-later.
- **Approach:** override + extend the existing `BOM Creator`; any new fields via
  fixtures use the `nbc_` prefix and are kept minimal (translation cost at merge
  = fixtures → native json fields).
- **Match erpnext conventions** — its ruff/eslint/prettier config, `FrappeTestCase`
  tests, conventional commits, no new heavy dependencies.
- **One fix = one unit = one potential PR.** Keep app-only concerns (install,
  workspace, branding) in a thin layer that's droppable at merge time.
- **Test site:** a dedicated local site (e.g. `bomcreator.localhost`) with
  frappe + erpnext + this app only — one dedicated site per app; never shared
  with unrelated apps.
- Every phase has a **Definition of Done** and a **Test Gate**. A phase is not
  complete until its automated tests pass on the test site.

---

## Phase 0 — Scaffold, test site & CI

**Goal:** installable app, isolated test site, green smoke test.

Tasks:
- `bench new-app new_bom_creator` (module `new_bom_creator`).
- Declare erpnext dependency in `hooks.py` (`required_apps = ["erpnext"]`).
- Create dedicated site:
  `bench new-site bomcreator.localhost --admin-password admin --mariadb-root-password admin </dev/null`
  then `bench --site bomcreator.localhost install-app erpnext new_bom_creator </dev/null`.
- `.pre-commit-config.yaml` (ruff + prettier, mirroring frappe/erpnext).
- Optional GitHub Actions: spin bench + erpnext, run `bench run-tests --app new_bom_creator`.

**Definition of Done:** app installs on a fresh site with erpnext present; site
migrates cleanly.

**Test Gate (smoke):**
- `test_app_installs` — module importable, hooks load.
- `bench --site bomcreator.localhost migrate` exits 0.

---

## Phase 1 — Data model + standard-BOM generation (parity baseline)

**Goal:** reproduce core BOM Creator's output for simple & multi-level trees,
through our own generator, with the known core bugs pre-covered by tests.

Tasks:
- DocType **BOM Builder** (header: item, qty, uom, company, currency,
  rm_cost_as_per, buying_price_list, project, status, output_mode placeholder).
- DocType **BOM Builder Item** (child: item_code, fg_item, qty, uom, stock_qty,
  conversion_factor, stock_uom, rate, amount, operation, is_expandable,
  parent_row_no, fg_reference_id, is_phantom_item — mirror of `BOM Creator Item`
  plus room for later fields).
- `generate_boms()` — port core's reverse-tree walk (`create_boms`/`create_bom`)
  that builds one `BOM` per expandable node, links child `bom_no`s, and submits.

**Definition of Done:** a builder tree produces the same BOM set a hand-build
would, for 1-level and N-level cases.

**Test Gate (integration):**
- `test_single_level_generates_one_bom`.
- `test_multi_level_links_child_boms` — parent BOM line `bom_no` points at child.
- `test_reused_subassembly_no_keyerror` — regression for core
  [#49746](https://github.com/frappe/erpnext/issues/49746) (same sub-assembly
  under two branches).
- `test_duplicate_item_guard` — regression for [#48006](https://github.com/frappe/erpnext/issues/48006).

---

## Phase 2 — UOM & conversion factor (headline gap #1)

**Goal:** per-line UOM independent of stock UOM, with correct conversion.

Tasks:
- Make line `uom` editable; on change call
  `erpnext.stock.get_item_details.get_conversion_factor(item_code, uom)` and set
  `conversion_factor`, then recompute `stock_qty = qty * conversion_factor`.
- Sub-assembly / raw-material entry dialog gains a **UOM** column (core omits it).
- Generator carries `uom` + `conversion_factor` + `stock_qty` onto the BOM line
  (standard BOM already honours these via `get_bom_material_detail`).
- Guard: UOM must exist in the item's UOM Conversion table, else clear error.

**Definition of Done:** entering "2.5 g" of a kg-stock polymer yields
`conversion_factor = 0.001`, `stock_qty = 0.0025 kg`, and the generated BOM line
matches.

**Test Gate:**
- `test_gram_of_kg_item_conversion` — factor & stock_qty correct.
- `test_generated_bom_line_carries_uom` — BOM line uom/cf/stock_qty correct.
- `test_costing_uses_stock_qty` — RM cost = valuation × stock_qty (not qty).
- `test_uom_not_in_conversion_table_errors` — friendly failure.

---

## Phase 3 — Draft output + default/active control (gaps #2, #3)

**Goal:** stop forcing submit-and-default; make the destructive action explicit.

Tasks:
- Header **Output Mode**: `Draft` (docstatus 0) vs `Submit` (docstatus 1).
- Per-FG **Set as Default** (default off when a default already exists) and
  **Is Active** controls; pass through to generated BOM (core hardcodes neither
  reachable).
- **Supersede preview**: before generating, show a dry-run summary —
  "N BOMs will be created; these items already have a default that will be
  replaced: …" — and require confirmation.

**Definition of Done:** user can produce draft BOMs, and can create a BOM
without disturbing an item's existing default.

**Test Gate:**
- `test_draft_mode_leaves_docstatus_zero`.
- `test_non_default_preserves_existing_default` — prior default untouched.
- `test_supersede_preview_lists_affected_items`.

---

## Phase 4 — Sub-assembly reuse & import (gaps #4, #5, #6)

**Goal:** stop retyping recipes that already exist; enable round-trip editing.

Tasks:
- **Fetch RM from default BOM** when adding a sub-assembly whose item has a
  submitted default BOM — pre-fill the raw-material grid
  (addresses [#42932](https://github.com/frappe/erpnext/issues/42932)).
- **Link existing BOM** as an explodable node without recreating children
  (addresses [#38438](https://github.com/frappe/erpnext/issues/38438)).
- **Import existing BOM tree** into a new BOM Builder for editing. Reconstruct
  the builder tree from a submitted BOM + its child `bom_no`s. On regenerate,
  route through erpnext's cancel-and-amend versioning (the same mechanism
  `manage_default_bom` relies on) — **never** blind-duplicate a new BOM number
  (relevant to [#38395](https://github.com/frappe/erpnext/issues/38395)).

**Definition of Done:** adding an existing sub-assembly auto-loads its RM; an
existing multi-level BOM can be imported, edited, and regenerated as a proper
new version.

**Test Gate:**
- `test_add_subassembly_prefills_from_default_bom`.
- `test_link_existing_bom_as_node_skips_recreation`.
- `test_import_bom_reconstructs_tree`.
- `test_regenerate_creates_new_version_not_orphan_default`.

---

## Phase 5 — Tree UX & level-based view (gap #8)

**Goal:** a legible tree; core reuses the generic account-tree widget with no
BOM-specific affordances.

Tasks:
- Custom tree page with: auto-computed **level numbers** (depth from root),
  level badges, indent/colour by level, collapse/expand **by depth**, and a
  per-node qty + UOM + level label.
- "Expand to level N" control derived from sub-assembly depth.

**Definition of Done:** a 4-level tree is visually scannable and collapsible by
level.

**Test Gate:**
- `test_level_computation` — depth assigned correctly for N-level tree
  (pure-function unit test).
- Manual visual UAT checklist (screenshots in `docs/`).

---

## Phase 6 — Navigation & entry points (gap #7)

**Goal:** discoverable from where users already are.

Tasks:
- Non-invasive `BOM` listview hook (app public JS) adding **"Create via BOM
  Builder"**.
- From a new/blank `BOM` form, a **"Switch to Builder"** action.
- Workspace shortcut + a Manufacturing workspace card.

**Definition of Done:** builder reachable from BOM list, new BOM form, and
workspace without editing erpnext source.

**Test Gate:**
- `test_bom_listview_hook_registered`.
- Manual navigation UAT checklist.

---

## Phase 7 — Costing parity & optional advanced fields

**Goal:** costing matches core BOM for equivalent input; expose high-value
fields the core wizard drops.

Tasks:
- Verify `raw_material_cost`, `rm_cost_as_per`, price-list & valuation paths
  equal a hand-built BOM (regression against core cost bugs).
- Optionally surface: per-line `source_warehouse`, header
  `default_source/target_warehouse` (and remove the dead `default_warehouse`
  concept), `inspection_required`/`quality_inspection_template`, per-line
  `include_item_in_manufacturing` / `allow_alternative_item` overrides.

**Definition of Done:** cost of a generated BOM equals cost of the equivalent
hand-built BOM within precision.

**Test Gate:**
- `test_costing_parity_with_manual_bom`.
- `test_parent_qty_cost_scaling` — regression for [#41617](https://github.com/frappe/erpnext/issues/41617).
- `test_subassembly_cost_rollup` — regression for [#52149](https://github.com/frappe/erpnext/issues/52149).
- `test_precision` — regression for [#37953](https://github.com/frappe/erpnext/issues/37953).

---

## Phase 8 — Packaging, docs & release

**Goal:** shippable v0.1.

Tasks:
- README screenshots, user guide, versioned release notes.
- Test fixtures documented; full regression suite green.
- Manual UAT sign-off checklist across all phases.
- Frappe Cloud bench group / deployment — **deferred; requires explicit
  confirmation** (per workspace rules, must never interfere with the live site).

**Definition of Done:** clean install → full workflow demoable on
`bomcreator.localhost`; all automated tests green; UAT checklist signed.

---

## Testing strategy (cross-cutting)

**Framework:** Frappe's `FrappeTestCase` (unit + integration), run via
`bench --site bomcreator.localhost run-tests --app new_bom_creator`.

**Layers:**
1. **Unit** — pure functions (conversion-factor math, level computation,
   supersede-diff) with no DB.
2. **Integration** — build a BOM Builder tree, call `generate_boms()`, assert on
   the resulting `BOM`/`BOM Item` rows.
3. **Regression-as-tests** — each known core BOM Creator bug is encoded as a
   passing test so our generator can't reintroduce it: #49746 (reuse KeyError),
   #48006 (duplicate items), #41617 (parent-qty cost), #52149 (sub-assembly
   cost), #37953 (precision), #43948/#48538 (parent_row_no integrity).
4. **Manual UAT** — per-phase checklists for the tree UI and navigation, with
   screenshots committed under `docs/`.

**Fixtures (test data):**
- Item `Polycarbonate` — stock UOM `Kg`, UOM conversion `Gram` (factor 1000).
- Item `Moulded Part A` — has a default BOM (for reuse/import tests).
- Item `Assembly A` — multi-level parent.
- A UOM `Gram` and its conversion detail on the polymer item.

**CI (optional but recommended):** GitHub Actions matrix on push/PR — install
frappe + erpnext + this app on a throwaway site, run the full suite. Keeps the
regression net honest as erpnext minor versions move.

---

## Out of scope (for now)

- Operations/routing costing surface — already tracked upstream
  (#44094 / #40529 / #48154); revisit after Phase 7 if still needed.
- Subcontracting BOM entry ([#38520](https://github.com/frappe/erpnext/issues/38520)).
- Frappe Cloud deployment — deferred pending explicit confirmation.
