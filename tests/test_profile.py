from haikuincidence.utils.data_utils import get_ignore_profile_list
from haikuincidence.utils.text_utils import check_profile

ignore_profile_list = get_ignore_profile_list()
match_substring = False


def test_profile_pass():
    with open("tests/data_profile_pass.txt", "r") as fp:
        profile_pass = fp.read().splitlines()

    for profile in profile_pass:
        status = dict(user=dict(description=profile))
        profile_passes = check_profile(
            status,
            ignore_profile_list=ignore_profile_list,
            match_substring=match_substring,
        )
        assert profile_passes, f"Should have passed: {status['user']['description']}"


def test_profile_fail():
    with open("tests/data_profile_fail.txt", "r") as fp:
        profile_pass = fp.read().splitlines()

    for profile in profile_pass:
        status = dict(user=dict(description=profile))
        profile_passes = check_profile(
            status,
            ignore_profile_list=ignore_profile_list,
            match_substring=match_substring,
        )
        assert (
            not profile_passes
        ), f"Should have failed: {status['user']['description']}"
