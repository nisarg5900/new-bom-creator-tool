# New BOM Creator Tool — Phased Development Plan

Verified against **ERPNext 16.21.1**.

---

## North star: dual delivery targets

Every phase produces artifacts that can be **shipped two ways**:

1. **Standalone app** — installed on any ERPNext v16 site, overriding the built-in
   BOM Creator via Frappe's `override_doctype_class`, `override_whitelisted_methods`,
   and `doctype_js` / bundle-override hooks. No fork.
2. **Upstream PR against `frappe/erpnext`** — each hooks-override maps ~1:1 onto
   an edit of the corresponding core file (`bom_creator.py`,
   `bom_creator.js`, `bom_configurator.bundle.js`, `bom_creator.json`, etc.).

Design discipline that keeps both viable:

- **One fix = one self-contained unit = one potential PR.** Small focused PRs
  merge; monolithic rewrites get ignored. Even if the whole vision isn't
  adopted, individual wins land.
- **License: GPLv3 from the first commit** (ERPNext is GPLv3 — any other
  licence is unmergeable).
- **ERPNext conventions**: their ruff/eslint/prettier config, `FrappeTestCase`
  tests, conventional-ish commit style, no new heavy dependencies.
- **Quarantine app-only concerns** (install hooks, workspace card, any
  branding) in a thin `app_shell/` layer that is obviously droppable at merge
  time.
- **Engage maintainers before heavy building.** Forum post →
  gauge appetite → file per-fix issues with a "willing to PR" offer → build.

---

## Design decision: improve the existing BOM Creator (do not build a parallel doctype)

For upstream-merge, the single most important rule is: **maintainers accept
improvements to the thing that already exists; they reject a second competing
tool.** So instead of a new `BOM Builder` doctype:

- Extend `BOM Creator` / `BOM Creator Item` with the small number of new fields
  we need (output mode, per-FG default-control, etc.).
- Override the four methods that hold all the bugs — `add_item`,
  `add_sub_assembly`, `create_bom`, `create_boms` — and the tree/dialog JS.
- Everything we generate remains a **standard `BOM` document** (no changes to
  BOM doctype itself).

New fields added by the app follow ERPNext naming (no `nbc_` prefix in the
merge-ready version). The standalone app keeps them non-invasive via
`custom_fields` fixtures so they roll back cleanly on uninstall.

---

## Two-layer workflow (product design)

Same building surface, two conceptual passes users can iterate on independently:

- **Layer 1 — Structure.** Map the skeleton: FG + qty + UOM; the component
  tree; which nodes are sub-assemblies vs raw materials; per-line qty & UOM
  (with correct conversion); reuse an existing sub-assembly's default BOM.
  Output = a validated draft structure.
- **Layer 2 — Detail.** Decorate each node: operations/routing (workstation,
  time, cost), by-products / secondary items, scrap / process loss, QC,
  source/target warehouses, alternative items, per-BOM active/default control.
  Output = submit → standard BOM(s).

The layers are not hard-gated modal steps — they're two toolbars / side-panels
over the same tree. Users can dip into detail mid-structure and back again.

**Positioning against direct BOM creation:** primary path, not exclusive. The
standard BOM form remains available for trivial BOMs, quick one-field edits,
and platform/API flows (Work Orders, subcontracting, MRP, Data Import all
create BOMs directly and must keep working). Entry points from the BOM list /
new-BOM form (Phase 6) make the tool the natural default without blocking the
form.

---

## Conventions

- **App module (standalone):** `new_bom_creator`.
- **Doctype changes:** to `BOM Creator` / `BOM Creator Item` (no parallel doctype).
- **Custom fields (standalone):** shipped via `custom_field` fixtures with the
  same names as the merge-ready version — swap-out at merge time = remove the
  fixture, add the field to the core JSON.
- **Test site:** dedicated `bomcreator.localhost` — one dedicated site per app;
  never shared with unrelated apps.
- **Definition of Done + Test Gate** required per phase.

---

## Phase 0 — Scaffold, test site, override plumbing

**Goal:** installable GPLv3 app that already knows how to override the four
methods and the JS bundle without changing behaviour yet (identity overrides).

