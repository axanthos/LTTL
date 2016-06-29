from LTTL.Input import Input
import LTTL.Segmenter as Segmenter
import LTTL.Processor as Processor
import re

input_seg = Input("a simple example")

word_seg = Segmenter.tokenize(
    input_seg,
    [(re.compile(r'\w+'), 'tokenize')],
)

letter_seg = Segmenter.tokenize(
    word_seg,
    [(re.compile(r'\w'), 'tokenize')],
)

table = Processor.count_in_context(
    units={'segmentation': letter_seg},
    contexts={'segmentation': word_seg},
)

table.to_normalized(mode='columns', type='l2')
