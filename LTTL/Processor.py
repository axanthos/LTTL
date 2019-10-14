"""Module Processor.py
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
"""

# TODO: document merge_strings

from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

from math import sqrt
from builtins import range
from builtins import str as text

import numpy as np

from .Segmentation import Segmentation
from .Table import *
from .Utils import (
    get_average,
    get_variety,
    get_expected_subsample_variety,
    tuple_to_simple_dict,
    sample_dict,
    prepend_unit_with_category,
    generate_random_annotation_key,
    get_unused_char_in_segmentation,
    iround,
)

__version__ = "1.0.6"


def count_in_context(
    units=None,
    contexts=None,
    progress_callback=None,
):
    """Count units in contexts.

    Parameter units is a dict with the following keys and values:
    KEY                     VALUE                           DEFAULT
    segmentation            unit segmentation               None
    annotation_key          annotation to be counted        None
    seq_length              length of unit sequences        1
    intra_seq_delimiter     string for joining sequences    '#'

    Parameter contexts is a dict with the following keys and values:
    KEY                     VALUE                           DEFAULT
    segmentation            context segmentation            None
    annotation_key          annotation to be counted        None
    merge                   merge contexts together?        False

    Returns an IntPivotCrosstab table.
    """

    default_units = {
        'segmentation': None,
        'annotation_key': None,
        'seq_length': 1,
        'intra_seq_delimiter': '#',
    }
    default_contexts = {
        'segmentation': None,
        'annotation_key': None,
        'merge': False,
    }
    if units is not None:
        default_units.update(units)
    units = default_units
    if contexts is not None:
        default_contexts.update(contexts)
    contexts = default_contexts

    freq = dict()
    context_types = list()
    unit_types = list()

    # CASE 1: context segmentation is specified...
    if (
        contexts['segmentation'] is not None and
        units['segmentation'] is not None
    ):

        # Set default context type.
        context_type = '__global__'

        # Optimization...
        context_annotation_key = contexts['annotation_key']
        context_segmentation = contexts['segmentation']
        unit_segmentation = units['segmentation']
        unit_annotation_key = units['annotation_key']
        unit_seq_length = units['seq_length']
        seq_join = units['intra_seq_delimiter'].join

        # CASE 1A: unit sequence length is greater than 1...
        if unit_seq_length > 1:

            # Get the list of units in final format...
            if unit_annotation_key is not None:
                unit_list = [
                    u.annotations.get(
                        unit_annotation_key,
                        '__none__',
                    )
                    for u in unit_segmentation
                ]
            else:
                unit_list = [u.get_content() for u in unit_segmentation]

            # Loop over context token indices...
            for context_index, context_segment in enumerate(
                    context_segmentation):

                # Get context token...
                context_token = context_segment

                # Get and store context type...
                if not contexts['merge']:
                    if context_annotation_key is not None:
                        context_type = context_segment.annotations.get(
                            context_annotation_key,
                            u'__none__',
                        )
                    else:
                        context_type = context_segment.get_content()

                    if context_type not in context_types:
                        context_types.append(context_type)

                # Loop over contained unit sequences
                for unit_seq_index in \
                        context_token.get_contained_sequence_indices(
                            unit_segmentation,
                            unit_seq_length,
                        ):

                    # Get unit type...
                    unit_type = seq_join(
                        unit_list[unit_seq_index:unit_seq_index+unit_seq_length]
                    )

                    # Store unit type...
                    if unit_type not in unit_types:
                        unit_types.append(unit_type)

                    # Increment count of context-unit pair...
                    type_pair = (context_type, unit_type)
                    freq[type_pair] = freq.get(type_pair, 0) + 1

                if progress_callback:
                    progress_callback()

            # Store default context type if needed...
            if len(freq) > 0 and len(context_types) == 0:
                context_types.append(context_type)

        # CASE 1B: unit sequence length is 1...
        else:

            # Loop over context tokens (=containing segments)
            for context_token in contexts['segmentation']:

                # Determine if context types are surface or annotations.
                if not contexts['merge']:
                    if context_annotation_key is not None:
                        context_type = context_token.annotations.get(
                            context_annotation_key,
                            '__none__',  # Default annotation
                        )
                    else:
                        context_type = context_token.get_content()

                # Loop over unit tokens (=contained segments)
                for unit_token in context_token.get_contained_segments(
                    unit_segmentation
                ):

                    # Determine if unit types are surface or anno.
                    if unit_annotation_key:
                        unit_type = unit_token.annotations.get(
                            unit_annotation_key,
                            '__none__',  # Default annotation
                        )
                    else:
                        unit_type = unit_token.get_content()

                    # Store context and unit type...
                    if context_type not in context_types:
                        context_types.append(context_type)
                    if unit_type not in unit_types:
                        unit_types.append(unit_type)

                    # Increment count of context-unit pair...
                    type_pair = (context_type, unit_type)
                    freq[type_pair] = freq.get(type_pair, 0) + 1

                if progress_callback:
                    progress_callback()

    # CASE 2: no context segmentation is specified...
    elif units['segmentation'] is not None:

        # Set default (unique) context type...
        context_type = '__global__'
        context_types.append(context_type)

        # Optimization...
        unit_annotation_key = units['annotation_key']
        unit_segmentation = units['segmentation']
        unit_segmentation_length = len(units['segmentation'])
        unit_seq_length = units['seq_length']
        seq_join = units['intra_seq_delimiter'].join

        # CASE 2A: unit sequence length is greater than 1...
        if unit_seq_length > 1:

            # Get the list of units in final format...
            if unit_annotation_key is not None:
                unit_list = [
                    u.annotations.get(
                        unit_annotation_key,
                        '__none__',
                    )
                    for u in unit_segmentation
                ]
            else:
                unit_list = [u.get_content() for u in unit_segmentation]

            # Loop over unit sequences (=contained segments)
            for unit_index in range(
                unit_segmentation_length - (unit_seq_length - 1)
            ):

                # Get unit type...
                unit_type = seq_join(
                    unit_list[unit_index: unit_index + unit_seq_length]
                )

                # Store unit type...
                if unit_type not in unit_types:
                    unit_types.append(unit_type)

                # Increment count of context-unit pair...
                type_pair = (context_type, unit_type)
                freq[type_pair] = freq.get(type_pair, 0) + 1

                if progress_callback:
                    progress_callback()

        # CASE 2B: unit sequence length is 1...
        else:

            # Get the list of units in final format...
            if unit_annotation_key is not None:
                unit_list = [
                    u.annotations.get(
                        unit_annotation_key,
                        '__none__',
                    )
                    for u in unit_segmentation
                ]
            else:
                unit_list = [u.get_content() for u in unit_segmentation]

            # Get unit types...
            unit_types = list(set(unit_list))

            # Loop over unit tokens (=contained segments)
            for unit_type in unit_list:

                # Increment count of context-unit pair...
                type_pair = (context_type, unit_type)
                freq[type_pair] = freq.get(type_pair, 0) + 1

                if progress_callback:
                    progress_callback()

    # Create pivot crosstab...
    if len(context_types) and isinstance(context_types[0], int):
        header_type = 'continuous'
    else:
        header_type = 'string'
    return (
        IntPivotCrosstab(
            context_types,
            unit_types,
            freq,
            '__unit__',
            'string',
            '__context__',
            header_type,
            dict([(u, 'continuous') for u in unit_types]),
            None,
            0,
            None,
        )
    )


