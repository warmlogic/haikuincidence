import logging
import re

# import random
from typing import Dict, List

from utils.data_base import Haiku
from utils.text_utils import (
    clean_token,
    remove_repeat_last_letter,
    text_might_contain_acronym,
)

logger = logging.getLogger("haikulogger")

# keep letters and apostrophes for contractions, and commas and periods for numbers
punct_to_keep = ["'", ",", "."]

# endings of contractions, for counting syllables
contraction_ends = ["d", "ll", "m", "re", "s", "t", "ve"]


def count_syllables(
    token: str,
    inflect_p,
    pronounce_dict: Dict,
    syllable_dict: Dict,
    emoticons_list: List,
    guess_syl_method: str,
) -> int:
    if token in emoticons_list:
        return 0

    # find whether the token is an exact match to a dictionary entry
    if token in syllable_dict:
        token_syl = syllable_dict[token]["syllables"]
        source = "Dict"
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"    {source}: {token}: {token_syl}")
        return token_syl

    token_clean = clean_token(token)

    subsyllable_count = 0
    for subtoken in token_clean.split():
        # remove starting or ending punctuation
        for punct in punct_to_keep:
            subtoken = subtoken.strip(punct)

        # keep capitalization for checking acronyms
        subtoken_orig = subtoken
        # lowercase for checking against syllable_dict and pronounce_dict
        subtoken = subtoken.lower()

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"    Subtoken: {subtoken}")

        if subtoken.replace(",", "").replace(".", "").isdigit():
            # split a string that looks like a year
            if len(subtoken) == 4:
                if subtoken.isdigit():
                    if (int(subtoken[:2]) % 10 == 0) and (int(subtoken[2:]) < 10):
                        subtoken = inflect_p.number_to_words(subtoken, andword="")
                    else:
                        subtoken = f"{subtoken[:2]} {subtoken[2:]}"
                else:
                    subtoken = inflect_p.number_to_words(subtoken, andword="")
            elif len(subtoken) == 2:
                if subtoken.isdigit():
                    # pronounce zero as "oh"
                    if subtoken[0] == "0":
                        subtoken = f"oh {subtoken[1]}"
                    else:
                        subtoken = inflect_p.number_to_words(subtoken, andword="")
                else:
                    subtoken = inflect_p.number_to_words(subtoken, andword="")
            else:
                subtoken = inflect_p.number_to_words(subtoken, andword="")
            # remove all punctuation except apostrophes
            subtoken = re.sub(r"[^\w']", " ", subtoken).strip()

        if subtoken in syllable_dict:
            subtoken_syl = syllable_dict[subtoken]["syllables"]
            source = "Dict"
            subsyllable_count += subtoken_syl
        elif remove_repeat_last_letter(subtoken) in syllable_dict:
            subtoken_syl = syllable_dict[remove_repeat_last_letter(subtoken)]["syllables"]
            source = "Dict (remove repeat)"
            subsyllable_count += subtoken_syl
        elif (subtoken_orig.endswith("s") or subtoken_orig.endswith("z")) and (
            subtoken[:-1] in syllable_dict
        ):
            subtoken_syl = syllable_dict[subtoken[:-1]]["syllables"]
            source = "Dict (singular)"
            subsyllable_count += subtoken_syl
        elif subtoken in pronounce_dict:
            subtoken_syl = max(
                [len([y for y in x if y[-1].isdigit()]) for x in pronounce_dict[subtoken]]
            )
            source = "CMU"
            subsyllable_count += subtoken_syl
        elif remove_repeat_last_letter(subtoken) in pronounce_dict:
            subtoken_syl = max(
                [
                    len([y for y in x if y[-1].isdigit()])
                    for x in pronounce_dict[remove_repeat_last_letter(subtoken)]
                ]
            )
            source = "CMU (remove repeat)"
            subsyllable_count += subtoken_syl
        elif (subtoken_orig.endswith("s") or subtoken_orig.endswith("z")) and (
            subtoken[:-1] in pronounce_dict
        ):
            subtoken_syl = max(
                [len([y for y in x if y[-1].isdigit()]) for x in pronounce_dict[subtoken[:-1]]]
            )
            source = "CMU (singular)"
            subsyllable_count += subtoken_syl
        else:
            # it's not a "real" word
            if re.findall(r"[^\w']", subtoken):
                # there are some non-letter characters remaining (shouldn't be possible);
                # run it through again
                subtoken_syl = count_syllables(
                    subtoken,
                    inflect_p,
                    pronounce_dict,
                    syllable_dict,
                    emoticons_list,
                    guess_syl_method,
                )
                source = "Non-letter chars"
                subsyllable_count += subtoken_syl
            else:
                if "'" in subtoken:
                    # contains an apostrophe
                    if subtoken.rsplit("'")[-1] in contraction_ends:
                        # ends with one of the contraction endings; make a guess
                        subtoken_syl = guess_syllables(subtoken, guess_syl_method)
                        source = "Guess"
                        subsyllable_count += subtoken_syl
                    else:
                        # doesn't end with a contraction ending;
                        # count each chunk between apostrophes
                        for subsubtoken in subtoken.rsplit("'"):
                            subtoken_syl = count_syllables(
                                subsubtoken,
                                inflect_p,
                                pronounce_dict,
                                syllable_dict,
                                emoticons_list,
                                guess_syl_method,
                            )
                            source = "Multiple apostrophes"
                            subsyllable_count += subtoken_syl
                else:
                    # no apostrophes;
                    # might be an acronym, split the letters apart and run it through again
                    if text_might_contain_acronym(subtoken_orig):
                        subtoken_syl = count_syllables(
                            " ".join(subtoken),
                            inflect_p,
                            pronounce_dict,
                            syllable_dict,
                            emoticons_list,
                            guess_syl_method,
                        )
                        source = "Acronym"
                        subsyllable_count += subtoken_syl
                    else:
                        # make a guess
                        subtoken_syl = guess_syllables(subtoken, guess_syl_method)
                        source = "Guess"
                        subsyllable_count += subtoken_syl
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"    {source}: {subtoken}: {subtoken_syl}")

    return subsyllable_count


