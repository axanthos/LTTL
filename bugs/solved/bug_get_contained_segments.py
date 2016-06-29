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

for seg in word_seg[1].get_contained_segments(vowel_seg):
    print(seg.get_content())