def count_in_window(
    units=None,
    window_size=1,
    progress_callback=None,
):
    """Count units in sliding window.

    Parameter units is a dict with the following keys and values:
    KEY                     VALUE                            DEFAULT
    segmentation            unit segmentation                None
    annotation_key          annotation to be counted         None
    seq_length              length of unit sequences         1
    intra_seq_delimiter     string for joining sequences     '#'

    Returns an IntPivotCrosstab table.
    """

    default_units = {
        'segmentation': None,
        'annotation_key': None,
        'seq_length': 1,
        'intra_seq_delimiter': '#',
    }
    if units is not None:
        default_units.update(units)
    units = default_units

    freq = dict()
    unit_types = list()
    window_type = 1

    if (
        units['segmentation'] is not None and
        len(units['segmentation']) >= window_size >= units['seq_length']
    ):

        # Optimization...
        unit_segmentation = units['segmentation']
        unit_annotation_key = units['annotation_key']

        # Get the list of units in final format (content or annotation)...
        if unit_annotation_key is not None:
            unit_list = [
                unit_token.annotations.get(
                    unit_annotation_key,
                    '__none__',  # Default annotation
                )
                for unit_token in unit_segmentation
            ]
        else:
            unit_list = [u.get_content() for u in unit_segmentation]

        # CASE 1: unit sequence length is greater than 1...
        if units['seq_length'] > 1:

            # Optimization...
            seq_join = units['intra_seq_delimiter'].join
            unit_seq_length = units['seq_length']

            # Get counts for first window...
            first_window = unit_list[:window_size]
            window_freq = dict()
            for unit_index in range(window_size - (unit_seq_length - 1)):
                unit_type = seq_join(
                    first_window[unit_index: unit_index + unit_seq_length]
                )
                if unit_type not in unit_types:
                    unit_types.append(unit_type)
                window_freq[unit_type] = window_freq.get(unit_type, 0) + 1

            # Update main counts...
            freq = dict(
                [(('1', k), v) for (k, v) in iteritems(window_freq)]
            )

            if progress_callback:
                progress_callback()

            # Loop over other window indices...
            for window_index in range(
                1,
                len(units['segmentation']) - (window_size - 1)
            ):

                # Decrement count of first unit in previous window...
                window_freq[
                    seq_join(
                        unit_list[window_index-1:window_index+unit_seq_length-1]
                    )
                ] -= 1

                # Increment count of last unit in current window...
                new_unit = seq_join(
                    unit_list[
                        window_index + window_size - unit_seq_length
                        :
                        window_index + window_size
                    ]
                )
                window_freq[new_unit] = window_freq.get(new_unit, 0) + 1
                if new_unit not in unit_types:
                    unit_types.append(new_unit)

                # Get window type...
                window_type = window_index + 1
                window_str = text(window_type)

                # Update main counts...
                freq.update(
                    dict(
                        [
                            ((window_str, k), v)
                            for (k, v) in iteritems(window_freq)
                        ]
                    )
                )

                if progress_callback:
                    progress_callback()

        # CASE 2: unit sequence length is 1...
        else:

            # Get unit types...
            unit_types = list(set(unit_list))

            # Get counts for first window...
            first_window = unit_list[:window_size]
            window_freq = dict()
            for unit_token in first_window:
                window_freq[unit_token] = window_freq.get(unit_token, 0) + 1

            # Update main counts...
            freq = dict(
                [(('1', k), v) for (k, v) in iteritems(window_freq)]
            )

            if progress_callback:
                progress_callback()

            # Loop over other window indices...
            for window_index in range(
                1,
                len(units['segmentation']) - (window_size - 1)
            ):

                # Decrement count of first unit in previous window...
                window_freq[unit_list[window_index - 1]] -= 1

                # Increment count of last unit in current window...
                new_unit = unit_list[window_index + window_size - 1]
                window_freq[new_unit] = window_freq.get(new_unit, 0) + 1

                # Get window type...
                window_type = window_index + 1
                window_str = text(window_type)
                # Update main counts...
                freq.update(
                    dict(
                        [
                            ((window_str, k), v)
                            for (k, v) in iteritems(window_freq)
                        ]
                    )
                )

                if progress_callback:
                    progress_callback()

    # Create pivot crosstab...
    return (
        IntPivotCrosstab(
            [text(i) for i in range(1, window_type + 1)],
            unit_types,
            freq,
            '__unit__',
            'string',
            '__context__',
            'continuous',
            dict([(u, 'continuous') for u in unit_types]),
            None,
            0,
            None,
        )
    )


def count_in_chain(
    units=None,
    contexts=None,
    progress_callback=None,
):
    """Count units given left and/or right context.

    Parameter units is a dict with the following keys and values:
    KEY                     VALUE                             DEFAULT
    segmentation            unit segmentation                 None
    annotation_key          annotation to be counted          None
    seq_length              length of unit sequences          1
    intra_seq_delimiter     string for joining sequences      '#'

    Parameter contexts is a dict with the following keys and values:
    KEY                     VALUE                             DEFAULT
    left_size               size of left context              1
    right_size              size of right context             0
    unit_pos_marker         string indicating unit position   '_'
    merge_strings           treat strings as contiguous?      False

    Returns a IntPivotCrosstab table.
    """

    default_units = {
        'segmentation': None,
        'annotation_key': None,
        'seq_length': 1,
        'intra_seq_delimiter': '#',
    }
    default_contexts = {
        'left_size': 1,
        'right_size': 0,
        'unit_pos_marker': '_',
        'merge_strings': False,
    }
    if units is not None:
        default_units.update(units)
    units = default_units
    if contexts is not None:
        default_contexts.update(contexts)
    contexts = default_contexts

    freq = dict()
    context_types = list()
    unit_types = list()

    # Optimization...
    unit_segmentation = units['segmentation']
    unit_annotation_key = units['annotation_key']
    unit_seq_length = units['seq_length']
    context_left_size = contexts['left_size']
    context_right_size = contexts['right_size']
    unit_pos_marker = contexts['unit_pos_marker']
    seq_join = units['intra_seq_delimiter'].join
    window_size = context_left_size + context_right_size + unit_seq_length
    merge_strings = contexts['merge_strings']

    if (
        unit_segmentation is not None and
        window_size <= len(unit_segmentation)
    ):

        # Get the list of units in final format (content or annotation)...
        if unit_annotation_key is not None:
            unit_list = [
               text(
                    unit_token.annotations.get(
                        unit_annotation_key,
                        '__none__',  # Default annotation
                    )
                )
                for unit_token in unit_segmentation
            ]
        else:
            unit_list = [u.get_content() for u in unit_segmentation]

        # Get the list of string indices...
        str_indices = [s.get_real_str_index() for s in unit_segmentation]

        # CASE 1: unit sequence length is greater than 1...
        if unit_seq_length > 1:

            # Loop over window indices...
            for window_index in range(
                len(units['segmentation']) - (window_size - 1)
            ):

                # Pass unless merges_strings is True or all str_indices in
                # this window are equal...
                idx_sequence = str_indices[
                    window_index : window_index + window_size
                ]
                if(
                    not merge_strings and
                    idx_sequence.count(idx_sequence[0]) != len(idx_sequence)
                ):
                    if progress_callback:
                        progress_callback()
                    continue

                # Get context type...
                context_type = '%s%s%s' % (
                    seq_join(
                        unit_list[window_index:window_index+context_left_size]
                    ),
                    unit_pos_marker,
                    seq_join(
                        unit_list[
                             window_index + context_left_size + unit_seq_length:
                             window_index + window_size
                        ]
                    )
                )

                # Get unit type...
                unit_type = seq_join(
                    unit_list[
                        window_index + context_left_size
                        :
                        window_index + context_left_size + unit_seq_length
                    ]
                )

                # Store context and unit type...
                if context_type not in context_types:
                    context_types.append(context_type)
                if unit_type not in unit_types:
                    unit_types.append(unit_type)

                # Increment count of context-unit pair...
                type_pair = (context_type, unit_type)
                freq[type_pair] = freq.get(type_pair, 0) + 1

                if progress_callback:
                    progress_callback()

        # CASE 2: unit sequence length is 1...
        else:

            # Get unit types...
            unit_types = list(
                set(
                    unit_list[
                        context_left_size:
                        len(units['segmentation']) - context_right_size
                    ]
                )
            )

            # Loop over window indices...
            for window_index in range(
                len(units['segmentation']) - (window_size - 1)
            ):

                # Pass unless merges_strings is True or all str_indices in
                # this window are equal...
                idx_sequence = str_indices[
                    window_index : window_index + window_size
                ]
                if(
                    not merge_strings and
                    idx_sequence.count(idx_sequence[0]) != len(idx_sequence)
                ):
                    if progress_callback:
                        progress_callback()
                    continue

                # Get context type...
                context_type = '%s%s%s' % (
                    seq_join(
                        unit_list[window_index:window_index+context_left_size]
                    ),
                    unit_pos_marker,
                    seq_join(
                        unit_list[
                            window_index + context_left_size + 1:
                            window_index + window_size
                        ]
                    )
                )

                # Get unit type...
                unit_type = unit_list[window_index + context_left_size]

                # Store context and unit type...
                if context_type not in context_types:
                    context_types.append(context_type)

                # Increment count of context-unit pair...
                type_pair = (context_type, unit_type)
                freq[type_pair] = freq.get(type_pair, 0) + 1

                if progress_callback:
                    progress_callback()

    # Create pivot crosstab...
    return (
        IntPivotCrosstab(
            context_types,
            unit_types,
            freq,
            '__unit__',
            'string',
            '__context__',
            'string',
            dict([(u, 'continuous') for u in unit_types]),
            None,
            0,
            None,
        )
    )


