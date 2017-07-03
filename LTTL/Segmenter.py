"""Module Segmentation.py
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
Provides public functions:
- concatenate()
- tokenize()
- select()
- threshold()
- sample()
- intersect()
- import_xml()
- recode)
- bypass()
"""

from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

import re
import random
import unicodedata

from .Segmentation import Segmentation
from .Segment import Segment
from .Input import Input
from .Utils import iround

from builtins import range
from builtins import str as text
from builtins import dict

__version__ = "1.0.5"


def concatenate(
    segmentations,
    label='my_concatenation',
    copy_annotations=True,
    import_labels_as='component_label',
    sort=False,
    auto_number_as=None,
    merge_duplicates=False,
    progress_callback=None,
):
    """Take a list of segmentations and concatenates them into a new one

    :param segmentations: list of segmentations to concatenate

    :param label: label assigned to output segmentation

    :param copy_annotations: boolean indicating whether annotations associated
    with input segments should be copied to output

    :param import_labels_as: annotation key to which input segmentation
    labels should be associated (as annotation values) in output segments
    (default 'component_label')

    :param auto_number_as: unless set to None (default), a string indicating
    the annotation key which should be used for storing an automatically
    generated numeric index for each segment.

    :param sort: boolean indicating whether output segments should be sorted by
    address (str_index, then start position, then end position)

    :param merge_duplicates: boolean indicating whether output segments with
    the same address should be merged into a single segment.

    :param progress_callback: callback for monitoring progress ticks (1 for each
    input segment)

    :return: new segmentation containing the concatenated segments
    """

    # Initializations...
    new_segments = Segmentation()
    new_segments.label = label

    # ordered list of all unique str_index involved
    str_indices = list()
    for segmentation in segmentations:
        for k in segmentation.str_index_ptr.keys():
            if k not in str_indices:
                str_indices.append(k)

    # Sort output segment list if needed...
    if sort:
        str_indices = sorted(str_indices)

    # For each str_index...
    for index in str_indices:

        merge_ptr = list()

        # Get all input segmentations using this str_index...
        for segmentation in segmentations:
            if index in segmentation.str_index_ptr:
                merge_ptr.append((
                    segmentation,
                    segmentation.str_index_ptr[index],
                    segmentation[segmentation.str_index_ptr[index]]
                ))

        # Used to remove duplicates if necessary
        last_seen = None

        # And perform a merge sort
        while len(merge_ptr) > 0:

            # get the first segment ordered by (start,end)
            _min = merge_ptr[0]
            _argmin = 0
            for i, ptr in enumerate(merge_ptr[1:]):
                if (ptr[2].start, ptr[2].end) < (_min[2].start, _min[2].end):
                    _min = ptr
                    _argmin = i + 1
            segment = _min[2]
            segmentation = merge_ptr[_argmin][0]

            # was it the last segment of this segmentation?
            if merge_ptr[_argmin][1] + 1 >= len(merge_ptr[_argmin][0]):
                del merge_ptr[_argmin]
            # otherwise increment the corresponding pointer and take the next
            # segment from this segmentation
            else:
                merge_ptr[_argmin] = (
                    merge_ptr[_argmin][0],
                    merge_ptr[_argmin][1] + 1,
                    merge_ptr[_argmin][0][merge_ptr[_argmin][1]+1],
                )

                # if we are done with this segmentation, remove it from the list
                if merge_ptr[_argmin][2].str_index != index:
                    del merge_ptr[_argmin]

            # Copy segment (including annotations and/or importing input
            # segmentation label if needed)...
            if import_labels_as is not None and len(import_labels_as) > 0:
                new_segment = segment.deepcopy(
                    annotations={import_labels_as: segmentation.label},
                    update=copy_annotations,
                )
            else:
                new_segment = segment.deepcopy(update=copy_annotations)

            if (
                merge_duplicates and
                last_seen and
                last_seen.start == new_segment.start and
                last_seen.end == new_segment.end
            ):

                # merge and update annotations
                last_segment = new_segments[-1]
                last_segment.annotations.update(new_segment.annotations)
                new_segments[-1] = last_segment
            else:
                # Append copied segment to list.
                new_segments.append(new_segment)

            last_seen = segment

            if progress_callback:
                progress_callback()

    # Auto-number if needed...
    if auto_number_as is not None and len(auto_number_as) > 0:
        _auto_number(new_segments, auto_number_as)

    return new_segments


