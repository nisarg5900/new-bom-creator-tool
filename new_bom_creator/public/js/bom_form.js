frappe.ui.form.on("BOM", {
	refresh(frm) {
		if (frm.is_new()) {
			frm.add_custom_button(
				__("Switch to BOM Creator"),
				() => {
					frappe.set_route("Form", "BOM Creator", "new");
				},
				__("Create")
			);
		}
	},
});
