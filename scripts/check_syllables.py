"""
Run as a module from the top-level folder like:
poetry run python -m scripts.check_syllables --text "my text here"

Some difficult words:

Currently correct:
restopped
insanely
DJ's
sourdough

Currently incorrect:
guidestone
oneworld
preheadache
hehehehe
wordle
"""

import argparse
import logging
from pathlib import Path

import inflect
from nltk.corpus import cmudict

from haikuincidence.utils.data_utils import (
    get_emoticons_list,
    get_ignore_tweet_list,
    get_syllable_dict,
    get_track_str,
)
from haikuincidence.utils.haiku_utils import get_haiku
from haikuincidence.utils.text_utils import check_text_wrapper, clean_text

logging.basicConfig(format="{asctime} : {levelname} : {message}", style="{")
logger = logging.getLogger("haiku_logger")
logger.setLevel(logging.DEBUG)

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process text and count syllables.")
    parser.add_argument(
        "-t", "--text", type=str, nargs="?", help="String to process, in quotes"
    )
    args = parser.parse_args()

    original_text = args.text
    status = dict(text=original_text, id_str="0")

    logger.debug(f"Original text:\n{original_text}")

    cleaned_text = clean_text(original_text)
    logger.debug(f"Cleaned text:\n{cleaned_text}")

    logger.debug(
        f"Passes check_text_wrapper: {check_text_wrapper(status, ignore_tweet_list)}"
    )

    haiku = get_haiku(
        cleaned_text,
        inflect_p,
        pronounce_dict,
        syllable_dict,
        emoticons_list,
        guess_syl_method,
    )

    logger.debug(f"Resulting haiku:\n{haiku}")
