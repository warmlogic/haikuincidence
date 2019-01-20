import configparser
from datetime import datetime
import logging
import pytz
import re
from typing import List, Dict

from ftfy import fix_text

config = configparser.ConfigParser()
config.read('config.ini')

logger_name = config['haiku'].get('logger_name', 'default_logger')

logger = logging.getLogger(logger_name)

# Regex to look for URLs https://gist.github.com/gruber/8891611
url_re = re.compile(r'(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))')


def clean_text(text: str, pronounce_dict: Dict, syllable_dict: Dict) -> str:
    '''Process text so it's ready for syllable counting
    '''

    # fix wonky characters
    text = fix_text(text)

    # split and rejoin to remove newlines
    text = ' '.join(text.split())

    text_final = []
    for token in text.split():
        # If it's a real word or is in the custom dictionary, keep it as is.
        # Try to split it if it's an acronym, or just keep it as is.
        if all_tokens_are_real(token, pronounce_dict, syllable_dict):
            text_final.append(token)
        else:
            text_final.extend(split_acronym(token))

    return ' '.join(text_final)


def check_text_wrapper(text: str, ignore_list: List[str]) -> bool:
    return all([
        (not text_contains_url(text)),
        (not text_contains_ignore_list(text, ignore_list)),
        (not text_has_chars_digits_together(text)),
        (not text_is_all_uppercase(text)),
        # (text_is_all_alpha(text)),
    ])


def check_tweet(status, ignore_list):
    '''Return True if tweet satisfies specific criteria
    '''
    return all([
        check_text_wrapper(status['text'], ignore_list),
        (status['lang'] == 'en'),
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
        # '(media' not in status['entities']),
        (len(status['text']) >= 17),
    ])


def date_string_to_datetime(date_string, fmt='%a %b %d %H:%M:%S +0000 %Y', tzinfo=pytz.UTC):
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


def split_acronym(token: str) -> List[str]:
    '''Split short acronyms. One option for all caps, one for lowercase.
    Otherwise return the token.
    '''
    token_clean = re.sub(r"[^\w']", ' ', token).strip()
    if len(token_clean) <= 5 and re.findall(r'\b[A-Z\.]{2,}s?\b', token_clean):
        return ' '.join(token).split()
    elif len(token_clean) <= 3 and re.findall(r'\b[a-z\.]{2,}s?\b', token_clean):
        return ' '.join(token).split()
    else:
        return [token]


def all_tokens_are_real(text: str, pronounce_dict: Dict, syllable_dict: Dict) -> bool:
    '''Return True if all tokens are real words (in pronunciation dictionary or
    in syllable dictionary)
    '''
    # Keep characters and apostrphes
    return all(
        (re.sub(r"[^\w']", '', token) and
            ((re.sub(r"[^\w']", '', token).lower() in pronounce_dict) or
                (re.sub(r"[^\w']", '', token).lower() in syllable_dict) or
                (remove_repeat_last_letter(
                    re.sub(r"[^\w']", '', token).lower()) in pronounce_dict) or
                (remove_repeat_last_letter(
                    re.sub(r"[^\w']", '', token).lower()) in syllable_dict))
         ) for token in text.split()
    )


def text_contains_url(text: str) -> bool:
    '''True if text contains a URL'''
    return len(url_re.findall(text)) > 0


def text_contains_ignore_list(text: str, ignore_list: List[str]) -> bool:
    '''Return True if anything from the ignore_list is in the text.
    All tokens from one ignore_list line must be somewhere in the text (AND logic),
    and each line is considered separately (OR logic).
    '''
    # found all of the subtokens from one ignore line in the status
    return any([all([ip in text.lower() for ip in ignore_line.split()]) for ignore_line in ignore_list])


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


# def text_is_all_alpha(text: str) -> bool:
#     '''Return True if every character is a letter.
#     Excludes punctuation and spaces.
#     '''
#     return all([char.isalpha() for char in re.sub(r'[^\w]', '', text)])


# def reform_acronyms(text):
#     '''TODO
#     NB: Will only work if an acronym can't be split across lines
#     '''
#     return text


