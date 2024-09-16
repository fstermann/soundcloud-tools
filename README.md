# soundcloud-archive


## Description

This repository provides a workflow to collect all liked, posted and reposted tracks and playlists of a users favorited artists for the past week.

The worlkflow is meant to be run weekly, and will store the tracks and playlists in a new playlist on the users SoundCloud account.

## Installation

```bash
pip install poetry
poetry install
```


## Settings

The following environment variables are required and can be set in a `.env` file in the root directory of the project:

```
OAUTH_TOKEN=
CLIENT_ID=
DATADOME_CLIENTID=
USER_ID=
PROXY=
```

## Usage

```bash
poetry run python soundcloud_archive.py
```

__Options__

- `--week`: The week number relative to the current week. For example, `--week=0` will download the tracks from the current week, `--week=-1` will download the tracks from the previous week, and so on.


## Workflow

In order to setup the workflow, simply add the environment variables as secrets in the GitHub repository settings. By default the workflow will run every Sunday at 08:00 AM, but this can be changed in the [`.github/workflows/run.yml`](.github/workflows/run.yml) file.

```yaml