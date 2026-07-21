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
from frappe.utils import cint, flt, sbool
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

	# Phase 5: link-only sub-assemblies reuse the item's default BOM.
	link_only = sbool(bom_item.get("link_only"))
	linked_bom = None
	if link_only:
		linked_bom = frappe.db.get_value("Item", bom_item.item_code, "default_bom")
		if not linked_bom:
			frappe.throw(
				_("Item {0} has no Default BOM to link.").format(bold(bom_item.item_code)),
				title=_("No Default BOM"),
			)

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
				"linked_bom": linked_bom,
			},
		)

		parent_row_no = item_row.idx
		name = ""
	else:
		if sbool(kwargs.phantom):
			parent_row = next(item for item in doc.items if item.name == kwargs.fg_reference_id)
			parent_row.is_phantom_item = 1
		parent_row_no = get_parent_row_no(doc, kwargs.fg_reference_id)

	# Linked sub-assemblies don't get raw material rows — the linked BOM
	# is the source of truth for downstream.
	if not link_only:
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


def _apply_output_control(bom_creator, row, bom):
	"""Phase 3: read is_default / is_active from the row (self for the
	root FG, child row for sub-assemblies) rather than defaulting to 1.
	Default of 1 preserves the pre-Phase-3 behaviour when the user hasn't
	touched the new fields.
	"""
	set_as_default = row.get("set_as_default")
	bom.is_default = cint(set_as_default if set_as_default is not None else 1)
	is_active = row.get("is_active")
	bom.is_active = cint(is_active if is_active is not None else 1)


def _should_submit(bom_creator):
	"""Phase 3: honour the output_mode field. Missing/'Submit' -> True."""
	return (bom_creator.get("output_mode") or "Submit") != "Draft"


def _compute_supersede_preview(bom_creator):
	"""List FGs whose existing default BOM would be replaced by generation."""
	preview = []

	def _consider(item_code, set_as_default):
		if not item_code:
			return
		will_default = cint(set_as_default if set_as_default is not None else 1)
		if not will_default:
			return
		existing = frappe.db.get_value(
			"BOM",
			{"item": item_code, "is_default": 1, "is_active": 1, "docstatus": 1},
			"name",
		)
		if existing:
			preview.append(
				{
					"item": item_code,
					"existing_default_bom": existing,
					"will_become_default": True,
				}
			)

	_consider(bom_creator.item_code, bom_creator.get("set_as_default"))
	for row in bom_creator.items:
		if row.is_expandable and row.item_code != bom_creator.item_code:
			_consider(row.item_code, row.get("set_as_default"))

	return preview


# --- Phase 4B: import an existing BOM back into BOM Creator ---------------


def _apply_import_from_bom(bom_name):
	"""Shared import logic — reconstruct a BOM Creator from a submitted BOM.

	Returns the name of the new BOM Creator (Draft). Callers may want to
	wrap this in a whitelisted method — see the module-level and subclass
	entry points below.
	"""
	root_bom = frappe.get_doc("BOM", bom_name)

	bc = frappe.new_doc("BOM Creator")
	bc.name = f"IMPORT-{root_bom.item}-{frappe.generate_hash(length=6)}"
	bc.item_code = root_bom.item
	bc.qty = root_bom.quantity or 1
	bc.company = root_bom.company
	bc.currency = root_bom.currency
	bc.conversion_rate = root_bom.conversion_rate or 1
	bc.rm_cost_as_per = root_bom.rm_cost_as_per or "Valuation Rate"
	bc.buying_price_list = root_bom.buying_price_list
	bc.project = root_bom.project
	bc.imported_from_bom = bom_name
	# Imports default to Draft output so the user can review before
	# regenerating (Phase 3 field).
	if hasattr(bc, "output_mode"):
		bc.output_mode = "Draft"

	_import_walk_bom(bc, root_bom, parent_row_no=None, visited={root_bom.name})

	bc.insert(ignore_permissions=True)
	return bc.name


def _import_walk_bom(bc, bom, parent_row_no, visited):
	"""Depth-first walk. `parent_row_no` = 1-based idx of the sub-assembly
	row this branch belongs under (None for direct children of the root
	FG). We predict idx from list position — Frappe assigns idx by
	position at save time.
	"""
	for item in bom.items:
		row_data = {
			"item_code": item.item_code,
			"qty": item.qty,
			"uom": item.uom,
			"stock_uom": item.stock_uom,
			"conversion_factor": item.conversion_factor or 1,
			"stock_qty": item.stock_qty or (flt(item.qty) * flt(item.conversion_factor or 1)),
			"rate": item.rate,
			"operation": item.operation,
			"fg_item": bom.item,
			"do_not_explode": 1,
			"is_phantom_item": cint(item.get("is_phantom_item")),
		}
		if parent_row_no is not None:
			row_data["parent_row_no"] = str(parent_row_no)
		bc.append("items", row_data)
		new_idx = len(bc.items)

		if item.bom_no:
			if item.bom_no in visited:
				frappe.throw(
					_("Cycle detected while importing BOM tree at {0}").format(item.bom_no),
					title=_("Cyclic BOM Reference"),
				)
			child_bom = frappe.get_doc("BOM", item.bom_no)
			_import_walk_bom(bc, child_bom, parent_row_no=new_idx, visited=visited | {item.bom_no})


def _compute_levels(items):
	"""Return {row.name: depth} for every BOM Creator Item row.

	Root (is_root=1) is level 0. Children are level 1, grandchildren 2, etc.
	Uses fg_reference_id as the parent pointer.
	"""
	children_of = {}
	for item in items:
		ref = item.get("fg_reference_id") or ""
		children_of.setdefault(ref, []).append(item)

	levels = {}
	queue = []
	for item in items:
		if cint(item.get("is_root")):
			levels[item.name] = 0
			queue.append(item.name)
			break

	while queue:
		parent_name = queue.pop(0)
		parent_level = levels[parent_name]
		for child in children_of.get(parent_name, []):
			levels[child.name] = parent_level + 1
			queue.append(child.name)

	return levels