Tasks:
- `bench new-app new_bom_creator` (GPLv3 in `license.txt`).
- `hooks.py`: `required_apps = ["erpnext"]`;
  `override_whitelisted_methods` for `add_item`, `add_sub_assembly`; class
  override for `BOMCreator` via `override_doctype_class`; JS override for
  `bom_creator.js` and the `bom_configurator` bundle via `app_include_js`.
- Identity wrappers (call `super()` / re-export the core function) so nothing
  breaks yet — verifies hook plumbing is correct.
- Dedicated test site `bomcreator.localhost` (frappe + erpnext + this app only).
- CI (GitHub Actions) that installs frappe + erpnext + this app on a throwaway
  site and runs `bench run-tests --app new_bom_creator`.

**Definition of Done:** app installs on a fresh site; migrations clean; core
BOM Creator behaviour unchanged.

**Test Gate:**
- `test_app_installs` — module importable, hooks load.
- `test_identity_override_no_behavioural_change` — core `create_bom` still
  produces the same `BOM` as vanilla erpnext for a fixture tree.

---

## Phase 1 — Bug fixes: dead fields *(smallest possible PR; relationship-builder)*

**Goal:** ship the trivial, high-signal cleanup as our first upstream PR to
establish a review relationship before we ask for larger changes.

