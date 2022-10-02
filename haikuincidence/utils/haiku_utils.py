import logging
import math
import re

from .data_base import Haiku
from .text_utils import (
    clean_token,
    remove_repeat_last_letter,
    text_might_contain_acronym,
)

# import random


logger = logging.getLogger("haiku_logger")

# keep letters and apostrophes for contractions, and commas and periods for numbers
punct_to_keep = ["'", ",", "."]

# endings of contractions, for counting syllables
contraction_ends = ["d", "ll", "m", "re", "s", "t", "ve"]


def count_syllables(
    token: str,
    inflect_p,
    pronounce_dict: dict,
    syllable_dict: dict,
    emoticons_list: list,
    guess_syl_method: str,
) -> int:
    if token in emoticons_list:
        return 0

    # find whether the token is an exact match to a dictionary entry
    if token in syllable_dict:
        token_syl = syllable_dict[token]["syllables"]
        source = "Syllable dictionary"
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"    {source}: {token}: {token_syl}")
        return token_syl

    token_clean = clean_token(token)

    sub_syllable_count = 0
    for sub_token in token_clean.split():
        # remove starting or ending punctuation
        for punct in punct_to_keep:
            sub_token = sub_token.strip(punct)

        # keep capitalization for checking acronyms
        sub_token_orig = sub_token
        # lowercase for checking against syllable_dict and pronounce_dict
        sub_token = sub_token.lower()

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"    Sub-token: {sub_token}")

        if sub_token.replace(",", "").replace(".", "").isdigit():
            # split a string that looks like a year
            if len(sub_token) == 4:
                if sub_token.isdigit():
                    if (int(sub_token[:2]) % 10 == 0) and (int(sub_token[2:]) < 10):
                        sub_token = inflect_p.number_to_words(sub_token, andword="")
                    else:
                        sub_token = f"{sub_token[:2]} {sub_token[2:]}"
                else:
                    sub_token = inflect_p.number_to_words(sub_token, andword="")
            elif len(sub_token) == 2:
                if sub_token.isdigit():
                    # pronounce zero as "oh"
                    if sub_token[0] == "0":
                        sub_token = f"oh {sub_token[1]}"
                    else:
                        sub_token = inflect_p.number_to_words(sub_token, andword="")
                else:
                    sub_token = inflect_p.number_to_words(sub_token, andword="")
            else:
                sub_token = inflect_p.number_to_words(sub_token, andword="")
            # remove all punctuation except apostrophes
            sub_token = re.sub(r"[^\w']", " ", sub_token).strip()

        if sub_token in syllable_dict:
            sub_token_syl = syllable_dict[sub_token]["syllables"]
            source = "Syllable dictionary"
            sub_syllable_count += sub_token_syl
        elif remove_repeat_last_letter(sub_token) in syllable_dict:
            sub_token_syl = syllable_dict[remove_repeat_last_letter(sub_token)][
                "syllables"
            ]
            source = "Syllable dictionary (remove repeat last letter)"
            sub_syllable_count += sub_token_syl
        elif (sub_token_orig.endswith("s") or sub_token_orig.endswith("z")) and (
            sub_token[:-1] in syllable_dict
        ):
            sub_token_syl = syllable_dict[sub_token[:-1]]["syllables"]
            source = "Syllable dictionary (singular)"
            sub_syllable_count += sub_token_syl
        elif sub_token in pronounce_dict:
            sub_token_syl = max(
                [
                    len([y for y in x if y[-1].isdigit()])
                    for x in pronounce_dict[sub_token]
                ]
            )
            source = "CMU dictionary"
            sub_syllable_count += sub_token_syl
        elif remove_repeat_last_letter(sub_token) in pronounce_dict:
            sub_token_syl = max(
                [
                    len([y for y in x if y[-1].isdigit()])
                    for x in pronounce_dict[remove_repeat_last_letter(sub_token)]
                ]
            )
            source = "CMU dictionary (remove repeat last letter)"
            sub_syllable_count += sub_token_syl
        elif (sub_token_orig.endswith("s") or sub_token_orig.endswith("z")) and (
            sub_token[:-1] in pronounce_dict
        ):
            sub_token_syl = max(
                [
                    len([y for y in x if y[-1].isdigit()])
                    for x in pronounce_dict[sub_token[:-1]]
                ]
            )
            source = "CMU dictionary (singular)"
            sub_syllable_count += sub_token_syl
        else:
            # it's not a "real" word
            if re.findall(r"[^\w']", sub_token):
                # there are non-letter characters remaining (shouldn't be possible);
                # run it through again
                sub_token_syl = count_syllables(
                    sub_token,
                    inflect_p,
                    pronounce_dict,
                    syllable_dict,
                    emoticons_list,
                    guess_syl_method,
                )
                source = "Non-letter characters"
                sub_syllable_count += sub_token_syl
            else:
                if "'" in sub_token:
                    # contains an apostrophe
                    if sub_token.rsplit("'")[-1] in contraction_ends:
                        # ends with one of the contraction endings; make a guess
                        sub_token_syl = guess_syllables(sub_token, guess_syl_method)
                        source = "Syllable guess"
                        sub_syllable_count += sub_token_syl
                    else:
                        # doesn't end with a contraction ending;
                        # count each chunk between apostrophes
                        for sub_sub_token in sub_token.rsplit("'"):
                            sub_token_syl = count_syllables(
                                sub_sub_token,
                                inflect_p,
                                pronounce_dict,
                                syllable_dict,
                                emoticons_list,
                                guess_syl_method,
                            )
                            source = "Multiple apostrophes"
                            sub_syllable_count += sub_token_syl
                else:
                    # no apostrophes; might be an acronym,
                    # split the letters apart and run it through again
                    if text_might_contain_acronym(sub_token_orig):
                        sub_token_syl = count_syllables(
                            " ".join(sub_token),
                            inflect_p,
                            pronounce_dict,
                            syllable_dict,
                            emoticons_list,
                            guess_syl_method,
                        )
                        source = "Acronym"
                        sub_syllable_count += sub_token_syl
                    else:
                        # make a guess
                        sub_token_syl = guess_syllables(
                            remove_repeat_last_letter(sub_token), guess_syl_method
                        )
                        source = "Syllable guess"
                        sub_syllable_count += sub_token_syl
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"    {source}: {sub_token}: {sub_token_syl}")

    return sub_syllable_count


