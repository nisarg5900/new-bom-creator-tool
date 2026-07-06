"""Phase 1 tests — dead-field cleanup.

Two dead artefacts in the built-in BOM Creator, verified in ERPNext 16.21.1:

1. bom_creator.js's do_not_explode handler called set_value on "bom_no",
   which is not a field on BOM Creator Item. Both branches were silent
   no-ops.

2. BOM Creator.default_warehouse was defined as a Link field on the header
   but never read anywhere in create_bom() / create_boms() (nor listed in
   BOM_FIELDS). Setting it in the UI had no effect.

The fork branch (nbc/1-dead-fields on nisarg5900/erpnext) removes both.
The standalone app can't remove a field from a core doctype via hooks, so
it hides default_warehouse via a Property Setter fixture — same
user-visible outcome.
"""

import frappe
from frappe.tests.utils import FrappeTestCase


class TestPhase1DeadFields(FrappeTestCase):
	def test_bom_no_absent_from_bom_creator_item(self):
		"""Locks in the assumption behind the JS cleanup.

		If a future ERPNext ever adds `bom_no` to BOM Creator Item, this test
		fails and we know to revisit the fork-side removal of the handler.
		"""
		field = frappe.get_meta("BOM Creator Item").get_field("bom_no")
		self.assertIsNone(
			field,
			"BOM Creator Item now has a 'bom_no' field — the Phase 1 JS cleanup "
			"was written assuming there is none. Revisit nbc/1-dead-fields on "
			"the fork.",
		)

	def test_default_warehouse_hidden_by_fixture(self):
		"""The Property Setter fixture hides default_warehouse on install."""
		field = frappe.get_meta("BOM Creator").get_field("default_warehouse")
		self.assertIsNotNone(
			field,
			"default_warehouse missing from BOM Creator — did erpnext already "
			"drop the field upstream? If so, the fixture is now redundant and "
			"can be removed from new_bom_creator/hooks.py.",
		)
		self.assertEqual(
			field.hidden,
			1,
			"default_warehouse should be hidden by the Phase 1 fixture but is not.",
		)

	def test_property_setter_fixture_registered_in_hooks(self):
		"""Fixture spec must remain in hooks.py so downstream installs get it."""
		from new_bom_creator import hooks

		specs = getattr(hooks, "fixtures", [])
		match = next(
			(
				spec
				for spec in specs
				if spec.get("dt") == "Property Setter"
				and any(
					f == ["field_name", "=", "default_warehouse"]
					for f in spec.get("filters", [])
				)
				and any(
					f == ["doc_type", "=", "BOM Creator"]
					for f in spec.get("filters", [])
				)
			),
			None,
		)
		self.assertIsNotNone(
			match,
			"Phase 1 Property Setter fixture (hide BOM Creator.default_warehouse) "
			"is missing from hooks.fixtures.",
		)