# TODO: verify impact of changing default value of merge_duplicate to False
# TODO: verify impact of sorting new segments outside of regex loop
def tokenize(
    segmentation,
    regexes,
    label='segmented_data',
    import_annotations=True,
    merge_duplicates=False,
    auto_number_as=None,
    progress_callback=None,
):
    """Tokenize the segments of an existing segmentation using regexes and
    create a new segmentation with the resulting tokens

    :param segmentation: the segmentation whose segments' content will be
    tokenized

    :param regexes: a list of tuple, where each tuple has a compiled regex
    as first element, either 'tokenize' or 'split' as second element (see
    below), and an optional dict as third element; the dict has a single key
    representing an annotation key to be created with the corresponding value
    (both the key and the value are unicode strings); regexes are successively
    applied to each segment of the input segmentation.

    :param label: the label assigned to the output segmentation

    :param import_annotations: boolean indicating whether annotations associated
    with input segments should be copied to output segments extracted from them
    (default True)

    :param merge_duplicates: boolean indicating whether output segments with
    the same address should be merged into a single segment (default False)

    :param auto_number_as: unless set to None (default), a string indicating
    the annotation key which should be used for storing an automatically
    generated numeric index for each segment

    :param progress_callback: callback for monitoring progress ticks (number of
    input segments)

    :return: new segmentation containing the tokenized segments

    In 'tokenize' mode, the regex describes the desired form of new segments,
    so that they are created on the basis of the matches of the regex. In
    'split' mode, the regex describes the separators between the desired
    segments (which are then created on the basis of what appears between the
    matches).

    Only in 'tokenize' mode:
    Annotation keys and values may contain backreferences in the form of
    and ampersand (&) immediately followed by a digit referring to the
    group to be captured. E.g. if the regex is r'Mrs? ([A-Z]\w+)', the
    annotation key--value pair could be {'name': '&1'}, so that the name
    is actually captured in the annotation.
    """

    # Initializations...
    new_segmentation = Segmentation(None, label)
    annotation_k_backref_indices = list()
    annotation_v_backref_indices = list()
    annotation_key_format = list()
    annotation_value_format = list()
    contains_backrefs = re.compile(r'&([0-9]+)')

    # For each regex...
    for regex in regexes:

        # If it is associated with an annotation key-value pair...
        if len(regex) == 3:

            # Get annotation key and value...
            key = list(regex[2])[0]
            value = list(regex[2].values())[0]

            # Look for backrefs in key and value, extract the list of
            # corresponding digits (indices) and associate it with this regex...
            annotation_k_backref_indices.append(
                [match for match in contains_backrefs.findall(key)]
            )
            annotation_v_backref_indices.append(
                [match for match in contains_backrefs.findall(value)]
            )

            # If backrefs were found, replace them in formats with standard
            # '%s' Python placeholders and associate the formats with this
            # regex, else set them to None...
            if len(annotation_k_backref_indices[-1]):
                annotation_key_format.append(
                    contains_backrefs.sub('%s', key)
                )
            else:
                annotation_key_format.append(None)
            if len(annotation_v_backref_indices[-1]):
                annotation_value_format.append(
                    contains_backrefs.sub('%s', value)
                )
            else:
                annotation_value_format.append(None)

        # Else if the regex is not associated with an annotation key-value pair,
        # set backref indices and formats to empty list and None...
        else:
            annotation_k_backref_indices.append(list())
            annotation_v_backref_indices.append(list())
            annotation_key_format.append(None)
            annotation_value_format.append(None)

    # For each input segment...
    for segment in segmentation:
        # Initializations...
        new_segments = list()
        str_index = segment.str_index
        start = segment.start or 0
        content = segment.get_content()

        # Copy existing annotations if needed...
        if import_annotations and segment.annotations is not None:
            old_segment_annotation_copy = segment.annotations.copy()
        else:
            old_segment_annotation_copy = None

        # For each regex...
        for regex_index in range(len(regexes)):
            regex = regexes[regex_index]

            # Prepare a fresh copy of the existing annotations...
            if old_segment_annotation_copy is not None:
                regex_annotations = old_segment_annotation_copy.copy()
            else:
                regex_annotations = None
            # CASE 1: If regex has mode 'tokenize'...
            if regex[1] == 'tokenize':

                # For each match of the regex...
                for match in re.finditer(regex[0], content):
                    key = None
                    value = None

                    # If there is a list of backref indices in the annotation
                    # key associated with this regex...
                    if len(annotation_k_backref_indices[regex_index]):

                        # Apply the corresponding format, replacing the
                        # backrefs with the relevant groups captured by the
                        # regex....
                        key = annotation_key_format[regex_index] % tuple(
                            [
                                match.group(int(i))
                                for i in annotation_k_backref_indices[
                                    regex_index
                                ]
                            ]
                        )

                    # Else, simply use the annotation key as provided by the
                    # user, if any...
                    elif len(regex) == 3:
                        key = list(regex[2])[0]

                    # If there is a list of backref indices in the annotation
                    # value...
                    if len(annotation_v_backref_indices[regex_index]):

                        # Apply the corresponding format, replacing the
                        # backrefs....
                        value = annotation_value_format[regex_index] % tuple(
                            [
                                match.group(int(i))
                                for i in annotation_v_backref_indices[
                                    regex_index
                                ]
                            ]
                        )
                    # Else use the annotation value as is, if any...
                    elif len(regex) == 3:
                        value = list(regex[2].values())[0]

                    # Prepare a copy of existing annotations for the segment
                    # corresponding to this match of the regex.
                    if regex_annotations is not None:
                        new_segment_annotations = regex_annotations.copy()
                    else:
                        new_segment_annotations = dict()
                    # Update annotations with the key-value pair prepared
                    # above, if any...
                    if key is not None and value is not None:
                        new_segment_annotations.update({key: value})

                    # Create and store the new segment...
                    new_segments.append(
                        Segment(
                            str_index,
                            start + match.start(),
                            start + match.end(),
                            new_segment_annotations
                        )
                    )

            # CASE 2: If regex has mode 'split'...
            elif regex[1] == 'split':

                # Prepare a copy of existing annotations for the segment
                # identified by this regex...
                if regex_annotations is not None:
                    new_segment_annotations = regex_annotations.copy()
                else:
                    new_segment_annotations = dict()

                # Update it with the annotation key and value provided by the
                # user, if any (no interpolation in this mode)...
                if len(regex) == 3:
                    key = list(regex[2])[0]
                    value = list(regex[2].values())[0]
                    new_segment_annotations.update({key: value})

                # For each match of the regex...
                previous_end_pos = start
                for match in re.finditer(regex[0], content):

                    # If this match is at the beginning of the segment, skip to
                    # next match...
                    if start + match.start() == previous_end_pos:
                        previous_end_pos = start + match.end()
                        continue

                    # Otherwise create and store the new segment...
                    new_segments.append(
                        Segment(
                            str_index,
                            previous_end_pos,
                            start + match.start(),
                            new_segment_annotations.copy()
                        )
                    )
                    previous_end_pos = start + match.end()

                # If the last match is not at the end of the segment, create
                # a last segment...
                segment_end_pos = start + len(content)
                if previous_end_pos < segment_end_pos:
                    new_segments.append(
                        Segment(
                            str_index,
                            previous_end_pos,
                            segment_end_pos,
                            new_segment_annotations.copy()
                        )
                    )

            # Other modes raise a ValueError exception.
            else:
                raise ValueError(
                    'Unknown regex mode "' + regex[1] + '", ' +
                    'should be either "tokenize" or "split"'
                )

            if progress_callback:
                progress_callback()

        # Sort segments...
        new_segments.sort(key=lambda s: (
            s.str_index,
            s.start,
            s.end,
        ))

        # Add the new segments to the output segmentation.
        new_segmentation.extend(new_segments)

    # Merge duplicate segments if needed...
    if merge_duplicates:
        new_segmentation = _merge_duplicate_segments(new_segmentation, False)

    # Auto-number (if needed)...
    if auto_number_as is not None and len(auto_number_as) > 0:
        _auto_number(new_segmentation, auto_number_as)

    return new_segmentation