def length_in_context(
    units=None,
    averaging=None,
    contexts=None,
    progress_callback=None,
):
    """Compute length of segmentation / av. length of units in contexts.

    Parameter averaging is a dict with the following keys and values:
    KEY                     VALUE                           DEFAULT
    segmentation            averaging unit segmentation     None
    std_deviation           compute standard deviation      False

    Parameter contexts is a dict with the following keys and values:
    KEY                     VALUE                           DEFAULT
    segmentation            context segmentation            None
    annotation_key          annotation to be used           None
    merge                   merge contexts together?        False

    NB: When some form of averaging is performed with large segmentations,
    execution can be *dramatically* slower if standard deviation is
    computed.

    Returns a Table.
    """

    default_contexts = {
        'segmentation': None,
        'annotation_key': None,
        'merge': False,
    }
    default_averaging = {
        'segmentation': None,
        'std_deviation': False,
    }
    if contexts is not None:
        default_contexts.update(contexts)
    contexts = default_contexts
    if averaging is not None:
        default_averaging.update(averaging)
    averaging = default_averaging

    values = dict()
    context_types = list()
    col_ids = list()

    # CASE 1: context segmentation is specified...
    if contexts['segmentation'] is not None and units is not None:

        # Optimization...
        context_annotation_key = contexts['annotation_key']
        context_segmentation = contexts['segmentation']

        # If contexts should be merged...
        if contexts['merge']:

            # Set default context type.
            context_types = ['__global__']

        # Else get the list of contexts in final format...
        else:
            if context_annotation_key is not None:
                context_list = [
                    c.annotations.get(
                        context_annotation_key,
                        '__none__',
                    )
                    for c in context_segmentation if c.annotations is not None
                ]
            else:
                context_list = [
                    c.get_content() for c in context_segmentation if
                    c is not None
                ]

        # CASE 1A: averaging units are specified...
        if averaging['segmentation'] is not None:

            lengths = dict()
            
            # Loop over context token indices...
            for context_index, context_segment in enumerate(
                contexts['segmentation']
            ):

                # Get context token...
                context_token = context_segment

                # Get and store context type...
                if contexts['merge']:
                    context_type = '__global__'
                else:
                    context_type = context_list[context_index]
                    if context_type not in context_types:
                        context_types.append(context_type)

                # Get averaging units for this context token...
                averaging_units = context_token.get_contained_segments(
                    averaging['segmentation']
                )

                # Get lengths for these averaging units and store with type...
                my_lengths = [
                    len(averaging_unit.get_contained_segments(units))
                    for averaging_unit in averaging_units
                ]              
                try:
                    lengths[context_type].extend(my_lengths)
                except KeyError:
                    lengths[context_type] = my_lengths
                    
                if progress_callback:
                    progress_callback()
            print(lengths)
            # Loop over context types...
            for context_type in context_types:

                # Store average and count for this context...
                values[context_type, '__length_average__'] = np.mean(
                    lengths[context_type]
                )
                values[context_type, '__length_count__'] = len(
                    lengths[context_type]
                )

                # If standard deviation should be computed...
                if averaging['std_deviation']:
                    values[context_type, '__length_std_deviation__'] =    \
                        np.std(lengths[context_type])

            # Store col ids...
            if len(values) > 0:
                col_ids.append('__length_average__')
                col_ids.append('__length_count__')
                if averaging['std_deviation']:
                    col_ids.append('__length_std_deviation__')

        # CASE 1B: no averaging units are specified...
        else:

            # Loop over context token indices...
            for context_index, context_segment in enumerate(
                    contexts['segmentation']):

                # Get context token...
                context_token = context_segment

                # Get and store context type...
                if not contexts['merge']:
                    context_type = context_list[context_index]
                    if context_type not in context_types:
                        context_types.append(context_type)

                # Increment length for this context...
                values[(context_type, '__length__')] = values.get(
                    (context_type, '__length__'), 0
                ) + len(
                    context_token.get_contained_segments(units)
                )

                if progress_callback:
                    progress_callback()

            # Store col ids...
            if len(values) > 0:
                col_ids.append('__length__')

    # CASE 2: context segmentation is not specified...
    elif units is not None:

        # CASE 2A: averaging units are specified...
        if averaging['segmentation'] is not None:

            # Set default (unique) context type...
            context_type = '__global__'
            context_types.append(context_type)

            lengths = [
                len(averaging_unit.get_contained_segments(units))
                for averaging_unit in averaging['segmentation']
            ]
            
            values[context_type, '__length_average__'] = np.mean(lengths)
            values[context_type, '__length_count__'] = len(lengths)
            
            # If standard deviation should be computed...
            if averaging['std_deviation']:
                values[context_type, '__length_std_deviation__'] =    \
                    np.std(lengths)

            # Store col ids...
            if len(values) > 0:
                col_ids.append('__length_average__')
                col_ids.append('__length_count__')
                if averaging['std_deviation']:
                    col_ids.append('__length_std_deviation__')

        # CASE 2B: no averaging units are specified...
        else:

            # Set default (unique) context type...
            context_type = '__global__'
            context_types.append(context_type)

            # Get length...
            values[(context_type, '__length__')] = len(units)

            # Store col ids...
            if len(values) > 0:
                col_ids.append('__length__')

    # Store default context type if needed...
    if len(values) > 0 and len(context_types) == 0:
        context_types.append(context_type)

    # Remove zero-length contexts...
    if averaging['segmentation'] is not None:
        length_col_name = '__length_average__'
    else:
        length_col_name = '__length__'
    context_types[:] = [
        c for c in context_types
        if (
            (c, length_col_name) in values and
            values[(c, length_col_name)]
        )
    ]
    values = dict(
        (key, value)
        for key, value in iteritems(values)
        if key[0] in context_types
    )

    # Create Table...
    if len(context_types) and isinstance(context_types[0], int):
        header_type = 'continuous'
    else:
        header_type = 'string'
    return (
        Table(
            context_types,
            col_ids,
            values,
            '__col__',
            'string',
            '__context__',
            header_type,
            dict([(c, 'continuous') for c in col_ids]),
            None,
            None,
            None,
        )
    )


