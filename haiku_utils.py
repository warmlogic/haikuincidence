import logging
import re
# import random
from typing import List, Dict

from text_utils import remove_repeat_last_letter, text_might_contain_acronym
from data_tweets_haiku import db_update_haiku_deleted

logging.basicConfig(format='{asctime} : {levelname} : {message}', level=logging.INFO, style='{')
logger = logging.getLogger(__name__)

# keep letters and apostrophes for contractions, and commas and periods for numbers
punct_to_keep = ["'", ',', '.']

# endings of contractions, for counting syllables
contraction_ends = ['d', 'll', 'm', 're', 's', 't', 've']


def clean_token(token):
    # remove space before some punctuation if preceded by a letter or number
    # ("hello ,how are you ? doing")
    token = re.sub(r'(\w)\s([.,;!?](?=\s|$)?)', r'\1\2', token)

    # put space after some punctuation if followed by a letter or number ("cat,dog")
    token = re.sub(r'(?<=[;!?])(?=[\w])', r' ', token)

    # put space after period if followed by a letter ("good.What")
    token = re.sub(r'(?<=[.,])(?=[A-Za-z])', r' ', token)

    # remove spaces around apostrophe if letter-space-apostrophe-space-letter
    token = re.sub(r"(\w)\s(['])[?=\s\w]", r"\1\2", token)

    # add space around some punctuation if letters on both sides
    token = re.sub(r'([\w])([#@&%=+/×\-](?=[\w]))', r'\1 \2 ', token)

    # try to replace a missing vowel with "u"
    token = re.sub(r'([\w])[\*]((?=[\w]))', r'\1u\2', token)

    # put a space after some punctuation that precedes a letter
    token = re.sub(r'([#@&%=+/×])((?=[\w]))', r'\1 \2', token)

    # put a space before some punctuation that follows a letter
    token = re.sub(r'([\w])([#@&%=+/×])', r'\1 \2', token)

    # special cases
    token = re.sub(r'\bb / c\b', 'because', token, flags=re.IGNORECASE)
    token = re.sub(r'\bb / t\b', 'between', token, flags=re.IGNORECASE)
    token = re.sub(r'\bw / o\b', 'without', token, flags=re.IGNORECASE)
    token = re.sub(r'\bw /\s\b', 'with ', token, flags=re.IGNORECASE)
    token = re.sub(r'\bw /\b', 'with', token, flags=re.IGNORECASE)
    token = re.sub(r'\ba\b\*', 'a star', token, flags=re.IGNORECASE)

    # replace some punctuation with words
    token = token.replace('@', 'at')
    token = token.replace('&', 'and')
    token = token.replace('%', 'percent')
    token = token.replace('=', 'equals')
    token = token.replace('×', 'times')
    token = token.replace('+', 'plus')
    # token = token.replace('*', 'star')
    # token = token.replace('/', 'slash')

    # keep the punctuation in punct_to_keep
    token_clean = re.sub(r"[^\w',\.]", ' ', token).strip()

    return token_clean


