frappe.listview_settings["BOM"] = frappe.listview_settings["BOM"] || {};

const _orig_onload = frappe.listview_settings["BOM"].onload;

frappe.listview_settings["BOM"].onload = function (listview) {
	if (_orig_onload) _orig_onload.call(this, listview);

	listview.page.add_inner_button(__("Create via BOM Creator"), () => {
		frappe.set_route("Form", "BOM Creator", "new");
	});
};
