"""Phase 5 tests — sub-assembly reuse.

Covers:
  - _fetch_default_bom_items returns items for an Item with a default BOM;
    returns None otherwise.
  - _apply_add_sub_assembly with link_only=True resolves the item's
    default BOM and writes linked_bom on the sub-assembly row.
  - create_bom skips the linked sub-assembly (no new BOM generated) and
    the parent BOM's item line points at row.linked_bom.
  - Custom field linked_bom + fixture registration.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from new_bom_creator.overrides.bom_creator import (
	_apply_add_sub_assembly,
	_fetch_default_bom_items,
)
from new_bom_creator.tests.utils import (
	TEST_COMPANY,
	cleanup_generated_boms,
	new_bom_creator,
)

# Same rationale as Phase 4A/4B — global_search queue isn't live in tests.
import frappe.utils.global_search as _gs

_gs.sync_value_in_queue = lambda *a, **kw: None


def _make_submitted_bom(name, item):
	"""Insert a minimal submitted BOM directly (no pricing wiring)."""
	stock_uom = frappe.db.get_value("Item", item, "stock_uom")
	frappe.db.sql(
		"""
		INSERT INTO `tabBOM`
			(name, item, is_default, is_active, docstatus, quantity, uom,
			 company, currency, rm_cost_as_per, conversion_rate,
			 creation, modified, modified_by, owner)
		VALUES (%s, %s, 1, 1, 1, 1, %s, %s, 'INR', 'Valuation Rate', 1,
			NOW(), NOW(), 'Administrator', 'Administrator')
		""",
		(name, item, stock_uom, TEST_COMPANY),
	)
	# Two dummy raw material lines
	for idx, (ic, qty) in enumerate([("NBC-POLY", 100), ("NBC-STEEL", 2)], start=1):
		frappe.db.sql(
			"""
			INSERT INTO `tabBOM Item`
				(name, parent, parenttype, parentfield, idx,
				 item_code, qty, uom, stock_uom, conversion_factor, stock_qty,
				 rate,
				 creation, modified, modified_by, owner)
			VALUES (%s, %s, 'BOM', 'items', %s, %s, %s, %s, %s, 1, %s, 0,
				NOW(), NOW(), 'Administrator', 'Administrator')
			""",
			(
				f"{name}-BI-{idx}",
				name,
				idx,
				ic,
				qty,
				frappe.db.get_value("Item", ic, "stock_uom"),
				frappe.db.get_value("Item", ic, "stock_uom"),
				qty,
			),
		)
	frappe.db.commit()


def _delete_bom(name):
	frappe.db.sql("DELETE FROM `tabBOM Item` WHERE parent = %s", (name,))
	frappe.db.sql("DELETE FROM `tabBOM` WHERE name = %s", (name,))
	frappe.db.commit()


def _set_item_default_bom(item_code, bom_name):
	frappe.db.set_value("Item", item_code, "default_bom", bom_name)
	frappe.db.commit()


class TestFetchDefaultBomItems(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._bom = "NBC-BOM-P5-FETCH"
		_make_submitted_bom(cls._bom, "NBC-STEEL")
		_set_item_default_bom("NBC-STEEL", cls._bom)

	@classmethod
	def tearDownClass(cls):
		_set_item_default_bom("NBC-STEEL", None)
		_delete_bom(cls._bom)
		super().tearDownClass()

	def test_item_with_default_bom_returns_items(self):
		result = _fetch_default_bom_items("NBC-STEEL")
		self.assertIsNotNone(result)
		self.assertEqual(result["default_bom"], self._bom)
		self.assertEqual(len(result["items"]), 2)
		codes = {i["item_code"] for i in result["items"]}
		self.assertEqual(codes, {"NBC-POLY", "NBC-STEEL"})

	def test_item_without_default_bom_returns_none(self):
		# NBC-POLY has no default BOM set — should return None.
		self.assertIsNone(_fetch_default_bom_items("NBC-POLY"))

	def test_empty_item_code_returns_none(self):
		self.assertIsNone(_fetch_default_bom_items(""))
		self.assertIsNone(_fetch_default_bom_items(None))


class TestLinkOnlyAddSubAssembly(FrappeTestCase):
	"""End-to-end: build a BOM Creator, add a sub-assembly with
	link_only=True, run create_boms, verify the linked BOM is referenced
	in the parent's BOM Item line and no new child BOM was generated.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._linked_bom = "NBC-BOM-P5-LINKED"
		_make_submitted_bom(cls._linked_bom, "NBC-STEEL")
		_set_item_default_bom("NBC-STEEL", cls._linked_bom)

	@classmethod
	def tearDownClass(cls):
		_set_item_default_bom("NBC-STEEL", None)
		_delete_bom(cls._linked_bom)
		super().tearDownClass()

	def setUp(self):
		self.bc_name = None

	def tearDown(self):
		if not self.bc_name:
			return
		# Clean up any generated BOMs for this test run.
		cleanup_generated_boms(self.bc_name)
		if frappe.db.exists("BOM Creator", self.bc_name):
			bc = frappe.get_doc("BOM Creator", self.bc_name)
			if bc.docstatus == 1:
				bc.cancel()
			bc.delete(ignore_permissions=True)
			frappe.db.commit()

	def test_link_only_sets_linked_bom_and_skips_child_generation(self):
		doc = new_bom_creator(
			item_code="NBC-POLY",
			qty=1,
			output_mode="Draft",
			set_as_default=0,
		)
		doc.insert(ignore_permissions=True)
		self.bc_name = doc.name

		# Add NBC-STEEL as a link-only sub-assembly under NBC-POLY (root).
		bom_item = frappe.as_json(
			{
				"item_code": "NBC-STEEL",
				"qty": 3,
				"link_only": 1,
				"items": [],
			}
		)
		_apply_add_sub_assembly(
			doc,
			frappe._dict(
				{
					"bom_item": bom_item,
					"fg_item": "NBC-POLY",
					"fg_reference_id": doc.name,
					"convert_to_sub_assembly": 0,
					"phantom": 0,
				}
			),
		)
		doc.reload()

		steel_row = next(r for r in doc.items if r.item_code == "NBC-STEEL")
		self.assertEqual(steel_row.linked_bom, self._linked_bom)
		# No raw material rows were appended for the linked sub-assembly.
		self.assertEqual(len(doc.items), 1)

		# Run the create-BOMs pipeline. Should generate exactly ONE BOM
		# (the root NBC-POLY BOM) whose items row references linked_bom.
		doc.create_boms()

		generated = frappe.get_all(
			"BOM",
			filters={"bom_creator": doc.name},
			fields=["name", "item", "docstatus"],
		)
		self.assertEqual(
			len(generated),
			1,
			f"Expected only the root BOM, got {generated}. "
			"Linked sub-assembly should NOT get a new BOM.",
		)
		root_bom = generated[0]["name"]

		root_bom_items = frappe.get_all(
			"BOM Item",
			filters={"parent": root_bom, "item_code": "NBC-STEEL"},
			fields=["item_code", "bom_no", "qty"],
		)
		self.assertEqual(len(root_bom_items), 1)
		self.assertEqual(root_bom_items[0]["bom_no"], self._linked_bom)


class TestPhase5Fixtures(FrappeTestCase):
	def test_linked_bom_custom_field_exists(self):
		self.assertIsNotNone(
			frappe.get_meta("BOM Creator Item").get_field("linked_bom"),
			"linked_bom custom field missing on BOM Creator Item.",
		)

	def test_get_default_bom_items_override_registered(self):
		mapping = frappe.get_hooks("override_whitelisted_methods") or {}
		self.assertEqual(
			mapping.get(
				"erpnext.manufacturing.doctype.bom_creator.bom_creator.get_default_bom_items"
			),
			["new_bom_creator.overrides.bom_creator.get_default_bom_items"],
		)
