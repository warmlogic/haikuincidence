import inflect
from nltk.corpus import cmudict

from haikuincidence.utils.data_utils import (
    get_emoticons_list,
    get_ignore_tweet_list,
    get_syllable_dict,
    get_track_str,
)
from haikuincidence.utils.haiku_utils import count_syllables, get_haiku
from haikuincidence.utils.text_utils import check_text_wrapper, clean_text

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


def test_haikus():
    with open("tests/data_haiku.txt", "r") as fp:
        haikus = fp.read().splitlines()

    for text in haikus:
        text = clean_text(text)

        count = count_syllables(
            text,
            inflect_p,
            pronounce_dict,
            syllable_dict,
            emoticons_list,
            guess_syl_method,
        )
        assert count == 17, f"Not 17 syllables: {text}"

        haiku = get_haiku(
            text, inflect_p, pronounce_dict, syllable_dict, emoticons_list, guess_syl_method
        )
        assert haiku != "", f"Not a haiku: {text}"
