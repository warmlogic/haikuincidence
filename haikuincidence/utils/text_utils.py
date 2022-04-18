import logging
import re
import unicodedata
from datetime import datetime
from typing import List

import emoji
import pytz
from ftfy import fix_text
from unidecode import unidecode

logger = logging.getLogger("haikulogger")

# Regex to look for all URLs (mailto:, x-whatever://, etc.)
# https://gist.github.com/gruber/249502
# Removed case insensitive flag from the start: (?i)
url_all_re = (
    r"\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)"
    + r"(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|"
    + r"(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
)
url_all_re_cmp = re.compile(url_all_re, flags=re.IGNORECASE)

# Web only version: https://gist.github.com/gruber/8891611

# Letters that can be pronounced as a single syllable when repeated (aaaaaaa)
PRONOUNCED_LETTERS = [
    "a",
    "e",
    "f",
    "h",
    "i",
    "l",
    "m",
    "n",
    "o",
    "r",
    "s",
    "u",
    "v",
    "w",
    "y",
    "z",
]

UNICODE_IGNORE = [
    "\\u3164",  # Hangul Filler
]


def clean_text(text: str) -> str:
    """Process text so it's ready for syllable counting"""
    # change some characters that are difficult to count syllables for, but keep emojis
    # split on whitespace and rejoin; removes multiple spaces and newlines
    if text is None:
        return text

    # Remove some unicode letters
    text_cleaned = " ".join(
        [
            "".join(
                [
                    letter
                    for letter in word
                    if letter.encode("unicode-escape").decode() not in UNICODE_IGNORE
                ]
            )
            for word in fix_text(text).split()
        ]
    )

    # Decode unicode letters and keep emojis
    text_cleaned = " ".join(
        [
            "".join(
                [
                    unidecode(letter) if not emoji.is_emoji(letter) else letter
                    for letter in word
                ]
            )
            for word in text_cleaned.split()
        ]
    )

    return text_cleaned


def check_profile(
    status, ignore_profile_list: List[str], match_substring: bool = False
) -> bool:
    return all(
        [
            (
                not text_contains_ignore_list(
                    clean_token(clean_text(status["user"]["description"])),
                    ignore_profile_list,
                    match_substring=match_substring,
                )
            ),
        ]
    )


def check_text_wrapper(text: str, ignore_list: List[str]) -> bool:
    return all(
        [
            (not text_contains_url(text)),
            (
                not text_contains_ignore_list_plural(
                    clean_token(clean_text(text)), ignore_list
                )
            ),
            (not text_has_chars_digits_together(text)),
            (not text_is_all_uppercase(text)),
            # (text_is_all_alpha(text)),
        ]
    )


def get_tweet_body(status):
    if "extended_tweet" in status:
        tweet_body = status["extended_tweet"]["full_text"]
    elif "text" in status:
        tweet_body = status["text"]
    else:
        tweet_body = ""
    return tweet_body


def check_tweet(
    status,
    ignore_tweet_list: List[str],
    language: str = "en",
    ignore_user_screen_names: List[str] = [],
    ignore_user_id_str: List[str] = [],
) -> bool:
    """Return True if tweet satisfies specific criteria"""
    tweet_body = get_tweet_body(status)

    if not tweet_body:
        return False

    return all(
        [
            check_text_wrapper(tweet_body, ignore_list=ignore_tweet_list),
            (status["lang"] == language),
            (not status["entities"]["hashtags"]),
            (not status["entities"]["urls"]),
            (not status["entities"]["user_mentions"]),
            (not status["entities"]["symbols"]),
            (not status["truncated"]),
            (not status["is_quote_status"]),
            (not status["in_reply_to_status_id_str"]),
            (not status["retweeted"]),
            (status["user"]["screen_name"] not in ignore_user_screen_names),
            (status["user"]["id_str"] not in ignore_user_id_str),
            (status["user"]["friends_count"] > 10),  # following
            (status["user"]["followers_count"] > 100),  # followers
            # (status['user']['verified']),
            # ('media' not in status['entities']),
            (len(tweet_body) >= 17),
        ]
    )


