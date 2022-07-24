import json
import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger("haiku_logger")


def get_track_str(filepath: Path = None) -> str:
    """track tweets that contain any of these words"""
    filepath = filepath or Path("data") / "track.txt"
    if filepath.exists():
        logger.info(f"Reading track list: {filepath}")
        with open(filepath, "r") as fp:
            track_str = ",".join(fp.read().splitlines())
    else:
        logger.info(f"No track list found at: {filepath}")
        track_str = ""
    return track_str


def get_ignore_tweet_list(filepath: Path = None) -> List:
    """filter out likely oppressive/offensive tweets using this word list"""
    filepath = filepath or Path("data") / "ignore_tweet.txt"
    if filepath.exists():
        logger.info(f"Reading ignore tweet list: {filepath}")
        with open(filepath, "r") as fp:
            ignore_tweet_list = fp.read().splitlines()
        # ensure lowercase
        ignore_tweet_list = list(set(x.lower() for x in ignore_tweet_list))
    else:
        logger.info(f"No ignore list found at: {filepath}")
        ignore_tweet_list = []

    return ignore_tweet_list


def get_ignore_profile_list(filepath: Path = None) -> List:
    """filter out tweets based on contents of user profile"""
    filepath = filepath or Path("data") / "ignore_profile.txt"
    if filepath.exists():
        logger.info(f"Reading ignore profile list: {filepath}")
        with open(filepath, "r") as fp:
            ignore_profile_list = fp.read().splitlines()
        # ensure lowercase
        ignore_profile_list = list(set(x.lower() for x in ignore_profile_list))
    else:
        logger.info(f"No ignore list found at: {filepath}")
        ignore_profile_list = []

    return ignore_profile_list


def get_syllable_dict(filepath: Path = None) -> Dict:
    """specify syllables for certain acronyms or abbreviations"""
    filepath = filepath or Path("data") / "syllables.json"
    if filepath.exists():
        logger.info(f"Reading syllable list: {filepath}")
        with open(filepath, "r") as fp:
            syllable_dict = json.loads(fp.read())
        # ensure lowercase
        syllable_dict = {k.lower(): v for k, v in syllable_dict.items()}
    else:
        logger.info(f"No syllable list found at: {filepath}")
        syllable_dict = {}
    return syllable_dict


def get_emoticons_list(filepath: Path = None) -> List:
    """text emoticons do not contribute to the syllable count"""
    filepath = filepath or Path("data") / "emoticons.txt"
    if filepath.exists():
        logger.info(f"Reading emoticon list: {filepath}")
        with open(filepath, "r") as fp:
            emoticons_list = fp.read().splitlines()
        emoticons_list = list(set(emoticons_list))
    else:
        logger.info(f"No emoticon list found at: {filepath}")
        emoticons_list = []
    return emoticons_list
