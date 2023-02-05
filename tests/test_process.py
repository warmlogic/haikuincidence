from haikuincidence.utils.text_utils import clean_text


def test_text_process():
    with open("tests/data_process.txt") as fp:
        inputs = fp.read().splitlines()

    for text in inputs:
        original, expected = text.split(",")
        text_cleaned = clean_text(original)
        assert text_cleaned == expected, f"{original} did not turn into {expected}"
