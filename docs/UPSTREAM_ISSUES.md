# Upstream ERPNext issue drafts — BOM Creator gaps

Brief, template-conforming drafts for `frappe/erpnext`, following ERPNext's
`CONTRIBUTING.md` (report each issue **separately**; be **brief**; use bullets +
screenshots). Verified against **ERPNext 16.21.1**.

**Sequencing:** forum-first (see [`FORUM_POST.md`](FORUM_POST.md)). File these
only after gauging appetite, then cross-link them to each other and to the
related existing issues. Each carries a **PR offer** — that, not the request
itself, is what generates a green signal (ERPNext states most feature requests
won't be actioned by the core team).

> Replace `#___` cross-links with real numbers once filed. Add screenshots/GIFs
> before posting — maintainers weight these heavily.

---

## BUG 1 — dead fields `bom_no` and `default_warehouse`
*(bug_report template)*

**Title:** `BOM Creator: two dead fields — client writes non-existent bom_no; default_warehouse never used`

**Steps to reproduce / evidence:**
- In `bom_creator.js`, the `do_not_explode` handler calls
  `frappe.model.set_value(cdt, cdn, "bom_no", …)`, but `BOM Creator Item` has no
  `bom_no` field → silent no-op.
- `BOM Creator.default_warehouse` is never read in `create_boms()` / `create_bom()`
  (nor in `BOM_FIELDS`) → setting it has no effect on the generated BOM.

**Expected:** wire both up (store `bom_no`; propagate `default_warehouse` to the
BOM's source/target warehouse) or remove them.

**Version:** 16.21.1 (also v15). **Module:** manufacturing.
**Related:** BUG 2 below (same tool). *Willing to submit a PR.*

---

## BUG 2 — cleanup accompanying the UOM fix *(optional, fold into FEAT 1)*

Kept as a note: the dead-field cleanup can ship in the same PR as FEAT 1 if
maintainers prefer fewer PRs. Otherwise file BUG 1 standalone.

---

## FEAT 1 — per-line UOM & conversion factor (needs no schema change)
*(feature_request template)*

**Title:** `BOM Creator: allow per-line UOM with correct conversion factor (currently locked to stock UOM)`

**Problem:**
- `add_item()` / `add_sub_assembly()` hardcode `uom = stock_uom`,
  `conversion_factor = 1`; the sub-assembly dialog has no UOM column.
- No call to `get_conversion_factor()` anywhere in the tool.
- Example: a moulded part uses **2.5 g** of a polymer whose stock UOM is **Kg** —
  only enterable as 0.0025 Kg, error-prone. The standard BOM form handles this;
  BOM Creator does not.

**Solution:** make line UOM editable (and add it to the dialog); on change call
`get_conversion_factor(item_code, uom)` and recompute `stock_qty`. The
`uom`/`conversion_factor`/`stock_qty` fields **already exist** on `BOM Creator
Item`, so **no schema change** is required — smallest possible PR.

**Version:** 16.21.1. **Module:** manufacturing.
**Related:** BUG 1 (dead-field cleanup can ride along). *Willing to submit a PR.*

---

## FEAT 2 — Draft output + is_default / is_active control
*(feature_request template)*

**Title:** `BOM Creator: allow Draft BOMs and control is_default/is_active (currently always submits and overrides the default)`

**Problem:**
- `create_bom()` always `submit()`s — no Draft option.
- `is_default` isn't exposed, so every generated BOM (including **each
  sub-assembly**, because the whole tree is walked) becomes the new default,
  silently superseding existing defaults.

**Solution:** an output mode (Draft / Submit); per-FG *Set as Default* (off when
a default already exists) and *Is Active*; a pre-generation dry-run summary
listing which items' defaults would be replaced.

**Version:** 16.21.1. **Module:** manufacturing. *Willing to submit a PR.*

---

## FEAT 3 — import an existing BOM into BOM Creator for editing
*(feature_request template)*

**Title:** `BOM Creator: import an existing (submitted) BOM tree back into the tool for editing`

**Problem:** the tool is one-directional (`create_bom()` always `new_doc("BOM")`);
you can't load an existing BOM to tweak a multi-level structure.

**Solution:** an *Import from BOM* action that reconstructs the tree from a
submitted BOM + its child `bom_no`s; on regenerate, route through the existing
cancel-and-amend versioning (never blind-duplicate a BOM number).

**Version:** 16.21.1. **Module:** manufacturing.
**Related:** [#38395](https://github.com/frappe/erpnext/issues/38395) (in-place
item switch — adjacent). *Willing to submit a PR.*

---

## FEAT 4 — entry points from the BOM list / new-BOM form
*(feature_request template)*

**Title:** `BOM Creator: add entry points from the BOM list and the new-BOM form`

**Problem:** `bom_list.js` and `bom_creator_list.js` have no cross-links; the
tool is hard to discover.

**Solution:** a "Create via BOM Creator" button on the BOM list; a "Switch to
BOM Creator" action on a blank BOM form; optional workspace card.

**Version:** 16.21.1. **Module:** manufacturing. *Willing to submit a PR.*

---

## UX 1 — tree view legibility & level-based grouping
*(feature_request template)*

**Title:** `BOM Creator: tree view is cluttered — add level-based grouping / collapse-by-depth`

**Problem:** the tree uses the generic account-tree widget — no level
distinction, no collapse/expand by depth; multi-level assemblies are hard to scan.

**Solution:** auto-computed level badges, indent/colour per level, expand-to-level
control, per-node qty + UOM + level. *(Attach a mockup.)*

**Version:** 16.21.1. **Module:** manufacturing. *Willing to submit a PR.*

---

## Duplicate check (run 2026-07-03, `gh search --repo frappe/erpnext`)

**Already open — 👍 / comment instead of re-filing, and cross-link from ours:**

| Topic | Existing issue |
|-------|----------------|
| Sub-assembly BOM not fetched automatically | [#42932](https://github.com/frappe/erpnext/issues/42932) |
| Link / reuse existing BOMs in the tree | [#38438](https://github.com/frappe/erpnext/issues/38438) |
| Operations support in BOM Creator | [#44094](https://github.com/frappe/erpnext/issues/44094), [#40529](https://github.com/frappe/erpnext/issues/40529), [#48154](https://github.com/frappe/erpnext/issues/48154) |
| Switch items in-place after duplicate | [#38395](https://github.com/frappe/erpnext/issues/38395) |

**Known bugs already filed (context for our regression tests):** #49746, #48006,
#48007, #38532, #41617, #52149, #37953, #43948, #48538.

**No existing issue (drafts above):** UOM/conversion, draft-vs-submit,
forced-default/supersede, import-for-editing, navigation, tree legibility,
dead fields.