def guess_syllables(word: str, method: str = None, mean_round_dir: str = None) -> int:
    """Guess the number of syllables in a string.
    Returned value depends on the method used. Mean is usually good enough.

    A diphthong is two vowel sounds in a single syllable (e.g., pie, boy, cow)
    """

    def avg_syl(minsyl: int, maxsyl: int, mean_round_dir: str):
        if mean_round_dir == "up":
            syl = math.ceil((minsyl + maxsyl) / 2)
        elif mean_round_dir == "down":
            syl = (minsyl + maxsyl) // 2
        return syl

    def get_syl_count_str(minsyl: int, maxsyl: int, mean_round_dir: str):
        return (
            f"min syl {minsyl},"
            f" mean syl {avg_syl(minsyl, maxsyl, mean_round_dir)},"
            f" max syl {maxsyl}"
        )

    vowels = ["a", "e", "i", "o", "u"]

    method = method or "mean"
    mean_round_dir = mean_round_dir or "down"

    assert method in ["min", "max", "mean"]
    if method == "mean":
        assert mean_round_dir in ["down", "up"]

    logger.debug(f"Guessing syllable count with method: {method}")
    if method == "mean":
        logger.debug(f"    Rounding direction: {mean_round_dir}")

    on_vowel = False
    in_diphthong = False
    minsyl = 0
    maxsyl = 0
    last_char = None

    word = word.lower()
    for i, c in enumerate(word):
        is_vowel = c in vowels

        # y is a special case:
        # serves as a vowel when the previous character was not a vowel,
        # serves as a consonant when the previous character was a vowel
        if c == "y":
            is_vowel = not on_vowel

        if is_vowel:
            logger.debug(f"vowel: {c}")
            if not on_vowel:
                # We weren't on a vowel before.
                # Seeing a new vowel bumps the syllable count.
                minsyl += 1
                maxsyl += 1
                logger.debug(
                    "    new syllable:"
                    f" {get_syl_count_str(minsyl, maxsyl, mean_round_dir)}"
                )
            elif on_vowel and not in_diphthong and c != last_char:
                # We were already in a vowel.
                # Don't increment anything except the max count,
                # and only do that once per diphthong.
                in_diphthong = True
                maxsyl += 1
                logger.debug(
                    "    diphthong:"
                    f" {c}: {get_syl_count_str(minsyl, maxsyl, mean_round_dir)}"
                )
        else:
            in_diphthong = False
            if re.findall(r"[\w]", c):
                logger.debug(f"consonant: {c}")
            else:
                logger.debug(f"other: {c}")

        if i + 1 == len(word):
            break

        on_vowel = is_vowel
        last_char = c

    # May have counted too many syllables: If word ends in e, or past tense (-ed),
    # run some checks.
    if (
        (len(word) >= 3)
        and ((word[-1] == "e") or (word[-2:] == "ed"))
        and (word[-2:] not in ["be", "ie", "ee"])
        and (word[-3] not in ["d", "t"])
    ):
        minsyl -= 1
        # maxsyl -= 1
        logger.debug(
            f"Ends in e or ed (with conditions), removing a syllable for '{word}':"
            f" {get_syl_count_str(minsyl, maxsyl, mean_round_dir)}"
        )

    if (len(word) >= 3) and (word[-2:] == "le") and (word[-3] not in vowels + ["l"]):
        minsyl += 1
        maxsyl += 1
        logger.debug(
            f"Adding back a syllable for '{word}':"
            f" {get_syl_count_str(minsyl, maxsyl, mean_round_dir)}"
        )

    # Possessive with word ending in certain sounds may not get enough syllables
    if (len(word) >= 3) and (word[-2:] == "'s") and (word[-3] in ["x"]):
        minsyl += 1
        maxsyl += 1
        logger.debug(
            f"Possessive: Adding a syllable for '{word}':"
            f" {get_syl_count_str(minsyl, maxsyl, mean_round_dir)}"
        )

    # check on ending with a consonant followed by y
    if (len(word) >= 3) and (word[-2] not in vowels) and (word[-1] == "y"):
        if word[-3] == "e":
            minsyl -= 1
            logger.debug(
                f"Ends with e + consonant + y: Removing a syllable for '{word}':"
                f" {get_syl_count_str(minsyl, maxsyl, mean_round_dir)}"
            )
        else:
            maxsyl += 1
            logger.debug(
                f"Ends with consonant + y: Adding a syllable for '{word}':"
                f" {get_syl_count_str(minsyl, maxsyl, mean_round_dir)}"
            )

    # other special cases
    if word.endswith("phobia") or word.endswith("bio"):
        maxsyl += 1

    # if found no syllables but there's at least one letter,
    # count as one syllable
    if re.findall(r"[\w]", word):
        if not minsyl:
            minsyl = 1
        if not maxsyl:
            maxsyl = 1

    if method == "min":
        syl = minsyl
    elif method == "mean":
        syl = avg_syl(minsyl, maxsyl, mean_round_dir)
    elif method == "max":
        syl = maxsyl

    return syl


