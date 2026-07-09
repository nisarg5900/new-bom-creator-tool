"""Phase 0 smoke tests.

Verify the hook plumbing is correct and identity wrappers do not change
BOM Creator behaviour. Substantive behaviour tests land in later phases.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.manufacturing.doctype.bom_creator.bom_creator import (
	BOMCreator as CoreBOMCreator,
)

from new_bom_creator.overrides.bom_creator import BOMCreator as OverrideBOMCreator


class TestAppInstalls(FrappeTestCase):
	def test_app_is_installed(self):
		"""new_bom_creator is present on the current site."""
		self.assertIn("new_bom_creator", frappe.get_installed_apps())

	def test_required_apps_declares_erpnext(self):
		hooks = frappe.get_hooks("required_apps", app_name="new_bom_creator") or []
		flat = [a for row in hooks for a in (row if isinstance(row, list) else [row])]
		self.assertIn("erpnext", flat)

	def test_override_doctype_class_registered(self):
		mapping = frappe.get_hooks("override_doctype_class") or {}
		self.assertIn("BOM Creator", mapping)
		self.assertEqual(
			mapping["BOM Creator"][-1],
			"new_bom_creator.overrides.bom_creator.BOMCreator",
		)

	def test_override_whitelisted_methods_registered(self):
		mapping = frappe.get_hooks("override_whitelisted_methods") or {}
		self.assertEqual(
			mapping.get("erpnext.manufacturing.doctype.bom_creator.bom_creator.add_item"),
			["new_bom_creator.overrides.bom_creator.add_item"],
		)
		self.assertEqual(
			mapping.get("erpnext.manufacturing.doctype.bom_creator.bom_creator.add_sub_assembly"),
			["new_bom_creator.overrides.bom_creator.add_sub_assembly"],
		)


class TestIdentityOverrideNoBehaviouralChange(FrappeTestCase):
	"""The Phase 0 override classes/methods are pass-throughs.

	These tests pin that fact so we notice the moment a later phase makes them
	non-identity (which they will — but only intentionally, per that phase's
	own tests).
	"""

	def test_override_class_only_defines_expected_public_methods(self):
		"""Guards against accidental overrides. Update this set each phase.

		Phase 0: {}          (identity subclass)
		Phase 2: add_item, add_sub_assembly (UOM & conversion factor fix)
		Phase 3: create_bom, get_supersede_preview (draft output + default control)
		"""
		self.assertTrue(issubclass(OverrideBOMCreator, CoreBOMCreator))
		override_public_names = {
			n for n in vars(OverrideBOMCreator) if not n.startswith("_")
		}
		expected = {"add_item", "add_sub_assembly", "create_bom", "get_supersede_preview"}
		self.assertEqual(
			override_public_names,
			expected,
			f"Override methods on BOMCreator changed unexpectedly. "
			f"Expected {expected}, got {override_public_names}. "
			f"If this is intentional, update the expected set with a note about the phase.",
		)

	def test_get_controller_returns_override_class(self):
		"""frappe.get_doc('BOM Creator') should use our subclass, not the core class."""
		from frappe.model.base_document import get_controller

		controller = get_controller("BOM Creator")
		self.assertIs(controller, OverrideBOMCreator)

	def test_whitelisted_wrappers_pass_through_to_core(self):
		"""Our add_item / add_sub_assembly forward to the core impls."""
		from new_bom_creator.overrides import bom_creator as ov
		from erpnext.manufacturing.doctype.bom_creator import bom_creator as core

		# The wrappers are registered on frappe's whitelisted set.
		self.assertIn(ov.add_item, frappe.whitelisted)
		self.assertIn(ov.add_sub_assembly, frappe.whitelisted)
		# And the module they forward through is the core module.
		self.assertIs(ov._core, core)
