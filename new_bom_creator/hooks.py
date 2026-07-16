app_name = "new_bom_creator"
app_title = "New BOM Creator"
app_publisher = "Nisarg"
app_description = "An improved BOM Creator for ERPNext: closes UOM, draft/default, import, and tree-view gaps in the built-in Multi-level BOM Creator."
app_email = "nisarg6900@gmail.com"
app_license = "gpl-3.0"

# Apps
# ------------------

required_apps = ["erpnext"]

# ---------------------------------------------------------------------------
# BOM Creator overrides (Phase 0 — identity wrappers; no behaviour change yet)
# ---------------------------------------------------------------------------

override_doctype_class = {
	"BOM Creator": "new_bom_creator.overrides.bom_creator.BOMCreator",
}

override_whitelisted_methods = {
	"erpnext.manufacturing.doctype.bom_creator.bom_creator.add_item":
		"new_bom_creator.overrides.bom_creator.add_item",
	"erpnext.manufacturing.doctype.bom_creator.bom_creator.add_sub_assembly":
		"new_bom_creator.overrides.bom_creator.add_sub_assembly",
	# Phase 4B: import_from_bom (present in fork nbc/4 but not yet in the
	# upstream erpnext version this app targets).
	"erpnext.manufacturing.doctype.bom_creator.bom_creator.import_from_bom":
		"new_bom_creator.overrides.bom_creator.import_from_bom",
}

# Phase 2: patch BOMConfigurator on the client for a per-line UOM column
# (absent in older erpnext; no-op if upstream has already added it).
doctype_js = {
	"BOM Creator": "public/js/bom_creator_patches.js",
}

# ---------------------------------------------------------------------------
# Fixtures — shipped Property Setters / Custom Fields that carry the
# hooks-side equivalent of the fork-branch doctype edits.
#
# Phase 1: hide BOM Creator.default_warehouse. On the fork branch we delete
# the field entirely; on the standalone we can't remove a field from a core
# doctype via hooks, so we hide it instead — same user-visible outcome.
# ---------------------------------------------------------------------------
fixtures = [
	{
		"dt": "Property Setter",
		"filters": [
			["doc_type", "=", "BOM Creator"],
			["field_name", "=", "default_warehouse"],
			["property", "=", "hidden"],
		],
	},
	# Phase 3 + 4B: custom fields we ship.
	{
		"dt": "Custom Field",
		"filters": [
			["dt", "in", ["BOM Creator", "BOM Creator Item"]],
			[
				"fieldname",
				"in",
				[
					"output_mode",
					"set_as_default",
					"is_active",
					"nbc_output_control_section",
					"nbc_output_column_break",
					"imported_from_bom",  # Phase 4B
				],
			],
		],
	},
]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "new_bom_creator",
# 		"logo": "/assets/new_bom_creator/logo.png",
# 		"title": "New BOM Creator",
# 		"route": "/new_bom_creator",
# 		"has_permission": "new_bom_creator.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/new_bom_creator/css/new_bom_creator.css"
# app_include_js = "/assets/new_bom_creator/js/new_bom_creator.js"

# include js, css files in header of web template
# web_include_css = "/assets/new_bom_creator/css/new_bom_creator.css"
# web_include_js = "/assets/new_bom_creator/js/new_bom_creator.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "new_bom_creator/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "new_bom_creator/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "new_bom_creator.utils.jinja_methods",
# 	"filters": "new_bom_creator.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "new_bom_creator.install.before_install"
# after_install = "new_bom_creator.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "new_bom_creator.uninstall.before_uninstall"
# after_uninstall = "new_bom_creator.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "new_bom_creator.utils.before_app_install"
# after_app_install = "new_bom_creator.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "new_bom_creator.utils.before_app_uninstall"
# after_app_uninstall = "new_bom_creator.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "new_bom_creator.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "new_bom_creator.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"new_bom_creator.tasks.all"
# 	],
# 	"daily": [
# 		"new_bom_creator.tasks.daily"
# 	],
# 	"hourly": [
# 		"new_bom_creator.tasks.hourly"
# 	],
# 	"weekly": [
# 		"new_bom_creator.tasks.weekly"
# 	],
# 	"monthly": [
# 		"new_bom_creator.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "new_bom_creator.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "new_bom_creator.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "new_bom_creator.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "new_bom_creator.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["new_bom_creator.utils.before_request"]
# after_request = ["new_bom_creator.utils.after_request"]

# Job Events
# ----------
# before_job = ["new_bom_creator.utils.before_job"]
# after_job = ["new_bom_creator.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"new_bom_creator.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

