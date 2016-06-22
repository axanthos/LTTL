from LTTL.Input import Input
from LTTL.Segmenter import concatenate

def main():
    input1 = Input('hello', 'str1')
    input2 = Input('world', 'str2')
    input3 = Input('!', 'str3')
    merged = concatenate([input1, input2, input3])
    print merged.to_string()

if __name__ == '__main__':
    main()


