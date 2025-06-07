# VibePilot

VibePilot is a command-line tool that sorts your Spotify **Liked Songs** into new playlists based on their overall vibe.

The script uses [Spotipy](https://spotipy.readthedocs.io/) for Spotify API access and optionally the [OpenAI Python SDK](https://github.com/openai/openai-python) to refine vibe classification with GPT models.

## Setup

1. Create a Spotify developer application at <https://developer.spotify.com/dashboard> and set a redirect URI (e.g. `http://localhost:8888/callback`).
2. Copy `.env.example` to `.env` and fill in your credentials. Optionally add your `OPENAI_API_KEY` for GPT-based filtering.
3. Install dependencies:

```bash
pip install spotipy python-dotenv openai
```

## Usage

Run the script to create playlists for each vibe category:

```bash
python main.py
```

You can supply a custom prompt to filter songs via GPT:

```bash
python main.py --prompt "upbeat summer beach"
```

The script will create playlists named after each vibe (e.g. *Chill Vibes*, *Hype Gym*) and log processed tracks to the `logs/` directory.

## Logs

Every run writes a timestamped JSON file in `logs/` containing the processed track IDs, the category assigned, and playlist IDs.

## Development

This repository contains a minimal prototype. Contributions are welcome!
