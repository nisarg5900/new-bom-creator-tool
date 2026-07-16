"""Phase 4B tests — import an existing BOM back into BOM Creator.

Verifies the recursive reconstruction: flat BOM (raw materials only),
multi-level BOM (one sub-assembly), UOM/conversion preservation, and
lineage tracking via imported_from_bom.

Tests build the source BOM(s) by writing directly into `tabBOM` /
`tabBOM Item` — sidesteps needing a full BOM.save()/submit() pipeline
(which requires pricing setup) while producing a shape that
import_from_bom will faithfully walk.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from new_bom_creator.overrides.bom_creator import (
	_apply_import_from_bom,
	_import_walk_bom,
)
from new_bom_creator.tests.utils import TEST_COMPANY

# Same rationale as Phase 4A — global_search queue isn't live in tests.
import frappe.utils.global_search as _gs

_gs.sync_value_in_queue = lambda *a, **kw: None


def _make_submitted_bom(name, item, items, currency="INR"):
	"""Insert a submitted BOM directly (bypasses BOM.save/submit)."""
	frappe.db.sql(
		"""
		INSERT INTO `tabBOM`
			(name, item, is_default, is_active, docstatus, quantity, uom,
			 company, currency, rm_cost_as_per, conversion_rate,
			 creation, modified, modified_by, owner)
		VALUES (%s, %s, 1, 1, 1, 1, %s, %s, %s, 'Valuation Rate', 1, NOW(), NOW(),
			'Administrator', 'Administrator')
		""",
		(name, item, frappe.db.get_value("Item", item, "stock_uom"), TEST_COMPANY, currency),
	)
	for idx, i in enumerate(items, start=1):
		frappe.db.sql(
			"""
			INSERT INTO `tabBOM Item`
				(name, parent, parenttype, parentfield, idx,
				 item_code, qty, uom, stock_uom, conversion_factor, stock_qty,
				 bom_no, rate,
				 creation, modified, modified_by, owner)
			VALUES (%s, %s, 'BOM', 'items', %s, %s, %s, %s, %s, %s, %s, %s, %s,
				NOW(), NOW(), 'Administrator', 'Administrator')
			""",
			(
				f"{name}-BI-{idx}",
				name,
				idx,
				i["item_code"],
				i["qty"],
				i.get("uom") or frappe.db.get_value("Item", i["item_code"], "stock_uom"),
				frappe.db.get_value("Item", i["item_code"], "stock_uom"),
				i.get("conversion_factor", 1),
				i.get("stock_qty", i["qty"]),
				i.get("bom_no") or None,
				i.get("rate", 0),
			),
		)
	frappe.db.commit()


def _cleanup_bom(name):
	frappe.db.sql("DELETE FROM `tabBOM Item` WHERE parent = %s", (name,))
	frappe.db.sql("DELETE FROM `tabBOM` WHERE name = %s", (name,))
	frappe.db.commit()


def _cleanup_bom_creator(name):
	if not frappe.db.exists("BOM Creator", name):
		return
	frappe.db.sql("DELETE FROM `tabBOM Creator Item` WHERE parent = %s", (name,))
	frappe.db.sql("DELETE FROM `tabBOM Creator` WHERE name = %s", (name,))
	frappe.db.commit()


class TestImportFromBom(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("Company", TEST_COMPANY):
			raise Exception(
				f"Fixture Company '{TEST_COMPANY}' missing. Run: bench --site "
				"bomcreator.localhost execute new_bom_creator.tests."
				"_setup_site_fixtures.seed"
			)
		cls._created_boms = []
		cls._created_bcs = []

	@classmethod
	def tearDownClass(cls):
		for name in cls._created_bcs:
			_cleanup_bom_creator(name)
		for name in cls._created_boms:
			_cleanup_bom(name)
		super().tearDownClass()

	def _track_bom(self, name):
		self.__class__._created_boms.append(name)

	def _track_bc(self, name):
		self.__class__._created_bcs.append(name)

	def test_flat_bom_reconstructs_correctly(self):
		"""One BOM with two raw material lines -> BOM Creator with two rows,
		both fg_item=root, both is_expandable=0, no parent_row_no.
		"""
		bom = "NBC-BOM-FLAT-TEST"
		_make_submitted_bom(
			bom,
			"NBC-POLY",
			[
				{"item_code": "NBC-POLY", "qty": 2500, "uom": "Gram", "conversion_factor": 0.001, "stock_qty": 2.5},
				{"item_code": "NBC-STEEL", "qty": 1, "uom": "Kg", "conversion_factor": 1, "stock_qty": 1},
			],
		)
		self._track_bom(bom)

		bc_name = _apply_import_from_bom(bom)
		self._track_bc(bc_name)

		bc = frappe.get_doc("BOM Creator", bc_name)
		self.assertEqual(bc.item_code, "NBC-POLY")
		self.assertEqual(bc.imported_from_bom, bom)
		self.assertEqual(len(bc.items), 2)

		poly_row = next(r for r in bc.items if r.item_code == "NBC-POLY")
		steel_row = next(r for r in bc.items if r.item_code == "NBC-STEEL")
		self.assertEqual(poly_row.uom, "Gram")
		self.assertAlmostEqual(poly_row.conversion_factor, 0.001, places=6)
		self.assertAlmostEqual(poly_row.stock_qty, 2.5, places=6)
		self.assertEqual(poly_row.fg_item, "NBC-POLY")
		self.assertFalse(poly_row.parent_row_no)
		self.assertEqual(steel_row.fg_item, "NBC-POLY")
		# set_reference_id in before_save should have set fg_reference_id
		# to bc.name for both (they're direct children of the root FG).
		self.assertEqual(poly_row.fg_reference_id, bc.name)
		self.assertEqual(steel_row.fg_reference_id, bc.name)

	def test_multi_level_bom_reconstructs_correctly(self):
		"""Root -> [sub-assembly (with its own child), raw material].

		The sub-assembly's own row goes to bc.items with parent_row_no unset
		(direct child of root). Its raw material goes to bc.items with
		parent_row_no = <idx of the sub-assembly row>. set_is_expandable
		marks the sub-assembly row is_expandable=1 (its item_code appears
		as fg_item on another row).
		"""
		# Child BOM for the sub-assembly item NBC-STEEL
		child_bom = "NBC-BOM-CHILD-TEST"
		_make_submitted_bom(
			child_bom,
			"NBC-STEEL",
			[
				{"item_code": "NBC-POLY", "qty": 500, "uom": "Gram", "conversion_factor": 0.001, "stock_qty": 0.5},
			],
		)
		self._track_bom(child_bom)

		# Root BOM references child_bom as a sub-assembly line
		root_bom = "NBC-BOM-ROOT-TEST"
		_make_submitted_bom(
			root_bom,
			"NBC-POLY",
			[
				{"item_code": "NBC-STEEL", "qty": 1, "bom_no": child_bom},
				{"item_code": "NBC-POLY", "qty": 1000, "uom": "Gram", "conversion_factor": 0.001, "stock_qty": 1.0},
			],
		)
		self._track_bom(root_bom)

		bc_name = _apply_import_from_bom(root_bom)
		self._track_bc(bc_name)

		bc = frappe.get_doc("BOM Creator", bc_name)
		self.assertEqual(bc.item_code, "NBC-POLY")
		# 3 rows: STEEL (sub-assembly), POLY-under-STEEL, POLY (root RM).
		self.assertEqual(len(bc.items), 3)

		steel_row = next(r for r in bc.items if r.item_code == "NBC-STEEL")
		child_poly_row = next(
			r for r in bc.items if r.item_code == "NBC-POLY" and r.fg_item == "NBC-STEEL"
		)
		root_poly_row = next(
			r for r in bc.items if r.item_code == "NBC-POLY" and r.fg_item == "NBC-POLY"
		)

		# Sub-assembly row is is_expandable (set_is_expandable in before_save).
		self.assertEqual(steel_row.is_expandable, 1)
		self.assertEqual(steel_row.fg_item, "NBC-POLY")
		self.assertFalse(steel_row.parent_row_no)

		# Root raw-material row (NBC-POLY under root FG).
		self.assertEqual(root_poly_row.is_expandable, 0)
		self.assertFalse(root_poly_row.parent_row_no)

		# Child raw-material row (NBC-POLY under NBC-STEEL sub-assembly).
		self.assertEqual(child_poly_row.is_expandable, 0)
		self.assertEqual(str(child_poly_row.parent_row_no), str(steel_row.idx))
		self.assertEqual(child_poly_row.fg_reference_id, steel_row.name)
		self.assertEqual(child_poly_row.uom, "Gram")
		self.assertAlmostEqual(child_poly_row.conversion_factor, 0.001, places=6)


class TestImportHooks(FrappeTestCase):
	def test_import_from_bom_module_fn_registered_in_overrides(self):
		mapping = frappe.get_hooks("override_whitelisted_methods") or {}
		self.assertEqual(
			mapping.get("erpnext.manufacturing.doctype.bom_creator.bom_creator.import_from_bom"),
			["new_bom_creator.overrides.bom_creator.import_from_bom"],
		)

	def test_imported_from_bom_field_exists(self):
		self.assertIsNotNone(
			frappe.get_meta("BOM Creator").get_field("imported_from_bom"),
			"imported_from_bom custom field missing on BOM Creator.",
		)
