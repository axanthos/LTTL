from __future__ import absolute_import
from __future__ import unicode_literals

from LTTL.Input import Input
from LTTL.Table import IntPivotCrosstab
import LTTL.Segmenter as Segmenter
import LTTL.Processor as Processor

import re

import unittest

__version__ = "1.0.0"


class TestCooc(unittest.TestCase):

    def setUp(self):
        input_seg = Input("un texte")
        word_seg = Segmenter.tokenize(
            input_seg,
            [(re.compile(r'\w+'), 'tokenize')],
            import_annotations=False,
        )
        letter_seg = Segmenter.tokenize(
            input_seg,
            [
                (re.compile(r'\w'), 'tokenize', {'type': 'C'}),
                (re.compile(r'[aeiouy]'), 'tokenize', {'type': 'V'}),
            ],
            import_annotations=False,
            merge_duplicates=True,
        )
        print letter_seg.to_string()
        vowel_seg, consonant_seg = Segmenter.select(
            letter_seg,
            re.compile(r'V'),
            annotation_key='type',
        )
        print vowel_seg.to_string()

        #  Create the cooccurrence matrix for cooccurrence in window
        #  with window_size=3 and without annotation (woa):
        self.window_woa_row_ids = ['u', 'n', 't', 'e', 'x']
        self.window_woa_col_ids = ['u', 'n', 't', 'e', 'x']
        self.window_woa_values = {
            ('u', 'u'): 1,
            ('u', 'n'): 1,
            ('u', 't'): 1,
            ('u', 'e'): 0,
            ('u', 'x'): 0,
            ('n', 'u'): 1,
            ('n', 'n'): 2,
            ('n', 't'): 2,
            ('n', 'e'): 1,
            ('n', 'x'): 0,
            ('t', 'u'): 1,
            ('t', 'n'): 2,
            ('t', 't'): 5,
            ('t', 'e'): 4,
            ('t', 'x'): 3,
            ('e', 'u'): 0,
            ('e', 'n'): 1,
            ('e', 't'): 4,
            ('e', 'e'): 4,
            ('e', 'x'): 3,
            ('x', 'u'): 0,
            ('x', 'n'): 0,
            ('x', 't'): 3,
            ('x', 'e'): 3,
            ('x', 'x'): 3,
        }
        self.window_woa_header_row_id = '__unit__'
        self.window_woa_header_row_type = 'string'
        self.window_woa_header_col_id = '__unit__'
        self.window_woa_header_col_type = 'string'
        self.window_woa_col_type = {
            col_id: 'continuous' for col_id in self.window_woa_col_ids
        }
        self.window_woa_ref = IntPivotCrosstab(
            self.window_woa_row_ids,
            self.window_woa_col_ids,
            self.window_woa_values,
            self.window_woa_header_row_id,
            self.window_woa_header_row_type,
            self.window_woa_header_col_id,
            self.window_woa_header_col_type,
            self.window_woa_col_type,
        )
        #  Create the cooccurrence matrix for cooccurrence in window
        #  with window_size=3 and with annotation (wa):
        self.window_wa_row_ids = ['C', 'V']
        self.window_wa_col_ids = ['C', 'V']
        self.window_wa_values = {
            ('C', 'C'): 5,
            ('C', 'V'): 5,
            ('V', 'C'): 5,
            ('V', 'V'): 5,
        }
        self.window_wa_header_row_id = '__unit__'
        self.window_wa_header_row_type = 'string'
        self.window_wa_header_col_id = '__unit__'
        self.window_wa_header_col_type = 'string'
        self.window_wa_col_type = {
            col_id: 'continuous' for col_id in self.window_wa_col_ids
        }
        self.window_wa_ref = IntPivotCrosstab(
            self.window_wa_row_ids,
            self.window_wa_col_ids,
            self.window_wa_values,
            self.window_wa_header_row_id,
            self.window_wa_header_row_type,
            self.window_wa_header_col_id,
            self.window_wa_header_col_type,
            self.window_wa_col_type,
        )
        # Create the cooccurrence matrix for cooccurrence in context
        # without the secondary unit (wos) and without annotation (woa):
        self.context_wos_woa_row_ids = ['u', 'n', 't', 'e', 'x']
        self.context_wos_woa_col_ids = ['u', 'n', 't', 'e', 'x']
        self.context_wos_woa_values = {
            ('u', 'u'): 1,
            ('u', 'n'): 1,
            ('u', 't'): 0,
            ('u', 'e'): 0,
            ('u', 'x'): 0,
            ('n', 'u'): 1,
            ('n', 'n'): 1,
            ('n', 't'): 0,
            ('n', 'e'): 0,
            ('n', 'x'): 0,
            ('t', 'u'): 0,
            ('t', 'n'): 0,
            ('t', 't'): 1,
            ('t', 'e'): 1,
            ('t', 'x'): 1,
            ('e', 'u'): 0,
            ('e', 'n'): 0,
            ('e', 't'): 1,
            ('e', 'e'): 1,
            ('e', 'x'): 1,
            ('x', 'u'): 0,
            ('x', 'n'): 0,
            ('x', 't'): 1,
            ('x', 'e'): 1,
            ('x', 'x'): 1,
        }
        self.context_wos_woa_header_row_id = '__context__'
        self.context_wos_woa_header_row_type = 'string'
        self.context_wos_woa_header_col_id = '__context__'
        self.context_wos_woa_header_col_type = 'string'
        self.context_wos_woa_col_type = {
            col_id: 'continuous' for col_id in self.context_wos_woa_col_ids
        }
        self.context_wos_woa_ref = IntPivotCrosstab(
            self.context_wos_woa_row_ids,
            self.context_wos_woa_col_ids,
            self.context_wos_woa_values,
            self.context_wos_woa_header_row_id,
            self.context_wos_woa_header_row_type,
            self.context_wos_woa_header_col_id,
            self.context_wos_woa_header_col_type,
            self.context_wos_woa_col_type,
        )
        # Create the cooccurrence matrix for cooccurrence in context
        # without the secondary unit (wos) and with annotation (wa):
        self.context_wos_wa_row_ids = ['V', 'C']
        self.context_wos_wa_col_ids = ['V', 'C']
        self.context_wos_wa_values = {
            ('V', 'V'): 2,
            ('V', 'C'): 2,
            ('C', 'V'): 2,
            ('C', 'C'): 2,
        }
        self.context_wos_wa_header_row_id = '__context__'
        self.context_wos_wa_header_row_type = 'string'
        self.context_wos_wa_header_col_id = '__context__'
        self.context_wos_wa_header_col_type = 'string'
        self.context_wos_wa_col_type = {
            col_id: 'continuous' for col_id in self.context_wos_wa_col_ids
        }
        self.context_wos_wa_ref = IntPivotCrosstab(
            self.context_wos_wa_row_ids,
            self.context_wos_wa_col_ids,
            self.context_wos_wa_values,
            self.context_wos_wa_header_row_id,
            self.context_wos_wa_header_row_type,
            self.context_wos_wa_header_col_id,
            self.context_wos_wa_header_col_type,
            self.context_wos_wa_col_type,
        )
        # Create the cooccurrence matrix for cooccurrence in context
        # with the secondary unit (ws) and without annotation (woa):
        self.context_ws_woa_col_ids = ['u', 'e']
        self.context_ws_woa_row_ids = ['n', 't', 'x']
        self.context_ws_woa_values = {
            ('n', 'u'): 1,
            ('n', 'e'): 0,
            ('t', 'u'): 0,
            ('t', 'e'): 1,
            ('x', 'u'): 0,
            ('x', 'e'): 1,
        }
        self.context_ws_woa_header_row_id = '__context__'
        self.context_ws_woa_header_row_type = 'string'
        self.context_ws_woa_header_col_id = '__context__'
        self.context_ws_woa_header_col_type = 'string'
        self.context_ws_woa_col_type = {
            col_id: 'continuous' for col_id in self.context_ws_woa_col_ids
        }
        self.context_ws_woa_ref = IntPivotCrosstab(
            self.context_ws_woa_row_ids,
            self.context_ws_woa_col_ids,
            self.context_ws_woa_values,
            self.context_ws_woa_header_row_id,
            self.context_ws_woa_header_row_type,
            self.context_ws_woa_header_col_id,
            self.context_ws_woa_header_col_type,
            self.context_ws_woa_col_type,
        )
        # Create the cooccurrence matrix for cooccurrence in context
        # with the secondary unit (ws) and with annotation (wa):
        self.context_ws_wa_row_ids = ['C']
        self.context_ws_wa_col_ids = ['V']
        self.context_ws_wa_values = {
            ('C', 'V'): 2,
        }
        self.context_ws_wa_header_row_id = '__context__'
        self.context_ws_wa_header_row_type = 'string'
        self.context_ws_wa_header_col_id = '__context__'
        self.context_ws_wa_header_col_type = 'string'
        self.context_ws_wa_col_type = {
            col_id: 'continuous' for col_id in self.context_ws_wa_col_ids
        }
        self.context_ws_wa_ref = IntPivotCrosstab(
            self.context_ws_wa_row_ids,
            self.context_ws_wa_col_ids,
            self.context_ws_wa_values,
            self.context_ws_wa_header_row_id,
            self.context_ws_wa_header_row_type,
            self.context_ws_wa_header_col_id,
            self.context_ws_wa_header_col_type,
            self.context_ws_wa_col_type,
        )
        self.output_cooc_in_window_woa = Processor.cooc_in_window(
            units={'segmentation': letter_seg},
            window_size=3,
        )
        self.output_cooc_in_window_wa = Processor.cooc_in_window(
            units={'segmentation': letter_seg, 'annotation_key': 'type'},
            window_size=3,
        )
        self.output_cooc_in_context_wos_woa = Processor.cooc_in_context(
            units={'segmentation': letter_seg},
            contexts={'segmentation': word_seg},
            units2=None,
        )
        self.output_cooc_in_context_wos_wa = Processor.cooc_in_context(
            units={'segmentation': letter_seg, 'annotation_key': 'type'},
            contexts={'segmentation': word_seg},
            units2=None,
        )
        self.output_cooc_in_context_ws_woa = Processor.cooc_in_context(
            units={'segmentation': vowel_seg},
            contexts={'segmentation': word_seg},
            units2={'segmentation': consonant_seg},
        )
        print Processor.count_in_context(
            units={'segmentation': vowel_seg},
            contexts={'segmentation': word_seg},
        ).to_string()
        print Processor.count_in_context(
            units={'segmentation': consonant_seg},
            contexts={'segmentation': word_seg},
        ).to_string()
        self.output_cooc_in_context_ws_wa = Processor.cooc_in_context(
            units={'segmentation': vowel_seg, 'annotation_key': 'type'},
            contexts={'segmentation': word_seg},
            units2={'segmentation': consonant_seg, 'annotation_key': 'type'},
        )
        print self.output_cooc_in_window_wa.values
        print self.output_cooc_in_window_woa.values

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Testing the table format to see if it is an IntPivotCrosstab
    # For all the co-occurrence methods and all possible parameters

    # 1. Co-occurrence in window without annotation:
    def test_cooc_window_woa_table_format(self):
        self.assertIsInstance(
            self.output_cooc_in_window_woa,
            IntPivotCrosstab,
        )

    # 2. Co-occurrence in window with annotation:
    def test_cooc_window_wa_table_format(self):
        self.assertIsInstance(
            self.output_cooc_in_window_wa,
            IntPivotCrosstab,
        )

    # 3. Co-occurrence in context without secondary unit and without annotation:
    def test_cooc_context_wos_woa_format(self):
        self.assertIsInstance(
            self.output_cooc_in_context_wos_woa,
            IntPivotCrosstab,
        )

    # 4. Co_occurrence in context wihout a secondary unit and with annotation:
    def test_cooc_context_wos_wa_format(self):
        self.assertIsInstance(
            self.output_cooc_in_context_wos_wa,
            IntPivotCrosstab,
        )

    # 5. Co_occurrence in context wih a secondary unit and without annotation:
    def test_cooc_context_ws_woa_format(self):
        self.assertIsInstance(
            self.output_cooc_in_context_ws_woa,
            IntPivotCrosstab,
        )

    # 6. Co_occurrence in context wih a secondary unit and with annotation:
    def test_cooc_context_ws_wa_format(self):
        self.assertIsInstance(
            self.output_cooc_in_context_ws_wa,
            IntPivotCrosstab,
        )

    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Testing the row ids, check if the row ids of the output of the function
    # correspond to the refrence table.
    # For all the co-occurrence methods and all possible parameters

    # 1. Co-occurrence in window without annotation:
    def test_cooc_window_woa_row_ids(self):
        self.assertItemsEqual(
            self.output_cooc_in_window_woa.row_ids,
            self.window_woa_row_ids,
        )

    # 2. Co-occurrence in window with annotation:
    def test_cooc_window_wa_row_ids(self):
        self.assertItemsEqual(
            self.output_cooc_in_window_wa.row_ids,
            self.window_wa_row_ids,
        )

    # 3. Co-occurrence in context without secondary unit and without annotation:
    def test_cooc_context_wos_woa_row_ids(self):
        self.assertItemsEqual(
            self.output_cooc_in_context_wos_woa.row_ids,
            self.context_wos_woa_row_ids,
        )

    # 4. Co_occurrence in context wihout a secondary unit and with annotation:
    def test_cooc_context_wos_wa_row_ids(self):
        self.assertItemsEqual(
            self.output_cooc_in_context_wos_wa.row_ids,
            self.context_wos_wa_row_ids,
        )

    # 5. Co_occurrence in context wih a secondary unit and without annotation:
    def test_cooc_context_ws_woa_row_ids(self):
        self.assertItemsEqual(
            self.output_cooc_in_context_ws_woa.row_ids,
            self.context_ws_woa_row_ids,
        )

    # 6. Co_occurrence in context wih a secondary unit and with annotation:
    def test_cooc_context_ws_wa_row_ids(self):
        self.assertItemsEqual(
            self.output_cooc_in_context_ws_wa.row_ids,
            self.context_ws_wa_row_ids,
        )

    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Testing the column ids, check if column ids of the output of the function
    # correspond to the reference table.
    # For all the co-occurrence methods and all possible parameters

    # 1. Co-occurrence in window without annotation:
    def test_cooc_window_woa_col_ids(self):
        self.assertItemsEqual(
            self.output_cooc_in_window_woa.col_ids,
            self.window_woa_col_ids,
        )

    # 2. Co-occurrence in window with annotation:
    def test_cooc_window_wa_col_ids(self):
        self.assertItemsEqual(
            self.output_cooc_in_window_wa.col_ids,
            self.window_wa_col_ids,
        )

    # 3. Co-occurrence in context without secondary unit and without annotation:
    def test_cooc_context_wos_woa_col_ids(self):
        self.assertItemsEqual(
            self.output_cooc_in_context_wos_woa.col_ids,
            self.context_wos_woa_col_ids,
        )

    # 4. Co_occurrence in context wihout a secondary unit and with annotation:
    def test_cooc_context_wos_wa_col_ids(self):
        self.assertItemsEqual(
            self.output_cooc_in_context_wos_wa.col_ids,
            self.context_wos_wa_col_ids,
        )

    # 5. Co_occurrence in context wih a secondary unit and without annotation:
    def test_cooc_context_ws_woa_col_ids(self):
        self.assertItemsEqual(
            self.output_cooc_in_context_ws_woa.col_ids,
            self.context_ws_woa_col_ids,
        )

    # 6. Co_occurrence in context wih a secondary unit and with annotation:
    def test_cooc_context_ws_wa_col_ids(self):
        self.assertItemsEqual(
            self.output_cooc_in_context_ws_wa.col_ids,
            self.context_ws_wa_col_ids,
        )

    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Testing the values, check if the values in the output of the function
    # correspond  to the reference table.
    # For all the co-occurrence methods and all possible parameters

    # 1. Co-occurrence in window without annotation:
    def test_cooc_window_woa_values(self):
        self.assertEqual(
            self.output_cooc_in_window_woa.values,
            self.window_woa_values,
        )

    # 2. Co-occurrence in window with annotation:
    def test_cooc_window_wa_values(self):
        self.assertEqual(
            self.output_cooc_in_window_wa.values,
            self.window_wa_values,
        )

    # 3. Co-occurrence in context without secondary unit and without annotation:
    def test_cooc_context_wos_woa_values(self):
        self.assertEqual(
            self.output_cooc_in_context_wos_woa.values,
            self.context_wos_woa_values,
        )

    # 4. Co_occurrence in context wihout a secondary unit and with annotation:
    def test_cooc_context_wos_wa_values(self):
        self.assertEqual(
            self.output_cooc_in_context_wos_wa.values,
            self.context_wos_wa_values,
        )

    # 5. Co_occurrence in context wih a secondary unit and without annotation:
    def test_cooc_context_ws_woa_values(self):
        self.assertEqual(
            self.output_cooc_in_context_ws_woa.values,
            self.context_ws_woa_values,
        )

    # 6. Co_occurrence in context wih a secondary unit and with annotation:
    def test_cooc_context_ws_wa_values(self):
        self.assertEqual(
            self.output_cooc_in_context_ws_wa.values,
            self.context_ws_wa_values,
        )

    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Check if header row id of the output of the function
    # correspond to the reference table.
    # For all the co-occurrence methods and all possible parameters

    # 1. Co-occurrence in window without annotation:
    def test_cooc_window_woa_header_row_id(self):
        self.assertEqual(
            self.output_cooc_in_window_woa.header_row_id,
            self.window_woa_header_row_id,
        )

    # 2. Co-occurrence in window with annotation:
    def test_cooc_window_wa_table_header_row_id(self):
        self.assertEqual(
            self.output_cooc_in_window_wa.header_row_id,
            self.window_wa_header_row_id,
        )

    # 3. Co-occurrence in context without secondary unit and without annotation:
    def test_cooc_context_wos_woa_header_row_id(self):
        self.assertEqual(
            self.output_cooc_in_context_wos_woa.header_row_id,
            self.context_wos_woa_header_row_id,
        )

    # 4. Co_occurrence in context wihout a secondary unit and with annotation:
    def test_cooc_context_wos_wa_header_row_id(self):
        self.assertEqual(
            self.output_cooc_in_context_wos_wa.header_row_id,
            self.context_wos_wa_header_row_id,
        )

    # 5. Co_occurrence in context wih a secondary unit and without annotation:
    def test_cooc_context_ws_woa_header_row_id(self):
        self.assertEqual(
            self.output_cooc_in_context_ws_woa.header_row_id,
            self.context_ws_woa_header_row_id,
        )

    # 6. Co_occurrence in context wih a secondary unit and with annotation:
    def test_cooc_context_ws_wa_header_row_id(self):
        self.assertEqual(
            self.output_cooc_in_context_ws_wa.header_row_id,
            self.context_ws_wa_header_row_id,
        )

    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Check if header row type of the output of the function
    # correspond to the reference table.
    # For all the co-occurrence methods and all possible parameters

    # 1. Co-occurrence in window without annotation:
    def test_cooc_window_woa_header_row_type(self):
        self.assertEqual(
            self.output_cooc_in_window_woa.header_row_type,
            self.window_woa_header_row_type,
        )

    # 2. Co-occurrence in window with annotation:
    def test_cooc_window_wa_table_header_row_type(self):
        self.assertEqual(
            self.output_cooc_in_window_wa.header_row_type,
            self.window_wa_header_row_type,
        )

    # 3. Co-occurrence in context without secondary unit and without annotation:
    def test_cooc_context_wos_woa_header_row_type(self):
        self.assertEqual(
            self.output_cooc_in_context_wos_woa.header_row_type,
            self.context_wos_woa_header_row_type,
        )

    # 4. Co_occurrence in context wihout a secondary unit and with annotation:
    def test_cooc_context_wos_wa_header_row_type(self):
        self.assertEqual(
            self.output_cooc_in_context_wos_wa.header_row_type,
            self.context_wos_wa_header_row_type,
        )

    # 5. Co_occurrence in context wih a secondary unit and without annotation:
    def test_cooc_context_ws_woa_header_row_type(self):
        self.assertEqual(
            self.output_cooc_in_context_ws_woa.header_row_type,
            self.context_ws_woa_header_row_type,
        )

    # 6. Co_occurrence in context wih a secondary unit and with annotation:
    def test_cooc_context_ws_wa_header_row_type(self):
        self.assertEqual(
            self.output_cooc_in_context_ws_wa.header_row_type,
            self.context_ws_wa_header_row_type,
        )

    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Check if header column id of the output of the
    # function correspond to the reference table.
    # For all the co-occurrence methods and all possible parameters

    # 1. Co-occurrence in window without annotation:
    def test_cooc_window_woa_header_col_id(self):
        self.assertEqual(
            self.output_cooc_in_window_woa.header_col_id,
            self.window_woa_header_col_id,
        )

    # 2. Co-occurrence in window with annotation:
    def test_cooc_window_wa_table_header_col_id(self):
        self.assertEqual(
            self.output_cooc_in_window_wa.header_col_id,
            self.window_wa_header_col_id,
        )

    # 3. Co-occurrence in context without secondary unit and without annotation:
    def test_cooc_context_wos_woa_header_col_id(self):
        self.assertEqual(
            self.output_cooc_in_context_wos_woa.header_col_id,
            self.context_wos_woa_header_col_id,
        )

    # 4. Co_occurrence in context wihout a secondary unit and with annotation:
    def test_cooc_context_wos_wa_header_col_id(self):
        self.assertEqual(
            self.output_cooc_in_context_wos_wa.header_col_id,
            self.context_wos_wa_header_col_id,
        )

    # 5. Co_occurrence in context wih a secondary unit and without annotation:
    def test_cooc_context_ws_woa_header_col_id(self):
        self.assertEqual(
            self.output_cooc_in_context_ws_woa.header_col_id,
            self.context_ws_woa_header_col_id,
        )

    # 6. Co_occurrence in context wih a secondary unit and with annotation:
    def test_cooc_context_ws_wa_header_col_id(self):
        self.assertEqual(
            self.output_cooc_in_context_ws_wa.header_col_id,
            self.context_ws_wa_header_col_id,
        )

    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Check if header column id of the output of the
    # function correspond to the reference table.
    # For all the co-occurrence methods and all possible parameters

    # 1. Co-occurrence in window without annotation:
    def test_cooc_window_woa_header_col_type(self):
        self.assertEqual(
            self.output_cooc_in_window_woa.header_col_type,
            self.window_woa_header_col_type,
        )

    # 2. Co-occurrence in window with annotation:
    def test_cooc_window_wa_table_header_col_type(self):
        self.assertEqual(
            self.output_cooc_in_window_wa.header_col_type,
            self.window_wa_header_col_type,
        )

    # 3. Co-occurrence in context without secondary unit and without annotation:
    def test_cooc_context_wos_woa_header_col_type(self):
        self.assertEqual(
            self.output_cooc_in_context_wos_woa.header_col_type,
            self.context_wos_woa_header_col_type,
        )

    # 4. Co_occurrence in context wihout a secondary unit and with annotation:
    def test_cooc_context_wos_wa_header_col_type(self):
        self.assertEqual(
            self.output_cooc_in_context_wos_wa.header_col_type,
            self.context_wos_wa_header_col_type,
        )

    # 5. Co_occurrence in context wih a secondary unit and without annotation:
    def test_cooc_context_ws_woa_header_col_type(self):
        self.assertEqual(
            self.output_cooc_in_context_ws_woa.header_col_type,
            self.context_ws_woa_header_col_type,
        )

    # 6. Co_occurrence in context wih a secondary unit and with annotation:
    def test_cooc_context_ws_wa_header_col_type(self):
        self.assertEqual(
            self.output_cooc_in_context_ws_wa.header_col_type,
            self.context_ws_wa_header_col_type,
        )

    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Testing the column type, check if column type of the output of the
    # function correspond to the reference table.
    # For all the co-occurrence methods and all possible parameters

    # 1. Co-occurrence in window without annotation:
    def test_cooc_window_woa_col_type(self):
        for col_type in self.output_cooc_in_window_woa.col_type.values():
                        self.assertEqual(col_type, 'continuous')

    # 2. Co-occurrence in window with annotation:
    def test_cooc_window_wa_table_col_type(self):
        for col_type in self.output_cooc_in_window_wa.col_type.values():
                        self.assertEqual(col_type, 'continuous')

    # 3. Co-occurrence in context without secondary unit and without annotation:
    def test_cooc_context_wos_woa_col_type(self):
        for col_type in self.output_cooc_in_context_wos_woa.col_type.values():
                        self.assertEqual(col_type, 'continuous')

    # 4. Co_occurrence in context wihout a secondary unit and with annotation:
    def test_cooc_context_wos_wa_col_type(self):
        for col_type in self.output_cooc_in_context_wos_wa.col_type.values():
                        self.assertEqual(col_type, 'continuous')

    # 5. Co_occurrence in context wih a secondary unit and without annotation:
    def test_cooc_context_ws_woa_col_type(self):
        for col_type in self.output_cooc_in_context_ws_wa.col_type.values():
                        self.assertEqual(col_type, 'continuous')

    # 6. Co_occurrence in context wih a secondary unit and with annotation:
    def test_cooc_context_ws_wa_col_type(self):
        for col_type in self.output_cooc_in_context_ws_wa.col_type.values():
                        self.assertEqual(col_type, 'continuous')


if __name__ == '__main__':
    unittest.main(verbosity=42)
