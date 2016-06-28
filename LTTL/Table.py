"""Module Table.py
Copyright 2012-2016 LangTech Sarl (info@langtech.ch)
---------------------------------------------------------------------------
This file is part of the LTTL package v2.0.

LTTL v2.0 is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

LTTL v2.0 is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with LTTL v2.0. If not, see <http://www.gnu.org/licenses/>.
---------------------------------------------------------------------------
Provides classes:
- Table
- Crosstab(Table)
- PivotCrosstab(Crosstab)
- FlatCrosstab(Crosstab)
- WeightedFlatCrosstab(Crosstab)
- IntPivotCrosstab(PivotCrosstab)
- IntWeightedFlatCrosstab(WeightedFlatCrosstab)
"""

from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

import numpy as np
from scipy.sparse import dok_matrix, isspmatrix

import os
import math
import sys
import six

from builtins import str as text
from future.utils import iteritems

__version__ = "1.0.0"


class Table(object):
    """Base class for tables in LTTL."""

    # TODO: modify client code (signature change: header_row/col).
    def __init__(
        self,
        row_ids,
        col_ids,
        values,
        header_row_id='__col__',    # formerly header_row['id']
        header_row_type='string',   # formerly header_row['type']
        header_col_id='__row__',    # formerly header_col['id']
        header_col_type='string',   # formerly header_col['type']
        col_type=None,
        class_col_id=None,
        missing=None,
        _cached_row_id=None,
        row_mapping=None,
        col_mapping=None,
    ):
        """Initialize a Table.

        :param row_ids: list of items (usually strings) used as row ids

        :param col_ids: list of items (usually strings) used as col ids

        :param values: dictionary containing storing values of the table's
        cells; keys are (row_id, col_id) tuples. Or it can be a numpy array
        that will be used directly as a dense matrix or a scipy.sparse matrix.
        In the case of a dictionnary, all col_types are expected to be
        identical.

        :param header_row_id: id of header row (default '__col__')

        :param header_row_type: a string indicating the type of header row
        (default 'string', other possible values 'continuous' and 'discrete')

        :param header_col_id: id of header col (default '__row__')

        :param header_col_type: a string indicating the type of header col
        (default 'string', other possible values 'continuous' and 'discrete')

        :param col_type: a dictionary where keys are col_ids and value are the
        corresponding types ('string', 'continuous' or 'discrete')

        :param class_col_id: id of the col that indicates the class associated
        with each row, if any (default None).

        :param missing: value assigned to missing values (default None)

        :param _cached_row_id: not for use by client code.

        :param row_mapping: dictionary mapping between the row name and the
        row index. Only mandatory if the constructor is provided with
        an already existing dok_matrix or numpy array.

        :param col_mapping: dictionary mappaing between the row name and the
        row index. Only mandatory if the constructor is provided with
        an already existing dok_matrix or numpy array.
        """

        if col_type is None:
            col_type = dict()

        self.row_ids = row_ids
        self.col_ids = col_ids

        if isinstance(values, np.ndarray) or isspmatrix(values):
            self.row_mapping = row_mapping
            self.col_mapping = col_mapping
            self.values = values
        else:
            # it is a dictionnary -> create a dok_matrix
            # here we guess the content type.
            # Could be better if we could get it from the constructor
            dtype = np.dtype(type(six.next(six.itervalues(values))))
            # build the mapping by taking the initial order of
            # row/col_ids
            self.row_mapping = dict(map(reversed, enumerate(row_ids)))
            self.col_mapping = dict(map(reversed, enumerate(col_ids)))
            self.values = dok_matrix((len(row_ids), len(col_ids)), dtype=dtype)
            for k, v in iteritems(values):
                self.values[self.row_mapping[k[0]], self.col_mapping[k[1]]] = v
        self.header_row_id = header_row_id
        self.header_row_type = header_row_type
        self.header_col_id = header_col_id
        self.header_col_type = header_col_type
        self.col_type = col_type
        self.class_col_id = class_col_id
        self.missing = missing
        self._cached_row_id = _cached_row_id

    def get(self, row, col, missing=None):
        """
        gets the item at coordinate (row, col)

        :param row: the row name as in row_ids

        :param col: the column name as in col_ids

        :param missing: if not None, replaces the default missing value
        of the class

        :return: the item from the table or self.missing or missing

        """
        missing = self.missing if missing is None else missing
        try:
            return self.values.get((self.row_mapping[row], self.col_mapping[col]), missing)
        except:
            return missing

    def to_dict(self):
        """
        inefficient, just for comparing output for testing
        """
        out = dict()
        rev_cols = dict(map(reversed, self.col_mapping.items()))
        rev_rows = dict(map(reversed, self.row_mapping.items()))
        for k, v in iteritems(self.values):
            out[(rev_rows[k[0]], rev_cols[k[1]])] = v
        return out

    # TODO: test.
    def to_string(
        self,
        output_orange_headers=False,
        col_delimiter='\t',
        row_delimiter=None,
    ):
        """Return a string representation of the table.

        :param output_orange_headers: a boolean indicating whether orange 2
        table headers should be added to the string representation (default
        False).

        :param col_delimiter: the unicode string that will be inserted between
        successive columns (default '\t')

        :param row_delimiter: the unicode string that will be inserted between
        successive rows (default '\r\n' on windows, '\n' elsewhere)

        :return: stringified table
        """

        # Select default row delimiter depending on OS...
        if row_delimiter is None:
            if os.name == 'nt':
                row_delimiter = '\r\n'
            else:
                row_delimiter = '\n'

        # Start with header col id.
        output_string = self.header_col_id + col_delimiter

        # Convert col headers to unicode strings and output...
        output_string += col_delimiter.join(text(i) for i in self.col_ids)

        # Add Orange 2 table headers if needed...
        if output_orange_headers:
            output_string += '%s%s%s' % (
                row_delimiter,
                self.header_col_type,
                col_delimiter,
            )
            col_type_list = [self.col_type.get(x, '') for x in self.col_ids]
            output_string += col_delimiter.join(col_type_list)
            output_string += row_delimiter + col_delimiter
            for col_id in self.col_ids:
                if col_id == self.class_col_id:
                    output_string += 'class'
                output_string += col_delimiter
            output_string = output_string[:-1]

        # Default (empty) string for missing values...
        if self.missing is None:
            missing = ''
        else:
            missing = text(self.missing)

        # Format row strings...
        row_strings = (
            '%s%s%s%s' % (
                row_delimiter,
                row_id,
                col_delimiter,
                col_delimiter.join(
                    [
                        text(self.get(row_id, col_id, missing))
                        for col_id in self.col_ids
                    ]
                )
            )
            for row_id in self.row_ids
        )

        # Concatenate into a single string and output it.
        return output_string + ''.join(row_strings)

    # Method to_orange_table() is defined differently for Python 2 and 3.
    if sys.version_info.major >= 3:

        # TODO: Implement and test.
        def to_orange_table(self, encoding='iso-8859-15'):
            """Create an Orange 3 table."""
            raise NotImplementedError('method not implemented yet!')

    else:
        # TODO: test.
        def to_orange_table(self, encoding='iso-8859-15'):
            """Create an Orange 2 table.

            :param encoding: a string indicating the encoding of strings in
            the Orange 2 table

            :return: an Orange 2 table

            NB:
            - Columns without a col_type will be set to 'string' by default.
            - Orange 2 does not support unicode well, so this method is
              likely to mangle non-ASCII data.
            """

            import Orange   # This can raise an ImportError.

            # Initialize list of features.
            features = list()

            # Get ordered list of col headers (with class col at the end)...
            ordered_cols = [self.header_col_id]
            ordered_cols.extend(
                [x for x in self.col_ids if x != self.class_col_id]
            )
            if self.class_col_id:
                ordered_cols.append(self.class_col_id)

            # For each col header...
            for col_id in ordered_cols:

                # Convert it to string and encode as specified...
                str_col_id = text(col_id)
                encoded_col_id = str_col_id.encode(
                    encoding,
                    errors='xmlcharrefreplace',
                )

                # Select col type for this col and create Orange feature...
                if col_id == self.header_col_id:
                    col_type = self.header_col_type
                else:
                    col_type = self.col_type.get(col_id, 'string')
                if col_type == 'string':
                    features.append(Orange.feature.String(encoded_col_id))
                elif col_type == 'continuous':
                    features.append(Orange.feature.Continuous(encoded_col_id))
                elif col_type == 'discrete':
                    values = list()
                    if col_id == self.header_col_id:
                        for row_id in self.row_ids:
                            value = row_id.encode(
                                encoding,
                                errors='xmlcharrefreplace',
                            )
                            if value not in values:
                                values.append(value)
                    else:
                        for row_id in self.row_ids:
                            _value = self.get(row_id, col_id, False)
                            if _value is not False:
                                value = _value.encode(
                                    encoding,
                                    errors='xmlcharrefreplace',
                                )
                                if value not in values:
                                    values.append(value)
                    feature = Orange.feature.Discrete(
                        name=encoded_col_id,
                        values=Orange.core.StringList(values),
                    )
                    features.append(feature)

            # Create Orange 2 domain and table based on features...
            domain = Orange.data.Domain(features, self.class_col_id)
            orange_table = Orange.data.Table(domain)

            # Default string for missing values...
            if self.missing is None:
                missing = '?'
            if self.missing is not None:
                missing = text(self.missing)

            # Store values in each row...
            for row_id in self.row_ids:
                row_data = list()
                for col_id in ordered_cols:
                    if col_id == self.header_col_id:
                        value = row_id
                    else:
                        value = self.get(row_id, col_id, missing)
                    if value:
                        value = text(value).encode(
                            encoding,
                            errors='xmlcharrefreplace',
                        )
                    row_data.append(value)
                orange_table.append(row_data)

            return orange_table

    # TODO: modify client code to match signature change (key_id etc).
    # TODO: test.
    def to_sorted(
        self,
        key_col_id=None,      # formerly row['key_id']
        reverse_rows=False,   # formerly row['reverse']
        key_row_id=None,      # formerly col['key_id']
        reverse_cols=False,   # formerly col['reverse']
    ):
        """Return a sorted copy of the table

        :param key_col_id: id of col to be used as key for sorting rows (default
        None means don't sort cols)

        :param reverse_rows: boolean indicating whether rows should be sorted
        in reverse order (default False); has no effect is key_col_id is None.

        :param key_row_id: id of row to be used as key for sorting cols (default
        None means don't sort cols)

        :param reverse_cols: boolean indicating whether cols should be sorted
        in reverse order (default False); has no effect is key_row_id is None.

        :return: a sorted copy of the table.
        """

        # If a col id was specified as key for sorting rows...
        if key_col_id is not None:

            # If it is header col id, sort rows by id...
            if key_col_id == self.header_col_id:
                new_row_ids = sorted(self.row_ids, reverse=reverse_rows)

            # Otherwise sort rows by selected col...
            else:
                unmapping = [''] * len(self.row_ids)
                for k, v in iteritems(self.row_mapping):
                    unmapping[v] = k
                col = self.col_mapping[key_col_id]
                if isinstance(self.values, type(np.array)):
                    order = np.argsort(self.values[:, col], 0)
                # dok_matrix of strings cannot be converted to an array
                elif self.values.dtype == np.dtype('<U'):
                    order = np.argsort([self.values[x, col]
                                        for x in range(len(self.row_ids))], 0)
                else:
                    order = np.argsort(self.values[:, col].A[:, 0], 0)

                if reverse_rows:
                    new_row_ids = [unmapping[x] for x in reversed(order)]
                else:
                    new_row_ids = [unmapping[x] for x in order]
        # Else if no col id was specified for sorting rows, copy them directly.
        else:
            new_row_ids = self.row_ids[:]

        # If a row id was specified as key for sorting cols...
        if key_row_id is not None:

            # If it is header row id, sort cols by id...
            if key_row_id == self.header_row_id:
                new_col_ids = sorted(self.col_ids, reverse=reverse_cols)

            # Otherwise sort cols by selected row...
            else:
                unmapping = [''] * len(self.col_ids)
                for k, v in iteritems(self.col_mapping):
                    unmapping[v] = k
                row = self.row_mapping[key_row_id]
                if isinstance(self.values, type(np.array)):
                    order = np.argsort(self.values[row, :], 0)
                # dok_matrix of strings cannot be converted to an array
                elif self.values.dtype == np.dtype('<U'):
                    order = np.argsort([self.values[row, x]
                                        for x in range(len(self.col_ids))], 0)
                else:
                    order = np.argsort(self.values[row, :].A[0], 0)
                if reverse_cols:
                    new_col_ids = [unmapping[x] for x in reversed(order)]
                else:
                    new_col_ids = [unmapping[x] for x in order]
        # Else if no row id was specified for sorting cols, copy them directly.
        else:
            new_col_ids = self.col_ids[:]

        # Get original table's creator and use it to create new table...
        if isinstance(self, IntPivotCrosstab):
            creator = IntPivotCrosstab
        elif isinstance(self, PivotCrosstab):
            creator = PivotCrosstab
        elif isinstance(self, FlatCrosstab):
            creator = FlatCrosstab
        elif isinstance(self, IntWeightedFlatCrosstab):
            creator = IntWeightedFlatCrosstab
        elif isinstance(self, WeightedFlatCrosstab):
            creator = WeightedFlatCrosstab
        else:
            creator = Table
        return creator(
            new_row_ids,
            new_col_ids,
            self.values.copy(),
            self.header_row_id,
            self.header_row_type,
            self.header_col_id,
            self.header_col_type,
            self.col_type.copy(),
            self.class_col_id,
            self.missing,
            self._cached_row_id,
            self.row_mapping,
            self.col_mapping,
        )

    # Todo: test.
    def deepcopy(self):
        """Deep copy a table"""

        # Get original table's creator and use it to create copy...
        if isinstance(self, IntPivotCrosstab):
            creator = IntPivotCrosstab
        elif isinstance(self, PivotCrosstab):
            creator = PivotCrosstab
        elif isinstance(self, FlatCrosstab):
            creator = FlatCrosstab
        elif isinstance(self, IntWeightedFlatCrosstab):
            creator = IntWeightedFlatCrosstab
        elif isinstance(self, WeightedFlatCrosstab):
            creator = WeightedFlatCrosstab
        else:
            creator = Table
        return creator(
            self.row_ids[:],
            self.col_ids[:],
            self.values.copy(),
            self.header_row_id,
            self.header_row_type,
            self.header_col_id,
            self.header_col_type,
            self.col_type.copy(),
            self.class_col_id,
            self.missing,
            self._cached_row_id,
            self.row_mapping.copy(),
            self.col_mapping.copy(),
        )