# TODO: verify number of iterations in callers (cf. auto-numbering)
def select(
    segmentation,
    regex,
    mode='include',
    annotation_key=None,
    label='selected_data',
    copy_annotations=True,
    auto_number_as=None,
    progress_callback=None,
):
    """In-/exclude segments in a segmentation based on a regex

    :param segmentation: the segmentation whose segments will be selected

    :param regex: the compiled regex that each segment will be matched against

    :param mode: either 'include' (default) or 'exclude'. The former means that
    matching segments will be kept in the output, and the other way round for
    the latter

    :param annotation_key: unless set to None (default), a string indicating
    the annotation key whose value should be matched against the regex in place
    of the segment's content.

    :param label: the label assigned to the output segmentation

    :param copy_annotations: boolean indicating whether annotations associated
    with input segments should be copied to output segments (default True)

    :param auto_number_as: unless set to None (default), a string indicating
    the annotation key which should be used for storing an automatically
    generated numeric index for each segment

    :param progress_callback: callback for monitoring progress ticks (1 for each
    input segment)

    :return: a tuple whose first element is a new segmentation containing the
    selected segments, and whose second value is a new segmentation containing
    the segments that have not been selected (the latter has the same label as
    the former, prefixed by 'NEG_')
    """

    # Initializations...
    new_segmentation = Segmentation(list(), label)
    neg_segmentation = Segmentation(list(), 'NEG_' + label)

    # For each input segment...
    for segment in segmentation:

        # Match either annotation value or segment content against regex...
        if annotation_key:
            if annotation_key in segment.annotations:
                match = regex.search(
                    text(segment.annotations[annotation_key])
                )
            else:
                match = None    # If key is not found, no match.
        else:
            match = regex.search(segment.get_content())

        # Copy segment (including annotations if needed)...
        new_segment = segment.deepcopy(update=copy_annotations)

        # Add copied segment to selected segments or to the complementary
        # segmentation...
        if (match and mode == 'include') or (not match and mode == 'exclude'):
            new_segmentation.append(new_segment)
        else:
            neg_segmentation.append(new_segment)

        if progress_callback:
            progress_callback()

    # Auto-number if needed...
    if auto_number_as is not None and len(auto_number_as) > 0:
        _auto_number(new_segmentation, auto_number_as)
        _auto_number(neg_segmentation, auto_number_as)

    return new_segmentation, neg_segmentation


