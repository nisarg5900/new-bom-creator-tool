"""One-shot site fixture seeder for the standalone test site.

Run once on a fresh bomcreator.localhost:

    bench --site bomcreator.localhost execute \\
        new_bom_creator.tests._setup_site_fixtures.seed

Idempotent — safe to re-run. Creates fixtures that can't be created
inside test transactions (Frappe's global_search sync asserts in tests
on inserts of doctypes that participate in global search — Item, UOM,
Company, and their dependencies).

Fixtures created:
    UOM             : Kg, Gram, Nos, Litre
    Item Group      : All Item Groups, NBC Test
    Item            : NBC-POLY (Kg-stock, Gram cf=0.001)
                      NBC-STEEL (Kg-stock)
    Fiscal Year     : 2026-2027
    Warehouse Type  : Transit, Stores, Work In Progress, Finished Goods
    Company         : NBC Test Company (abbr NBC, INR, India, Standard CoA)
                      plus auto-created warehouses under NBC.
"""

import frappe


def seed():
	frappe.local.lang = "en"
	result = []

	# UOMs
	for uom in ["Kg", "Gram", "Nos", "Litre"]:
		if not frappe.db.exists("UOM", uom):
			frappe.get_doc({"doctype": "UOM", "uom_name": uom, "name": uom}).insert(
				ignore_permissions=True
			)
	result.append("UOMs:ok")

	# Item groups
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
	result.append("ItemGroups:ok")

	# Items
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
	if not frappe.db.exists("Item", "NBC-STEEL"):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "NBC-STEEL",
				"item_name": "NBC Test Steel",
				"item_group": "NBC Test",
				"stock_uom": "Kg",
				"is_stock_item": 1,
			}
		).insert(ignore_permissions=True)
	result.append("Items:ok")

	# Fiscal Year
	if not frappe.db.exists("Fiscal Year", "2026-2027"):
		frappe.get_doc(
			{
				"doctype": "Fiscal Year",
				"year": "2026-2027",
				"year_start_date": "2026-04-01",
				"year_end_date": "2027-03-31",
			}
		).insert(ignore_permissions=True)
	result.append("FiscalYear:ok")

	# Warehouse Types (Company creation validates against these)
	for wt in ["Transit", "Stores", "Work In Progress", "Finished Goods"]:
		if not frappe.db.exists("Warehouse Type", wt):
			frappe.get_doc({"doctype": "Warehouse Type", "name": wt}).insert(
				ignore_permissions=True
			)
	result.append("WarehouseTypes:ok")

	# Company (auto-creates warehouses + CoA)
	if not frappe.db.exists("Company", "NBC Test Company"):
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": "NBC Test Company",
				"abbr": "NBC",
				"default_currency": "INR",
				"country": "India",
				"chart_of_accounts": "Standard",
			}
		).insert(ignore_permissions=True)
	result.append("Company:ok")

	frappe.db.commit()
	return result
