# Changelog

## 1.0.0

Initial release — feature-complete standalone app.

### Features

- **Phase 1 — Dead-field cleanup:** hide unused `default_warehouse`; remove
  dead `bom_no` client write.
- **Phase 2 — UOM & conversion:** per-line UOM with strict item-specific
  conversion factors; UOM column in sub-assembly dialog.
- **Phase 3 — Draft / default control:** `output_mode` (Draft/Submit),
  `set_as_default`, `is_active` per FG; supersede-preview dialog.
- **Phase 4 — Import from BOM:** reconstruct a BOM Creator tree from any
  submitted BOM for editing.
- **Phase 5 — Sub-assembly reuse:** auto-populate RM from default BOM; link
  an existing BOM as-is (skip recreation).
- **Phase 6 — Navigation:** "Create via BOM Creator" on BOM list; "Switch to
  BOM Creator" on new BOM form; Manufacturing workspace shortcut.
- **Phase 7 — Tree legibility:** colour-coded level badges (L0–L4+),
  left-border depth indicator, expand-to-level bar.
- **Phase 8 — Layer 2 fields:** warehouses, inspection, backflush,
  operations (`transfer_material_against`, `fg_based_operating_cost`),
  process loss (`process_loss_percentage`), per-item `source_warehouse` /
  `allow_alternative_item` / `include_item_in_manufacturing`.
- **Phase 8 — Labour charges:** quick-add toolbar button for service items.

### Compatibility

- ERPNext v16 (16.21.1 – 16.26.x+).
- Handles both pre-16.26.2 module-function and post-16.26.2 instance-method
  call paths for `add_item` / `add_sub_assembly`.

### Tests

56 tests covering all phases end-to-end.
