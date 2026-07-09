"""BOM Creator overrides — standalone mirror of the fork branches.

Phase 0: identity plumbing (see git history).
Phase 1: default_warehouse hidden via Property Setter fixture (no code here).
Phase 2 (this file): per-line UOM & conversion factor.

Upstream refactored add_item / add_sub_assembly from module functions
(16.21.1 and earlier) to instance methods on BOMCreator (16.26.2+). We fix
BOTH call paths so the app works across erpnext v16 minor versions:

    - Module wrappers below (via `override_whitelisted_methods`) fire on
      older erpnext where the frontend calls the full dotted path.
    - Instance methods on our BOMCreator subclass (via
      `override_doctype_class`) fire on newer erpnext where the frontend
      calls the short name against the doc.
"""

import frappe
from frappe import _, bold
from frappe.utils import flt, sbool
from erpnext.manufacturing.doctype.bom_creator import bom_creator as _core
from erpnext.manufacturing.doctype.bom_creator.bom_creator import (
	BOMCreator as _CoreBOMCreator,
	get_item_details,
	get_parent_row_no,
)


def _resolve_line_uom(item_code, uom, stock_uom):
	"""Return (resolved_uom, conversion_factor) for a BOM Creator line.

	Strategy — strict, item-specific:
	  - Empty uom → default to stock_uom, cf=1.
	  - uom == stock_uom → cf=1.
	  - Otherwise, look up cf in the item's UOM Conversion Detail table.
	    If not present, throw (do NOT fall back to erpnext's global UOM
	    Conversion Rate, which silently returns cf=1.0 for unmapped UOMs
	    and thus produces silently-wrong stock quantities — this is the
	    exact bug we are fixing).
	"""
	resolved_uom = uom or stock_uom
	if not resolved_uom:
		return None, 1.0
	if resolved_uom == stock_uom:
		return resolved_uom, 1.0

	cf = frappe.db.get_value(
		"UOM Conversion Detail",
		{"parent": item_code, "uom": resolved_uom},
		"conversion_factor",
	)
	cf = flt(cf)
	if not cf:
		frappe.throw(
			_(
				"UOM {0} is not configured for Item {1}. Add it to the item's UOM Conversion table."
			).format(bold(resolved_uom), bold(item_code)),
			title=_("UOM Not Configured"),
		)
	return resolved_uom, cf


def _apply_add_item(doc, kwargs):
	"""Shared add_item logic. Mutates `doc`; returns the saved doc."""
	item_info = get_item_details(kwargs.item_code)

	parent_row_no = ""
	if kwargs.fg_reference_id and doc.name != kwargs.fg_reference_id:
		parent_row_no = get_parent_row_no(doc, kwargs.fg_reference_id)

	resolved_uom, cf = _resolve_line_uom(kwargs.item_code, kwargs.get("uom"), item_info.stock_uom)
	qty = flt(kwargs.get("qty") or 0)
	kwargs.update(
		{
			"uom": resolved_uom,
			"stock_uom": item_info.stock_uom,
			"conversion_factor": cf,
			"stock_qty": qty * cf,
		}
	)

	if parent_row_no:
		kwargs.update({"parent_row_no": parent_row_no})

	doc.append("items", kwargs)
	doc.save()
	return doc


def _apply_add_sub_assembly(doc, kwargs):
	"""Shared add_sub_assembly logic. Mutates `doc`; returns the saved doc."""
	bom_item = frappe.parse_json(kwargs.bom_item)

	name = kwargs.fg_reference_id
	parent_row_no = ""

	if not kwargs.convert_to_sub_assembly:
		item_info = get_item_details(bom_item.item_code)
		parent_row_no = get_parent_row_no(doc, kwargs.fg_reference_id)

		resolved_uom, cf = _resolve_line_uom(
			bom_item.item_code, bom_item.get("uom"), item_info.stock_uom
		)
		qty = flt(bom_item.qty)

		item_row = doc.append(
			"items",
			{
				"item_code": bom_item.item_code,
				"qty": qty,
				"uom": resolved_uom,
				"fg_item": kwargs.fg_item,
				"conversion_factor": cf,
				"parent_row_no": parent_row_no,
				"fg_reference_id": name,
				"stock_qty": qty * cf,
				"do_not_explode": 1,
				"is_expandable": 1,
				"stock_uom": item_info.stock_uom,
				"operation": bom_item.operation,
				"is_phantom_item": sbool(kwargs.phantom),
			},
		)

		parent_row_no = item_row.idx
		name = ""
	else:
		if sbool(kwargs.phantom):
			parent_row = next(item for item in doc.items if item.name == kwargs.fg_reference_id)
			parent_row.is_phantom_item = 1
		parent_row_no = get_parent_row_no(doc, kwargs.fg_reference_id)

	for row in bom_item.get("items") or []:
		row = frappe._dict(row)
		item_info = get_item_details(row.item_code)
		resolved_uom, cf = _resolve_line_uom(row.item_code, row.get("uom"), item_info.stock_uom)
		qty = flt(row.qty)
		doc.append(
			"items",
			{
				"item_code": row.item_code,
				"qty": qty,
				"operation": row.operation,
				"fg_item": bom_item.item_code,
				"uom": resolved_uom,
				"fg_reference_id": name,
				"parent_row_no": parent_row_no,
				"conversion_factor": cf,
				"do_not_explode": 1,
				"stock_qty": qty * cf,
				"stock_uom": item_info.stock_uom,
			},
		)

	doc.save()
	return doc


def _coerce_kwargs(kwargs):
	if isinstance(kwargs, str):
		kwargs = frappe.parse_json(kwargs)
	if isinstance(kwargs, dict):
		kwargs = frappe._dict(kwargs)
	return kwargs


class BOMCreator(_CoreBOMCreator):
	"""Subclass override — fires on erpnext 16.26.2+ where the frontend
	calls `add_item` / `add_sub_assembly` as instance methods on the doc.
	"""

	@frappe.whitelist()
	def add_item(self, **kwargs):
		return _apply_add_item(self, _coerce_kwargs(kwargs))

	@frappe.whitelist()
	def add_sub_assembly(self, **kwargs):
		return _apply_add_sub_assembly(self, _coerce_kwargs(kwargs))


# Module-level whitelisted wrappers — fire on erpnext 16.21.1 and earlier
# where the frontend calls the full dotted path.
@frappe.whitelist()
def add_item(**kwargs):
	kwargs = _coerce_kwargs(kwargs)
	doc = frappe.get_doc("BOM Creator", kwargs.parent)
	return _apply_add_item(doc, kwargs)


@frappe.whitelist()
def add_sub_assembly(**kwargs):
	kwargs = _coerce_kwargs(kwargs)
	doc = frappe.get_doc("BOM Creator", kwargs.parent)
	return _apply_add_sub_assembly(doc, kwargs)
