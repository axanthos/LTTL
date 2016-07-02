from LTTL.Input import Input
import LTTL.Segmenter as Segmenter
import re

def main():

    input_seg = Input("un texte")

    verbatim_seg = Segmenter.tokenize(
        input_seg,
        [(re.compile(r'.+'), 'tokenize')],
    )

    # verbatim in input = ok
    print "verbatim in input:",
    contained_segments = input_seg[0].get_contained_segments(verbatim_seg)
    try:
        print "ok" if contained_segments[0].get_content() == 'un texte' else "fail"
    except:
        print "fail"

    # verbatim in verbatim = ok
    print "verbatim in verbatim:",
    contained_segments = verbatim_seg[0].get_contained_segments(verbatim_seg)
    try:
        print "ok" if contained_segments[0].get_content() == 'un texte' else "fail"
    except:
        print "fail"

    # input in verbatim = fail
    print "input in verbatim:",
    contained_segments = verbatim_seg[0].get_contained_segments(input_seg)
    try:
        print "ok" if contained_segments[0].get_content() == 'un texte' else "fail"
    except:
        print "fail"

    # input in input = fail
    print "input in input:",
    contained_segments = input_seg[0].get_contained_segments(input_seg)
    try:
        print "ok" if contained_segments[0].get_content() == 'un texte' else "fail"
    except:
        print "fail"


if __name__ == '__main__':
    main()