Scope (maps to `docs/UPSTREAM_ISSUES.md` → BUG 1):
- Remove or wire up `bom_creator.js`'s `set_value(cdt, cdn, "bom_no", …)` call
  (that field doesn't exist on `BOM Creator Item`).
- Remove or wire up header `default_warehouse` (currently never read by
  `create_bom` / `create_boms`).

**Definition of Done:** unused code paths gone or functional; nothing regresses.

**Test Gate:**
- `test_do_not_explode_toggle_no_error` — regression harness for the dead
  set_value.
- `test_default_warehouse_either_propagates_or_absent` — pins whichever
  decision is taken.

**Upstream PR:** small, isolated, easy to review — ideal first contact.

---

## Phase 2 — UOM & conversion factor *(no schema change; smallest feature PR)*

**Goal:** the headline pain point. Line UOM independent of stock UOM, with
correct conversion factor. `uom` / `conversion_factor` / `stock_qty` fields
already exist on `BOM Creator Item`, so **no doctype change**.

Scope (→ FEAT 1):
- Override `add_item()` / `add_sub_assembly()` to stop hardcoding
  `uom = stock_uom` and `conversion_factor = 1`.
- On UOM change (client), call
  `erpnext.stock.get_item_details.get_conversion_factor(item_code, uom)` and
  recompute `stock_qty`.
- Add a **UOM column** to the sub-assembly dialog's Raw Materials grid.
- Friendly error when the chosen UOM isn't in the item's UOM Conversion table.
- Generator carries `uom` / `conversion_factor` / `stock_qty` onto the BOM
  line (standard BOM already honours these).

**Definition of Done:** entering "2.5 g" of a Kg-stock polymer yields
`conversion_factor = 0.001`, `stock_qty = 0.0025 Kg`, and the generated BOM
line matches.

**Test Gate:**
- `test_gram_of_kg_item_conversion` — factor + stock_qty correct.
- `test_generated_bom_line_carries_uom` — BOM line uom/cf/stock_qty correct.
- `test_costing_uses_stock_qty` — RM cost = valuation × stock_qty (not qty).
- `test_uom_not_in_conversion_table_errors` — friendly failure.

**Upstream PR:** clean, no schema change, tightly scoped — good second PR.

---

## Phase 3 — Draft output + is_default / is_active control

**Goal:** stop forcing submit-and-default; make destructive actions explicit.

Scope (→ FEAT 2):
- Add `output_mode` (Draft / Submit) to `BOM Creator`.
- Add per-FG `set_as_default` and `is_active` (defaults respect existing
  defaults; `set_as_default` defaults *off* when a default BOM already exists
  for that item).
- **Supersede preview** before generation: "N BOMs will be created; these
  items already have a default that will be replaced: …", requiring
  confirmation.
- Override `create_bom` to honour these.

**Definition of Done:** user can produce draft BOMs and can create a BOM
without disturbing an existing default.

**Test Gate:**
- `test_draft_mode_leaves_docstatus_zero`.
- `test_non_default_preserves_existing_default`.
- `test_supersede_preview_lists_affected_items`.

**Upstream PR:** adds fields — the biggest schema change, but small in
scope; still isolated.

---

## Phase 4 — Import an existing BOM into BOM Creator for editing

**Goal:** stop the tool from being one-directional.

Scope (→ FEAT 3):
- Server helper that reconstructs a `BOM Creator` tree from a submitted `BOM`
  and its child `bom_no`s.
- Client action **"Import from BOM"** on new `BOM Creator` forms.
- On regenerate: route through ERPNext's existing cancel-and-amend versioning
  (the mechanism `manage_default_bom` relies on) — never blind-duplicate a BOM
  number.

**Definition of Done:** a submitted multi-level BOM can be imported, edited,
and regenerated as a proper new version.

**Test Gate:**
- `test_import_bom_reconstructs_tree` — round-trip preserves qty / uom / hierarchy.
- `test_regenerate_creates_new_version_not_orphan_default`.
- `test_import_of_bom_with_reused_subassembly` — regression for
  [#49746](https://github.com/frappe/erpnext/issues/49746) shape.

**Upstream PR:** larger; may need pre-review discussion on the versioning path.

---

## Phase 5 — Sub-assembly reuse *(coordinates with upstream #42932 / #38438)*

**Goal:** stop retyping recipes that already exist.

Scope:
- **Fetch RM from default BOM** when a sub-assembly item has one — pre-fills
  the Raw Materials grid in the Add Sub Assembly dialog. Coordinates with
  [#42932](https://github.com/frappe/erpnext/issues/42932).
- **Link existing BOM as an explodable node** — skip recreation of its
  children in `create_boms`. Coordinates with
  [#38438](https://github.com/frappe/erpnext/issues/38438).

**Definition of Done:** adding an existing sub-assembly auto-loads its RM; a
linked BOM does not get duplicated on generation.

**Test Gate:**
- `test_add_subassembly_prefills_from_default_bom`.
- `test_link_existing_bom_as_node_skips_recreation`.

**Upstream PR:** contribute directly to the tickets that already exist rather
than filing new ones. Comment on those issues linking our PR.

---

## Phase 6 — Navigation entry points

**Goal:** discoverable from where users already are, without editing erpnext.

Scope (→ FEAT 4):
- Non-invasive `BOM` listview hook (app public JS) → "Create via BOM Creator".
- New/blank `BOM` form → "Switch to BOM Creator" action.
- Optional workspace shortcut card under Manufacturing.

**Definition of Done:** BOM Creator reachable from BOM list, new-BOM form, and
workspace, all without touching erpnext source.

**Test Gate:**
- `test_bom_listview_hook_registered`.
- Manual navigation UAT checklist (screenshots in `docs/`).

**Upstream PR:** trivial JS additions — very small PR.

---

## Phase 7 — Tree view legibility (Layer 1 UX polish)

**Goal:** a legible tree that survives real-world multi-level BOMs.

Confirmed pain from a real 3-level test BOM: parent / child boundaries become
ambiguous when many items share indentation levels, folder-vs-leaf iconography
carries all the semantic weight, and there is no way to focus on a single
depth.

Scope (→ UX 1):
- Auto-computed **level numbers** per node (depth from FG root).
- Level badges + subtle indent/colour distinction per level.
- **Expand / collapse by depth** ("Expand to level N"), N derived from
  the tree's max depth.
- Per-node display: qty + UOM + level chip.

**Definition of Done:** the same 3-level test BOM is visually scannable and
collapsible by level.

**Test Gate:**
- `test_level_computation` — depth assigned correctly for N-level tree (pure
  function unit test).
- Manual visual UAT — screenshots in `docs/` (before/after).

**Note:** the standard `BOM` doctype has its **own** read-only tree view
(distinct from BOM Creator's build-time tree). The same level-badge treatment
would help there too, but ship it as a separate follow-up PR against the BOM
tree page — do not bundle.

---

## Phase 8 — Layer 2: operations, warehouses, alternates, by-products
*(optional / advanced; ship as its own PR family after Phase 6)*

**Goal:** decorate nodes with the details currently unreachable through the
wizard. Coordinates with existing upstream tickets.

Scope, prioritised:
1. **Operations table** per FG (workstation, time, cost) — currently BOM
   Creator has only a single `operation` link per row. Coordinates with
   [#44094](https://github.com/frappe/erpnext/issues/44094),
   [#40529](https://github.com/frappe/erpnext/issues/40529),
   [#48154](https://github.com/frappe/erpnext/issues/48154).
2. **Per-line `source_warehouse`** and header
   `default_source_warehouse` / `default_target_warehouse` (fold in the
   `default_warehouse` dead-field decision from Phase 1).
3. **Per-line `include_item_in_manufacturing` / `allow_alternative_item`**
   overrides (both currently hardcoded to `1`).
4. **`inspection_required` / `quality_inspection_template`**.
5. **`backflush_based_on`**.
6. **Secondary items / by-products** and **process loss** — larger scope;
   requires a UI section per FG.

**Definition of Done (per sub-scope):** the field surfaces in Layer 2 and
carries through to the generated BOM identically to a manual BOM entry.

**Test Gate:** per-field integration tests + `test_costing_parity_with_manual_bom`.

**Upstream PRs:** one per sub-scope, filed in the order above (smaller and
less contentious first).

---

## Phase 9 — Packaging, docs, release

- README screenshots (before/after tree, UOM entry, supersede preview).
- User guide + versioned release notes.
- Full regression suite green on CI.
- UAT sign-off checklist.
- Frappe Cloud deployment — **deferred; requires explicit confirmation.**

---

## Testing strategy (cross-cutting)

**Framework:** `FrappeTestCase`, run via
`bench --site bomcreator.localhost run-tests --app new_bom_creator`.

**Layers:**
1. **Unit** — pure functions (conversion math, level computation, supersede
   diff), no DB.
2. **Integration** — build tree, call `create_boms`, assert on the resulting
   `BOM` / `BOM Item` rows.
3. **Regression-as-tests** — every known core bug encoded as a passing test so
   our overrides cannot reintroduce it: #49746 (reuse KeyError), #48006/#48007/
   #38532 (duplicate/multi-branch), #41617 (parent-qty cost), #52149
   (sub-assembly cost), #37953 (precision), #43948/#48538 (parent_row_no
   integrity).
4. **Costing parity** — `test_costing_parity_with_manual_bom` — cost of a
   generated BOM equals cost of an equivalent hand-built BOM within precision.
5. **Manual UAT** — per-phase checklists with screenshots in `docs/`.

**Fixtures:**
- Item `Polycarbonate` — stock UOM `Kg`, UOM conversion `Gram` (factor 1000).
- Item `Moulded Part A` — has a default BOM (for reuse/import tests).
- Item `Assembly A` — multi-level parent (3 levels).
- A UOM `Gram` + its conversion detail on the polymer item.

**CI:** GitHub Actions matrix on push/PR — install frappe + erpnext + this
app on a throwaway site, run the full suite. Keeps the regression net honest
as erpnext minor versions move.

---

## Merge-mode ↔ standalone-mode mapping

For each phase's changes, the app tree records the mapping so upstream
translation is mechanical:

```
new_bom_creator/
├── overrides/            # standalone hooks
│   ├── bom_creator.py    # override class
│   ├── bom_creator.js    # override client script
│   └── bom_configurator_bundle.js
├── fixtures/
│   └── custom_field.json # standalone-only, dropped at merge time
├── app_shell/            # workspace, install hooks — dropped at merge time
└── merge_map.md          # per-file diff summary for each PR
```

`merge_map.md` is maintained as we go; a phase is not complete until its
`merge_map` entry is written.

---

## Out of scope

- Frappe Cloud deployment — deferred pending explicit confirmation.
- Subcontracting BOM entry
  ([#38520](https://github.com/frappe/erpnext/issues/38520)) — track upstream.
- Alternative-item substitution UX beyond the per-line toggle in Phase 8.