def length_in_window(
    units=None,
    averaging=None,
    window_size=1,
    progress_callback=None,
):
    """Compute average length of units in sliding window.

    Parameter averaging is a dict with the following keys and values:
    KEY                     VALUE                           DEFAULT
    segmentation            averaging unit segmentation     None
    std_deviation           compute standard deviation      False

    NB: When some form of averaging is performed with large segmentations,
    execution can be dramatically slower if standard deviation is
    computed.

    Returns a Table.
    """

    default_averaging = {
        'segmentation': None,
        'std_deviation': False,
    }
    if averaging is not None:
        default_averaging.update(averaging)
    averaging = default_averaging

    values = dict()
    window_type = 0
    col_ids = list()

    if (
        units is not None and
        averaging['segmentation'] is not None and
        window_size <= len(averaging['segmentation'])
    ):

        # Optimization...
        averaging_segmentation = averaging['segmentation']

        # CASE 1: standard deviation must be computed...
        if averaging['std_deviation']:

            # Get lengths for first window...
            lengths = [
                len(a.get_contained_segments(units))
                for a in averaging_segmentation[:window_size]
            ]

            # Compute and store average and standard deviation...
            sum_values = sum(lengths)
            sum_squares = sum(l * l for l in lengths)
            average = sum_values / window_size
            stdev = math.sqrt(sum_squares / window_size - average * average)
            window_type = 1
            values[('1', '__length_average__')] = average
            values[('1', '__length_std_deviation__')] = stdev
            values[('1', '__length_count__')] = window_size

            if progress_callback:
                progress_callback()

            # Loop over other window indices...
            for window_index in range(
                1, len(averaging_segmentation) - (window_size - 1)
            ):

                # Get window type...
                window_type = window_index + 1

                # Remove first length of window and decrement sums...
                removed_length = lengths.pop(0)
                sum_values -= removed_length
                sum_squares -= removed_length * removed_length

                # Get length of new averaging unit...
                added_length = len(
                    averaging_segmentation[
                        window_index + window_size - 1
                    ].get_contained_segments(units)
                )

                # Add new length to window and increment sums...
                lengths.append(added_length)
                sum_values += added_length
                sum_squares += added_length * added_length

                # Compute and store average and standard deviation...
                average = sum_values / window_size
                stdev = math.sqrt(
                    sum_squares / window_size -
                    average * average
                )
                window_str = text(window_type)
                values[(window_str, '__length_average__')] = average
                values[(window_str, '__length_std_deviation__')] = stdev
                values[(window_str, '__length_count__')] = window_size

                if progress_callback:
                    progress_callback()

        # CASE 2: standard deviation need not be computed......
        else:

            # Get lengths for first window...
            lengths = [
                len(a.get_contained_segments(units))
                for a in averaging_segmentation[:window_size]
            ]

            # Compute and store average...
            sum_values = sum(lengths)
            average = sum_values / window_size
            window_type = 1
            values[('1', '__length_average__')] = average
            values[('1', '__length_count__')] = window_size

            if progress_callback:
                progress_callback()

            # Loop over other window indices...
            for window_index in range(
                1, len(averaging_segmentation) - (window_size - 1)
            ):

                # Get window type...
                window_type = window_index + 1

                # Remove first length of window and decrement sums...
                removed_length = lengths.pop(0)
                sum_values -= removed_length

                # Get length of new averaging unit...
                added_length = len(
                    averaging_segmentation[
                        window_index + window_size - 1
                    ].get_contained_segments(units)
                )

                # Add new length to window and increment sums...
                lengths.append(added_length)
                sum_values += added_length

                # Compute and store average and standard deviation...
                average = sum_values / window_size
                window_str = text(window_type)
                values[(window_str, '__length_average__')] = average
                values[(window_str, '__length_count__')] = window_size

                if progress_callback:
                    progress_callback()

        # Store col ids...
        if len(values) > 0:
            col_ids.append('__length_average__')
            if averaging['std_deviation']:
                col_ids.append('__length_std_deviation__')
            col_ids.append('__length_count__')

    # Create Table...
    return (
        Table(
            [text(i) for i in range(1, window_type + 1)],
            col_ids,
            values,
            '__col__',
            'string',
            '__context__',
            'continuous',
            dict([(c, 'continuous') for c in col_ids]),
            None,
            None,
            None,
        )
    )


