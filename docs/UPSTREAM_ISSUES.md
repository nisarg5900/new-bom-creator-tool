# Upstream ERPNext issue drafts — BOM Creator gaps

Ready-to-paste drafts for `frappe/erpnext`. Verified against **ERPNext 16.21.1**
(`erpnext/manufacturing/doctype/bom_creator/`).

**Do not post blindly** — a duplicate check was run on 2026-07-03 (see the
"Duplicate check" section at the end). Items already tracked upstream are listed
there; upvote/comment on those instead of re-filing.

Drafts below are the ones with **no existing upstream issue**:

- [Issue A — Bug: two dead fields](#issue-a--bug-dead-fields-bom_no-and-default_warehouse)
- [Issue B — Feature: line UOM & conversion factor](#issue-b--feature-per-line-uom--conversion-factor)
- [Issue C — Feature: Draft output + default/active control](#issue-c--feature-draft-output--is_default--is_active-control)
- [Issue D — Feature: navigation entry points](#issue-d--feature-entry-points-from-bom-list--new-bom)
- [Issue E — UX: tree view legibility & level grouping](#issue-e--ux-tree-view-legibility--level-based-grouping)
- [Issue F — Feature: import existing BOM for editing](#issue-f--feature-import-an-existing-bom-into-bom-creator-for-editing)

---

## Issue A — Bug: dead fields `bom_no` and `default_warehouse`

**Title:** `BOM Creator: two dead fields — client writes to non-existent bom_no, and default_warehouse is never used`

**Body:**

### Information about the bug

Two fields in the BOM Creator tool have no effect:

**1. `bom_no` — client writes to a field that doesn't exist on the child table.**
In `bom_creator.js`, the `do_not_explode` handler does:

```js
frappe.model.set_value(cdt, cdn, "bom_no", r.message);
```

But `BOM Creator Item` (`bom_creator_item.json`) has **no `bom_no` field** — its
field list has `item_code, item_name, item_group, fg_item, is_expandable,
sourced_by_supplier, bom_created, is_subcontracted, is_phantom_item, operation,
description, qty, rate, uom, stock_qty, conversion_factor, stock_uom, amount,
base_rate, base_amount, do_not_explode, parent_row_no, fg_reference_id,
instruction`. So the `set_value` (and the `else` branch clearing it) are silent
no-ops. Looks like leftover code from a refactor.

**2. `default_warehouse` — header field never consumed.**
`BOM Creator` has a `default_warehouse` Link field, but it is never read in
`create_boms()` / `create_bom()` (nor mapped in `BOM_FIELDS`). Setting it in the
UI has no effect on the generated BOM's source/target warehouse.

### Expected

Either wire these fields up (fetch/store `bom_no`; propagate `default_warehouse`
to the BOM's `default_source_warehouse`/`default_target_warehouse`) or remove
them to avoid confusion.

### Version
ERPNext 16.21.1 (also present in v15).

### Module
manufacturing

---

## Issue B — Feature: per-line UOM & conversion factor

**Title:** `BOM Creator: allow per-line UOM with correct conversion factor (currently locked to stock UOM)`

**Body:**

### Is your feature request related to a problem?

BOM Creator forces every line to the item's **stock UOM** with
**conversion_factor = 1**, and provides no way to enter a component in a
different UOM.

In `bom_creator.py`, both `add_item()` and `add_sub_assembly()` hardcode:

```python
kwargs.update({
    "uom": item_info.stock_uom,
    "stock_uom": item_info.stock_uom,
    "conversion_factor": 1,
})
```

The "Add Sub Assembly" dialog's Raw Materials grid only exposes `item_code` and
`qty` — there is no UOM column at all. There is no call to
`erpnext.stock.get_item_details.get_conversion_factor()` anywhere in the file.

**Concrete case:** an injection-moulded part uses **2.5 g** of a polymer whose
stock UOM is **Kg**. In BOM Creator you can only enter the quantity in Kg
(0.0025), which is awkward and error-prone. The standard BOM form handles this
correctly — changing a line's UOM calls `get_conversion_factor()` and recomputes
`stock_qty` — but BOM Creator does not.

### Describe the solution you'd like

- Make the line **UOM** editable in BOM Creator (and add a UOM column to the
  sub-assembly Raw Materials dialog).
- On UOM change, look up the factor via `get_conversion_factor(item_code, uom)`
  against the item's UOM Conversion table and recompute
  `stock_qty = qty × conversion_factor` — mirroring standard BOM behaviour.
- Carry the chosen `uom` / `conversion_factor` / `stock_qty` into the generated
  BOM line (standard BOM already honours these).

### Version
ERPNext 16.21.1

### Module
manufacturing

---

## Issue C — Feature: Draft output + is_default / is_active control

**Title:** `BOM Creator: allow generating Draft BOMs and control is_default/is_active (currently always submits and overrides the default)`

**Body:**

### Is your feature request related to a problem?

BOM Creator's "Create Multi-level BOM" action is irreversible and opinionated in
two ways:

**1. Always submits.** `create_bom()` ends with:

```python
bom.save(ignore_permissions=True)
bom.submit()
```

There is no option to leave the generated BOMs as **Draft** for review before
submission.

**2. Always becomes the default, for every node.** `is_default` is not part of
`BOM_FIELDS` and is not exposed anywhere in the tool, so every generated BOM
takes the doctype default `is_default = 1`. Because `create_boms()` walks the
**entire** reverse tree and calls `create_bom()` for every expandable node,
**each sub-assembly** also becomes the new default — silently superseding any
previously established default BOM for that item, with no warning.

For users who maintain multiple BOMs per item (versions, alternates), this
overwrites their default set-up unexpectedly.

### Describe the solution you'd like

- An **output mode**: *Draft* (docstatus 0) vs *Submit*.
- A per-finished-good **Set as Default** control (defaulting to *off* when a
  default BOM already exists for that item) and an **Is Active** control.
- Before generation, a **dry-run summary**: "N BOMs will be created; these items
  already have a default that will be replaced: …", requiring confirmation.

### Version
ERPNext 16.21.1

### Module
manufacturing

---

## Issue D — Feature: entry points from BOM list / new BOM

**Title:** `BOM Creator: add entry points from the BOM list and the new-BOM form`

**Body:**

### Is your feature request related to a problem?

BOM Creator and BOM are disconnected in the UI. `bom_list.js` and
`bom_creator_list.js` contain no cross-links: there is no way to launch BOM
Creator from the **BOM list** toolbar, and no "switch to the wizard" affordance
from a blank **new BOM** form. New users rarely discover the tool exists.

### Describe the solution you'd like

- A **"Create via BOM Creator"** button on the BOM list view.
- A **"Switch to BOM Creator"** action on a new/blank BOM form.
- (Optional) a workspace shortcut card under Manufacturing.

### Version
ERPNext 16.21.1

### Module
manufacturing

---

## Issue E — UX: tree view legibility & level-based grouping

**Title:** `BOM Creator: tree view is cluttered — add level-based grouping / collapse-by-depth`

**Body:**

### Is your feature request related to a problem?

The BOM Creator tree uses the generic `frappe.views.trees["BOM Configurator"]`
widget (the same one used for Account / Item Group trees), with no BOM-specific
affordances. For multi-level assemblies it becomes hard to scan: there is no
visual level distinction and no way to collapse or expand by depth.

### Describe the solution you'd like

- Auto-computed **level numbers** (depth from the root FG), shown as badges.
- Visual level distinction (indent / colour per level).
- **Collapse / expand by level** ("expand to level N"), with levels derived
  automatically from the number of sub-assembly tiers.
- Per-node display of qty + UOM + level.

### Version
ERPNext 16.21.1

### Module
manufacturing

---

## Issue F — Feature: import an existing BOM into BOM Creator for editing

**Title:** `BOM Creator: allow importing an existing (submitted) BOM tree back into the tool for editing`

**Body:**

### Is your feature request related to a problem?

BOM Creator is one-directional: it generates BOMs but cannot **load an existing
BOM** back in for further editing. `create_bom()` always does
`frappe.new_doc("BOM")`, so there is no round-trip. If you need to tweak a
multi-level structure you previously built, you must rebuild the tree from
scratch. (Related but distinct from
[#38395](https://github.com/frappe/erpnext/issues/38395), which asks for
in-place item switching within the tool.)

### Describe the solution you'd like

- An **Import from BOM** action that reconstructs a BOM Creator tree from a
  submitted BOM and its child `bom_no`s.
- On regeneration, route through the existing **cancel-and-amend versioning**
  path (the mechanism `manage_default_bom` already relies on) so a new BOM
  **version** is produced — rather than blindly minting a duplicate BOM number
  or clobbering defaults.

### Version
ERPNext 16.21.1

### Module
manufacturing

---

## Duplicate check (run 2026-07-03, `gh search issues --repo frappe/erpnext`)

**Already open upstream — upvote/comment instead of re-filing:**

| Topic | Existing issue |
|-------|----------------|
| Sub-assembly BOM not fetched automatically (fetch RM) | [#42932](https://github.com/frappe/erpnext/issues/42932) |
| Link / reuse existing BOMs in the tree | [#38438](https://github.com/frappe/erpnext/issues/38438) |
| Operations support in BOM Creator | [#44094](https://github.com/frappe/erpnext/issues/44094), [#40529](https://github.com/frappe/erpnext/issues/40529), [#48154](https://github.com/frappe/erpnext/issues/48154) |
| Switch items in-place after duplicate | [#38395](https://github.com/frappe/erpnext/issues/38395) |

**Known bugs already filed (context for our regression tests):** #49746 (reuse
KeyError), #48006/#48007/#38532 (duplicate / multi-branch items), #41617
(parent-qty cost), #52149 (sub-assembly cost), #37953 (precision), #43948/#48538
(parent_row_no integrity).

**No existing issue found (drafts A–F above):** UOM/conversion factor,
draft-vs-submit, forced-default/supersede, navigation entry points, tree-view
legibility, dead fields, import-for-editing.