class Crosstab(Table):
    """Base class for crosstabs (i.e. contingency tables)."""

    # TODO: test.
    @staticmethod
    def get_unique_items(seq):
        """Get list of unique items in sequence (in original order)

        (Adapted from http://www.peterbe.com/plog/uniqifiers-benchmark)

        :param seq: the iterable from which unique items should be extracted

        :return: a list of unique items in input iterable
        """
        seen = dict()
        result = list()
        for item in seq:
            if item in seen:
                continue
            seen[item] = 1
            result.append(item)
        return result


class PivotCrosstab(Crosstab):
    """A class for storing crosstabs in 'pivot' format.
    It is always represented as a dok_matrix in the backend,
    which dtype is always numerical (int or float).

    Example:
               --------+-------+
               | unit1 | unit2 |
    +----------+-------+-------+
    | context1 |   1   |   3   |
    +----------+-------+-------+
    | context2 |   4   |   2   |
    +----------+-------+-------+
    """

    # TODO: test.
    def to_transposed(self):
        """Return a transposed copy of the crosstab"""
        new_col_ids = self.row_ids[:]
        return PivotCrosstab(
            self.col_ids[:],
            new_col_ids,
            self.values.transpose(),
            self.header_col_id,
            self.header_col_type,
            self.header_row_id,
            self.header_row_type,
            dict([(col_id, 'continuous') for col_id in new_col_ids]),
            None,
            self.missing,
            self.header_col_id,    # TODO: check this (was self._cached_row_id).
            self.col_mapping.copy(),
            self.row_mapping.copy(),
        )

    # TODO: test.
    def to_weighted_flat(self, progress_callback=None, dtype=np.float):
        """Convert the crosstab in 'weighted and flat' format

        :param progress_callback: callback for monitoring progress ticks (number
        of rows in table)

        :return: a copy of the table in WeightedFlatCrosstab format
        """

        # Initialize col ids and types for the converted table...
        new_header_col_id = '__id__'
        new_header_col_type = 'continuous'  # TODO: check (was string)
        new_col_ids = [self.header_row_id or '__column__']
        num_row_ids = len(self.row_ids)
        if num_row_ids > 1:
            second_col_id = self.header_col_id or '__row__'
            new_cached_row_id = None
            new_col_ids.append(second_col_id)
        else:
            new_cached_row_id = self.header_col_id  # TODO: check (was self.row_ids[0]
        new_col_type = dict((col_id, 'discrete') for col_id in new_col_ids)
        new_col_ids.append('__weight__')
        new_col_type['__weight__'] = 'continuous'

        row_counter = 0
        new_values = np.empty((self.values.nnz),
                              dtype=np.dtype([('col', np.dtype('object')),
                                     ('row', np.dtype('object')),
                                     ('val', dtype)])
                              )
        new_row_ids = list(range(1, self.values.nnz + 1))
        for row_id in self.row_ids:
            for col_id in self.col_ids:
                count = self.get(row_id, col_id, 0)
                if count == 0:
                    continue
                new_values[row_counter] = (col_id, row_id, count)
                row_counter += 1
            if progress_callback:
                progress_callback()
        return WeightedFlatCrosstab(
            new_row_ids,
            new_col_ids,
            new_values,
            header_col_id=new_header_col_id,
            header_col_type=new_header_col_type,
            col_type=new_col_type,
            class_col_id=None,
            missing=self.missing,
            _cached_row_id=new_cached_row_id,
            col_mapping=dict(map(reversed, enumerate(new_col_ids))),
        )

    # TODO: test.
    def to_numpy(self):
        """Return a numpy array with the content of a crosstab
        It is undefined for dtype string"""

        return self.values.A

    # TODO: test.
    @classmethod
    def from_numpy(
        cls,
        row_ids,
        col_ids,
        np_array,
        header_row_id='__col__',
        header_row_type='string',
        header_col_id='__row__',
        header_col_type='string',
        col_type=None,
        class_col_id=None,
        missing=None,
        _cached_row_id=None,
    ):
        """Return an (Int)PivotCrosstab based on a numpy array.

        :param row_ids: list of items (usually strings) used as row ids

        :param col_ids: list of items (usually strings) used as col ids

        :param np_array: numpy array containing the values to be stored in the
        table; the ordering of rows and column is assumed to match the ordering
        of row ids and col ids.

        :param header_row_id: id of header row (default '__col__')

        :param header_row_type: a string indicating the type of header row
        (default 'string', other possible values 'continuous' and 'discrete')

        :param header_col_id: id of header col (default '__row__')

        :param header_col_type: a string indicating the type of header col
        (default 'string', other possible values 'continuous' and 'discrete')

        :param col_type: a dictionary where keys are col_ids and value are the
        corresponding types ('string', 'continuous' or 'discrete')

        :param class_col_id: id of the col that indicates the class associated
        with each row, if any (default None).

        :param missing: value assigned to missing values (default None)

        :param _cached_row_id: not for use by client code.

        :return: a PivotCrosstab or IntPivotCrosstab with the data from the
        input numpy array.
        """
        table_values = dok_matrix(np_array)

        # build the mapping assuming order given by row/col_ids is the same
        # as in the np array
        row_mapping = dict(map(reversed, enumerate(row_ids)))
        col_mapping = dict(map(reversed, enumerate(col_ids)))

        if cls == IntPivotCrosstab:
            if not issubclass(np_array.dtype.type, np.integer):
                raise ValueError(
                    'Cannot cast non-integer numpy array to IntPivotCrosstab.'
                )
        return cls(
            row_ids,
            col_ids,
            table_values,
            header_row_id,
            header_row_type,
            header_col_id,
            header_col_type,
            col_type,
            class_col_id,
            missing,
            _cached_row_id,
            row_mapping,
            col_mapping,
        )