# TODO: verify number of iterations in callers (cf. auto-numbering)
def threshold(
    segmentation,
    min_count=None,
    max_count=None,
    annotation_key=None,
    label='thresholded_data',
    copy_annotations=True,
    auto_number_as=None,
    progress_callback=None,
):
    """Include segments in a segmentation based on min/max count

    :param segmentation: the segmentation whose segments will be selected

    :param min_count: the minimum count threshold for a segment type to
    be included in the output (default None)

    :param max_count: the maximum count threshold for a segment type to
    be included in the output (default None)

    :param annotation_key: unless set to None (default), a string indicating
    the annotation key whose value will be counted in place of the segment's
    content to determine in-/exclusion

    :param label: the label assigned to the output segmentation

    :param copy_annotations: boolean indicating whether annotations associated
    with input segments should be copied to output segments (default True)

    :param auto_number_as: unless set to None (default), a string indicating
    the annotation key which should be used for storing an automatically
    generated numeric index for each segment

    :param progress_callback: callback for monitoring progress ticks (1 for each
    input segment)

    :return: a tuple whose first element is a new segmentation containing the
    selected segments, and whose second value is a new segmentation containing
    the segments that have not been selected (the latter has the same label as
    the former, prefixed by 'NEG_')
    """

    # Get numeric values for effectively not setting a minimum count (=0) or a
    # maximum count (=length of input segmentation)...
    if min_count is None:
        min_count = 0
    if max_count is None:
        max_count = len(segmentation)

    # Get a list of items to be counted (segment content or annotation value)...
    if annotation_key is None:
        token_list = [u.get_content() for u in segmentation]
    else:
        token_list = [
            u.annotations[annotation_key] for u in segmentation if (
                annotation_key in u.annotations
            )
        ]

    # Count item frequency...
    count = dict()
    for token in token_list:
        try:
            count[token] += 1
        except KeyError:
            count[token] = 1

    # Initialize output segmentations...
    new_segmentation = Segmentation(list(), label)
    neg_segmentation = Segmentation(list(), 'NEG_' + label)

    # For each input segment...
    for segment in segmentation:

        # Get relevant item (content or annotation key)...
        if annotation_key:
            try:
                token = segment.annotations[annotation_key]
            except KeyError:
                token = '__none__'
        else:
            token = segment.get_content()

        # Copy segment (including annotations if needed)...
        new_segment = segment.deepcopy(update=copy_annotations)

        # If the count of this item's type is in the specified range, add copied
        # segment to the selected segments, else add it to complementary
        # segmentation...
        if min_count <= count[token] <= max_count:
            new_segmentation.append(new_segment)
        else:
            neg_segmentation.append(new_segment)

        if progress_callback:
            progress_callback()

    # Auto-number if needed...
    if auto_number_as is not None and len(auto_number_as) > 0:
        _auto_number(new_segmentation, auto_number_as)
        _auto_number(neg_segmentation, auto_number_as)

    return new_segmentation, neg_segmentation


