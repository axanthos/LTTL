from LTTL.Input import Input
import LTTL.Segmenter as Segmenter
import re

input_seg = Input("un texte")

word_seg = Segmenter.tokenize(
    input_seg,
    [(re.compile(r'\w+'), 'tokenize')],
)

consonant_seg = Segmenter.tokenize(
    input_seg,
    [(re.compile(r'[^aeiouy]'), 'tokenize')],
)

# Prints nothing (though 'n' is in 'un'
for seg in word_seg[0].get_contained_segments(consonant_seg):
    print(seg.get_content())