def count_syllables(token: str,
                    inflect_p,
                    pronounce_dict: Dict,
                    syllable_dict: Dict,
                    emoticons_list: List,
                    ) -> int:
    if token in emoticons_list:
        return 0

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
            logger.debug(f'    Subtoken: {subtoken}')

        if subtoken.replace('.', '').isdigit() or subtoken.replace(',', '').isdigit():
            # split a string that looks like a year
            if len(subtoken) == 4:
                if (subtoken[:2] == '18') or (subtoken[:2] == '19'):
                    subtoken = f'{subtoken[:2]} {subtoken[2:]}'
                else:
                    subtoken = inflect_p.number_to_words(subtoken, andword='')
            elif len(subtoken) == 2:
                # pronounce zero as "oh"
                if (subtoken[0] == '0') and subtoken[1].isdigit():
                    subtoken = f'oh {subtoken[1]}'
                else:
                    subtoken = inflect_p.number_to_words(subtoken, andword='')
            else:
                subtoken = inflect_p.number_to_words(subtoken, andword='')
            # remove all punctuation except apostrophes
            subtoken = re.sub(r"[^\w']", ' ', subtoken).strip()

        if subtoken in syllable_dict:
            subtoken_syl = syllable_dict[subtoken]['syllables']
            source = 'Dict'
            subsyllable_count += subtoken_syl
        elif remove_repeat_last_letter(subtoken) in syllable_dict:
            subtoken_syl = syllable_dict[remove_repeat_last_letter(subtoken)]['syllables']
            source = 'Dict (remove repeat)'
            subsyllable_count += subtoken_syl
        elif (subtoken.endswith('s') or subtoken.endswith('z')) and (subtoken[:-1] in syllable_dict):
            subtoken_syl = syllable_dict[subtoken[:-1]]['syllables']
            source = 'Dict (singular)'
            subsyllable_count += subtoken_syl
        elif subtoken in pronounce_dict:
            subtoken_syl = max([len([y for y in x if y[-1].isdigit()]) for x in pronounce_dict[subtoken]])
            source = 'CMU'
            subsyllable_count += subtoken_syl
        elif remove_repeat_last_letter(subtoken) in pronounce_dict:
            subtoken_syl = max([len([y for y in x if y[-1].isdigit()]) for x in pronounce_dict[remove_repeat_last_letter(subtoken)]])
            source = 'CMU (remove repeat)'
            subsyllable_count += subtoken_syl
        elif (subtoken.endswith('s') or subtoken.endswith('z')) and (subtoken[:-1] in pronounce_dict):
            subtoken_syl = max([len([y for y in x if y[-1].isdigit()]) for x in pronounce_dict[subtoken[:-1]]])
            source = 'CMU (singular)'
            subsyllable_count += subtoken_syl
        else:
            # it's not a "real" word
            if re.findall(r"[^\w']", subtoken):
                # there are some non-letter characters remaining (shouldn't be possible); run it through again
                subtoken_syl = count_syllables(subtoken, inflect_p, pronounce_dict, syllable_dict, emoticons_list)
                source = 'Non-letter chars'
                subsyllable_count += subtoken_syl
            else:
                if "'" in subtoken:
                    # contains an apostrophe
                    if subtoken.rsplit("'")[-1] in contraction_ends:
                        # ends with one of the contraction endings; make a guess
                        subtoken_syl = guess_syllables(subtoken)[0]
                        source = 'Guess'
                        subsyllable_count += subtoken_syl
                    else:
                        # doesn't end with a contraction ending; count each chunk between apostrophes
                        for subsubtoken in subtoken.rsplit("'"):
                            subtoken_syl = count_syllables(subsubtoken, inflect_p, pronounce_dict, syllable_dict, emoticons_list)
                            source = 'Multiple apostrophes'
                            subsyllable_count += subtoken_syl
                else:
                    # no apostrophes;
                    # might be an acronym, split the letters apart and run it through again
                    if text_might_contain_acronym(subtoken_orig):
                        subtoken_syl = count_syllables(' '.join(subtoken), inflect_p, pronounce_dict, syllable_dict, emoticons_list)
                        source = 'Acronym'
                        subsyllable_count += subtoken_syl
                    else:
                        # make a guess
                        subtoken_syl = guess_syllables(subtoken)[0]
                        source = 'Guess'
                        subsyllable_count += subtoken_syl
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"    {source}: {subtoken}: {subtoken_syl}")

    return subsyllable_count


def guess_syllables(word: str, verbose=False) -> (int, int):
    '''Guess the number of syllables in a string.
    Returns minimum and maximum guesses. Minimum is usually good enough.

    A diphthong is two vowel sounds in a single syllable (e.g., pie, boy, cow)

    Adapted from https://github.com/akkana/scripts/blob/master/countsyl
    '''
    vowels = ['a', 'e', 'i', 'o', 'u']

    on_vowel = False
    in_diphthong = False
    minsyl = 0
    maxsyl = 0
    lastchar = None

    if word:
        word = word.lower()
        for c in word:
            is_vowel = c in vowels

            if on_vowel is None:
                on_vowel = is_vowel

            # y is a special case
            if c == 'y':
                is_vowel = not on_vowel

            if is_vowel:
                if verbose:
                    print(f'{c} is a vowel')
                if not on_vowel:
                    # We weren't on a vowel before.
                    # Seeing a new vowel bumps the syllable count.
                    if verbose:
                        print('new syllable')
                    minsyl += 1
                    maxsyl += 1
                elif on_vowel and not in_diphthong and c != lastchar:
                    # We were already in a vowel.
                    # Don't increment anything except the max count,
                    # and only do that once per diphthong.
                    if verbose:
                        print(f'{c} is a diphthong')
                    in_diphthong = True
                    maxsyl += 1
            else:
                if re.findall(r'[\w]', c):
                    if verbose:
                        print('[consonant]')
                else:
                    if verbose:
                        print('[other]')

            on_vowel = is_vowel
            lastchar = c

        # Some special cases: ends in e, or past tense, may have counted too many
        if len(word) >= 2 and (word[-2:] != 'ie') and ((word[-1] == 'e') or (word[-2:] == 'ed')):
            minsyl -= 1
        # if it ended with a consonant followed by y, count that as a syllable.
        if word[-1] == 'y' and not on_vowel:
            maxsyl += 1

        # if found no syllables but there's at least one letter,
        # count as one syllable
        if re.findall(r'[\w]', word):
            if not minsyl:
                minsyl = 1
            if not maxsyl:
                maxsyl = 1

    return minsyl, maxsyl


