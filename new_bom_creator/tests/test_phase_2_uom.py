"""Phase 2 tests — per-line UOM & conversion factor.

Exercises the shared helper _resolve_line_uom that both the module-level and
class-method paths use in overrides/bom_creator.py. If this helper is right,
both call paths inherit the same behaviour by construction.

Fixture (created out-of-band on bomcreator.localhost, kept idempotently in
setUpClass):
  - UOM "Kg", "Gram" (defaults)
  - Item Group "NBC Test"
  - Item "NBC-POLY": stock_uom=Kg, UOM Conversion Detail Gram = 0.001
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from new_bom_creator.overrides.bom_creator import _resolve_line_uom


def _ensure_fixtures():
	# Include "Litre" so the unknown-UOM test doesn't insert inside a test
	# transaction (that hits a Frappe website-route generation quirk in tests).
	for uom in ["Kg", "Gram", "Litre"]:
		if not frappe.db.exists("UOM", uom):
			frappe.get_doc({"doctype": "UOM", "uom_name": uom, "name": uom}).insert(
				ignore_permissions=True
			)

	if not frappe.db.exists("Item Group", "All Item Groups"):
		frappe.get_doc(
			{"doctype": "Item Group", "item_group_name": "All Item Groups", "is_group": 1}
		).insert(ignore_permissions=True)

	if not frappe.db.exists("Item Group", "NBC Test"):
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": "NBC Test",
				"parent_item_group": "All Item Groups",
			}
		).insert(ignore_permissions=True)

	if not frappe.db.exists("Item", "NBC-POLY"):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "NBC-POLY",
				"item_name": "NBC Test Polycarbonate",
				"item_group": "NBC Test",
				"stock_uom": "Kg",
				"is_stock_item": 1,
				"uoms": [
					{"uom": "Kg", "conversion_factor": 1},
					{"uom": "Gram", "conversion_factor": 0.001},
				],
			}
		).insert(ignore_permissions=True)

	frappe.db.commit()


class TestResolveLineUom(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_ensure_fixtures()

	def test_empty_uom_defaults_to_stock_uom_with_cf_1(self):
		uom, cf = _resolve_line_uom("NBC-POLY", None, "Kg")
		self.assertEqual(uom, "Kg")
		self.assertEqual(cf, 1.0)

	def test_stock_uom_explicit_returns_cf_1(self):
		uom, cf = _resolve_line_uom("NBC-POLY", "Kg", "Kg")
		self.assertEqual(uom, "Kg")
		self.assertEqual(cf, 1.0)

	def test_alt_uom_uses_item_conversion_table(self):
		"""2.5 g of a Kg-stock polymer → stock_qty = 0.0025 Kg."""
		uom, cf = _resolve_line_uom("NBC-POLY", "Gram", "Kg")
		self.assertEqual(uom, "Gram")
		self.assertAlmostEqual(cf, 0.001, places=6)
		# The consuming code computes stock_qty = qty * cf.
		self.assertAlmostEqual(2.5 * cf, 0.0025, places=6)

	def test_unknown_uom_raises_friendly_error(self):
		"""If a UOM is not in the item's conversion table, throw not silently succeed."""
		# Litre is a real UOM (see setUpClass) but NBC-POLY only has Kg + Gram
		# in its conversion table, so resolving Litre for that item must throw.
		with self.assertRaises(frappe.ValidationError) as cm:
			_resolve_line_uom("NBC-POLY", "Litre", "Kg")
		self.assertIn("UOM", str(cm.exception))


class TestPhase2Hooks(FrappeTestCase):
	def test_bom_creator_doctype_js_registered(self):
		"""The client-side UOM patch must be wired into hooks.doctype_js."""
		mapping = frappe.get_hooks("doctype_js") or {}
		bom_creator_js = mapping.get("BOM Creator") or []
		# Frappe collects doctype_js as a list even for a single entry.
		self.assertTrue(
			any("bom_creator_patches" in path for path in bom_creator_js),
			f"Expected 'public/js/bom_creator_patches.js' in doctype_js['BOM Creator'], "
			f"got: {bom_creator_js}",
		)
