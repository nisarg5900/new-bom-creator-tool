# New BOM Creator Tool

An improved BOM Creator for ERPNext — closing the gaps in the built-in
*Multi-level BOM Creator* while keeping the generated BOMs 100% standard.

> **ERPNext v16** (verified against 16.21.1+). License: **GPLv3**.

## What it does

The app enhances the existing `BOM Creator` doctype via Frappe hooks — no
parallel doctype, no data-model changes. Every generated BOM is a standard
`BOM` document that works with Work Orders, MRP, subcontracting, and
everything else in ERPNext.

### Features

| Area | What changes |
|------|-------------|
| **UOM & conversion** | Per-line UOM selection with strict item-specific conversion factors. No more silent `cf=1` for unmapped UOMs. |
| **Draft / default control** | Choose Draft or Submitted output. Opt in/out of setting the generated BOM as default. Active/inactive flag. Supersede-preview dialog warns before replacing existing defaults. |
| **Import from BOM** | Reconstruct a BOM Creator tree from any existing submitted BOM for editing. |
| **Sub-assembly reuse** | Auto-populate raw materials from an item's default BOM. Link an existing BOM as-is instead of generating a new one. |
| **Navigation** | "Create via BOM Creator" button on BOM list. "Switch to BOM Creator" on new BOM forms. Workspace shortcut in Manufacturing. |
| **Tree legibility** | Colour-coded level badges (L0–L4+). Left-border depth indicator. Expand-to-level bar (1–5, All). |
| **Layer 2 fields** | Warehouses, inspection, backflush, operations (transfer_material_against, fg_based_operating_cost), process loss, per-item source warehouse / alternative item / include-in-manufacturing — all carried through to the generated BOM. |
| **Labour charges** | Quick-add toolbar button for service items (non-stock, piece-rate labour). |
| **Dead-field cleanup** | Hides the unused `default_warehouse` field that core never consumes. |

### Two-layer workflow

- **Layer 1 — Structure.** FG item, qty, UOM, component tree, sub-assemblies.
- **Layer 2 — Detail.** Operations, warehouses, quality, process loss,
  per-item overrides.

Structure first, detail second — two passes over the same tree.

## Installation

```bash
# On an existing ERPNext v16 bench
bench get-app --branch main https://github.com/nisarg5900/new-bom-creator-tool
bench --site <your-site> install-app new_bom_creator
```

The app requires ERPNext (`required_apps = ["erpnext"]`). On install it adds
a "BOM Creator" shortcut to the Manufacturing workspace.

## Compatibility

| Dependency | Version |
|------------|---------|
| Frappe     | v16     |
| ERPNext    | v16 (16.21.1 – 16.26.x+) |
| Python     | 3.12+   |

The app handles both the pre-16.26.2 module-function call path and the
post-16.26.2 instance-method call path for `add_item` / `add_sub_assembly`.

## How it works

All changes are applied via Frappe's hook system — no core patches required:

- `override_doctype_class` — subclasses `BOMCreator` for `create_bom` and
  method overrides.
- `override_whitelisted_methods` — intercepts `add_item`,
  `add_sub_assembly`, `import_from_bom`, `get_default_bom_items`.
- `doctype_js` — client-side patches for the BOM Creator tree (UOM column,
  level badges, labour button, supersede preview) and BOM form (switch
  button).
- `doctype_list_js` — BOM list "Create via BOM Creator" action.
- `fixtures` — Property Setter (hide dead field) + Custom Fields (output
  control, Layer 2 fields).
- `after_install` — adds Manufacturing workspace shortcut.

## Upstream fork branches

Each feature is also expressed as a focused branch on
[nisarg5900/erpnext](https://github.com/nisarg5900/erpnext), ready for a
maintainer to PR into `frappe/erpnext`:

| Branch | Scope |
|--------|-------|
| `nbc/1-dead-fields` | Remove unused `default_warehouse` and dead `bom_no` client write |
| `nbc/2-uom-conversion` | Per-line UOM with strict conversion |
| `nbc/3-draft-and-default` | Draft output, is_default/is_active control, supersede preview |
| `nbc/4-import-from-bom` | Import existing BOM into BOM Creator |
| `nbc/5-sub-assembly-reuse` | Fetch RM from default BOM + link BOM as-is |
| `nbc/6-navigation` | Entry points from BOM list/form + workspace shortcut |
| `nbc/7-tree-legibility` | Level badges, depth borders, expand-to-level |
| `nbc/8-layer2-fields` | Warehouses, inspection, backflush, per-item fields |
| `nbc/8-layer2-ops-labour` | Operations, process loss, labour charges |

## Tests

```bash
bench --site <your-site> run-tests --app new_bom_creator
```

56 tests covering: hook wiring, UOM conversion (happy + error paths), draft
output, default/active control, supersede preview, import-from-BOM, linked
BOM reuse, navigation hooks, tree level computation, Layer 2 field
carry-through (header + per-item + fetch_from bypass), operations,
process loss, labour charges JS, and end-to-end BOM generation integration.

## License

GPLv3 — same as ERPNext.
