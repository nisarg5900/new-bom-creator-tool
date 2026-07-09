"""Phase 3 tests — draft output + is_default/is_active + supersede preview.

Tests the pure helpers (_should_submit, _apply_output_control,
_compute_supersede_preview) that both call paths share, plus the schema
plumbing (custom_field fixture + hooks registration).

End-to-end integration (actually generating BOMs on a live site) is
deferred until we have a full Company/Currency/etc. setup — the pure
helpers are what carry the correctness of the fix.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from new_bom_creator.overrides.bom_creator import (
	_apply_output_control,
	_compute_supersede_preview,
	_should_submit,
)


class _StubRow:
	"""Plain object with .get() — a plain dict/frappe._dict would shadow
	the `items` field with the built-in dict.items method.
	"""

	def __init__(self, **kw):
		for k, v in kw.items():
			setattr(self, k, v)

	def get(self, k, default=None):
		return getattr(self, k, default)


class _StubBom:
	"""Minimal stand-in for a BOM doc — only tracks what our code writes."""

	def __init__(self):
		self.is_default = None
		self.is_active = None


class TestOutputMode(FrappeTestCase):
	def test_missing_output_mode_submits(self):
		self.assertTrue(_should_submit(_StubRow()))

	def test_output_mode_submit_submits(self):
		self.assertTrue(_should_submit(_StubRow(output_mode="Submit")))

	def test_output_mode_draft_does_not_submit(self):
		self.assertFalse(_should_submit(_StubRow(output_mode="Draft")))


class TestApplyOutputControl(FrappeTestCase):
	def test_defaults_preserve_previous_behaviour_is_default_1_is_active_1(self):
		bom = _StubBom()
		_apply_output_control(_StubRow(), _StubRow(), bom)
		self.assertEqual(bom.is_default, 1)
		self.assertEqual(bom.is_active, 1)

	def test_explicit_set_as_default_off_produces_is_default_0(self):
		bom = _StubBom()
		_apply_output_control(_StubRow(), _StubRow(set_as_default=0), bom)
		self.assertEqual(bom.is_default, 0)
		# is_active still defaults to 1
		self.assertEqual(bom.is_active, 1)

	def test_explicit_is_active_off_produces_is_active_0(self):
		bom = _StubBom()
		_apply_output_control(_StubRow(), _StubRow(is_active=0), bom)
		self.assertEqual(bom.is_active, 0)


class TestSupersedePreview(FrappeTestCase):
	"""Uses a dedicated Item + BOM fixture created in setUpClass.

	NBC-STEEL: stock item, has a *simulated* existing default BOM row in
	the DB. We don't actually save a real BOM (that requires Company +
	warehouse setup); we insert directly into the DB so the query in
	_compute_supersede_preview finds it.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Reuse the NBC Test item group from Phase 2 (idempotent).
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
		for uom in ["Kg", "Nos"]:
			if not frappe.db.exists("UOM", uom):
				frappe.get_doc({"doctype": "UOM", "uom_name": uom, "name": uom}).insert(
					ignore_permissions=True
				)
		# NBC-STEEL is pre-seeded on this site outside test context — inserting
		# an Item inside a test transaction hits Frappe's global_search
		# "should not fail silently" assert (needs a working queue).
		frappe.db.commit()

	def _fake_existing_default_bom(self, item):
		"""Insert a stub BOM row so _compute_supersede_preview sees it."""
		name = f"NBC-BOM-EXISTING-{item}"
		# Idempotent: skip if a stub for this item already exists.
		if not frappe.db.exists("BOM", {"item": item, "is_default": 1, "docstatus": 1}):
			frappe.db.sql(
				"""
				INSERT INTO `tabBOM`
					(name, item, is_default, is_active, docstatus, quantity, uom, company, creation, modified, modified_by, owner)
				VALUES
					(%s, %s, 1, 1, 1, 1, 'Kg', NULL, NOW(), NOW(), 'Administrator', 'Administrator')
				""",
				(name, item),
			)
			frappe.db.commit()
		return name

	def _make_bom_creator_stub(self, item_code, set_as_default=None, items=None):
		return _StubRow(
			item_code=item_code,
			name="NBC-BC-STUB",
			set_as_default=set_as_default,
			items=items or [],
		)

	def test_no_existing_default_returns_empty_preview(self):
		stub = self._make_bom_creator_stub("NBC-STEEL", set_as_default=1)
		# Ensure no existing default BOM for NBC-STEEL.
		frappe.db.sql("DELETE FROM `tabBOM` WHERE item = 'NBC-STEEL'")
		frappe.db.commit()
		self.assertEqual(_compute_supersede_preview(stub), [])

	def test_existing_default_and_set_as_default_produces_preview(self):
		existing = self._fake_existing_default_bom("NBC-STEEL")
		stub = self._make_bom_creator_stub("NBC-STEEL", set_as_default=1)
		preview = _compute_supersede_preview(stub)
		self.assertEqual(len(preview), 1)
		self.assertEqual(preview[0]["item"], "NBC-STEEL")
		self.assertEqual(preview[0]["existing_default_bom"], existing)
		self.assertTrue(preview[0]["will_become_default"])

	def test_existing_default_but_set_as_default_off_omits_from_preview(self):
		"""User opted out — no supersede, no preview entry."""
		self._fake_existing_default_bom("NBC-STEEL")
		stub = self._make_bom_creator_stub("NBC-STEEL", set_as_default=0)
		self.assertEqual(_compute_supersede_preview(stub), [])


class TestPhase3Fixtures(FrappeTestCase):
	def test_custom_fields_registered_in_hooks(self):
		specs = frappe.get_hooks("fixtures", app_name="new_bom_creator") or []
		# specs may be a list of lists depending on hook resolution
		flat = []
		for entry in specs:
			if isinstance(entry, list):
				flat.extend(entry)
			else:
				flat.append(entry)
		custom_field_spec = next(
			(s for s in flat if isinstance(s, dict) and s.get("dt") == "Custom Field"),
			None,
		)
		self.assertIsNotNone(
			custom_field_spec,
			"Phase 3 Custom Field fixture spec missing from hooks.fixtures.",
		)

	def test_output_mode_field_exists_on_bom_creator(self):
		self.assertIsNotNone(
			frappe.get_meta("BOM Creator").get_field("output_mode"),
			"output_mode custom field missing on BOM Creator.",
		)

	def test_set_as_default_field_exists_on_bom_creator_item(self):
		self.assertIsNotNone(
			frappe.get_meta("BOM Creator Item").get_field("set_as_default"),
			"set_as_default custom field missing on BOM Creator Item.",
		)
