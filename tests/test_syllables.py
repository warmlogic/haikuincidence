from pathlib import Path

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
data_dir = Path.cwd() / "data"
track_str = get_track_str(data_dir / "track.txt")
ignore_tweet_list = get_ignore_tweet_list(data_dir / "ignore_tweet.txt")
syllable_dict = get_syllable_dict(data_dir / "syllables.json")
emoticons_list = get_emoticons_list(data_dir / "emoticons.txt")


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