def sample(
    segmentation,
    sample_size,
    mode='random',
    label='sampled_data',
    copy_annotations=True,
    auto_number_as=None,
    progress_callback=None,
):
    """Draw a sample from a segmentation

    :param segmentation: the segmentation whose segments will be sampled

    :param sample_size: the number of segments to sample

    :param mode: either 'random' (default) or 'systematic'; the former means
    that segments can be taken from any position in the input segmentation,
    while the latter means that segments are sampled at fixed intervals (every
    n-th input segment, starting from the first).

    :param label: the label assigned to the output segmentation

    :param copy_annotations: boolean indicating whether annotations associated
    with input segments should be copied to output segments (default True)

    :param auto_number_as: unless set to None (default), a string indicating
    the annotation key which should be used for storing an automatically
    generated numeric index for each segment

    :param progress_callback: callback for monitoring progress ticks (1 for each
    input segment)

    :return: a tuple whose first element is a new segmentation containing the
    sampled segments, and whose second value is a new segmentation containing
    the segments that have not been sampled (the latter has the same label as
    the former, prefixed by 'NEG_')
    """

    # Initialize output segmentations...
    new_segmentation = Segmentation(None, label)
    neg_segmentation = Segmentation(None, 'NEG_' + label)

    # Get the indices of sampled segments...
    if mode == 'random':
        sampled_indices = sorted(random.sample(
            range(len(segmentation)),
            sample_size
        ))
    elif mode == 'systematic':
        step = 1 / (sample_size / len(segmentation))
        step = iround(step)
        sampled_indices = list(range(len(segmentation)))[::step]
    # Other modes raise a ValueError exception.
    else:
        raise ValueError(
            'Unknown sampling mode "' + mode + '", ' +
            'should be either "random" or "systematic"'
        )

    # For each sampled segment...
    for index, segment in enumerate(segmentation):

        # Copy segment (including annotations if needed)...
        new_segment = segment.deepcopy(update=copy_annotations)

        # Assign new segment to sampled segmentation or complementary
        # segmentation...
        if index in sampled_indices:
            new_segmentation.append(new_segment)
        else:
            neg_segmentation.append(new_segment)

        if progress_callback:
            progress_callback()

    # Auto-number if needed...
    if auto_number_as is not None and len(auto_number_as) > 0:
        _auto_number(new_segmentation, auto_number_as)
        _auto_number(neg_segmentation, auto_number_as)

    return new_segmentation, neg_segmentation


# TODO: verify number of iterations in callers (cf. auto-numbering)
def intersect(
    source,
    filtering,
    source_annotation_key=None,
    filtering_annotation_key=None,
    mode='include',
    label='selected_data',
    copy_annotations=True,
    auto_number_as=None,
    progress_callback=None,
):
    """In-/exclude segments in a segmentation ("source") based on whether these
    types occur in another segmentation ("filtering").

    :param source: the source segmentation, whose segments will be included in
    or excluded from the output

    :param filtering: the filtering segmentation, whose segments will be used
    to determine in-/exclusion of source segments

    :param source_annotation_key: unless set to None (default), a string
    indicating the annotation key whose value will be used in place of source
    segment content to determine in-/exclusion

    :param filtering_annotation_key: unless set to None (default), a string
    indicating the annotation key whose value will be used in place of
    filtering segment content to determine in-/exclusion

    :param mode: either 'include' (default) or 'exclude'. The former means that
    source segments present in filtering segmentation will be kept in the
    output, and the latter means that they will be excluded from the output.

    :param label: the label assigned to the output segmentation

    :param copy_annotations: boolean indicating whether annotations associated
    with input segments should be copied to output segments (default True)

    :param auto_number_as: unless set to None (default), a string indicating
    the annotation key which should be used for storing an automatically
    generated numeric index for each segment

    :param progress_callback: callback for monitoring progress ticks (1 for
    each source segment)

    :return: a tuple whose first element is a new segmentation containing the
    selected segments, and whose second value is a new segmentation containing
    the segments that have not been selected (the latter has the same label as
    the former, prefixed by 'NEG_')
    """

    # Build a list with filtering items (content or annotation values)...
    if filtering_annotation_key is not None:
        filtering_list = [
            s.annotations[filtering_annotation_key] for s in filtering if (
                filtering_annotation_key in s.annotations
            )
        ]
    else:
        filtering_list = [s.get_content() for s in filtering]

    # Store filtering items in a set (for fast retrieval)...
    filtering_set = set(filtering_list)

    # Initialize the output segmentations...
    new_segmentation = Segmentation(list(), label)
    neg_segmentation = Segmentation(list(), 'NEG_' + label)

    # For each source segment...
    for segment in source:

        # Copy segment (including annotations if needed)...
        new_segment = segment.deepcopy(update=copy_annotations)

        # Match source item against filtering item and store copied segment in
        # output segmentation accordingly...
        if source_annotation_key:
            if source_annotation_key in segment.annotations:
                match = text(segment.annotations[source_annotation_key]) \
                    in filtering_set
            else:
                match = 0
        else:
            match = segment.get_content() in filtering_set
        if (match and mode == 'include') or (not match and mode == 'exclude'):
            new_segmentation.append(new_segment)
        else:
            neg_segmentation.append(new_segment)

        if progress_callback:
            progress_callback()

    # Auto-number (if needed)...
    if auto_number_as is not None and len(auto_number_as) > 0:
        _auto_number(new_segmentation, auto_number_as)
        _auto_number(neg_segmentation, auto_number_as)

    return new_segmentation, neg_segmentation


