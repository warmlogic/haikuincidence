import json
from pathlib import Path
import requests
from typing import List, Dict
import logging

logger = logging.getLogger("haikulogger")


def get_track_str(filepath: Path = None) -> str:
    '''track tweets that contain any of these words
    '''
    filepath = filepath or Path(__file__).parent.parent / 'data' / 'track.txt'
    if filepath.exists():
        logger.info(f'Reading track list: {filepath}')
        with open(filepath, 'r') as fp:
            track_str = ','.join(fp.read().splitlines())
    else:
        logger.info(f'No track list found at: {filepath}')
        track_str = ''
    return track_str


def get_ignore_list(filepath: Path = None) -> List:
    '''filter out likely oppressive/offensive tweets using this word list
    '''
    filepath = filepath or Path(__file__).parent.parent / 'data' / 'ignore.txt'
    if filepath.exists():
        logger.info(f'Reading ignore list: {filepath}')
        with open(filepath, 'r') as fp:
            ignore_list = fp.read().splitlines()
        # ensure lowercase
        ignore_list = list(set(x.lower() for x in ignore_list))
    else:
        logger.info(f'No ignore list found at: {filepath}')
        ignore_list = []

    return ignore_list


def get_syllable_dict(filepath: Path = None) -> Dict:
    '''specify syllables for certain acronyms or abbreviations
    '''
    filepath = filepath or Path(__file__).parent.parent / 'data' / 'syllables.json'
    if filepath.exists():
        logger.info(f'Reading syllable list: {filepath}')
        with open(filepath, 'r') as fp:
            syllable_dict = json.loads(fp.read())
        # ensure lowercase
        syllable_dict = {k.lower(): v for k, v in syllable_dict.items()}
    else:
        logger.info(f'No syllable list found at: {filepath}')
        syllable_dict = {}
    return syllable_dict


def get_emoticons_list(filepath: Path = None) -> List:
    '''text emoticons do not contribute to the syllable count
    '''
    filepath = filepath or Path(__file__).parent.parent / 'data' / 'emoticons.txt'
    if filepath.exists():
        logger.info(f'Reading emoticon list: {filepath}')
        with open(filepath, 'r') as fp:
            emoticons_list = fp.read().splitlines()
        emoticons_list = list(set(emoticons_list))
    else:
        logger.info(f'No emoticon list found at: {filepath}')
        emoticons_list = []
    return emoticons_list