def date_string_to_datetime(
    date_string: str,
    fmt: str = "%a %b %d %H:%M:%S +0000 %Y",
    tzinfo=pytz.UTC,
) -> datetime:
    return datetime.strptime(date_string, fmt).replace(tzinfo=tzinfo)


def remove_repeat_last_letter(text: str) -> str:
    """Turn a string that has a repeated last letter into
    the same string with only one instance of that letter.
    wtfffff = wtf. lmaoooo = lmao. stuff = stuf.
    If the entire text is the same letter and not one that can be pronounced,
    keep the letters.
    """
    if (text is None) or (not text):
        return text

    # If it's a single letter that can be pronounced, return the full token
    # Set intersection is the letter if it's in the special list, else empty
    if (len(set(text)) <= 1) and (set(text) & set(PRONOUNCED_LETTERS)):
        return text

    return re.sub(rf"({text[-1]})\1+$", r"\1", text)


def text_might_contain_acronym(text: str) -> bool:
    """True if text satisfies acronym criteria.
    One option for all caps, one for lowercase.
    """

    # If it's a single letter that can be pronounced, don't try to make it an acronym
    # Set intersection is the letter if it's in the special list, else empty
    if (len(set(text)) <= 1) and (set(text) & set(PRONOUNCED_LETTERS)):
        return False

    return (len(text) <= 5 and re.findall(r"\b[A-Z\.]{2,}s?\b", text)) or (
        len(text) <= 3 and re.findall(r"\b[a-z\.]{2,}s?\b", text)
    )


def text_contains_url(text: str) -> bool:
    """True if text contains a URL"""
    return len(url_all_re_cmp.findall(text)) > 0


def text_contains_ignore_list_plural(
    text: str, ignore_list: List[str], match_substring: bool = False
) -> bool:
    """Return True if anything from the ignore list is in the text.

    Each ignore list line is considered separately (OR logic).

    All tokens from one ignore list line must be somewhere in the text (AND logic).

    Each token in the ignore list line is also augmented to consider some basic plural
    forms, e.g., if ignore_list line is 'god dog', will match 'dogs are gods' but not
    'doggies are godly'.
    """
    # found all of the subtokens from one ignore line in the text
    if text is None:
        return text

    if match_substring:
        text_compare = text.lower()
    else:
        text_compare = text.lower().split()

    return any(
        [
            all(
                [
                    any(
                        [
                            it in text_compare
                            for it in [itok, f"{itok}s", f"{itok}z", f"{itok}es"]
                        ]
                    )
                    for itok in ignore_line.split()
                ]
            )
            for ignore_line in ignore_list
        ]
    )


def text_contains_ignore_list(
    text: str, ignore_list: List[str], match_substring: bool = False
) -> bool:
    """Return True if anything from the ignore list is in the text.
    Each ignore list line is considered separately (OR logic).
    All tokens from one ignore list line must be somewhere in the text (AND logic).
    """
    # found all of the subtokens from one ignore line in the text
    if text is None:
        return text

    if match_substring:
        text_compare = text.lower()
    else:
        text_compare = text.lower().split()

    return any(
        [
            all([itok in text_compare for itok in ignore_line.lower().split()])
            for ignore_line in ignore_list
        ]
    )


def text_has_chars_digits_together(text: str) -> bool:
    """It's not easy to count syllables for a token that contains letters and digits
    (h3llo). Return True if we find one of those.
    """
    # keep only letters and spaces
    text_split = re.sub(r"[^\w\s]", "", text).split()
    # count number of tokens that are solely digits
    num_nums = sum(
        sum(char.isdigit() for char in token) == len(token) for token in text_split
    )
    # count number of tokens that are solely letters
    num_words = sum(
        sum(char.isalpha() for char in token) == len(token) for token in text_split
    )
    # are the counts above different from the length of tokens?
    return num_nums + num_words != len(text_split)


def text_is_all_uppercase(text: str) -> bool:
    """Return True if every character is uppercase.
    Excludes punctuation, spaces, and digits.
    """
    return all([char.isupper() for char in re.sub(r"[^A-Za-z]", "", text)])


