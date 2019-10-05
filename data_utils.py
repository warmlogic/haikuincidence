import json
from pathlib import Path
import requests
from typing import List, Dict
import logging

logging.basicConfig(format='{asctime} : {levelname} : {message}', level=logging.INFO, style='{')
logger = logging.getLogger(__name__)


def get_track_str(filepath: Path=None) -> str:
    '''track tweets that contain any of these words
    '''
    filepath = filepath or Path('data') / 'track.txt'
    if filepath.exists():
        with open(filepath, 'r') as fp:
            track_str = ','.join(fp.read().splitlines())
    else:
        track_str = ''
    return track_str


def get_ignore_list(filepath: Path=None, use_external: bool=True) -> List:
    '''ignore tweets that contain any of these words
    '''
    filepath = filepath or Path('data') / 'ignore.txt'
    if filepath.exists():
        with open(filepath, 'r') as fp:
            ignore_list = fp.read().splitlines()
        # ensure lowercase
        ignore_list = list(set(x.lower() for x in ignore_list))
    else:
        ignore_list = []

    # filter out likely oppressive/offensive tweets using this word list
    if use_external:
        bad_words_url = 'https://raw.githubusercontent.com/dariusk/wordfilter/master/lib/badwords.json'
        logger.info(f'Reading external ignore list: {bad_words_url}')
        response = requests.get(bad_words_url)
        if response.status_code == 200:
            ignore_list = list(set(x.lower() for x in response.json() + ignore_list))

    return ignore_list


def get_syllable_dict(filepath: Path=None) -> Dict:
    '''specify syllables for certain acronyms or abbreviations
    '''
    filepath = filepath or Path('data') / 'syllables.json'
    if filepath.exists():
        with open(filepath, 'r') as fp:
            syllable_dict = json.loads(fp.read())
        # ensure lowercase
        syllable_dict = {k.lower(): v for k, v in syllable_dict.items()}
    else:
        syllable_dict = {}
    return syllable_dict


def get_emoticons_list(filepath: Path=None) -> List:
    '''text emoticons do not contribute to the syllable count
    '''
    filepath = filepath or Path('data') / 'emoticons.txt'
    if filepath.exists():
        with open(filepath, 'r') as fp:
            emoticons_list = fp.read().splitlines()
        emoticons_list = list(set(emoticons_list))
    else:
        emoticons_list = []
    return emoticons_list