def variety_in_context(
    units=None,
    categories=None,
    contexts=None,
    measure_per_category=False,
    apply_resampling=False,
    subsample_size=None,
    num_subsamples=None,
    progress_callback=None,
):
    """Get variety of units in contexts.

    Parameter units is a dict with the following keys and values:
    KEY                     VALUE                           DEFAULT
    segmentation            unit segmentation               None
    annotation_key          annotation to be considered     None
    seq_length              length of unit sequences        1
    weighting               Bool                            False

    Parameter categories is a dict with the following keys and values:
    KEY                     VALUE                           DEFAULT
    annotation_key          annotation to be considered     None
    weighting               Bool                            False
    adjust                  Bool                            True

    Parameter contexts is a dict with the following keys and values:
    KEY                     VALUE                           DEFAULT
    segmentation            context segmentation            None
    annotation_key          annotation to be considered     None
    merge                   merge contexts together?        False

    Returns a Table.
    """
    default_units = {
        'segmentation': None,
        'annotation_key': None,
        'seq_length': 1,
        'weighting': False,
    }
    default_categories = {
        'annotation_key': None,
        'weighting': False,
        'adjust': True,
    }
    default_contexts = {
        'segmentation': None,
        'annotation_key': None,
        'merge': False,
        'weighting': False,
    }
    if units is not None:
        default_units.update(units)
    units = default_units
    if categories is not None:
        default_categories.update(categories)
    categories = default_categories
    if contexts is not None:
        default_contexts.update(contexts)
    contexts = default_contexts

    # Inititalize target lexematic diversity (for RMSP computation).
    target_NLTTR = 0

    # If categories are specified...
    if measure_per_category:
        if units['seq_length'] > 1:
            raise ValueError(
                'Cannot measure diversity per category when '
                'sequence length is greater than 1'
            )
        new_annotation_key = generate_random_annotation_key(
            units['segmentation'],
        )
        category_delimiter = get_unused_char_in_segmentation(
            units['segmentation'],
            categories['annotation_key'],
        )
        recoded_units = prepend_unit_with_category(
            units['segmentation'],
            category_delimiter,
            new_annotation_key,
            categories['annotation_key'],
            units['annotation_key'],
        )
        counts = count_in_context(
            {
                'segmentation': recoded_units,
                'annotation_key': new_annotation_key,
                'seq_length': units['seq_length'],
            },
            contexts,
            progress_callback,
        )
        if apply_resampling and categories['adjust']:
            category_counts = count_in_context(
                {
                    'segmentation': units['segmentation'],
                    'annotation_key': categories['annotation_key'],
                    'seq_length': units['seq_length'],
                },
                contexts,
                progress_callback,
            )
            # Compute target lexematic diversity (for RMSP)...
            expected_varieties = list()
            for row_id in category_counts.row_ids:
                row = tuple_to_simple_dict(category_counts.values, row_id)
                try:
                    expected_varieties.append(
                        get_expected_subsample_variety(row, subsample_size)
                    )
                except ValueError:
                    pass
            if expected_varieties:
                target_NLTTR = max(expected_varieties) / subsample_size

    # Else if categories are not specified...
    else:
        counts = count_in_context(
            units,
            contexts,
            progress_callback,
        )
        category_delimiter = None

    # Compute varieties...
    new_values = dict()
    if (
        len(counts.row_ids) == 1 and
        counts.row_ids[0] == '__global__'
    ):
        default_row_id = '__global__'
    else:
        default_row_id = None
    for row_id in counts.row_ids:
        row = tuple_to_simple_dict(counts.values, row_id)
        if default_row_id is not None:
            row_id = default_row_id
        if apply_resampling:

            if measure_per_category:

                if categories["adjust"]:
                    # Find optimal subsample size (RMSP)...
                    cat_row = tuple_to_simple_dict(
                        category_counts.values,
                        row_id,
                    )
                    if subsample_size > sum(cat_row.values()):
                        continue
                    size_low, size_high = 2, subsample_size
                    size_tmp = size_high
                    NLTTR_tmp = get_expected_subsample_variety(
                        cat_row,
                        size_tmp,
                    ) / size_tmp
                    while(True):
                        if NLTTR_tmp == target_NLTTR or size_low == size_high:
                            break
                        if size_high - size_low == 1:
                            high = get_expected_subsample_variety(
                                cat_row,
                                size_high,
                            ) / size_high
                            low = get_expected_subsample_variety(
                                cat_row,
                                size_low,
                            ) / size_low
                            if high - target_NLTTR < target_NLTTR - low:
                                size_tmp = size_high
                            else:
                                size_tmp = size_low
                            break
                        size_tmp = iround((size_low+size_high) / 2)
                        NLTTR_tmp = get_expected_subsample_variety(
                            cat_row,
                            size_tmp,
                        ) / size_tmp
                        if NLTTR_tmp < target_NLTTR:
                            size_high = size_tmp
                        elif NLTTR_tmp > target_NLTTR:
                            size_low = size_tmp
                else:
                    size_tmp = subsample_size
                varieties = list()
                for i in range(num_subsamples):
                    try:
                        sampled_row = sample_dict(row, size_tmp)
                        varieties.append(
                            get_variety(
                                sampled_row,
                                unit_weighting=units['weighting'],
                                category_weighting=categories['weighting'],
                                category_delimiter=category_delimiter,
                            )
                        )
                    except ValueError:
                        break
                if varieties:
                    (
                        new_values[(row_id, '__variety_average__')],
                        new_values[(row_id, '__variety_std_deviation__')],
                    ) = get_average(varieties)
                    if categories["adjust"]:
                        new_values[(row_id, '__subsample_size__')] = size_tmp
                    new_values[(row_id, '__variety_count__')] = num_subsamples

            elif units['weighting']:

                varieties = list()
                for i in range(num_subsamples):
                    try:
                        sampled_row = sample_dict(row, subsample_size)
                        varieties.append(
                            get_variety(
                                sampled_row,
                                unit_weighting=units['weighting'],
                                category_weighting=categories['weighting'],
                                category_delimiter=category_delimiter,
                            )
                        )
                    except ValueError:
                        break
                if varieties:
                    (
                        new_values[(row_id, '__variety_average__')],
                        new_values[(row_id, '__variety_std_deviation__')],
                    ) = get_average(varieties)
                    new_values[(row_id, '__variety_count__')] = num_subsamples


            else:
                try:
                    new_values[(row_id, '__expected_variety__')]    \
                        = get_expected_subsample_variety(row, subsample_size)
                except ValueError:
                    pass
        else:
            new_values[(row_id, '__variety__')] = get_variety(
                row,
                unit_weighting=units['weighting'],
                category_weighting=categories['weighting'],
                category_delimiter=category_delimiter,
            )
        if progress_callback:
            progress_callback()

    if default_row_id is not None:
        counts.row_ids[0] = default_row_id

    if apply_resampling:
        if measure_per_category:
            new_col_ids = [
                '__variety_average__',
                '__variety_std_deviation__',
            ]
            if categories["adjust"]:
                new_col_ids.append('__subsample_size__')
            new_col_ids.append('__variety_count__')
        elif units['weighting']:
            new_col_ids = [
                '__variety_average__',
                '__variety_std_deviation__',
                '__variety_count__',
            ]

        else:
            new_col_ids = ['__expected_variety__']
    else:
        new_col_ids = ['__variety__']

    return (
        Table(
            counts.row_ids[:],
            new_col_ids,
            new_values,
            '__col__',
            'string',
            counts.header_col_id,
            counts.header_col_type,
            dict([(c, 'continuous') for c in new_col_ids]),
            None,
            None,
            None,
        )
    )


