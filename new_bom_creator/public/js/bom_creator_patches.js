// Standalone JS patch for BOM Creator: adds a per-line UOM column that
// isn't present in ERPNext <= 16.26.1. On newer erpnext where the column
// exists upstream, the guard checks make this a no-op.
//
// Loaded via doctype_js in new_bom_creator/hooks.py.

frappe.ui.form.on("BOM Creator", {
	refresh(frm) {
		// Phase 4B: "Import from BOM" button on brand-new forms. Runs on
		// every refresh (not gated by the one-shot patched flag below),
		// because add_custom_button doesn't persist across refreshes.
		if (frm.is_new()) {
			frm.add_custom_button(__("Import from BOM"), () => {
				const dialog = new frappe.ui.Dialog({
					title: __("Import from an existing BOM"),
					fields: [
						{
							label: __("BOM"),
							fieldname: "bom_name",
							fieldtype: "Link",
							options: "BOM",
							reqd: 1,
							get_query() {
								return { filters: { docstatus: 1 } };
							},
						},
					],
				});
				dialog.set_primary_action(__("Import"), () => {
					const data = dialog.get_values();
					frappe.call({
						method: "erpnext.manufacturing.doctype.bom_creator.bom_creator.import_from_bom",
						args: { bom_name: data.bom_name },
						freeze: true,
						freeze_message: __("Reconstructing BOM Creator tree..."),
						callback(r) {
							if (r.message) {
								dialog.hide();
								frappe.set_route("Form", "BOM Creator", r.message);
							}
						},
					});
				});
				dialog.show();
			});
		}

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
		// grid, extends item_code change() to prefill UOM, and (Phase 5) adds
		// a top-level Sub Assembly Item change() that auto-populates the grid
		// from the item's default BOM plus a Link BOM as-is checkbox.
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

			// Phase 5: top-level Sub Assembly Item auto-populate + link_only.
			const sub_item_field = fields.find(
				(f) => f.fieldname === "item_code" && f.fieldtype === "Link" && f.options === "Item"
			);
			if (sub_item_field && !sub_item_field._nbc_patched) {
				sub_item_field._nbc_patched = true;
				const orig_change = sub_item_field.change;
				sub_item_field.change = function () {
					if (orig_change) orig_change.call(this);
					const item_code = this.value;
					const dialog = this.layout && this.layout.dialog;
					if (!item_code || !dialog) return;
					frappe.call({
						method:
							"erpnext.manufacturing.doctype.bom_creator.bom_creator.get_default_bom_items",
						args: { item_code },
						callback(r) {
							if (!r.message) return;
							const info = r.message;
							const grid = dialog.fields_dict.items.grid;
							if (grid.data && grid.data.some((row) => row.item_code)) return;
							grid.df.data = info.items.map((it) => ({
								item_code: it.item_code,
								qty: it.qty,
								uom: it.uom,
								conversion_factor: it.conversion_factor,
								stock_qty: it.stock_qty,
								operation: it.operation,
							}));
							grid.refresh();
							const link_only_df = dialog.fields_dict.link_only;
							if (link_only_df) {
								dialog.set_df_property(
									"link_only",
									"description",
									__("Reuse {0} as-is (linked). Raw materials above are for reference.", [
										info.default_bom,
									])
								);
							}
						},
					});
				};
			}
			if (!fields.some((f) => f.fieldname === "link_only")) {
				fields.push({
					fieldname: "link_only",
					label: __("Link BOM as-is (reuse; don't generate new)"),
					fieldtype: "Check",
					default: 0,
					description: __("Requires the item to have a Default BOM."),
				});
			}
			return fields;
		};

		// --- Phase 7: tree view legibility — level badges + expand-to-level -----
		const _NBC_LEVEL_PALETTE = [
			{ bg: "var(--blue-100)", text: "var(--blue-700)", border: "var(--blue-300)" },
			{ bg: "var(--cyan-100)", text: "var(--cyan-700)", border: "var(--cyan-300)" },
			{ bg: "var(--green-100)", text: "var(--green-700)", border: "var(--green-300)" },
			{ bg: "var(--orange-100)", text: "var(--orange-700)", border: "var(--orange-300)" },
			{ bg: "var(--gray-100)", text: "var(--gray-700)", border: "var(--gray-300)" },
		];

		function _nbc_get_level(node) {
			let level = 0;
			let n = node;
			while (n.parent_node) {
				level++;
				n = n.parent_node;
			}
			return level;
		}

		function _nbc_level_color(level) {
			return _NBC_LEVEL_PALETTE[Math.min(level, _NBC_LEVEL_PALETTE.length - 1)];
		}

		if (!document.getElementById("nbc-level-styles")) {
			const style = document.createElement("style");
			style.id = "nbc-level-styles";
			style.textContent = `
				.nbc-level-badge {
					display: inline-block;
					font-size: 10px;
					font-weight: 600;
					padding: 1px 6px;
					border-radius: 3px;
					margin-right: 6px;
					line-height: 16px;
					vertical-align: middle;
					letter-spacing: 0.3px;
				}
				.nbc-level-bar {
					display: flex;
					align-items: center;
					gap: 4px;
					margin-bottom: 8px;
					padding: 4px 0;
				}
				.nbc-level-bar .btn {
					padding: 2px 10px;
					font-size: 11px;
				}
				.nbc-level-bar .btn.btn-primary-dark {
					background-color: var(--primary);
					color: #fff;
				}
				.nbc-level-bar-label {
					font-size: 11px;
					color: var(--text-muted);
					margin-right: 4px;
					white-space: nowrap;
				}
				.tree-node .nbc-node-border {
					border-left: 3px solid transparent;
					padding-left: 4px;
				}
			`;
			document.head.appendChild(style);
		}

		// Wrap tree_methods to augment onrender with level badge + border
		const _orig_tree_methods = BOMConfigurator.prototype.tree_methods;
		BOMConfigurator.prototype.tree_methods = function (...args) {
			const methods = _orig_tree_methods.apply(this, args);
			const orig_onrender = methods.onrender;
			methods.onrender = function (node) {
				if (orig_onrender) orig_onrender.call(this, node);

				const level = _nbc_get_level(node);
				const colors = _nbc_level_color(level);

				// Add level badge before the qty pill
				const $pill = $(node.parent ? node.parent.get(0) : node.$ul)
					.find("> .bom-qty-pill")
					.first();
				if ($pill.length && !$pill.find(".nbc-level-badge").length) {
					$(`<span class="nbc-level-badge" style="background:${colors.bg};color:${colors.text};border:1px solid ${colors.border}">L${level}</span>`).prependTo($pill);
				}

				// Add left border colour to the tree link
				const $link = node.$tree_link;
				if ($link && !$link.hasClass("nbc-node-border")) {
					$link.addClass("nbc-node-border").css("border-left-color", colors.border);
				}
			};
			return methods;
		};

		// Wrap prepare_layout to add the expand-to-level control bar
		const _orig_prepare_layout = BOMConfigurator.prototype.prepare_layout;
		BOMConfigurator.prototype.prepare_layout = function () {
			_orig_prepare_layout.call(this);
			const me = this;
			const $main = $(this.page);

			if ($main.find(".nbc-level-bar").length) return;

			const $bar = $(`
				<div class="nbc-level-bar">
					<span class="nbc-level-bar-label">${__("Expand to level")}:</span>
				</div>
			`);

			function expandToLevel(targetLevel) {
				const tree = frappe.views.trees["BOM Configurator"]?.tree;
				if (!tree) return;

				// Ensure all nodes are loaded first
				const root = tree.root_node;
				if (!root.loaded) {
					tree.load_children(root, true);
				}

				const allNodes = Object.values(tree.nodes);
				allNodes.forEach((n) => {
					if (!n.expandable) return;
					const lvl = _nbc_get_level(n);
					if (lvl < targetLevel) {
						if (!n.expanded) {
							n.$ul.show();
							n.expanded = true;
						}
					} else {
						if (n.expanded) {
							n.$ul.hide();
							n.expanded = false;
						}
					}
				});

				$bar.find(".btn").removeClass("btn-primary-dark btn-primary").addClass("btn-default");
				$bar.find(`.btn[data-nbc-level="${targetLevel}"]`)
					.removeClass("btn-default")
					.addClass("btn-primary-dark");
			}

			for (let i = 1; i <= 5; i++) {
				const $btn = $(`<button class="btn btn-xs btn-default" data-nbc-level="${i}">${i}</button>`);
				$btn.on("click", () => expandToLevel(i));
				$bar.append($btn);
			}

			const $allBtn = $(`<button class="btn btn-xs btn-default" data-nbc-level="99">${__("All")}</button>`);
			$allBtn.on("click", () => {
				const tree = frappe.views.trees["BOM Configurator"]?.tree;
				if (!tree) return;
				tree.load_children(tree.root_node, true);
				$(tree.root_node.parent ? tree.root_node.parent.get(0) : $main.get(0))
					.find(".tree-children")
					.show();
				Object.values(tree.nodes).forEach((n) => {
					if (n.expandable) n.expanded = true;
				});
				$bar.find(".btn").removeClass("btn-primary-dark btn-primary").addClass("btn-default");
				$allBtn.removeClass("btn-default").addClass("btn-primary-dark");
			});
			$bar.append($allBtn);

			$main.prepend($bar);
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
