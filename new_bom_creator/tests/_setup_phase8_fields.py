"""Idempotent: create Phase 8 custom fields on the current site."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	fields = {
		"BOM Creator": [
			{
				"fieldname": "nbc_layer2_section",
				"fieldtype": "Section Break",
				"label": "Warehouses & Quality",
				"insert_after": "is_active",
				"collapsible": 1,
				"is_system_generated": 1,
			},
			{
				"fieldname": "default_source_warehouse",
				"fieldtype": "Link",
				"options": "Warehouse",
				"label": "Default Source Warehouse",
				"insert_after": "nbc_layer2_section",
				"is_system_generated": 1,
			},
			{
				"fieldname": "nbc_layer2_column_break",
				"fieldtype": "Column Break",
				"insert_after": "default_source_warehouse",
				"is_system_generated": 1,
			},
			{
				"fieldname": "default_target_warehouse",
				"fieldtype": "Link",
				"options": "Warehouse",
				"label": "Default Target Warehouse",
				"insert_after": "nbc_layer2_column_break",
				"is_system_generated": 1,
			},
			{
				"fieldname": "inspection_required",
				"fieldtype": "Check",
				"label": "Inspection Required",
				"insert_after": "default_target_warehouse",
				"is_system_generated": 1,
			},
			{
				"fieldname": "quality_inspection_template",
				"fieldtype": "Link",
				"options": "Quality Inspection Template",
				"label": "Quality Inspection Template",
				"insert_after": "inspection_required",
				"depends_on": "inspection_required",
				"is_system_generated": 1,
			},
			{
				"fieldname": "backflush_based_on",
				"fieldtype": "Select",
				"label": "Backflush Based On",
				"options": "BOM\nMaterial Transferred for Manufacture",
				"insert_after": "quality_inspection_template",
				"is_system_generated": 1,
			},
			{
				"fieldname": "nbc_operations_section",
				"fieldtype": "Section Break",
				"label": "Operations",
				"insert_after": "backflush_based_on",
				"collapsible": 1,
				"depends_on": "routing",
				"is_system_generated": 1,
			},
			{
				"fieldname": "transfer_material_against",
				"fieldtype": "Select",
				"label": "Transfer Material Against",
				"options": "\nWork Order\nJob Card",
				"insert_after": "nbc_operations_section",
				"depends_on": "routing",
				"is_system_generated": 1,
			},
			{
				"fieldname": "fg_based_operating_cost",
				"fieldtype": "Check",
				"label": "FG Based Operating Cost",
				"insert_after": "transfer_material_against",
				"depends_on": "routing",
				"is_system_generated": 1,
			},
			{
				"fieldname": "nbc_process_loss_section",
				"fieldtype": "Section Break",
				"label": "Process Loss",
				"insert_after": "fg_based_operating_cost",
				"collapsible": 1,
				"is_system_generated": 1,
			},
			{
				"fieldname": "process_loss_percentage",
				"fieldtype": "Percent",
				"label": "% Process Loss",
				"insert_after": "nbc_process_loss_section",
				"is_system_generated": 1,
			},
		],
		"BOM Creator Item": [
			{
				"fieldname": "source_warehouse",
				"fieldtype": "Link",
				"options": "Warehouse",
				"label": "Source Warehouse",
				"insert_after": "linked_bom",
				"is_system_generated": 1,
			},
			{
				"fieldname": "allow_alternative_item",
				"fieldtype": "Check",
				"label": "Allow Alternative Item",
				"default": "1",
				"insert_after": "source_warehouse",
				"is_system_generated": 1,
			},
			{
				"fieldname": "include_item_in_manufacturing",
				"fieldtype": "Check",
				"label": "Include Item In Manufacturing",
				"default": "1",
				"insert_after": "allow_alternative_item",
				"is_system_generated": 1,
			},
		],
	}
	create_custom_fields(fields, update=True)
	frappe.db.commit()
	print("Phase 8 custom fields created.")


if __name__ == "__main__":
	execute()
