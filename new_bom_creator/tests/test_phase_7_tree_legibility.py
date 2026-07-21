"""Phase 7 tests — tree view legibility.

Covers:
  - _compute_levels correctly assigns depth from root for flat and
    multi-level trees (pure-function unit tests, no DB).
  - JS patch file exists and is loadable.
"""

from unittest.mock import MagicMock
from frappe.tests.utils import FrappeTestCase
from new_bom_creator.overrides.bom_creator import _compute_levels


def _stub_item(name, fg_reference_id, is_root=0):
	m = MagicMock()
	m.name = name
	m.get = lambda k, d=None: {"fg_reference_id": fg_reference_id, "is_root": is_root}.get(k, d)
	return m


class TestComputeLevels(FrappeTestCase):
	def test_single_root(self):
		items = [_stub_item("R", "DOC", is_root=1)]
		levels = _compute_levels(items)
		self.assertEqual(levels, {"R": 0})

	def test_flat_tree(self):
		items = [
			_stub_item("R", "DOC", is_root=1),
			_stub_item("A", "R"),
			_stub_item("B", "R"),
		]
		levels = _compute_levels(items)
		self.assertEqual(levels, {"R": 0, "A": 1, "B": 1})

	def test_three_level_tree(self):
		items = [
			_stub_item("R", "DOC", is_root=1),
			_stub_item("SA", "R"),
			_stub_item("RM1", "SA"),
			_stub_item("RM2", "SA"),
			_stub_item("RM3", "R"),
		]
		levels = _compute_levels(items)
		self.assertEqual(levels, {"R": 0, "SA": 1, "RM1": 2, "RM2": 2, "RM3": 1})

	def test_deep_chain(self):
		items = [
			_stub_item("R", "DOC", is_root=1),
			_stub_item("L1", "R"),
			_stub_item("L2", "L1"),
			_stub_item("L3", "L2"),
			_stub_item("L4", "L3"),
		]
		levels = _compute_levels(items)
		self.assertEqual(levels["L4"], 4)

	def test_empty_items(self):
		self.assertEqual(_compute_levels([]), {})


class TestPhase7JsPatchExists(FrappeTestCase):
	def test_js_patch_file_contains_level_badge(self):
		import os

		js_path = os.path.join(
			os.path.dirname(os.path.dirname(__file__)),
			"public",
			"js",
			"bom_creator_patches.js",
		)
		self.assertTrue(os.path.exists(js_path))
		content = open(js_path).read()
		self.assertIn("nbc-level-badge", content)
		self.assertIn("nbc-level-bar", content)
		self.assertIn("_nbc_get_level", content)
