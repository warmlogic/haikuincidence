from pathlib import Path

from haikuincidence.utils.data_utils import get_ignore_profile_list
from haikuincidence.utils.text_utils import check_profile

data_dir = Path.cwd() / "data"

ignore_profile_list = get_ignore_profile_list(data_dir / "ignore_profile.txt")
match_substring = False
remove_punct = True


def test_profile_pass():
    with open("tests/data_profile_pass.txt", "r") as fp:
        profile_pass = fp.read().splitlines()

    for profile in profile_pass:
        status = {"user": {"description": profile}}
        profile_passes = check_profile(
            status,
            ignore_profile_list=ignore_profile_list,
            match_substring=match_substring,
            remove_punct=remove_punct,
        )
        assert profile_passes, f"Should have passed: {status['user']['description']}"


def test_profile_fail():
    with open("tests/data_profile_fail.txt", "r") as fp:
        profile_pass = fp.read().splitlines()

    for profile in profile_pass:
        status = {"user": {"description": profile}}
        profile_passes = check_profile(
            status,
            ignore_profile_list=ignore_profile_list,
            match_substring=match_substring,
            remove_punct=remove_punct,
        )
        assert (
            not profile_passes
        ), f"Should have failed: {status['user']['description']}"
