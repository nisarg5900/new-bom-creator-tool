# Forum post draft — gauge maintainer appetite

**Where:** https://discuss.frappe.io/c/erpnext/6 (Manufacturing)
**Goal:** find out whether the maintainers see these BOM Creator gaps as worth
closing and would welcome PRs — before investing in the build. This is the
sanctioned venue for "is this on your radar" (the issue tracker is not).

> Paste the body below and add screenshots/GIFs where noted. Repo:
> https://github.com/nisarg5900/new-bom-creator-tool
> **Before posting:** flip the repo to public (it is currently private) — the
> forum post links to it. If you'd rather not, remove the repo URL from the
> body.

---

**Title:** Improving the Multi-level BOM Creator — a set of gaps + willingness to contribute PRs

**Body:**

Hi all,

I've been using the Multi-level BOM Creator for real multi-level BOMs (moulded
parts with polymer raw materials) and hit a consistent set of gaps. I've written
up a design + phased plan and I'm willing to contribute the work as PRs — but
before investing, I'd like to check whether the team sees these as in-scope and
would accept PRs for them.

The gaps (each verified against `erpnext/manufacturing/doctype/bom_creator/` on
v16 / 16.21.1):

- **Per-line UOM / conversion factor.** Lines are locked to the item's stock UOM
  with `conversion_factor = 1`; there's no UOM column in the sub-assembly dialog
  and no `get_conversion_factor()` call. Entering e.g. 2.5 g of a Kg-stock
  polymer isn't possible cleanly. *(Notably, the `uom`/`conversion_factor`/
  `stock_qty` fields already exist on `BOM Creator Item`, so this looks like a
  small logic-only fix.)*
- **Always submits; no Draft option.** `create_bom()` always `submit()`s.
- **Forced default.** Every generated BOM (including each sub-assembly) becomes
  `is_default`, silently superseding existing defaults, with no opt-out.
- **No round-trip / import** of an existing BOM back into the tool for editing.
- **Discovery:** no entry point from the BOM list or new-BOM form.
- **Tree legibility:** the generic tree gets hard to scan for deep assemblies —
  no level grouping / collapse-by-depth. *(mockup below)*
- Two minor dead fields (`bom_no` write target that doesn't exist;
  `default_warehouse` never consumed).

I've also found existing related issues and would cross-link rather than
duplicate: fetching a sub-assembly's BOM (#42932), reusing/linking existing BOMs
(#38438), operations support (#44094 / #40529 / #48154), in-place item switching
(#38395).

My intended approach keeps everything producing standard `BOM` documents and
improves the existing BOM Creator (not a parallel tool), so each item can be a
small, self-contained PR. Full write-up and phased plan here:
**https://github.com/nisarg5900/new-bom-creator-tool**.

### Questions for the maintainers

1. Are any of these already on the roadmap?
2. Which would you consider in-scope for PRs to core?
3. Any you'd prefer to see as a separate app rather than in core?

### Questions for everyone using BOM Creator in production

I want to make sure I'm not building around only my own workflow. Please
chime in:

- **Which of these hits you the hardest?** Helps me prioritise the PR order.
- **What am I missing?** Any gap not on this list — bugs, feature requests,
  edge cases in costing / subcontracting / variants / process loss / print
  output / batch qty / alternative items / by-products / operations that
  BOM Creator handles poorly.
- **UX ideas for the tree view.** Expand-to-level? Colour or icon by depth?
  A cost overlay per node? Something else?
- **Two-layer workflow feedback.** I'm proposing *Structure* first (tree +
  qty/UOM + sub-assembly reuse), *Detail* second (operations, warehouses,
  alternates, by-products, active/default) — over the same tree, not a modal
  wizard. Does that match how you actually build BOMs?
- **Anything you've already worked around locally** with client scripts /
  custom apps — I'd rather learn from your patches than reinvent them.

Happy to start with the smallest, lowest-risk ones (the UOM fix and the
dead-field cleanup). Thanks!

*(Attaching a screenshot of a real 3-level BOM tree to illustrate the
legibility point.)*