def get_haiku(text: str,
              inflect_p,
              pronounce_dict: Dict,
              syllable_dict: Dict,
              emoticons_list: List,
              ) -> str:
    '''Attempt to turn a string into a haiku.
    Returns haiku if able, otherwise returns empty string.

    Inspired by https://github.com/tomwardill/python-haiku/blob/master/haiku_checker.py
    '''
    haiku_form = [5, 12, 17]
    haiku = [[] for _ in range(len(haiku_form))]
    syllable_count = 0
    haiku_line = 0
    haiku_line_prev = 0

    text_split = text.split()
    # Add tokens to create potential haiku
    for i, token in enumerate(text_split):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'Original token: {token}')
        # Add tokens with no syllables (punctuation, emoji)) to the end of the
        # previous line instead of the start of the current line
        if (re.findall(r"[^\w']", token) and (count_syllables(token, inflect_p, pronounce_dict, syllable_dict, emoticons_list) == 0)):
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
        syllable_count += count_syllables(token, inflect_p, pronounce_dict, syllable_dict, emoticons_list)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'{syllable_count} syllables counted total')

        if syllable_count == haiku_form[haiku_line]:
            # Reached exactly the number of syllables for this line, go to next line
            haiku_line += 1
        if i < len(text_split) - 1 and haiku_line >= len(haiku_form) and (count_syllables(' '.join(text_split[i + 1:]), inflect_p, pronounce_dict, syllable_dict, emoticons_list) > 0):
            # There are syllables in the remaining tokens to check, but have reached the number of lines in a haiku.
            # Therefore not a haiku coincidence!
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Not a haiku because are more lines to check: {' '.join(text_split[i + 1:])}")
            return ''
    if haiku_line == len(haiku_form):
        # Reached the end, and found the right number of lines. Haiku coincidence!
        return ['\n'.join([' '.join(line) for line in haiku])][0]
    else:
        # Did not find the right number of lines. Not a haiku coincidence!
        return ''


def construct_haiku_to_post(h, this_status) -> Dict:
    return {
        'user_id_str': h.user_id_str,
        'user_screen_name': h.user_screen_name,
        'status_id_str': h.status_id_str,
        'favorite_count': this_status['favorite_count'],
        'retweet_count': this_status['retweet_count'],
        'followers_count': this_status['user']['followers_count'],
        'text_original': h.text_original,
        'text_clean': h.text_clean,
        'haiku': h.haiku,
    }


def get_best_haiku(haikus, twitter, session) -> Dict:
    '''Attempt to get the haiku by assessing verified user,
    or number of favorites, retweets, or followers.
    High probability that followers will yield a tweet. Otherwise get the most recent one.

    TODO: If there's more than 1 verified user (extremely unlikely), rank tweets
    '''
    # initialize
    haiku_to_post = {
        'status_id_str': '',
        'favorite_count': 0,
        'retweet_count': 0,
        'followers_count': 0,
    }
    # find the best haiku
    for h in haikus:
        logger.debug(f'Haiku: {h.haiku}')
        try:
            this_status = twitter.show_status(id=h.status_id_str)
        except Exception:
            logger.exception('Exception when checking statuses (1)')
            logger.info(f'{h.user_screen_name}/status/{h.status_id_str}')
            # Tweet no longer exists
            this_status = {}
            # soft delete
            db_update_haiku_deleted(session, h.status_id_str)
        if this_status:
            if this_status['user']['verified']:
                haiku_to_post = construct_haiku_to_post(h, this_status)
            else:
                if this_status['favorite_count'] > haiku_to_post['favorite_count']:
                    haiku_to_post = construct_haiku_to_post(h, this_status)
                elif this_status['retweet_count'] > haiku_to_post['retweet_count']:
                    haiku_to_post = construct_haiku_to_post(h, this_status)
                elif this_status['user']['followers_count'] > haiku_to_post['followers_count']:
                    haiku_to_post = construct_haiku_to_post(h, this_status)

    if haiku_to_post['status_id_str'] == '':
        # # if no tweet was better than another, pick a random one
        # h = random.choice(haikus)
        # if no tweet was better than another, pick the most recent tweet
        for h in haikus[::-1]:
            try:
                this_status = twitter.show_status(id=h.status_id_str)
            except Exception:
                logger.exception(f'Exception when getting best status (2)')
                logger.info(f'{h.user_screen_name}/status/{h.status_id_str}')
                # Tweet no longer exists, not going to post a haiku this time
                this_status = {}
                # soft delete
                db_update_haiku_deleted(session, h.status_id_str)
            if this_status:
                haiku_to_post = construct_haiku_to_post(h, this_status)
                break

    return haiku_to_post