class IntPivotCrosstab(PivotCrosstab):
    """A class for storing crosstabs in 'pivot' format, with integer values."""

    def to_transposed(self):
        """Return a transposed copy of the crosstab"""
        transposed = super(IntPivotCrosstab, self).to_transposed()
        transposed.__class__ = IntPivotCrosstab
        return transposed

    def to_normalized(self, mode='rows', type='l1', progress_callback=None):
        """Return a normalized copy of the crosstab (where normalization is
        defined in a rather liberal way, cf. details below.

        :param mode: a string indicating the kind of normalization desired;
        possible values are
        - 'rows': row normalization
        - 'columns': column normalization
        - 'table': normalize with regard to entire table sum
        - 'presence/absence': set non-zero values to 1
        - 'quotients': compute independence quotients under independence
        - 'TF-IDF': term frequency - inverse document frequency transform

        :param type: either 'l1' (default) or 'l2'; applicable only in mode
        'rows', 'columns' and 'table'

        :param progress_callback: callback for monitoring progress ticks; number
        of ticks depends on mode:
        - 'rows': number of rows
        - 'columns': number of columns
        - 'table': not applicable
        - 'presence/absence': number of rows times number of columns
        - 'quotients': number of columns times (number of rows + 1)
        - 'TF-IDF': number of columns

        :return: normalized copy of crosstab
        """
        new_values = dict()
        if mode == 'rows':
            table_class = PivotCrosstab
            if type == 'l1':
                new_values = dok_matrix(np.nan_to_num(self.values /
                                        self.values.sum(1)))
            elif type == 'l2':
                new_values = dok_matrix(np.nan_to_num(self.values /
                                        np.sqrt(self.values.power(2).sum(1))))
        elif mode == 'columns':
            table_class = PivotCrosstab
            if type == 'l1':
                new_values = dok_matrix(np.nan_to_num(self.values /
                                        self.values.sum(0)))
            elif type == 'l2':
                new_values = dok_matrix(np.nan_to_num(self.values /
                                        np.sqrt(self.values.power(2).sum(0))))
        elif mode == 'table':
            table_class = PivotCrosstab
            if type == 'l1':
                new_values = dok_matrix(self.values / self.values.sum())
            elif type == 'l2':
                new_values = dok_matrix(self.values /
                                        math.sqrt(self.values.power(2).sum()))
        elif mode == 'presence/absence':
            table_class = IntPivotCrosstab
            new_values = dok_matrix(np.nan_to_num(self.values / self.values))
        elif mode == 'quotients':
            table_class = PivotCrosstab
            new_values = dok_matrix(np.nan_to_num(self.values *
                                                  self.values.sum() /
                                                  (self.values.sum(1) *
                                                   self.values.sum(0))
                                                  )
                                    )
        elif mode == 'TF-IDF':
            table_class = PivotCrosstab
            new_values = dok_matrix(
                np.nan_to_num(
                    np.multiply(self.values.todense(),
                                np.log(len(self.row_ids) /
                                       np.nan_to_num(self.values /
                                                     self.values
                                                     ).sum(0)
                                       )

                                )
                    )
            )

        return (table_class(
            list(self.row_ids),
            list(self.col_ids),
            new_values,
            self.header_row_id,
            self.header_row_type,
            self.header_col_id,
            self.header_col_type,
            dict(self.col_type),
            None,
            self.missing,
            self._cached_row_id,
            self.row_mapping,
            self.col_mapping,
        ))

    def to_document_frequency(self, progress_callback=None):
        """Return a table with document frequencies based on the crosstab"""
        context_type = '__document_frequency__'
        document_freq = dok_matrix(np.nan_to_num(self.values /
                                                 self.values
                                                 ).sum(0))
        return (
            IntPivotCrosstab(
                [context_type],
                self.col_ids[:],
                document_freq,
                '__unit__',
                'string',
                '__context__',
                'string',
                self.col_type.copy(),
                None,
                0,
                None,
                {context_type: 0},
                self.col_mapping.copy(),
            )
        )

    def to_association_matrix(self, bias='none', progress_callback=None):
        """Return a table with Markov associativities between columns
        (cf. Bavaud & Xanthos 2005, Deneulin et al. 2014)
        """
        # orange_table = self.to_orange_table('utf8')
        # freq_table = Orange.data.preprocess.RemoveDiscrete(orange_table)
        # freq = freq_table.to_numpy()[0]
        freq = self.to_numpy()  # TODO: check (was previous 2 lines)
        if self.header_col_type == 'continuous':
            freq = freq[::, 1::]
        total_freq = freq.sum()
        sum_col = freq.sum(axis=0)
        sum_row = freq.sum(axis=1)
        exchange = np.dot(
            np.transpose(freq),
            np.dot(
                np.diag(1 / sum_row),
                freq
            )
        ) / total_freq
        if bias == 'frequent':
            output_matrix = exchange
        elif bias == 'none':
            sqrt_pi_inv = np.diag(1 / np.sqrt(sum_col / total_freq))
            output_matrix = np.dot(sqrt_pi_inv, np.dot(exchange, sqrt_pi_inv))
        else:
            pi_inv = np.diag(1 / (sum_col / total_freq))
            output_matrix = np.dot(pi_inv, np.dot(exchange, pi_inv))
        values = dok_matrix(output_matrix)
        return (
            PivotCrosstab(
                self.col_ids[:],
                self.col_ids[:],
                values,
                header_col_id='__unit__',
                header_col_type='string',
                col_type=self.col_type.copy(),
                row_mapping=self.col_mapping.copy(),
                col_mapping=self.col_mapping.copy(),
            )
        )

    def to_flat(self, progress_callback=None):
        """Return a copy of the crosstab in 'flat' format"""
        new_header_col_id = '__id__'
        new_header_col_type = 'string'
        new_col_ids = [self.header_row_id or '__column__']
        new_col_ids.append(self.header_col_id or '__row__')
        new_cached_row_id = None
        new_col_type = dict([(col_id, 'discrete') for col_id in new_col_ids])
        new_values = list()

        for row_id in self.row_ids:
            for col_id in self.col_ids:
                count = self.get(row_id, col_id, 0)
                new_values.extend([[col_id, row_id]] * count)
            if progress_callback:
                progress_callback()

        new_row_ids = list(range(1, len(new_values) + 1))
        new_values = np.array(new_values)

        return (
            FlatCrosstab(
                new_row_ids,
                new_col_ids,
                new_values,
                header_col_id=new_header_col_id,
                header_col_type=new_header_col_type,
                col_type=new_col_type,
                class_col_id=None,
                missing=self.missing,
                _cached_row_id=new_cached_row_id,
                col_mapping={new_col_ids[0]: 0, new_col_ids[1]: 1}
            )
        )

    def to_weighted_flat(self, progress_callback=None):
        """Return a copy of the crosstab in 'weighted and flat' format with
        integer values
        """
        weighted_flat = super(IntPivotCrosstab, self).to_weighted_flat(
            progress_callback=progress_callback,
            dtype=np.int,
        )
        weighted_flat.__class__ = IntWeightedFlatCrosstab
        return weighted_flat


