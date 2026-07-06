"""BOM Creator overrides — Phase 0 identity wrappers.

Every function here is a pass-through to the core erpnext implementation.
The point of this file at Phase 0 is to prove the hook plumbing works
(class swap + whitelisted-method redirect) without changing behaviour.

Substantive changes land in later phases:
- Phase 1: dead-field cleanup (bom_no / default_warehouse).
- Phase 2: UOM & conversion factor in add_item / add_sub_assembly.
- Phase 3: draft output + is_default / is_active control on the class.
- Phase 4: import-from-BOM helper.
- Phase 5: sub-assembly reuse.
"""

import frappe
from erpnext.manufacturing.doctype.bom_creator import bom_creator as _core
from erpnext.manufacturing.doctype.bom_creator.bom_creator import (
	BOMCreator as _CoreBOMCreator,
)


class BOMCreator(_CoreBOMCreator):
	pass


@frappe.whitelist()
def add_item(**kwargs):
	return _core.add_item(**kwargs)


@frappe.whitelist()
def add_sub_assembly(**kwargs):
	return _core.add_sub_assembly(**kwargs)
