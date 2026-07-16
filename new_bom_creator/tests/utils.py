"""Test fixture helpers shared across phases.

Some fixtures are seeded outside test transactions because Frappe's
global_search sync asserts in tests on inserts of doctypes that
participate in global search (Item, UOM, Company). Pre-seed script:

    bench --site bomcreator.localhost execute \\
        new_bom_creator.tests._setup_site_fixtures.seed

Pre-seeded on bomcreator.localhost:
  UOM             : Kg, Gram, Litre
  Item Group      : All Item Groups, NBC Test
  Item            : NBC-POLY (Kg-stock, Gram cf=0.001)
                    NBC-STEEL (Kg-stock)
  Fiscal Year     : 2026-2027
  Warehouse Type  : Transit, Stores, Work In Progress, Finished Goods
  Company         : NBC Test Company (abbr NBC, INR, India, Standard CoA)
"""

import frappe

TEST_COMPANY = "NBC Test Company"
TEST_COMPANY_ABBR = "NBC"
TEST_CURRENCY = "INR"


def new_bom_creator(item_code, qty=1, output_mode="Draft", set_as_default=None, is_active=None):
	# BOM Creator uses autoname="prompt"; supply a unique name explicitly.
	import time

	doc = frappe.new_doc("BOM Creator")
	doc.name = f"NBC-TEST-{item_code}-{int(time.time() * 1000)}"
	doc.item_code = item_code
	doc.qty = qty
	doc.company = TEST_COMPANY
	doc.currency = TEST_CURRENCY
	doc.conversion_rate = 1.0
	doc.rm_cost_as_per = "Valuation Rate"
	doc.output_mode = output_mode
	if set_as_default is not None:
		doc.set_as_default = set_as_default
	if is_active is not None:
		doc.is_active = is_active
	return doc


def cleanup_generated_boms(bom_creator_name):
	boms = frappe.get_all("BOM", filters={"bom_creator": bom_creator_name}, pluck="name")
	for name in boms:
		frappe.db.sql("DELETE FROM `tabBOM Item` WHERE parent = %s", (name,))
		frappe.db.sql("DELETE FROM `tabBOM Operation` WHERE parent = %s", (name,))
		frappe.db.sql("DELETE FROM `tabBOM` WHERE name = %s", (name,))
	frappe.db.commit()