class FlatCrosstab(Crosstab):
    """A class for storing crosstabs in 'flat' format in LTTL.
    They are stored as numpy arrays with column type "string"
    (and int for the weighted version). There is no row_mapping,
    because the row_ids is a counter, that can be used as a direct reference.

    Given the currently implemented methods and constructors, identical rows
    are always consecutive. This property is used to speed up the wheigthed
    conversion.

    Example:
    +----------+-------+
    | context  | unit  |
    +==========+=======+
    | context1 | unit1 |
    +----------+-------+
    | context1 | unit2 |
    +----------+-------+
    | context1 | unit2 |
    +----------+-------+
    | context1 | unit2 |
    +----------+-------+
    | context2 | unit1 |
    +----------+-------+
    | context2 | unit1 |
    +----------+-------+
    | context2 | unit1 |
    +----------+-------+
    | context2 | unit1 |
    +----------+-------+
    | context2 | unit2 |
    +----------+-------+
    | context2 | unit2 |
    +----------+-------+
    """

    def get(self, row, col, missing=None):
        """
        gets the item at coordinate (row, col)

        :param row: the row name as in row_ids

        :param col: the column name as in col_ids

        :param missing: if not None, replaces the default missing value
        of the class

        :return: the item from the table or self.missing or missing

        """
        try:
            return self.values[row - 1, self.col_mapping[col]]
        except:
            return self.missing if missing is None else missing

    def to_pivot(self, progress_callback=None):
        """Return a copy of the crosstab in 'pivot' format"""
        new_header_row_id = self.col_ids[0]
        new_header_row_type = 'discrete'
        new_header_col_id = self.col_ids[1]
        new_header_col_type = 'discrete'
        new_col_ids = np.unique(self.values[:, 1]).tolist()
        new_row_ids = np.unique(self.values[:, 0]).tolist()
        row_mapping = dict(map(reversed, enumerate(new_row_ids)))
        col_mapping = dict(map(reversed, enumerate(new_col_ids)))
        new_values = dok_matrix((len(new_row_ids), len(new_col_ids)), dtype=np.int32)

        for i in range(self.values.shape[0]):
            row = row_mapping[self.values[i, 0]]
            col = col_mapping[self.values[i, 1]]
            new_values[row, col] = new_values[row, col] + 1
            if progress_callback:
                progress_callback()
        return (
            IntPivotCrosstab(
                new_row_ids,
                new_col_ids,
                new_values,
                new_header_row_id,
                new_header_row_type,
                new_header_col_id,
                new_header_col_type,
                dict([(col_id, 'continuous') for col_id in new_col_ids]),
                None,
                self.missing,
                self._cached_row_id,
                row_mapping,
                col_mapping,
            )
        )

    def to_weighted_flat(self, progress_callback=None):
        """Return a copy of the crosstab in 'weighted and flat' format"""
        new_col_ids = list(self.col_ids)
        new_col_type = dict(self.col_type)
        new_values = list()
        new_row_ids = list()
        previous_row = None
        previous_count = 0
        for row_id in self.row_ids:
            if previous_row is not None and (previous_row == self.values[row_id - 1, :]).all():
                previous_count += 1
            else:
                if previous_count > 0:
                    new_values.append((previous_row[0],
                                       previous_row[1],
                                       previous_count)
                                      )
                previous_row = self.values[row_id - 1, :]
                previous_count = 1
            if progress_callback:
                progress_callback()
        new_values.append((previous_row[0],
                            previous_row[1],
                            previous_count)
                        )
        new_row_ids = list(range(1, len(new_values) + 1))
        new_values = np.array(new_values, dtype=np.dtype([('col', np.dtype('object')),
                                     ('row', np.dtype('object')),
                                     ('val', np.dtype('int'))])
                              )

        new_col_ids.append('__weight__')
        new_col_type['__weight__'] = 'continuous'
        return (
            IntWeightedFlatCrosstab(
                new_row_ids,
                new_col_ids,
                new_values,
                self.header_row_id,
                self.header_row_type,
                self.header_col_id,
                self.header_col_type,
                new_col_type,
                None,
                self.missing,
                self._cached_row_id,
                col_mapping=dict(map(reversed, enumerate(new_col_ids)))
            )
        )


