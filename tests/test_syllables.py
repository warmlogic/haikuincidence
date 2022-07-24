import inflect
from nltk.corpus import cmudict

from haikuincidence.utils.data_utils import (
    get_emoticons_list,
    get_ignore_tweet_list,
    get_syllable_dict,
    get_track_str,
)
from haikuincidence.utils.haiku_utils import count_syllables, get_haiku
from haikuincidence.utils.text_utils import clean_text

# get data to use for dealing with tweets
track_str = get_track_str()
ignore_tweet_list = get_ignore_tweet_list()
syllable_dict = get_syllable_dict()
emoticons_list = get_emoticons_list()

# Use inflect to change digits to their English word equivalent
inflect_p = inflect.engine()
# Use the CMU dictionary to count syllables
pronounce_dict = cmudict.dict()

# guess_syl_method = "min"
guess_syl_method = "mean"
# guess_syl_method = "max"


def get_syllable_count_and_haiku(text):
    count = count_syllables(
        text,
        inflect_p,
        pronounce_dict,
        syllable_dict,
        emoticons_list,
        guess_syl_method,
    )

    haiku = get_haiku(
        text, inflect_p, pronounce_dict, syllable_dict, emoticons_list, guess_syl_method
    )

    return count, haiku


def test_haikus():
    with open("tests/data_haiku.txt", "r") as fp:
        inputs = fp.read().splitlines()

    for text in inputs:
        text_cleaned = clean_text(text)
        count, haiku = get_syllable_count_and_haiku(text_cleaned)

        assert count == 17, f"{count} syllables, not 17 syllables: {text_cleaned}"
        assert haiku != "", f"Not a haiku: {text_cleaned}"


def test_not_haikus():
    with open("tests/data_not_haiku.txt", "r") as fp:
        inputs = fp.read().splitlines()

    for text in inputs:
        text_cleaned = clean_text(text)
        count, haiku = get_syllable_count_and_haiku(text_cleaned)

        print(text_cleaned)
        assert (
            haiku == ""
        ), f"Syllable count: {count}, not supposed to be a haiku: {text_cleaned}"


def test_text_processing():
    with open("tests/data_clean.txt", "r") as fp:
        inputs = fp.read().splitlines()

    for text in inputs:
        original, expected = text.split(",")
        text_cleaned = clean_text(original)
        assert text_cleaned == expected, f"{original} did not turn into {expected}"