def variety_in_window(
    units=None,
    categories=None,
    measure_per_category=False,
    window_size=1,
    apply_resampling=False,
    subsample_size=None,
    num_subsamples=None,
    progress_callback=None,
):
    """Get variety of units in sliding window.

    Parameter units is a dict with the following keys and values:
    KEY                     VALUE                           DEFAULT
    segmentation            unit segmentation               None
    annotation_key          annotation to be considered     None
    seq_length              length of unit sequences        1
    weighting               Bool                            False

    Parameter categories is a dict with the following keys and values:
    KEY                     VALUE                           DEFAULT
    annotation_key          annotation to be considered     None
    weighting               Bool                            False
    adjust                  Bool                            True

    Returns a Table.
    """

    default_units = {
        'segmentation': None,
        'annotation_key': None,
        'seq_length': 1,
        'weighting': False,
    }
    default_categories = {
        'annotation_key': None,
        'weighting': False,
        'adjust': True,
    }
    if units is not None:
        default_units.update(units)
    units = default_units
    if categories is not None:
        default_categories.update(categories)
    categories = default_categories

    # Inititalize target lexematic diversity (for RMSP computation).
    target_NLTTR = 0

    # If categories are specified...
    if measure_per_category:
        if units['seq_length'] > 1:
            raise ValueError(
                'Cannot measure diversity per category when '
                'sequence length is greater than 1'
            )
        new_annotation_key = generate_random_annotation_key(
            units['segmentation'],
        )
        category_delimiter = get_unused_char_in_segmentation(
            units['segmentation'],
            categories['annotation_key'],
        )
        recoded_units = prepend_unit_with_category(
            units['segmentation'],
            category_delimiter,
            new_annotation_key,
            categories['annotation_key'],
            units['annotation_key'],
        )
        counts = count_in_window(
            {
                'segmentation': recoded_units,
                'annotation_key': new_annotation_key,
                'seq_length': units['seq_length'],
                'weighting': units['weighting'],
            },
            window_size,
            progress_callback,
        )
        if apply_resampling and categories['adjust']:
            category_counts = count_in_window(
                {
                    'segmentation': units['segmentation'],
                    'annotation_key': categories['annotation_key'],
                    'seq_length': units['seq_length'],
                },
                window_size,
                progress_callback,
            )
            # Compute target lexematic diversity (for RMSP)...
            expected_varieties = list()
            for row_id in category_counts.row_ids:
                row = tuple_to_simple_dict(category_counts.values, row_id)
                try:
                    expected_varieties.append(
                        get_expected_subsample_variety(row, subsample_size)
                    )
                except ValueError:
                    pass
            if expected_varieties:
                target_NLTTR = max(expected_varieties) / subsample_size

    # Else if categories are not specified...
    else:
        counts = count_in_window(
            units,
            window_size,
            progress_callback,
        )
        category_delimiter = None

    # Compute varieties...
    new_values = dict()
    for row_id in counts.row_ids:
        row = tuple_to_simple_dict(counts.values, row_id)
        if apply_resampling:
            if measure_per_category:

                if categories["adjust"]:
                    # Find optimal subsample size (RMSP)...
                    cat_row = tuple_to_simple_dict(
                        category_counts.values,
                        row_id,
                    )
                    if subsample_size > sum(cat_row.values()):
                        continue
                    size_low, size_high = 2, subsample_size
                    size_tmp = size_high
                    NLTTR_tmp = get_expected_subsample_variety(
                        cat_row,
                        size_tmp,
                    ) / size_tmp
                    while(True):
                        if NLTTR_tmp == target_NLTTR or size_low == size_high:
                            break
                        if size_high - size_low == 1:
                            high = get_expected_subsample_variety(
                                cat_row,
                                size_high,
                            ) / size_high
                            low = get_expected_subsample_variety(
                                cat_row,
                                size_low,
                            ) / size_low
                            if high - target_NLTTR < target_NLTTR - low:
                                size_tmp = size_high
                            else:
                                size_tmp = size_low
                            break
                        size_tmp = iround((size_low+size_high) / 2)
                        NLTTR_tmp = get_expected_subsample_variety(
                            cat_row,
                            size_tmp,
                        ) / size_tmp
                        if NLTTR_tmp < target_NLTTR:
                            size_high = size_tmp
                        elif NLTTR_tmp > target_NLTTR:
                            size_low = size_tmp
                else:
                    size_tmp = subsample_size

                varieties = list()
                for i in range(num_subsamples):
                    try:
                        sampled_row = sample_dict(row, size_tmp)
                        varieties.append(
                            get_variety(
                                sampled_row,
                                unit_weighting=units['weighting'],
                                category_weighting=categories['weighting'],
                                category_delimiter=category_delimiter,
                            )
                        )
                    except ValueError:
                        break
                if varieties:
                    (
                        new_values[(row_id, '__variety_average__')],
                        new_values[(row_id, '__variety_std_deviation__')],
                    ) = get_average(varieties)
                    new_values[(row_id, '__subsample_size__')] = size_tmp
                    new_values[(row_id, '__variety_count__')] = num_subsamples

            elif units['weighting']:

                varieties = list()
                for i in range(num_subsamples):
                    try:
                        sampled_row = sample_dict(row, subsample_size)
                        varieties.append(
                            get_variety(
                                sampled_row,
                                unit_weighting=units['weighting'],
                                category_weighting=categories['weighting'],
                                category_delimiter=category_delimiter,
                            )
                        )
                    except ValueError:
                        break
                if varieties:
                    (
                        new_values[(row_id, '__variety_average__')],
                        new_values[(row_id, '__variety_std_deviation__')],
                    ) = get_average(varieties)
                    new_values[(row_id, '__variety_count__')] = num_subsamples


            else:
                try:
                    new_values[(row_id, '__expected_variety__')]    \
                        = get_expected_subsample_variety(row, subsample_size)
                except ValueError:
                    pass
        else:
            new_values[(row_id, '__variety__')] = get_variety(
                row,
                unit_weighting=units['weighting'],
                category_weighting=categories['weighting'],
                category_delimiter=category_delimiter,
            )
        if progress_callback:
            progress_callback()

    if apply_resampling:
        if measure_per_category:
            new_col_ids = [
                '__variety_average__',
                '__variety_std_deviation__',
                '__subsample_size__',
                '__variety_count__',
            ]
        elif units['weighting']:
            new_col_ids = [
                '__variety_average__',
                '__variety_std_deviation__',
                '__variety_count__',
            ]

        else:
            new_col_ids = ['__expected_variety__']
    else:
        new_col_ids = ['__variety__']

    return (
        Table(
            counts.row_ids[:],
            new_col_ids,
            new_values,
            '__col__',
            'string',
            '__context__',
            'continuous',
            dict([(c, 'continuous') for c in new_col_ids]),
            None,
            None,
            None,
        )
    )


def annotate_contexts(
    units=None,
    multiple_values=None,
    contexts=None,
    progress_callback=None,
):
    """Annotate contexts.

    Parameter units is a dict with the following keys and values:
    KEY                     VALUE                           DEFAULT
    segmentation            unit segmentation               None
    annotation_key          annotation to be added          None
    seq_length              length of unit sequences        1
    intra_seq_delimiter     string for joining sequences    '#'

    Parameter multiple_values is a dict with following keys and values:
    KEY                     VALUE                           DEFAULT
    sort_order              order for sorting values        'Frequency'
    reverse                 reverse sort order?             False
    keep_only_first         keep only first value?          True
    value_delimiter         string for joining values       '|'

    Parameter contexts is a dict with the following keys and values:
    KEY                     VALUE                           DEFAULT
    segmentation            context segmentation            None
    annotation_key          annotation to annotated (sic)   None
    merge                   merge contexts together?        False

    Returns a table.
    """

    default_units = {
        'segmentation': None,
        'annotation_key': None,
        'seq_length': 1,
        'intra_seq_delimiter': '#',
    }
    default_multiple_values = {
        'sort_order': 'Frequency',
        'reverse': True,
        'keep_only_first': True,
        'value_delimiter': '|',
    }
    default_contexts = {
        'segmentation': None,
        'annotation_key': None,
        'merge': False,
    }
    if units is not None:
        default_units.update(units)
    units = default_units
    if multiple_values is not None:
        default_multiple_values.update(multiple_values)
    multiple_values = default_multiple_values
    if contexts is not None:
        default_contexts.update(contexts)
    contexts = default_contexts

    counts = count_in_context(
        units,
        contexts,
        progress_callback,
    )

    new_values = dict()
    for row_id in counts.row_ids:
        row = tuple_to_simple_dict(counts.values, row_id)
        if multiple_values['sort_order'] == 'Frequency':
            annotations = sorted(
                row,
                key=row.__getitem__,
                reverse=multiple_values['reverse'],
            )
        elif multiple_values['sort_order'] == 'ASCII':
            annotations = sorted(
                row.keys(),
                reverse=multiple_values['reverse'],
            )
        if multiple_values['keep_only_first']:
            new_values[(row_id, '__annotation__')] = annotations[0]
        else:
            new_values[(row_id, '__annotation__')] = (
                multiple_values['value_delimiter'].join(
                    text(a) for a in annotations
                )
            )

    # Create table...
    return (
        Table(
            counts.row_ids[:],
            ['__annotation__'],
            new_values,
            '__col__',
            'string',
            counts.header_col_id,
            counts.header_col_type,
            {'__annotation__': 'discrete'},
            '__annotation__',
            None,
            None,
        )
    )