def count_syllables(token: str,
                    inflect_p,
                    pronounce_dict: Dict,
                    syllable_dict: Dict,
                    emoticons_list: List,
                    ):
    if token in emoticons_list:
        return 0

    # endings of contractions, for counting syllables
    contraction_ends = ['d', 'll', 'm', 're', 's', 't', 've']

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
    token = re.sub(r'\bb / c\b', 'because', token)
    token = re.sub(r'\bb / t\b', 'between', token)
    token = re.sub(r'\bw / o\b', 'without', token)
    token = re.sub(r'\bw /\s\b', 'with ', token)
    token = re.sub(r'\bw /\b', 'with', token)
    token = re.sub(r'\ba\b\*', 'a star', token.lower())

    # replace some punctuation with words
    token = token.replace('#', 'hashtag')
    token = token.replace('@', 'at')
    token = token.replace('&', 'and')
    token = token.replace('%', 'percent')
    token = token.replace('=', 'equals')
    token = token.replace('×', 'times')
    token = token.replace('+', 'plus')
    # token = token.replace('*', 'star')
    # token = token.replace('/', 'slash')

    # keep letters and apostrophes for contractions, and commas and periods for numbers
    punct_to_keep = ["'", ',', '.']
    token_clean = re.sub(r"[^\w',\.]", ' ', token).lower().strip()

    subsyllable_count = 0
    for subtoken in token_clean.split():
        # remove starting or ending punctuation
        for punct in punct_to_keep:
            subtoken = subtoken.strip(punct)

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
                if (subtoken[0] == '0') and subtoken[1].isdigit():
                    subtoken = f'oh {subtoken[1]}'
                else:
                    subtoken = inflect_p.number_to_words(subtoken, andword='')
            else:
                subtoken = inflect_p.number_to_words(subtoken, andword='')
            # remove all punctuation except apostrophes
            subtoken = re.sub(r"[^\w']", ' ', subtoken).strip()
        if subtoken in syllable_dict:
            subsyllable_count += syllable_dict[subtoken]['syllables']
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"    Dict: {subtoken}: {syllable_dict[subtoken]['syllables']}")
        elif remove_repeat_last_letter(subtoken) in syllable_dict:
            subtoken = remove_repeat_last_letter(subtoken)
            subsyllable_count += syllable_dict[subtoken]['syllables']
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"    Dict: {subtoken}: {syllable_dict[subtoken]['syllables']}")
        elif subtoken in pronounce_dict:
            subsyllable_count += max([len([y for y in x if y[-1].isdigit()]) for x in pronounce_dict[subtoken]])
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"    CMU: {subtoken}: {max([len([y for y in x if y[-1].isdigit()]) for x in pronounce_dict[subtoken]])}")
        elif remove_repeat_last_letter(subtoken) in pronounce_dict:
            subtoken = remove_repeat_last_letter(subtoken)
            subsyllable_count += max([len([y for y in x if y[-1].isdigit()]) for x in pronounce_dict[subtoken]])
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"    CMU: {subtoken}: {max([len([y for y in x if y[-1].isdigit()]) for x in pronounce_dict[subtoken]])}")
        else:
            # it's not a "real" word
            # if there are some non-letter characters remaining (shouldn't be possible)
            if re.findall(r"[^\w']", subtoken):
                subsyllable_count += count_syllables(subtoken, inflect_p, pronounce_dict, syllable_dict, emoticons_list)
            else:
                if "'" in subtoken:
                    if subtoken.rsplit("'")[-1] in contraction_ends:
                        subsyllable_count += guess_syllables(subtoken)[0]
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f"    Guess: {subtoken}: {guess_syllables(subtoken)[0]}")
                    else:
                        # count each chunk between apostrophes
                        for subsubtoken in subtoken.rsplit("'"):
                            subsyllable_count += count_syllables(subsubtoken, inflect_p, pronounce_dict, syllable_dict, emoticons_list)
                else:
                    # make a guess
                    subsyllable_count += guess_syllables(subtoken)[0]
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"    Guess: {subtoken}: {guess_syllables(subtoken)[0]}")
    return subsyllable_count


def guess_syllables(word: str, verbose=False):
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
