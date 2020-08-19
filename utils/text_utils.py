from datetime import datetime
import logging
import pytz
import re
from typing import List

from unidecode import unidecode
from ftfy import fix_text

logger = logging.getLogger("haikulogger")

# Regex to look for All URLs https://gist.github.com/gruber/249502
url_all_re = re.compile(r'(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’]))')
# Web only version: https://gist.github.com/gruber/8891611


def clean_text(text: str) -> str:
    '''Process text so it's ready for syllable counting

    If this doesn't properly handle emojis, try https://stackoverflow.com/a/49930688/2592858
    '''
    # fix wonky characters, but keep emojis
    # split on whitespace and rejoin; removes multiple spaces and newlines
    return ' '.join([''.join([unidecode(letter) if (str(letter.encode('unicode-escape'))[2] != '\\')
                    else letter for letter in word]) for word in fix_text(text).split()])


def check_text_wrapper(text: str, ignore_list: List[str]) -> bool:
    return all([
        (not text_contains_url(text)),
        (not text_contains_ignore_list(text, ignore_list)),
        (not text_has_chars_digits_together(text)),
        (not text_is_all_uppercase(text)),
        # (text_is_all_alpha(text)),
    ])


def check_tweet(status, ignore_list: List[str], language: str = 'en') -> bool:
    '''Return True if tweet satisfies specific criteria
    '''
    return all([
        check_text_wrapper(status['text'], ignore_list),
        (status['lang'] == language),
        (not status['entities']['hashtags']),
        (not status['entities']['urls']),
        (not status['entities']['user_mentions']),
        (not status['entities']['symbols']),
        (not status['truncated']),
        (not status['is_quote_status']),
        (not status['in_reply_to_status_id_str']),
        (not status['retweeted']),
        (status['user']['friends_count'] > 10),  # following
        (status['user']['followers_count'] > 100),  # followers
        # (status['user']['verified']),
        # ('media' not in status['entities']),
        (len(status['text']) >= 17),
    ])


def date_string_to_datetime(
    date_string: str,
    fmt: str = '%a %b %d %H:%M:%S +0000 %Y',
    tzinfo=pytz.UTC,
) -> datetime:
    return datetime.strptime(date_string, fmt).replace(tzinfo=tzinfo)


def remove_repeat_last_letter(text: str) -> str:
    '''Turn a string that has a repeated last letter into
    the same string with only one instance of that letter.
    wtfffff = wtf. lmaoooo = lmao. stuff = stuf.
    '''
    if text:
        return re.sub(rf'({text[-1]})\1+$', r'\1', text)
    else:
        return ''


def text_might_contain_acronym(text: str) -> bool:
    '''True if text satisfies acronym criteria. One option for all caps, one for lowercase.'''
    return ((len(text) <= 5 and re.findall(r'\b[A-Z\.]{2,}s?\b', text)) or
            (len(text) <= 3 and re.findall(r'\b[a-z\.]{2,}s?\b', text)))


def text_contains_url(text: str) -> bool:
    '''True if text contains a URL'''
    return len(url_all_re.findall(text)) > 0


def text_contains_ignore_list(text: str, ignore_list: List[str]) -> bool:
    '''Return True if anything from the ignore list is in the text.
    Each ignore list line is considered separately (OR logic).
    All tokens from one ignore list line must be somewhere in the text (AND logic).
    Each token in the ignore list line is also augmented to consider some basic plural forms,
    e.g., if ignore_list line is 'god dog', will match 'dogs are gods' but not 'doggies are godly'.
    '''
    # found all of the subtokens from one ignore line in the status
    return any(
        [
            all(
                [
                    any([it in text.lower().split() for it in [itok, f'{itok}s', f'{itok}z', f'{itok}es']]) for itok in ignore_line.split()
                ]
            ) for ignore_line in ignore_list
        ]
    )


def text_has_chars_digits_together(text: str) -> bool:
    '''It's not easy to count syllables for a token that contains letters and digits (h3llo).
    Return True if we find one of those.
    '''
    # keep only letters and spaces
    text_split = re.sub(r'[^\w\s]', '', text).split()
    # count number of tokens that are solely digits
    num_nums = sum(sum(char.isdigit() for char in token) == len(token) for token in text_split)
    # count number of tokens that are solely letters
    num_words = sum(sum(char.isalpha() for char in token) == len(token) for token in text_split)
    # are the counts above different from the length of tokens?
    return num_nums + num_words != len(text_split)


def text_is_all_uppercase(text: str) -> bool:
    '''Return True if every character is uppercase.
    Excludes punctuation, spaces, and digits.
    '''
    return all([char.isupper() for char in re.sub(r'[^A-Za-z]', '', text)])


# def split_acronym(token: str) -> List[str]:
#     '''Split short acronyms. One option for all caps, one for lowercase.
#     Otherwise return the token.
#     '''
#     token_clean = re.sub(r"[^\w']", ' ', token).strip()
#     if text_might_contain_acronym(token_clean):
#         return ' '.join(token).split()
#     else:
#         return [token]


# def all_tokens_are_real(text: str, pronounce_dict: Dict, syllable_dict: Dict) -> bool:
#     '''Return True if all tokens are real words (in pronunciation dictionary or
#     in syllable dictionary)
#     '''
#     # Keep characters and apostrphes
#     return all(
#         (re.sub(r"[^\w']", '', token) and
#             ((re.sub(r"[^\w']", '', token).lower() in pronounce_dict) or
#                 (re.sub(r"[^\w']", '', token).lower() in syllable_dict) or
#                 (remove_repeat_last_letter(re.sub(r"[^\w']", '', token).lower()) in pronounce_dict) or
#                 (remove_repeat_last_letter(re.sub(r"[^\w']", '', token).lower()) in syllable_dict))
#          ) for token in text.split()
#     )


# def text_is_all_alpha(text: str) -> bool:
#     '''Return True if every character is a letter.
#     Excludes punctuation and spaces.
#     '''
#     return all([char.isalpha() for char in re.sub(r'[^\w]', '', text)])