def clean_token(token: str, unicode_normalize_form: str = "NFKC") -> str:
    if token is None:
        return token

    # Normalize unicode letters
    # NFKD: decomposes, NFKC: composes pre-combined characters again
    token = unicodedata.normalize(unicode_normalize_form, token)

    # # remove space before some punctuation if preceded by a letter or number
    # # ("hello ,how are you ? doing")
    # token = re.sub(r"(\w)\s([.,;!?](?=\s|$)?)", r"\1\2", token)

    # put space after some punctuation if followed by a letter or number ("cat,dog")
    token = re.sub(r"(?<=[;!?])(?=[\w])", r" ", token)

    # put space after period if followed by a letter ("good.What")
    token = re.sub(r"(?<=[.,])(?=[A-Za-z])", r" ", token)

    # remove spaces around apostrophe if letter-space-apostrophe-space-letter
    token = re.sub(r"(\w)\s(['])[?=\s\w]", r"\1\2", token)

    # add space around some punctuation if letters on both sides
    token = re.sub(r"([\w])([#@&%=+/×\-](?=[\w]))", r"\1 \2 ", token)

    # try to replace an asterisk (representing a missing vowel) with "u"
    token = re.sub(r"([\w])[\*]((?=[\w]))", r"\1u\2", token)

    # put a space after some punctuation that precedes a letter
    token = re.sub(r"([#@&=+/×])((?=[\w]))", r"\1 \2", token)

    # put a space before some punctuation that follows a letter
    token = re.sub(r"([\w])([#@&%=+/×])", r"\1 \2", token)

    # special cases
    token = re.sub(r"\bb / c\b", "because", token, flags=re.IGNORECASE)
    token = re.sub(r"\bb / t\b", "between", token, flags=re.IGNORECASE)
    token = re.sub(r"\bw / o\b", "without", token, flags=re.IGNORECASE)
    token = re.sub(r"\bw /\s\b", "with ", token, flags=re.IGNORECASE)
    token = re.sub(r"\bw /\b", "with", token, flags=re.IGNORECASE)
    token = re.sub(r"\ba\b\*", "a star", token, flags=re.IGNORECASE)

    # replace some punctuation with words
    token = token.replace("@", "at")
    token = token.replace("#", "number")
    token = token.replace("&", "and")
    token = token.replace("%", "percent")
    token = token.replace("=", "equals")
    token = token.replace("×", "times")
    token = token.replace("+", "plus")
    # token = token.replace('*', 'star')
    # token = token.replace('/', 'slash')

    # keep the following punctuation: letters, apostrophes, commas, periods
    token_clean = re.sub(r"[^\w',\.]", " ", token).strip()

    return token_clean


# def split_acronym(token: str) -> List[str]:
#     """Split short acronyms. One option for all caps, one for lowercase.
#     Otherwise return the token.
#     """
#     token_clean = re.sub(r"[^\w']", " ", token).strip()
#     if text_might_contain_acronym(token_clean):
#         return " ".join(token).split()
#     else:
#         return [token]


# def all_tokens_are_real(text: str, pronounce_dict: Dict, syllable_dict: Dict) -> bool:
#     """Return True if all tokens are real words (in pronunciation dictionary or
#     in syllable dictionary)
#     """
#     # Keep characters and apostrophes
#     return all(
#         (
#             re.sub(r"[^\w']", "", token)
#             and (
#                 (re.sub(r"[^\w']", "", token).lower() in pronounce_dict)
#                 or (re.sub(r"[^\w']", "", token).lower() in syllable_dict)
#                 or (
#                     remove_repeat_last_letter(re.sub(r"[^\w']", "", token).lower())
#                     in pronounce_dict
#                 )
#                 or (
#                     remove_repeat_last_letter(re.sub(r"[^\w']", "", token).lower())
#                     in syllable_dict
#                 )
#             )
#         )
#         for token in text.split()
#     )


# def text_is_all_alpha(text: str) -> bool:
#     """Return True if every character is a letter.
#     Excludes punctuation and spaces.
#     """
#     return all([char.isalpha() for char in re.sub(r"[^\w]", "", text)])
