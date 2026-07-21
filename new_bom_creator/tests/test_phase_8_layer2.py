"""Phase 8 tests — Layer 2 field pass-throughs.

Covers sub-scopes 2-5:
  - Header-level fields (default warehouses, inspection, backflush) carry
    through from BOM Creator to the generated BOM.
  - Per-line fields (source_warehouse, allow_alternative_item,
    include_item_in_manufacturing) carry through to the BOM Item lines.
  - Custom field fixtures are registered.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import cint

from new_bom_creator.overrides.bom_creator import _apply_add_item
from new_bom_creator.tests.utils import (
	TEST_COMPANY,
	cleanup_generated_boms,
	new_bom_creator,
)

import frappe.utils.global_search as _gs

_gs.sync_value_in_queue = lambda *a, **kw: None


class TestPhase8Fixtures(FrappeTestCase):
	"""All Phase 8 custom fields exist on the meta."""

	def test_bom_creator_header_fields(self):
		meta = frappe.get_meta("BOM Creator")
		for fname in (
			"default_source_warehouse",
			"default_target_warehouse",
			"inspection_required",
			"quality_inspection_template",
			"backflush_based_on",
		):
			self.assertIsNotNone(
				meta.get_field(fname),
				f"{fname} custom field missing on BOM Creator.",
			)

	def test_bom_creator_item_fields(self):
		meta = frappe.get_meta("BOM Creator Item")
		for fname in (
			"source_warehouse",
			"allow_alternative_item",
			"include_item_in_manufacturing",
		):
			self.assertIsNotNone(
				meta.get_field(fname),
				f"{fname} custom field missing on BOM Creator Item.",
			)


class TestLayer2FieldPassThrough(FrappeTestCase):
	"""End-to-end: fields set on BOM Creator appear on the generated BOM."""

	def setUp(self):
		self.bc_name = None

	def tearDown(self):
		if not self.bc_name:
			return
		cleanup_generated_boms(self.bc_name)
		if frappe.db.exists("BOM Creator", self.bc_name):
			bc = frappe.get_doc("BOM Creator", self.bc_name)
			if bc.docstatus == 1:
				bc.flags.ignore_links = True
				bc.cancel()
			bc.delete(ignore_permissions=True, force=True)
			frappe.db.commit()

	def _get_warehouse(self):
		"""Return a warehouse that exists for TEST_COMPANY."""
		wh = frappe.db.get_value(
			"Warehouse",
			{"company": TEST_COMPANY, "is_group": 0},
			"name",
		)
		return wh

	def test_header_fields_carry_through(self):
		wh = self._get_warehouse()
		if not wh:
			self.skipTest("No warehouse found for test company")

		doc = new_bom_creator(
			item_code="NBC-POLY",
			qty=1,
			output_mode="Draft",
			set_as_default=0,
		)
		doc.default_source_warehouse = wh
		doc.default_target_warehouse = wh
		doc.inspection_required = 1
		doc.backflush_based_on = "Material Transferred for Manufacture"
		doc.insert(ignore_permissions=True)
		self.bc_name = doc.name

		_apply_add_item(
			doc,
			frappe._dict(
				{
					"parent": doc.name,
					"fg_item": "NBC-POLY",
					"item_code": "NBC-STEEL",
					"fg_reference_id": doc.name,
					"qty": 2,
				}
			),
		)
		doc.reload()
		doc.create_boms()

		generated = frappe.get_all(
			"BOM",
			filters={"bom_creator": doc.name},
			fields=["name"],
		)
		self.assertTrue(generated, "No BOM generated")
		bom = frappe.get_doc("BOM", generated[0]["name"])

		self.assertEqual(bom.default_source_warehouse, wh)
		self.assertEqual(bom.default_target_warehouse, wh)
		self.assertEqual(cint(bom.inspection_required), 1)
		self.assertEqual(bom.backflush_based_on, "Material Transferred for Manufacture")

	def test_per_item_fields_carry_through(self):
		wh = self._get_warehouse()

		doc = new_bom_creator(
			item_code="NBC-POLY",
			qty=1,
			output_mode="Draft",
			set_as_default=0,
		)
		doc.insert(ignore_permissions=True)
		self.bc_name = doc.name

		_apply_add_item(
			doc,
			frappe._dict(
				{
					"parent": doc.name,
					"fg_item": "NBC-POLY",
					"item_code": "NBC-STEEL",
					"fg_reference_id": doc.name,
					"qty": 2,
				}
			),
		)
		doc.reload()

		steel_row = next(r for r in doc.items if r.item_code == "NBC-STEEL")
		steel_row.allow_alternative_item = 0
		steel_row.include_item_in_manufacturing = 0
		if wh:
			steel_row.source_warehouse = wh
		doc.save(ignore_permissions=True)

		doc.create_boms()

		generated = frappe.get_all(
			"BOM",
			filters={"bom_creator": doc.name},
			fields=["name"],
		)
		self.assertTrue(generated)
		bom_items = frappe.get_all(
			"BOM Item",
			filters={"parent": generated[0]["name"], "item_code": "NBC-STEEL"},
			fields=["allow_alternative_item", "include_item_in_manufacturing", "source_warehouse"],
		)
		self.assertEqual(len(bom_items), 1)
		self.assertEqual(cint(bom_items[0]["allow_alternative_item"]), 0)
		self.assertEqual(cint(bom_items[0]["include_item_in_manufacturing"]), 0)
		if wh:
			self.assertEqual(bom_items[0]["source_warehouse"], wh)

	def test_defaults_backward_compat(self):
		"""When per-line fields are not set, they default to 1 (backward compat)."""
		doc = new_bom_creator(
			item_code="NBC-POLY",
			qty=1,
			output_mode="Draft",
			set_as_default=0,
		)
		doc.insert(ignore_permissions=True)
		self.bc_name = doc.name

		_apply_add_item(
			doc,
			frappe._dict(
				{
					"parent": doc.name,
					"fg_item": "NBC-POLY",
					"item_code": "NBC-STEEL",
					"fg_reference_id": doc.name,
					"qty": 1,
				}
			),
		)
		doc.reload()
		doc.create_boms()

		generated = frappe.get_all(
			"BOM",
			filters={"bom_creator": doc.name},
			fields=["name"],
		)
		self.assertTrue(generated)
		bom_items = frappe.get_all(
			"BOM Item",
			filters={"parent": generated[0]["name"], "item_code": "NBC-STEEL"},
			fields=["allow_alternative_item", "include_item_in_manufacturing"],
		)
		self.assertEqual(len(bom_items), 1)
		self.assertEqual(cint(bom_items[0]["allow_alternative_item"]), 1)
		self.assertEqual(cint(bom_items[0]["include_item_in_manufacturing"]), 1)
