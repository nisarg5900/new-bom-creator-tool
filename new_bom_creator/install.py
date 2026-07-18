import frappe


def after_install():
	_add_workspace_shortcut()


def _add_workspace_shortcut():
	"""Add a 'BOM Creator' shortcut to the Manufacturing workspace (if it exists)."""
	if not frappe.db.exists("Workspace", "Manufacturing"):
		return

	existing = frappe.db.exists(
		"Workspace Shortcut",
		{"parent": "Manufacturing", "link_to": "BOM Creator"},
	)
	if existing:
		return

	ws = frappe.get_doc("Workspace", "Manufacturing")
	ws.append(
		"shortcuts",
		{
			"label": "BOM Creator",
			"type": "DocType",
			"link_to": "BOM Creator",
			"color": "Blue",
		},
	)
	ws.flags.ignore_links = True
	ws.save(ignore_permissions=True)
	frappe.db.commit()
