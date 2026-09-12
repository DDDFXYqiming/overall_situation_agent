import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from overall_situation_agent import aggregations


class SupplementaryLabelsPathTests(unittest.TestCase):
    def setUp(self):
        aggregations._FOUR_DIM_CACHE = None

    def tearDown(self):
        aggregations._FOUR_DIM_CACHE = None

    def test_unconfigured_path_keeps_optional_mapping_empty(self):
        with patch.dict(os.environ, {'SUPPLEMENTARY_LABELS_FILE': ''}):
            self.assertEqual(aggregations._load_four_dim_mapping(), {})

    def test_explicit_path_is_used(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'labels.xlsx'
            file.touch()
            data = pd.DataFrame([['a', 'b', 'sample-label', '', '平台产品']])
            with patch.dict(os.environ, {'SUPPLEMENTARY_LABELS_FILE': str(file)}), patch('pandas.read_excel', return_value=data) as read:
                result = aggregations._load_four_dim_mapping()
                self.assertEqual(result['sample-label'], ('商业运营', '平台产品'))
                read.assert_called_once_with(file, sheet_name='三级问题标签')

    def test_missing_explicit_path_is_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'SUPPLEMENTARY_LABELS_FILE': str(Path(directory) / 'absent.xlsx')}):
            with self.assertRaises(FileNotFoundError):
                aggregations._load_four_dim_mapping()