class WeightedFlatCrosstab(Crosstab):
    """A class for storing crosstabs in 'weighted and flat' format.

    Example:
    +----------+-------+-------+
    | context  | unit  | count |
    +==========+=======+=======+
    | context1 | unit1 |   1   |
    +----------+-------+-------+
    | context1 | unit2 |   3   |
    +----------+-------+-------+
    | context2 | unit1 |   4   |
    +----------+-------+-------+
    | context2 | unit2 |   2   |
    +----------+-------+-------+
    """

    def get(self, row, col, missing=None):
        """
        gets the item at coordinate (row, col)

        :param row: the row name as in row_ids

        :param col: the column name as in col_ids

        :param missing: if not None, replaces the default missing value
        of the class

        :return: the item from the table or self.missing or missing

        """
        try:
            return self.values[row - 1][self.col_mapping[col]]
        except:
            return self.missing if missing is None else missing

    def to_pivot(self, progress_callback=None):
        """Return a copy of the crosstab in 'pivot' format"""
        new_header_row_id = self.col_ids[0]
        new_header_row_type = 'discrete'
        new_header_col_id = self.col_ids[1]
        new_header_col_type = 'discrete'
        new_col_ids = np.unique([x[0] for x in self.values]).tolist()
        new_row_ids = np.unique([x[1] for x in self.values]).tolist()
        row_mapping = dict(map(reversed, enumerate(new_row_ids)))
        col_mapping = dict(map(reversed, enumerate(new_col_ids)))
        new_values = dok_matrix((len(new_row_ids), len(new_col_ids)), dtype=np.float)

        for i in range(self.values.shape[0]):
            row = row_mapping[self.values[i][1]]
            col = col_mapping[self.values[i][0]]
            new_values[row, col] = self.values[i][2]
            if progress_callback:
                progress_callback()

        return (
            PivotCrosstab(
                new_row_ids,
                new_col_ids,
                new_values,
                new_header_row_id,
                new_header_row_type,
                new_header_col_id,
                new_header_col_type,
                dict([(col_id, 'continuous') for col_id in new_col_ids]),
                None,
                self.missing,
                row_mapping=row_mapping,
                col_mapping=col_mapping,
            )
        )


