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

		// --- Phase 3: supersede-preview dialog ---------------------------------
		// The core create_multi_level_bom handler calls enqueue_create_boms
		// directly. Replace it with one that first asks get_supersede_preview
		// and, if any items' default BOM would be replaced, shows a confirm
		// dialog listing them.
		const handlers = frappe.ui.form.handlers["BOM Creator"] || {};
		handlers["create_multi_level_bom"] = [
			function (frm) {
				frm.call({ method: "get_supersede_preview", doc: frm.doc }).then((r) => {
					const preview = r.message || [];
					const proceed = () => {
						frm.call({ method: "enqueue_create_boms", doc: frm.doc });
					};
					if (!preview.length) {
						proceed();
						return;
					}
					const rows = preview
						.map(
							(p) =>
								`<tr>
									<td>${frappe.utils.escape_html(p.item)}</td>
									<td>${frappe.utils.escape_html(p.existing_default_bom)}</td>
								</tr>`
						)
						.join("");
					const body =
						`<p>${__(
							"The default BOM for the following items will be replaced by the newly-generated BOMs:"
						)}</p>` +
						`<div style="max-height: 240px; overflow-y: auto;">` +
						`<table class="table table-bordered">` +
						`<thead><tr><th>${__("Item")}</th><th>${__(
							"Existing Default BOM"
						)}</th></tr></thead>` +
						`<tbody>${rows}</tbody></table></div>` +
						`<p>${__(
							"Uncheck 'Set as Default BOM' on those items and rerun if you want to keep the current defaults."
						)}</p>`;
					frappe.confirm(body, proceed);
				});
			},
		];
	},
});
