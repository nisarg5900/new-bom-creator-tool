"""Phase 6 tests — navigation entry points.

Covers:
  - doctype_list_js hook registers bom_list.js for the BOM doctype.
  - doctype_js hook registers bom_form.js for the BOM doctype.
  - after_install hook is registered.
  - The workspace shortcut installer doesn't crash (smoke test).
"""

import frappe
from frappe.tests.utils import FrappeTestCase


class TestBomListviewHookRegistered(FrappeTestCase):
	def test_bom_listview_js_hook(self):
		mapping = frappe.get_hooks("doctype_list_js") or {}
		self.assertIn("BOM", mapping)
		paths = mapping["BOM"]
		self.assertTrue(
			any("bom_list.js" in p for p in paths),
			f"bom_list.js not found in doctype_list_js['BOM']: {paths}",
		)

	def test_bom_form_js_hook(self):
		mapping = frappe.get_hooks("doctype_js") or {}
		self.assertIn("BOM", mapping)
		paths = mapping["BOM"]
		self.assertTrue(
			any("bom_form.js" in p for p in paths),
			f"bom_form.js not found in doctype_js['BOM']: {paths}",
		)

	def test_after_install_hook_registered(self):
		hooks = frappe.get_hooks("after_install", app_name="new_bom_creator") or []
		flat = [h for row in hooks for h in (row if isinstance(row, list) else [row])]
		self.assertTrue(
			any("new_bom_creator.install.after_install" in h for h in flat),
			f"after_install hook not registered: {flat}",
		)


class TestWorkspaceShortcutInstaller(FrappeTestCase):
	def test_installer_does_not_crash(self):
		from new_bom_creator.install import _add_workspace_shortcut

		_add_workspace_shortcut()