def import_xml(
    segmentation,
    element,
    conditions=None,
    import_element_as=None,
    label='xml_data',
    import_annotations=True,
    merge_duplicates=False,
    auto_number_as=None,
    remove_markup=False,
    preserve_leaves=False,
    progress_callback=None,
):
    """Create a segmentation based on the xml content of an existing one.

    Each occurrence of a specified xml tag is converted into a segment, and
    its attribute-value pairs are converted into annotation key-value pairs.

    Empty elements are discarded since they cannot be represented by LTTL's
    data model.

    XML processing is rather crude for the time being: no attempt to
    resolve entities, detect errors and recover from them, and so on.

    :param segmentation: the segmentation whose segment's content will be
    parsed

    :param element: the specific xml tag used for creating segments

    :param conditions: a dict where each key is the name of an attribute
    and each value is a compiled regex that must be satisfied by the
    attribute value for an occurrence of the element to be selected,
    e.g. {'class': re.compile(r'^navigation$')} (default None)

    :param import_element_as: unless set to None (default), a string indicating
    the annotation key which should be used for storing the name of the
    xml element

    :param label: the label assigned to the output segmentation

    :param import_annotations: boolean indicating whether annotations
    associated with input segments should be copied to output segments
    extracted from them (default True)

    :param merge_duplicates: boolean indicating whether output segments with
    the same address should be merged into a single segment (default False)

    :param auto_number_as: unless set to None (default), a string indicating
    the annotation key which should be used for storing an automatically
    generated numeric index for each segment

    :param remove_markup: a boolean indicating whether markup occurring within
    the xml elements being retrieved should be discarded or kept (default
    True). If discarded, more segments will usually be generated, since LTTL's
    data model has no means of representing discontinuous units with a single
    segment.

    :param preserve_leaves: a boolean determining the processing of the very
    particular case where (a) extracted elements are exactly embedded in one
    another, (b) they have different values for the same attribute, (c) the
    remove_markup parameter is selected and (d) the merge_duplicates option
    as well. In such a case, the method will seek to fuse the considered
    elements into one, and it will only be able to keep one of the conflicting
    annotation values; if preserve_leaves is False (default), the value
    associated to the element closest to the root in the XML tree will be kept,
    otherwise the value of the element closest to the "surface" will be kept.

    :param progress_callback: callback for monitoring progress ticks (1 for
    each input segment)

    :return: new segmentation containing the extracted segments
    """

    # Initializations...
    if conditions is None:
        conditions = dict()
    tag_regex = re.compile(r'</?[^>]+?/?>')
    stack = list()
    attr_stack = list()
    new_segmentation = Segmentation(list(), label)

    # Remove angle brackets from element if necessary...
    element = element.replace('<', '').replace('>', '')

    # Inner helper for removing segments that are empty or don't match
    # attribute regexes...
    def filter_segment(str_index, start, end, annotations):
        start = start or 0
        if end is None:
            end = len(Segmentation.get_data(str_index))
        if start == end:
            return False
        for (attr, value_regex) in conditions.items():
            if (
                    (attr not in annotations) or
                    (not value_regex.search(annotations[attr]))
            ):
                return False
        return True

    temp_segments = list()

    # For each input segment...
    for old_segment in segmentation:

        # Get its content and copy its annotations (if needed)...
        old_content = old_segment.get_content()
        if import_annotations:
            old_anno_copy = old_segment.annotations.copy()
        else:
            old_anno_copy = dict()

        # Create annotation for xml element if needed
        if import_element_as is not None and len(import_element_as) > 0:
            old_anno_copy.update({import_element_as: element})

        # Get segment address...
        old_str_index = old_segment.str_index
        old_start = old_segment.start or 0

        # For each occurrence of the specified xml tag in the content...
        for match in re.finditer(tag_regex, old_content):

            # Get tag position and parse it...
            tag_start = old_start + match.start()
            tag_end = old_start + match.end()
            tag = Segmentation.get_data(old_str_index)[tag_start:tag_end]
            tag_desc = _parse_xml_tag(tag)

            # Get the address and annotations of potential new segments,
            # removing inner markup if needed...
            if remove_markup:
                for index in range(len(stack)):
                    if stack[index][-1][0] == old_str_index:
                        stack[index][-1][2] = tag_start
                    else:
                        anno = old_anno_copy.copy()
                        anno.update(attr_stack[index])
                        stack[index].append([old_str_index, 0, tag_start, anno])
                if (
                        tag_desc['element'] == element and
                        not tag_desc['is_empty']
                ):
                    if tag_desc['is_opening']:
                        stack.append(list())
                        attr_stack.append(tag_desc['attributes'])
                    elif stack:
                        temp_segments.extend(
                            [
                                Segment(s[0], s[1], s[2], s[3])
                                for s in stack.pop()
                                if filter_segment(s[0], s[1], s[2], s[3])
                            ]
                        )
                        attr_stack.pop()
                    # TODO: use tag to produce a more useful error message.
                    else:
                        raise ValueError('xml parsing error')
                for index in range(len(stack)):
                    anno = old_anno_copy.copy()
                    anno.update(attr_stack[index])
                    stack[index].append([old_str_index, tag_end, None, anno])
            else:
                for index in range(len(stack)):
                    if stack[index][-1][0] != old_str_index:
                        anno = old_anno_copy.copy()
                        anno.update(attr_stack[index])
                        stack[index].append(
                            [old_str_index, 0, None, anno]
                        )
                if (
                        tag_desc['element'] == element and
                        not tag_desc['is_empty']
                ):
                    if tag_desc['is_opening']:
                        anno = old_anno_copy.copy()
                        anno.update(tag_desc['attributes'])
                        stack.append([
                            [old_str_index, tag_end, None, anno]
                        ])
                        attr_stack.append(tag_desc['attributes'])
                    elif stack:
                        stack[-1][-1][2] = tag_start
                        temp_segments.extend(
                            [
                                Segment(s[0], s[1], s[2], s[3])
                                for s in stack.pop()
                                if filter_segment(s[0], s[1], s[2], s[3])
                            ]
                        )
                        attr_stack.pop()
                    # TODO: use tag to produce a more useful error message.
                    else:
                        raise ValueError(
                            'xml parsing error '
                            '(orphan closing tag)'
                        )

        if progress_callback:
            progress_callback()

    temp_segments = sorted(
        temp_segments, key=lambda seg: (seg.str_index, seg.start, seg.end)
    )
    new_segmentation.extend(temp_segments)

    # TODO: use stack to produce a more useful error message.
    if stack:
        raise ValueError('xml parsing error (missing closing tag)')

    # Sort segments...
    # new_segmentation = new_segmentation._sort()

    # Delete duplicate segments and merge their annotations if needed...
    if merge_duplicates:
        new_segmentation = _merge_duplicate_segments(
            new_segmentation,
            preserve_leaves,
        )

    # Auto-number if needed...
    if auto_number_as is not None and len(auto_number_as) > 0:
        _auto_number(new_segmentation, auto_number_as)

    return new_segmentation