def context(
    units=None,
    contexts=None,
    progress_callback=None,
):
    """Concordance based on containing segmentation.

    Parameter units is a dict with the following keys and values:
    KEY                     VALUE                           DEFAULT
    segmentation            unit segmentation               None
    annotation_key          annotation to be displayed      None
    separate_annotation     display annotation in own col.  True

    Parameter contexts is a dict with the following keys and values:
    KEY                     VALUE                           DEFAULT
    segmentation            context segmentation            None
    annotation_key          annotation to be displayed      None
    max_num_chars           maximum number of chars         None

    Returns a table.
    """

    default_units = {
        'segmentation': None,
        'annotation_key': None,
        'separate_annotation': True,
    }
    default_contexts = {
        'segmentation': None,
        'annotation_key': None,
        'max_num_chars': None,
    }
    if units is not None:
        default_units.update(units)
    units = default_units
    if contexts is not None:
        default_contexts.update(contexts)
    contexts = default_contexts

    row_id = 0
    new_values = dict()
    has_imm_left = False
    has_imm_right = False

    # Optimization...
    unit_segmentation = units['segmentation']
    unit_annotation_key = units['annotation_key']
    context_segmentation = contexts['segmentation']
    context_annotation_key = contexts['annotation_key']
    max_num_chars = contexts['max_num_chars']

    # Loop over context token indices...
    for context_index, context_segment in enumerate(context_segmentation):

        # Get context token and annotation...
        context_token = context_segment
        if context_annotation_key is not None:
            context_annotation = context_token.annotations.get(
                context_annotation_key,
                '__none__',
            )

        # Set max_len
        if max_num_chars is None:
            max_len = len(context_token.get_content())
        else:
            max_len = max_num_chars

        # Loop over contained units.
        for unit_index in \
                context_token.get_contained_segment_indices(
                    unit_segmentation,
                ):

            # Increment row_id.
            row_id += 1

            # Store unit position.
            new_values[(row_id, '__pos__')] = context_index + 1

            # Get unit token and its string value.
            unit_token = unit_segmentation[unit_index]
            new_values[(row_id, '__key_segment__')] \
                = unit_token.get_content()
            if unit_annotation_key is not None:
                annotation_value = unit_token.annotations.get(
                    unit_annotation_key,
                    '__none__',
                )
                if units['separate_annotation']:
                    new_values[(row_id, unit_annotation_key)] \
                        = annotation_value
                else:
                    new_values[(row_id, '__key_segment__')] \
                        = annotation_value

            # Left and right context...
            unit_start = unit_token.start or 0
            unit_end = unit_token.end or \
                len(Segmentation.get_data(unit_token.str_index))
            context_start = context_token.start or 0
            context_end = context_token.end or \
                len(Segmentation.get_data(context_token.str_index))
            if context_start < unit_start:
                imm_left_start = max(
                    context_start,
                    unit_start - max_len,
                )
                if unit_start > imm_left_start:
                    new_values[(row_id, '__left__')] = \
                        Segmentation.get_data(unit_token.str_index)[
                            imm_left_start:unit_start
                        ]
                    has_imm_left = True
            if context_end > unit_end:
                imm_right_end = min(
                    context_end,
                    unit_end + max_len,
                )
                if imm_right_end > unit_end:
                    new_values[(row_id, '__right__')] = \
                        Segmentation.get_data(unit_token.str_index)[
                            unit_end:imm_right_end
                        ]
                    has_imm_right = True

            # Context annotation:
            if context_annotation_key is not None:
                new_values[(row_id, context_annotation_key)] \
                    = context_annotation

        if progress_callback:
            progress_callback()

    # Create table...
    col_ids = ['__pos__']
    if has_imm_left:
        col_ids.append('__left__')
    col_ids.append('__key_segment__')
    if has_imm_right:
        col_ids.append('__right__')
    if unit_annotation_key is not None and units['separate_annotation']:
        col_ids.append(unit_annotation_key)
    if context_annotation_key is not None:
        col_ids.append(context_annotation_key)
    col_types = dict([(p, 'string') for p in col_ids])
    col_types['__pos__'] = 'continuous'
    return (
        Table(
            range(1, row_id + 1),
            col_ids,
            new_values,
            '__col__',
            'string',
            '__id__',
            'continuous',
            col_types,
            None,
            None,
            None,
        )
    )


def neighbors(
    units=None,
    contexts=None,
    progress_callback=None,
):
    """Concordance based on neighboring segments.

    Parameter units is a dict with the following keys and values:
    KEY                     VALUE                           DEFAULT
    segmentation            unit segmentation               None
    annotation_key          annotation to be displayed      None
    separate_annotation     display annotation in own col.  True

    Parameter contexts is a dict with the following keys and values:
    KEY                     VALUE                           DEFAULT
    segmentation            context segmentation            None
    annotation_key          annotation to be displayed      None
    max_distance            maximum distance of neighbors   None
    merge_strings           treat strings as contiguous?    False

    Returns a table.
    """

    default_units = {
        'segmentation': None,
        'annotation_key': None,
        'separate_annotation': True,
    }
    default_contexts = {
        'segmentation': None,
        'annotation_key': None,
        'max_distance': None,
        'merge_strings': False,
    }
    if units is not None:
        default_units.update(units)
    units = default_units
    if contexts is not None:
        default_contexts.update(contexts)
    contexts = default_contexts

    row_id = 0
    new_values = dict()
    if contexts['max_distance'] is not None:
        adjacent_positions = range(1, contexts['max_distance'] + 1)
    else:
        adjacent_positions = range(1, len(contexts['segmentation']))

    # Optimization...
    unit_segmentation = units['segmentation']
    unit_annotation_key = units['annotation_key']
    context_annotation_key = contexts['annotation_key']
    context_segmentation = contexts['segmentation']
    merge_strings = contexts['merge_strings']

    # Loop over context token indices...
    for context_index, context_segment in enumerate(context_segmentation):

        # Get context token and its content...
        context_token = context_segment

        # Loop over contained units.
        for unit_index in \
                context_token.get_contained_segment_indices(
                    unit_segmentation,
                ):

            # Increment row_id.
            row_id += 1

            # Store unit position.
            new_values[(row_id, '__pos__')] = context_index + 1

            # Get unit token and its string value.
            unit_token = unit_segmentation[unit_index]
            new_values[(row_id, '__key_segment__')] \
                = unit_token.get_content()
            if unit_annotation_key is not None:
                annotation_value = unit_token.annotations.get(
                    unit_annotation_key,
                    '__none__',
                )
                if units['separate_annotation']:
                    new_values[(row_id, unit_annotation_key)] \
                        = annotation_value
                else:
                    new_values[(row_id, '__key_segment__')] \
                        = annotation_value

            # Get unit token's str_index.
            unit_token_str_index = unit_token.get_real_str_index()

            # Neighboring segments...
            for pos in adjacent_positions:
                left_index = context_index - pos
                if left_index >= 0:
                    left_token = context_segmentation[left_index]
                    if (
                        merge_strings or
                        unit_token_str_index == left_token.get_real_str_index()
                    ):
                        if context_annotation_key is not None:
                            string_value = left_token.annotations.get(
                                context_annotation_key,
                                '__none__',
                            )
                        else:
                            string_value = left_token.get_content()
                        new_values[(row_id, text(pos) + 'L')] = \
                            string_value
                right_index = context_index + pos
                if right_index < len(context_segmentation):
                    right_token = context_segmentation[right_index]
                    if (
                        merge_strings or
                        unit_token_str_index == right_token.get_real_str_index()
                    ):
                        if context_annotation_key is not None:
                            string_value = right_token.annotations.get(
                                context_annotation_key,
                                '__none__',
                            )
                        else:
                            string_value = right_token.get_content()
                        new_values[(row_id, text(pos) + 'R')] = \
                            string_value

        if progress_callback:
            progress_callback()

    # Create table...
    col_ids = ['__pos__']
    col_ids.extend([text(p) + 'L' for p in reversed(adjacent_positions)])
    col_ids.append('__key_segment__')
    col_ids.extend([text(p) + 'R' for p in adjacent_positions])
    if unit_annotation_key is not None and units['separate_annotation']:
        col_ids.append(unit_annotation_key)
    col_types = dict([(p, 'string') for p in col_ids])
    col_types['__pos__'] = 'continuous'
    return (
        Table(
            range(1, row_id + 1),
            col_ids,
            new_values,
            '__col__',
            'string',
            '__id__',
            'continuous',
            col_types,
            None,
            None,
            None,
        )
    )


