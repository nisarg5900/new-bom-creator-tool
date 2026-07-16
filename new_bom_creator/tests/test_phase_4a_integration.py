"""Phase 4A end-to-end integration test.

Runs one BOM Creator through the full override pipeline against a real
site with a real Company + warehouses, and asserts that Phase 2 (UOM /
conversion factor) and Phase 3 (output_mode Draft, is_default control)
land correctly in the generated BOM row.

This is the first test that actually calls the overridden create_bom
end-to-end; earlier phases tested pure helpers only.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from new_bom_creator.tests.utils import (
	TEST_COMPANY,
	cleanup_generated_boms,
	new_bom_creator,
)

# Bypass Frappe's "should not fail silently in tests" global_search assert.
# The site's redis queue isn't up in this test process, and we don't need
# global_search behaviour for these tests.
import frappe.utils.global_search as _gs

_gs.sync_value_in_queue = lambda *a, **kw: None


class TestBomCreatorEndToEnd(FrappeTestCase):
	"""Draft-mode end-to-end: create BOM Creator -> add polymer in Gram ->
	create_boms -> verify the resulting draft BOM.

	Draft mode is deliberate: no submit, no manage_default_bom side-effects,
	no interaction with any existing (non-existent) default BOM, no need
	for pricing setup. Purely exercises our override wiring.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Sanity: fixture must exist. If missing, the test skips with a
		# pointer to the seed script — no test-time reinvention.
		if not frappe.db.exists("Company", TEST_COMPANY):
			raise Exception(
				f"Fixture Company '{TEST_COMPANY}' missing on site. "
				"Run: bench --site bomcreator.localhost execute "
				"new_bom_creator._seed_scratch.seed"
			)

	def setUp(self):
		self.bc_name = None

	def tearDown(self):
		if self.bc_name:
			cleanup_generated_boms(self.bc_name)
			# Now safely delete the BOM Creator itself.
			if frappe.db.exists("BOM Creator", self.bc_name):
				bc = frappe.get_doc("BOM Creator", self.bc_name)
				if bc.docstatus == 1:
					bc.cancel()
				bc.delete(ignore_permissions=True)
				frappe.db.commit()

	def test_draft_output_mode_generates_correct_bom(self):
		"""End-to-end: NBC-POLY as FG, 1kg batch, add itself as an RM in
		grams (2500 g) → generated BOM should be draft (docstatus=0),
		is_default=0 (we set set_as_default=0), and the item line should
		carry uom=Gram, conversion_factor=0.001, stock_qty=2.5.
		"""
		doc = new_bom_creator(
			item_code="NBC-POLY",
			qty=1,
			output_mode="Draft",
			set_as_default=0,
			is_active=1,
		)
		doc.insert(ignore_permissions=True)
		self.bc_name = doc.name

		# Add the FG's own material line via the overridden add_item —
		# this exercises Phase 2's UOM/conversion-factor logic on the way in.
		doc.add_item(
			item_code="NBC-POLY",
			qty=2500,
			uom="Gram",
			fg_item="NBC-POLY",
			fg_reference_id=doc.name,
		)
		doc.reload()

		# The child row landed with our UOM fix already applied.
		self.assertEqual(len(doc.items), 1)
		row = doc.items[0]
		self.assertEqual(row.item_code, "NBC-POLY")
		self.assertEqual(row.uom, "Gram")
		self.assertAlmostEqual(row.conversion_factor, 0.001, places=6)
		self.assertAlmostEqual(row.stock_qty, 2.5, places=6)

		# Now run create_boms — this exercises Phase 3's create_bom override.
		# Bypass enqueue_bom_creation (which .enqueue()s a background job)
		# and call create_boms directly for a synchronous test.
		doc.create_boms()

		boms = frappe.get_all(
			"BOM",
			filters={"bom_creator": doc.name},
			fields=["name", "docstatus", "is_default", "is_active", "item"],
		)
		self.assertEqual(len(boms), 1, f"Expected one generated BOM, got {boms}")
		bom = boms[0]

		# Phase 3: Draft output mode -> docstatus stays 0.
		self.assertEqual(bom.docstatus, 0, "output_mode=Draft should leave BOM at docstatus=0")
		# Phase 3: set_as_default=0 -> is_default=0.
		self.assertEqual(bom.is_default, 0, "set_as_default=0 should produce is_default=0")
		# Phase 3: is_active=1 preserved.
		self.assertEqual(bom.is_active, 1)
		self.assertEqual(bom.item, "NBC-POLY")

		# Phase 2: the BOM's own items row inherits uom / cf / stock_qty
		# from the BOM Creator Item row.
		bom_items = frappe.get_all(
			"BOM Item",
			filters={"parent": bom.name},
			fields=["item_code", "uom", "conversion_factor", "stock_qty", "qty"],
		)
		self.assertEqual(len(bom_items), 1, f"Expected one BOM Item, got {bom_items}")
		bi = bom_items[0]
		self.assertEqual(bi.item_code, "NBC-POLY")
		self.assertEqual(bi.uom, "Gram")
		self.assertAlmostEqual(bi.conversion_factor, 0.001, places=6)
		self.assertAlmostEqual(bi.qty, 2500, places=2)
		self.assertAlmostEqual(bi.stock_qty, 2.5, places=6)
