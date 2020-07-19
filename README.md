# Haikuincidence

Find tweets that contain coincidental haikus, and [tweet these beautiful poems](https://twitter.com/haikuincidence).

```text
You're a poet and
you didn't even know it.
Hey, that's a haiku! ✌️
```

## Setup

### Data setup

1. Add phrases to `data/track.txt` to only search for tweets that contain any of the exact strings, one string per line (see [the documentation about `track`](https://developer.twitter.com/en/docs/tweets/filter-realtime/guides/basic-stream-parameters) for more info)
    1. If file does not exist or is empty, gets tweets from the [sample stream](https://developer.twitter.com/en/docs/tweets/sample-realtime/api-reference/get-statuses-sample)
1. Add phrases to `data/ignore.txt` to ignore tweets that contain tokens from any of these strings, one string per line. Uses `AND` and `OR` logic like the track list, but tokens for `AND` (a single line) can match anywhere. Also matches basic plural versions of words (e.g., `dog` in `data/ignore.txt` will match `dogs` in a tweet's text). See the function `text_contains_ignore_list` (in `utils/text_utils.py`) for more info.
    1. Whether or not this file exists, by default this program ignores tweets with words read in the `get_ignore_list` function (in `utils/data_utils.py`)
1. Add pre-defined syllable counts to `data/syllables.json`

### Credentials and other variables

If running the app on Heroku (see below), `.env` is not needed but it may still be convenient to fill in the environment variables.

1. Copy the (hidden) `.env_template.ini` file to `.env`
1. Edit `.env` to include your credentials (don't commit this file)

## Database setup

- If running the app on Heroku, you can easily provision a database for your app by installing the Postgres add-on (see below).
  - Your database credentials will automatically be added to your app's Config Vars.
- If not running the app on Heroku, you'll need to set up your own database.
  - Add your database credentials to `.env`

## Run the application

### As a Heroku app

1. Follow the [instructions for creating a Heroku app](https://devcenter.heroku.com/articles/getting-started-with-python)
1. Create add-ons for:
   1. [Papertrail](https://elements.heroku.com/addons/papertrail)
   1. [Postgres](https://elements.heroku.com/addons/heroku-postgresql)
1. Heroku does not use the `.env` file. Instead, add the environment variables as Config Vars to your app via the web-based dashboard.

#### Heroku logs

1. View the logs via the [Heroku CLI](https://devcenter.heroku.com/articles/logging#view-logs) or on Papertrail

### As a `systemd` service

1. Install required packages
   1. Run the following command to install [Miniconda (Python 3)](https://conda.io/miniconda.html) and the required libraries (installed in the `base` conda environment):

        ```bash
        ./python_env_setup.sh
        ```

   1. Log out and back in to ensure the `base` conda environment is active
1. `sudo cp haikuincidence.service /etc/systemd/system/haikuincidence.service`
   1. Update the user name and repo path as necessary (e.g., the user will be `ubuntu` if using an AWS EC2 instance)
1. `sudo systemctl daemon-reload`
1. `sudo systemctl enable haikuincidence`
1. `sudo systemctl start haikuincidence`
1. To stop completely:
   1. `sudo systemctl stop haikuincidence`
   1. `sudo systemctl disable haikuincidence`

#### `systemd` logs

- To read `systemd`'s logs (includes log messages from Python): `sudo journalctl -u haikuincidence`
- To follow `systemd`'s logs (includes log messages from Python): `sudo journalctl -f -u haikuincidence`

## Attribution

I borrowed and adapted code from these nice resources. Thank you!

- Default oppressive word filter from [this repo](https://github.com/dariusk/wordfilter)
- Syllable counting from [this script](https://github.com/akkana/scripts/blob/master/countsyl)
- Haiku checker from [this script](https://github.com/tomwardill/python-haiku/blob/master/haiku_checker.py)
- URL regex from [this gist](https://gist.github.com/gruber/8891611)

## License

Copyright (c) 2018 Matt Mollison Licensed under the MIT license.