def recode(
    segmentation,
    substitutions=None,
    case=None,
    remove_accents=False,
    label='my_recoded_data',
    copy_annotations=True,
    progress_callback=None,
):
    """Recode the string(s) associated with a segmentation.

    Standard preprocessing options (change case and remove accents) are
    available, as well as regex-based substitutions. Note that if both types of
    recoding are requested, preprocessing is applied prior to substitutions.

    :param segmentation: the segmentation whose segments' content will be
    recoded

    :param substitutions: a list of tuple, where each tuple has a compiled
    regex as first element, and a replacement string as second element (see
    below); substitutions are successively applied to each segment of the input
    segmentation.

    :param case: unless set to None (default), a unicode string indicating how
    case should be modified (either 'lower' or 'upper')

    :param remove_accents: boolean indicating whether accents should be removed
    (default True)

    :param label: the label assigned to the output segmentation

    :param copy_annotations: boolean indicating whether annotations associated
    with input segments should be copied to output segments (default True)

    :param progress_callback: callback for monitoring progress ticks (1 for
    each input segment)

    :return: tuple whose first element is a new segmentation containing the
    recoded segments (this will be an Input object if it contains only one
    segment, and a Segmentation object if it contains more than one segments or
    if no string was modified by the specified recoding operations); the second
    element is the total number of replacements performed.

    Replacement strings may contain backreferences in the form of an ampersand
    (&) immediately followed by a digit referring to the group to be captured
    (the form &+digit, which is not standard in Python, is used here for
    consistency with LTTL.Segmenter.tokenize()).

    A ValueError exception is raised if input segmentation is overlapping.
    """

    # Check that input segmentation is not overlapping...
    if not segmentation.is_non_overlapping():
        raise ValueError('Cannot apply recoder to overlapping segmentation.')

    # Initializations...
    new_objects = list()
    backref = re.compile(r'&(?=[0-9]+)')

    last_recoded = False
    old_str_index = -1
    new_str_index = -1

    total_num_subs = 0

    # For each input segment...
    for segment in segmentation:

        # Get its content and initialized recoded string...
        original_text = segment.get_content()
        recoded_text = original_text

        # Change case if needed...
        if case == 'lower':
            recoded_text = recoded_text.lower()
        elif case == 'upper':
            recoded_text = recoded_text.upper()

        # Remove accents if needed...
        # (cf. http://stackoverflow.com/questions/517923/
        # what-is-the-best-way-to-remove-accents-in-a-python-unicode-string)
        if remove_accents:
            recoded_text = ''.join(
                (c for c in unicodedata.normalize('NFD', recoded_text)
                 if unicodedata.category(c) != 'Mn')
            )

        # Apply substitutions (if any)...
        if substitutions is not None:
            for substitution in substitutions:
                repl_string = backref.sub(r'\\', substitution[1])
                recoded_text, num_subs = substitution[0].subn(
                    repl_string,
                    recoded_text,
                )
                total_num_subs += num_subs

        # If text was modified, create and store new Input...
        if recoded_text != original_text:
            new_input = Input()
            new_input.update(recoded_text, label)
            modified_segment = new_input[0]
            if copy_annotations:
                modified_segment.annotations.update(segment.annotations.copy())
                new_input[0] = modified_segment
            last_recoded = True
            new_objects.append(new_input)

        # Else if text was not modified, create and store new Segment...
        else:
            # last segment was recoded and thus has a new str_index
            if last_recoded and segment.str_index == old_str_index:
                Segmentation.set_data(-1, old_str_index)
                new_str_index = len(Segmentation.data) - 1
            if segment.str_index != old_str_index:
                old_str_index = segment.str_index
                new_str_index = segment.str_index

            new_segment = Segment(
                str_index=new_str_index,
                start=segment.start,
                end=segment.end,
            )

            if copy_annotations:
                new_segment.annotations.update(segment.annotations)
            last_recoded = False
            new_objects.append(new_segment)

        if progress_callback:
            progress_callback()

    # If list of new objects contains a single Input, return it.
    if len(new_objects) == 1 and isinstance(new_objects[0], Input):
        return new_objects[0], total_num_subs
    # Otherwise return a new segmentation with the segments in the list
    # (including those contained in Input objects).
    # else:
    new_segmentation = Segmentation(None, label)
    for new_object in new_objects:
        if isinstance(new_object, Input):
            new_segmentation.append(new_object[0])
        else:
            new_segmentation.append(new_object)
    return new_segmentation, total_num_subs


