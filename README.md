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
1. Add phrases to `data/ignore_tweet.txt` to ignore tweets that contain tokens from any of these strings, one string per line. Uses `AND` and `OR` logic like the track list, but tokens for `AND` (a single line) can match anywhere. Also matches basic plural versions of words (e.g., `dog` in `data/ignore_tweet.txt` will match `dogs` in a tweet's text). See the function `text_contains_ignore_list_plural` (in `utils/text_utils.py`) for more info.
    1. Whether or not this file exists, by default this program ignores tweets with words read in the `get_ignore_tweet_list` function (in `utils/data_utils.py`)
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

These instructions use the Heroku CLI

1. Fork this repo on GitHub and ensure you have a branch called `main`
1. Create a new app on Heroku: `heroku create my-app-name`
1. Install add-ons for:
   1. [Papertrail](https://elements.heroku.com/addons/papertrail)
      1. `heroku addons:create papertrail -a my-app-name`
   1. [Postgres](https://elements.heroku.com/addons/heroku-postgresql)
      1. `heroku addons:create heroku-postgres -a my-app-name`
1. Create a new token: `heroku authorizations:create -d "my cool token description"`
   1. Add the token to your GitHub repo's Secrets under the name `HEROKU_API_KEY`
1. Add your Heroku app's name to the GitHub repo's Secrets under the name `HEROKU_APP_NAME`
1. Configure the application by adding environment variables as [Config Vars](https://devcenter.heroku.com/articles/config-vars)
1. Commit and push to your GitHub repo's `main` branch
   1. This can be through committing a change, merging a PR, or just running `git commit -m "empty commit" --allow-empty`
   1. This will use GitHub Actions to build the app using Docker and deploy to Heroku

#### Heroku logs

1. View the logs via the [Heroku CLI](https://devcenter.heroku.com/articles/logging#view-logs) or on Papertrail

## Attribution

I borrowed and adapted code from these nice resources. Thank you!

- Default oppressive word filter from [this repo](https://github.com/dariusk/wordfilter)
- Syllable counting from [this script](https://github.com/akkana/scripts/blob/master/countsyl)
- Haiku checker from [this script](https://github.com/tomwardill/python-haiku/blob/master/haiku_checker.py)
- URL regex from [this gist](https://gist.github.com/gruber/8891611)

## License

Copyright (c) 2018 Matt Mollison Licensed under the MIT license.
