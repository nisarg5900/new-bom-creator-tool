// Standalone JS patch for BOM Creator: adds a per-line UOM column that
// isn't present in ERPNext <= 16.26.1. On newer erpnext where the column
// exists upstream, the guard checks make this a no-op.
//
// Loaded via doctype_js in new_bom_creator/hooks.py.

frappe.ui.form.on("BOM Creator", {
	refresh(frm) {
		if (window._nbc_bom_creator_patched) return;
		if (typeof BOMConfigurator === "undefined") return;
		window._nbc_bom_creator_patched = true;

		// --- Patch add_item ---------------------------------------------------
		// The core client uses `frappe.prompt` with just Item + Qty. We swap
		// in a Dialog that also exposes UOM, defaulting to the item's stock UOM.
		BOMConfigurator.prototype.add_item = function (node, view) {
			const bom_configurator = this;
			const dialog = new frappe.ui.Dialog({
				title: __("Add Item"),
				fields: [
					{
						label: __("Item"),
						fieldname: "item_code",
						fieldtype: "Link",
						options: "Item",
						reqd: 1,
						change() {
							const ic = dialog.get_value("item_code");
							if (ic) {
								frappe.db.get_value("Item", ic, "stock_uom").then((r) => {
									const su = r.message && r.message.stock_uom;
									if (su && !dialog.get_value("uom")) {
										dialog.set_value("uom", su);
									}
								});
							}
						},
					},
					{ label: __("Qty"), fieldname: "qty", default: 1.0, fieldtype: "Float", reqd: 1 },
					{
						label: __("UOM"),
						fieldname: "uom",
						fieldtype: "Link",
						options: "UOM",
						reqd: 1,
						description: __(
							"Must be listed in the item's UOM Conversion table. Server computes the conversion factor."
						),
					},
				],
			});
			dialog.set_primary_action(__("Add"), () => {
				const data = dialog.get_values();
				if (!node.data.parent_id) {
					node.data.parent_id = bom_configurator.frm.doc.name;
				}
				frappe.call({
					method: "erpnext.manufacturing.doctype.bom_creator.bom_creator.add_item",
					args: {
						parent: bom_configurator.frm.doc.name,
						fg_item: node.data.value,
						item_code: data.item_code,
						fg_reference_id: node.data.name || bom_configurator.frm.doc.name,
						qty: data.qty,
						uom: data.uom,
					},
					callback: (r) => {
						view.events.load_tree(r, node);
					},
				});
				dialog.hide();
			});
			dialog.show();
		};

		// --- Patch get_sub_assembly_modal_fields ------------------------------
		// Wraps the core method to inject a UOM column into the Raw Materials
		// grid, and extends the item_code change() to prefill UOM = stock_uom.
		const orig_gsmf = BOMConfigurator.prototype.get_sub_assembly_modal_fields;
		BOMConfigurator.prototype.get_sub_assembly_modal_fields = function (...args) {
			const fields = orig_gsmf.apply(this, args);
			const items = fields.find((f) => f.fieldname === "items");
			if (items && !items.fields.some((f) => f.fieldname === "uom")) {
				items.fields.push({
					label: __("UOM"),
					fieldname: "uom",
					fieldtype: "Link",
					options: "UOM",
					reqd: 1,
					in_list_view: 1,
				});
				const item_code_field = items.fields.find((f) => f.fieldname === "item_code");
				if (item_code_field) {
					const orig_change = item_code_field.change;
					item_code_field.change = function () {
						if (orig_change) orig_change.call(this);
						const doc = this.doc;
						if (doc && doc.item_code) {
							frappe.db.get_value("Item", doc.item_code, "stock_uom").then((r) => {
								const su = r.message && r.message.stock_uom;
								if (su) this.grid.set_value("uom", su, doc);
							});
						}
					};
				}
			}
			return fields;
		};
	},
});