class BOMCreator(_CoreBOMCreator):
	"""Subclass override — fires on erpnext 16.26.2+ where the frontend
	calls `add_item` / `add_sub_assembly` as instance methods on the doc.
	Also carries the Phase 3 create_bom override, which is needed on ALL
	erpnext versions (create_bom is always an instance method).
	"""

	@frappe.whitelist()
	def add_item(self, **kwargs):
		return _apply_add_item(self, _coerce_kwargs(kwargs))

	@frappe.whitelist()
	def add_sub_assembly(self, **kwargs):
		return _apply_add_sub_assembly(self, _coerce_kwargs(kwargs))

	@frappe.whitelist()
	def get_supersede_preview(self):
		return _compute_supersede_preview(self)

	@frappe.whitelist()
	def import_from_bom(self, bom_name):
		"""Bound to the subclass so newer erpnext (that would call via
		doc.<method>) resolves to us. Argument mirrors the module fn."""
		return _apply_import_from_bom(bom_name)

	@frappe.whitelist()
	def get_default_bom_items(self, item_code):
		"""Phase 5: Add Sub Assembly dialog pre-fills from item's default BOM."""
		return _fetch_default_bom_items(item_code)

	def create_bom(self, row, production_item_wise_rm):
		"""Phase 3: honour output_mode + per-row set_as_default / is_active.

		We reimplement rather than pre/post-process because the core's
		bom.submit() is unconditional and post-processing a submitted BOM
		back to draft is unsafe. The body mirrors the core method with
		three additions:
		  - bom.is_default / is_active read from the row (Phase 3).
		  - bom.submit() only when output_mode != 'Draft' (Phase 3).
		"""
		from erpnext.manufacturing.doctype.bom_creator.bom_creator import (
			BOM_FIELDS,
			BOM_ITEM_FIELDS,
		)

		# Phase 5: linked sub-assemblies (row.linked_bom set) reuse an
		# existing submitted BOM instead of generating a new one. Skip.
		# The parent BOM's item line consumes item.linked_bom directly
		# in the inner loop below.
		if row is not self and row.get("linked_bom"):
			return

		bom_creator_item = row.name if row.name != self.name else ""
		if frappe.db.exists(
			"BOM",
			{
				"bom_creator": self.name,
				"item": row.item_code,
				"bom_creator_item": bom_creator_item,
				"docstatus": 1,
			},
		):
			return

		bom = frappe.new_doc("BOM")
		bom.update(
			{
				"item": row.item_code,
				"bom_type": "Production",
				"quantity": row.qty,
				"allow_alternative_item": 1,
				"bom_creator": self.name,
				"bom_creator_item": bom_creator_item,
				"is_phantom_bom": row.get("is_phantom_item"),
			}
		)

		if row.item_code == self.item_code:
			bom.is_phantom_bom = self.is_phantom
			if not self.is_phantom and (self.routing or self.has_operations()):
				bom.routing = self.routing
				bom.with_operations = 1
				bom.transfer_material_against = "Work Order"

		for field in BOM_FIELDS:
			if self.get(field):
				bom.set(field, self.get(field))

		_apply_output_control(self, row, bom)

		for item in production_item_wise_rm[(row.item_code, row.name)]["items"]:
			bom_no = ""
			item.do_not_explode = 1
			# Phase 5: honour a pre-linked BOM (from #38438). If set, the
			# parent BOM's item line points at the linked BOM and no child
			# is generated for this branch.
			if item.get("linked_bom"):
				bom_no = item.linked_bom
				item.do_not_explode = 0
			elif (item.item_code, item.name) in production_item_wise_rm:
				bom_no = production_item_wise_rm.get((item.item_code, item.name)).bom_no
				item.do_not_explode = 0

			item_args = {}
			for field in BOM_ITEM_FIELDS:
				item_args[field] = item.get(field)

			item_args.update(
				{
					"bom_no": bom_no,
					"allow_alternative_item": 1,
					"include_item_in_manufacturing": 1,
				}
			)

			bom.append("items", item_args)

		bom.save(ignore_permissions=True)
		if _should_submit(self):
			bom.submit()

		production_item_wise_rm[(row.item_code, row.name)].bom_no = bom.name


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


@frappe.whitelist()
def import_from_bom(bom_name):
	"""Module-level entry point — the client button on older erpnext
	calls this at the full dotted path, redirected via
	override_whitelisted_methods to point here on erpnext where the
	upstream method doesn't yet exist.
	"""
	return _apply_import_from_bom(bom_name)


@frappe.whitelist()
def get_default_bom_items(item_code):
	"""Module-level entry point for the Phase 5 auto-populate helper."""
	return _fetch_default_bom_items(item_code)


def _fetch_default_bom_items(item_code):
	"""Shared logic — see fork branch nbc/5-sub-assembly-reuse for the
	same helper on the class module.
	"""
	if not item_code:
		return None
	default_bom = frappe.db.get_value("Item", item_code, "default_bom")
	if not default_bom:
		return None
	items = frappe.get_all(
		"BOM Item",
		filters={"parent": default_bom, "parenttype": "BOM"},
		fields=[
			"item_code",
			"qty",
			"uom",
			"stock_uom",
			"conversion_factor",
			"stock_qty",
			"rate",
			"operation",
			"bom_no",
		],
		order_by="idx",
	)
	return {"default_bom": default_bom, "items": items}