def get_haiku(
    text: str,
    inflect_p,
    pronounce_dict: dict,
    syllable_dict: dict,
    emoticons_list: list,
    guess_syl_method: str,
) -> str:
    """Attempt to turn a string into a haiku.
    Returns haiku if able, otherwise returns empty string.

    Inspired by https://github.com/tomwardill/python-haiku/blob/master/haiku_checker.py
    """
    haiku_form = [5, 12, 17]
    haiku = [[] for _ in range(len(haiku_form))]
    syllable_count = 0
    haiku_line = 0
    haiku_line_prev = 0

    text_split = text.split()
    # Add tokens to create potential haiku
    for i, token in enumerate(text_split):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Original token: {token}")
        # Add tokens with no syllables (punctuation, emoji)) to the end of the
        # previous line instead of the start of the current line
        if re.findall(r"[^\w']", token) and (
            count_syllables(
                token,
                inflect_p,
                pronounce_dict,
                syllable_dict,
                emoticons_list,
                guess_syl_method,
            )
            == 0
        ):
            if haiku_line_prev == haiku_line:
                haiku[haiku_line].append(token)
            else:
                haiku[haiku_line - 1].append(token)
            continue
        else:
            # Add token to this line of the potential haiku
            haiku[haiku_line].append(token)
            # note what line was being worked on for this token
            haiku_line_prev = haiku_line

        # Count number of syllables for this token
        syllable_count += count_syllables(
            token,
            inflect_p,
            pronounce_dict,
            syllable_dict,
            emoticons_list,
            guess_syl_method,
        )
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"{syllable_count} syllables counted total")

        if syllable_count == haiku_form[haiku_line]:
            # Reached exactly the number of syllables for this line, go to next line
            haiku_line += 1
        if (
            i < len(text_split) - 1
            and haiku_line >= len(haiku_form)
            and (
                count_syllables(
                    " ".join(text_split[i + 1 :]),
                    inflect_p,
                    pronounce_dict,
                    syllable_dict,
                    emoticons_list,
                    guess_syl_method,
                )
                > 0
            )
        ):
            # There are syllables in the remaining tokens to check,
            # but have reached the number of lines in a haiku.
            # Therefore not a haiku coincidence!
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "Not a haiku because are more lines to check:"
                    f" {' '.join(text_split[i + 1:])}"
                )
            return ""
    if haiku_line == len(haiku_form):
        # Reached the end, and found the right number of lines. Haiku coincidence!
        return ["\n".join([" ".join(line) for line in haiku])][0]
    else:
        # Did not find the right number of lines. Not a haiku coincidence!
        return ""