class IntWeightedFlatCrosstab(WeightedFlatCrosstab):
    """A class for storing crosstabs in 'weighted and flat' format in LTTL,
    where weights are integer values.
    """

    def to_pivot(self, progress_callback=None):
        """Return a copy of the crosstab in 'pivot' format, with int values"""
        pivot = super(IntWeightedFlatCrosstab, self).to_pivot(
            progress_callback=progress_callback
        )
        pivot.__class__ = IntPivotCrosstab
        pivot.values = pivot.values.astype(np.int)
        return pivot

    def to_flat(self, progress_callback=None):
        """Return a copy of the crosstab in 'flat' format"""
        new_col_ids = list([c for c in self.col_ids if c != '__weight__'])
        new_col_type = dict(self.col_type)
        del new_col_type['__weight__']
        new_col_mapping = dict(self.col_mapping)
        del new_col_mapping['__weight__']
        row_counter = 0
        new_values = np.empty((sum(x[2] for x in self.values), 2), dtype=np.dtype("object"))
        new_row_ids = list(range(1, len(new_values) + 1))
        for row_id in range(len(self.row_ids)):
            for i in range(self.values[row_id][2]):
                new_values[row_counter, 0] = self.values[row_id][0]
                new_values[row_counter, 1] = self.values[row_id][1]
                row_counter += 1
                if progress_callback:
                    progress_callback()
        return (
            FlatCrosstab(
                new_row_ids,
                new_col_ids,
                new_values,
                self.header_row_id,
                self.header_row_type,
                self.header_col_id,
                self.header_col_type,
                new_col_type,
                None,
                self.missing,
                self._cached_row_id,
                col_mapping=new_col_mapping,

            )
        )
