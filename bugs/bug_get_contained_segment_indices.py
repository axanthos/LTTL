from LTTL.Input import Input
import LTTL.Segmenter as Segmenter
import re

input_seg = Input("un texte")

word_seg = Segmenter.tokenize(
    input_seg,
    [(re.compile(r'\w+'), 'tokenize')],
)

vowel_seg = Segmenter.tokenize(
    input_seg,
    [(re.compile(r'[aeiouy]'), 'tokenize')],
)

for i in word_seg[1].get_contained_segment_indices(vowel_seg):
    print(vowel_seg[i].get_content())