def construct_haiku_to_post(h, this_status) -> dict:
    return {
        "user_id_str": h.user_id_str,
        "user_screen_name": h.user_screen_name,
        "status_id_str": h.status_id_str,
        "favorite_count": this_status["favorite_count"],
        "retweet_count": this_status["retweet_count"],
        "followers_count": this_status["user"]["followers_count"],
        "text_original": h.text_original,
        "text_clean": h.text_clean,
        "haiku": h.haiku,
    }


def get_best_haiku(haikus, twitter, db_session) -> dict:
    """Attempt to get the haiku by assessing verified user,
    or number of favorites, retweets, or followers.
    High probability that followers will yield a tweet.
    Otherwise get the most recent one.

    TODO: If there's more than 1 verified user (extremely unlikely), rank tweets
    """
    # initialize
    haiku_to_post = {
        "status_id_str": "",
        "favorite_count": 0,
        "retweet_count": 0,
        "followers_count": 0,
    }
    # find the best haiku
    for h in haikus:
        logger.debug(f"Haiku: {h.haiku}")
        try:
            this_status = twitter.show_status(id=h.status_id_str)
        except Exception as e:
            logger.warning(f"Exception when checking statuses (1): {e}")
            logger.info(f"{h.user_screen_name}/status/{h.status_id_str}")
            # Tweet no longer exists
            this_status = {}
            # soft delete
            Haiku.update_haiku_deleted(db_session, h.status_id_str)
        if this_status:
            if this_status["user"]["verified"]:
                haiku_to_post = construct_haiku_to_post(h, this_status)
            else:
                if this_status["favorite_count"] > haiku_to_post["favorite_count"]:
                    haiku_to_post = construct_haiku_to_post(h, this_status)
                elif this_status["retweet_count"] > haiku_to_post["retweet_count"]:
                    haiku_to_post = construct_haiku_to_post(h, this_status)
                elif (
                    this_status["user"]["followers_count"]
                    > haiku_to_post["followers_count"]
                ):
                    haiku_to_post = construct_haiku_to_post(h, this_status)

    if haiku_to_post["status_id_str"] == "":
        # # if no tweet was better than another, pick a random one
        # h = random.choice(haikus)
        # if no tweet was better than another, pick the most recent tweet
        for h in haikus[::-1]:
            try:
                this_status = twitter.show_status(id=h.status_id_str)
            except Exception as e:
                logger.warning(f"Exception when getting best status (2): {e}")
                logger.info(f"{h.user_screen_name}/status/{h.status_id_str}")
                # Tweet no longer exists, not going to post a haiku this time
                this_status = {}
                # soft delete
                Haiku.update_haiku_deleted(db_session, h.status_id_str)
            if this_status:
                haiku_to_post = construct_haiku_to_post(h, this_status)
                break

    return haiku_to_post