def collocations(
    units=None,
    contexts=None,
    progress_callback=None,
):
    """Collocations based on neighboring segments.

    Parameter contexts is a dict with the following keys and values:
    KEY                     VALUE                           DEFAULT
    segmentation            context segmentation            None
    annotation_key          annotation to be displayed      None
    max_distance            maximum distance of neighbors   None
    min_frequency           minimum type frequency          1
    merge_strings           treat strings as contiguous?    False

    Returns a table.
    """

    default_contexts = {
        'segmentation': None,
        'annotation_key': None,
        'max_distance': None,
        'min_frequency': 1,
        'merge_strings': False,
    }
    if contexts is not None:
        default_contexts.update(contexts)
    contexts = default_contexts

    neighbor_indices = set()
    global_freq = dict()
    local_freq = dict()
    new_values = dict()
    if contexts['max_distance'] is not None:
        adjacent_positions = range(1, contexts['max_distance'] + 1)
    else:
        adjacent_positions = range(1, len(contexts['segmentation']))

    # Optimization...
    context_annotation_key = contexts['annotation_key']
    context_segmentation = contexts['segmentation']
    context_min_frequency = contexts['min_frequency']
    merge_strings = contexts['merge_strings']

    # Get the list of context segments in final formats
    if context_annotation_key is not None:
        context_list = [
            c.annotations.get(
                context_annotation_key,
                '__none__',
            )
            for c in context_segmentation
        ]
    else:
        context_list = [c.get_content() for c in context_segmentation]

    # Loop over context token indices...
    for context_index, context_segment in enumerate(context_segmentation):

        # Get context token and its content...
        context_token = context_segment

        # Increment global frequency
        global_freq[context_list[context_index]] \
            = global_freq.get(context_list[context_index], 0) + 1

        # Loop over contained units.
        for unit_index in context_token.get_contained_segment_indices(units):

            # Get unit token's str_index.
            unit_token_str_index = units[unit_index].get_real_str_index()

            # Neighboring segments...
            for pos in adjacent_positions:
                left_index = context_index - pos
                if left_index >= 0:
                    if (
                        merge_strings or
                        unit_token_str_index ==
                          context_segmentation[left_index].get_real_str_index()
                    ):
                        neighbor_indices.add(left_index)
                right_index = context_index + pos
                if right_index < len(context_segmentation):
                    if (
                        merge_strings or
                        unit_token_str_index ==
                          context_segmentation[right_index].get_real_str_index()
                    ):
                        neighbor_indices.add(right_index)

        if progress_callback:
            progress_callback()

    # Count local frequency...
    for neighbor in [context_list[i] for i in neighbor_indices]:
        local_freq[neighbor] = local_freq.get(neighbor, 0) + 1

    # Remove low frequency types if needed...
    if context_min_frequency > 1:
        neighbor_types = [
            i for i in sorted(local_freq.keys())
            if global_freq[i] >= context_min_frequency
        ]
    else:
        neighbor_types = sorted(local_freq.keys())

    # Total frequencies...
    local_total_count = sum([local_freq[t] for t in neighbor_types])
    global_total_count = sum(global_freq.values())

    # Compute mutual information and store it along with frequency...
    for neighbor_type in neighbor_types:
        local_prob = local_freq[neighbor_type] / local_total_count
        global_prob = global_freq[neighbor_type] / global_total_count
        new_values[
            (neighbor_type, '__mutual_info__')
        ] = math.log(local_prob / global_prob, 2)
        new_values[
            (neighbor_type, '__local_freq__')
        ] = local_freq[neighbor_type]
        new_values[(neighbor_type, '__local_prob__')] = local_prob
        new_values[
            (neighbor_type, '__global_freq__')
        ] = global_freq[neighbor_type]
        new_values[(neighbor_type, '__global_prob__')] = global_prob

    # Create table...
    col_ids = [
        '__mutual_info__',
        '__local_freq__',
        '__local_prob__',
        '__global_freq__',
        '__global_prob__',
    ]
    return (
        Table(
            neighbor_types,
            col_ids,
            new_values,
            '__col__',
            'string',
            '__unit__',
            'string',
            dict([(c, 'continuous') for c in col_ids]),
            None,
            None,
            None,
        )
    )


# TODO: docstring
def cooc_in_window(
    units=None,
    window_size=2,
    progress_callback=None,
):
    """ Measure the cooccurrence in sliding window """
    contingency = count_in_window(
        units,
        window_size,
        progress_callback,
    )
    normalized = contingency.to_normalized('presence/absence')
    np_contingency = normalized.to_numpy()
    cooc = np.dot(
        np.transpose(np_contingency),
        np_contingency,
    )
    try:
        new_header_row_id = (
            contingency.header_row_id[:-2]
            + "2"
            + contingency.header_row_id[-2:]
        )
        return IntPivotCrosstab.from_numpy(
            contingency.col_ids[:],
            contingency.col_ids[:],
            cooc,
            contingency.header_row_id,
            contingency.header_row_type,
            new_header_row_id,
            contingency.header_row_type,
            contingency.col_type,
        )
    except IndexError:
        return IntPivotCrosstab(list(), list(), dict())


# TODO: docstring
def cooc_in_context(
    units=None,
    contexts= None,
    units2=None,
    progress_callback=None,
):
    """ Measure the cooccurrence in a context type segmentation"""
    contingency = count_in_context(
        units,
        contexts,
        progress_callback,
    )
    normalized = contingency.to_normalized('presence/absence')
    np_contingency = normalized.to_numpy()
    if units2 is not None:
        contingency2 = count_in_context(units2, contexts, progress_callback)
        normalized2 = contingency2.to_normalized('presence/absence')
        np_contingency2 = normalized2.to_numpy()
        row_labels = contingency.row_ids
        row_labels2 = contingency2.row_ids
        keep_from_contingency = [
            i for i in xrange(len(row_labels)) if row_labels[i] in row_labels2
        ]
        keep_from_contingency2 =[
            i for i in xrange(len(row_labels2)) if row_labels2[i] in row_labels
        ]
        try:
            np_contingency = np_contingency[keep_from_contingency].astype(int)
            np_contingency2 = np_contingency2[keep_from_contingency2].astype(int)
            cooc = np.dot(np.transpose(np_contingency2), np_contingency)
            if contingency.header_row_id == contingency2.header_row_id:
                new_header_row_id = (
                    contingency.header_row_id[:-2]
                    + "2"
                    + contingency.header_row_id[-2:]
                )
            else:
                new_header_row_id = contingency.header_row_id
            return IntPivotCrosstab.from_numpy(
                contingency2.col_ids[:],
                contingency.col_ids[:],
                cooc,
                contingency.header_row_id,
                contingency.header_row_type,
                new_header_row_id,
                contingency2.header_row_type,
                contingency.col_type,
            )
        except IndexError:
            return IntPivotCrosstab(list(), list(), dict())
    else:
        cooc = np.dot(np.transpose(np_contingency), np_contingency)
        try:
            new_header_row_id = (
                contingency.header_row_id[:-2]
                + "2"
                + contingency.header_row_id[-2:]
            )
            return IntPivotCrosstab.from_numpy(
                contingency.col_ids[:],
                contingency.col_ids[:],
                cooc,
                contingency.header_row_id,
                contingency.header_row_type,
                new_header_row_id,
                contingency.header_row_type,
                contingency.col_type,
            )
        except IndexError:
            return IntPivotCrosstab(list(), list(), dict())
