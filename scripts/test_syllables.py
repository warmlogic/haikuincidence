# Run from the scripts folder like: python test_syllables.py --text "my text here"

import argparse
import logging
import sys

import inflect
from nltk.corpus import cmudict

sys.path.append('..')

from utils.data_utils import get_ignore_list, get_syllable_dict, get_emoticons_list
from utils.text_utils import clean_text, check_text_wrapper
from utils.haiku_utils import get_haiku


logging.basicConfig(format='{asctime} : {levelname} : {message}', style='{')
logger = logging.getLogger("haikulogger")
logger.setLevel(logging.DEBUG)

# get data to use for dealing with tweets
ignore_list = get_ignore_list()
syllable_dict = get_syllable_dict()
emoticons_list = get_emoticons_list()

# Use inflect to change digits to their English word equivalent
inflect_p = inflect.engine()
# Use the CMU dictionary to count syllables
pronounce_dict = cmudict.dict()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process text and count syllables.')
    parser.add_argument('-t', '--text', type=str, nargs='?', help='String to process, in quotes')
    args = parser.parse_args()

    text = args.text

    logger.debug(f'Original text: {text}')

    text = clean_text(text)
    logger.debug(f'Cleaned text: {text}')

    logger.debug(f'Passes check_text_wrapper: {check_text_wrapper(text, ignore_list)}')

    haiku = get_haiku(text, inflect_p, pronounce_dict, syllable_dict, emoticons_list)

    logger.debug(f'Resulting haiku: {haiku}')