def guess_syllables(word: str, method: str = "min") -> int:
    """Guess the number of syllables in a string.
    Returned value depends on the method used. Minimum is usually good enough.

    A diphthong is two vowel sounds in a single syllable (e.g., pie, boy, cow)

    Adapted from https://github.com/akkana/scripts/blob/master/countsyl
    """

    def get_syl_count_str(minsyl, maxsyl):
        return f"min syl {minsyl}," + f" mean syl {(minsyl + maxsyl) // 2}," + f" max syl {maxsyl}"

    assert method in ["min", "max", "mean"]
    logger.debug(f"Guessing syllable count with method: {method}")

    vowels = ["a", "e", "i", "o", "u"]

    on_vowel = False
    in_diphthong = False
    minsyl = 0
    maxsyl = 0
    lastchar = None

    if word:
        word = word.lower()
        for i, c in enumerate(word):
            is_vowel = c in vowels

            if on_vowel is None:
                on_vowel = is_vowel

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
                    logger.debug(f"new syllable: {get_syl_count_str(minsyl, maxsyl)}")
                elif on_vowel and not in_diphthong and c != lastchar:
                    # We were already in a vowel.
                    # Don't increment anything except the max count,
                    # and only do that once per diphthong.
                    in_diphthong = True
                    maxsyl += 1
                    logger.debug(f"diphthong: {c}: {get_syl_count_str(minsyl, maxsyl)}")
            else:
                if re.findall(r"[\w]", c):
                    logger.debug(f"consonant: {c}")
                else:
                    logger.debug(f"other: {c}")

            # if len(word[i:]) >= 2 and not any([x in vowels + ["y"] for x in word[i:]]):
            #     minsyl += 1
            #     maxsyl += 1
            #     logger.debug(
            #         f"remaining letters are all consonants: {word[i:]}. add 1:"
            #         + f"{get_syl_count_str(minsyl, maxsyl)}"
            #     )
            #     break

            on_vowel = is_vowel
            lastchar = c

        # May have counted too many syllables: word ends in e, or past tense (-ed)
        if (
            (len(word) >= 3)
            and ((word[-1] == "e") or (word[-2:] == "ed"))
            and (word[-2:] not in ["be", "ie"])
            and (word[-3] not in ["d", "t"])
        ):
            minsyl -= 1
            logger.debug(f"Removing a syllable for '{word}': {get_syl_count_str(minsyl, maxsyl)}")

        # Posessive with word ending in certain sounds may not get enough syllables
        if (len(word) >= 3) and (word[-2:] == "'s") and (word[-3] in ["x"]):
            minsyl += 1
            maxsyl += 1
            logger.debug(f"Adding a syllable for '{word}': {get_syl_count_str(minsyl, maxsyl)}")

        # if it ended with a consonant followed by y, count that as a syllable.
        if word[-1] == "y" and not on_vowel:
            maxsyl += 1
            logger.debug(f"Adding a syllable for '{word}': {get_syl_count_str(minsyl, maxsyl)}")

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
        # Average and round down
        syl = (minsyl + maxsyl) // 2
    elif method == "max":
        syl = maxsyl

    return syl


def get_haiku(
    text: str,
    inflect_p,
    pronounce_dict: Dict,
    syllable_dict: Dict,
    emoticons_list: List,
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
                    f"Not a haiku because are more lines to check: {' '.join(text_split[i + 1:])}"
                )
            return ""
    if haiku_line == len(haiku_form):
        # Reached the end, and found the right number of lines. Haiku coincidence!
        return ["\n".join([" ".join(line) for line in haiku])][0]
    else:
        # Did not find the right number of lines. Not a haiku coincidence!
        return ""


def construct_haiku_to_post(h, this_status) -> Dict:
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


def get_best_haiku(haikus, twitter, session) -> Dict:
    """Attempt to get the haiku by assessing verified user,
    or number of favorites, retweets, or followers.
    High probability that followers will yield a tweet. Otherwise get the most recent one.

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
            Haiku.update_haiku_deleted(session, h.status_id_str)
        if this_status:
            if this_status["user"]["verified"]:
                haiku_to_post = construct_haiku_to_post(h, this_status)
            else:
                if this_status["favorite_count"] > haiku_to_post["favorite_count"]:
                    haiku_to_post = construct_haiku_to_post(h, this_status)
                elif this_status["retweet_count"] > haiku_to_post["retweet_count"]:
                    haiku_to_post = construct_haiku_to_post(h, this_status)
                elif this_status["user"]["followers_count"] > haiku_to_post["followers_count"]:
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
                Haiku.update_haiku_deleted(session, h.status_id_str)
            if this_status:
                haiku_to_post = construct_haiku_to_post(h, this_status)
                break

    return haiku_to_post