def bypass(segmentation, label='bypassed_data'):
    """Return a verbatim copy of a segmentation

    :param segmentation: the segmentation whose segments' content will be
    deep copied

    :param label: the label assigned to the output segmentation

    :return: deep copied segmentation.
    """
    return Segmentation([s.deepcopy() for s in segmentation], label)


def _merge_duplicate_segments(segmentation, take_first=False):
    """Delete duplicate segments in a segmentation and merge their annotations

    Using the fact that segments are always ordered by (start,end) and
    str_index are contiguous, it only needs to look for consecutively identical
    segments.

    :param segmentation: the list of input segments can be a Segmentation or
    a list

    :param take_first: if set to True the annotations of the first segment, in
    case of conflit when merging, are not overwritten

    :return: output segmentation with merged segments
    """

    new_segments = Segmentation(label=segmentation.label)

    last_seen = None

    for segment in segmentation:

        # is it a duplicate?
        if (
            last_seen and
            last_seen.str_index == segment.str_index and
            last_seen.start == segment.start and
            last_seen.end == segment.end
        ):

            last_segment = new_segments[-1]

            if take_first:
                segment.annotations.update(last_segment.annotations)
                new_segments[-1] = segment
            else:
                last_segment.annotations.update(segment.annotations)
                new_segments[-1] = last_segment
        # otherwise just add it
        else:
            new_segments.append(segment)

        last_seen = segment

    return new_segments


def _auto_number(segmentation, annotation_key):
    """Add annotation with integers from 1 to N to segments in a list (in place)

    :param segment_list: the list of segments to auto-number

    :param annotation_key: the annotation key with which generated numbers will
    be associated
    """
    counter = 1
    for index, segment in enumerate(segmentation):
        segment.annotations[annotation_key] = counter
        segmentation[index] = segment
        counter += 1


def _parse_xml_tag(tag):
    """Parse an xml tag and return a dict describing it.

    :return: a dict with following keys:
    - is_element:   False for processing instructions, comments, etc.
    - is_opening:   True if tag is element opening tag, False otherwise
    - is_empty:     True if tag is empty element, False otherwise
    - element:      element name (None if not is_element)
    - attributes:   a dict with a key-value pair for each xml attribute
    If parsing fails somehow, return value is None.
    """
    element_regex = re.compile(r'(\w+)', re.U)
    attribute_regex = re.compile(r'''(\w+)\s*=\s*(['"])(.+?)(?<!\\)\2''', re.U)
    tag_description = {
        'is_element': False,
        'is_opening': False,
        'is_empty': False,
        'element': None,
        'attributes': dict(),
    }
    if tag[1] == '!' or tag[1] == '?':
        return tag_description
    elem = re.search(element_regex, tag)
    if elem:
        tag_description['is_element'] = True
        tag_description['element'] = elem.group(1)
        for attr in re.finditer(attribute_regex, tag):
            tag_description['attributes'][attr.group(1)] = attr.group(3)
        if tag[1] != '/':
            tag_description['is_opening'] = True
        if tag[-2] == '/':
            tag_description['is_empty'] = True
        return tag_description
    return None
