"""VibePilot - Sort Spotify liked songs into vibe-based playlists."""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Dict, List

from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

try:
    import openai
except ImportError:  # pragma: no cover - optional dependency
    openai = None


VIBES = [
    "Chill Vibes",
    "Sad Bops",
    "Hype Gym",
    "Night Drive",
    "Lo-Fi Focus",
    "Romantic Mood",
]


def auth_spotify() -> spotipy.Spotify:
    """Authenticate with Spotify using environment credentials.

    Returns
    -------
    spotipy.Spotify
        Authenticated client instance.
    """
    load_dotenv()
    scope = "user-library-read playlist-modify-private playlist-modify-public"
    return spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))


def fetch_liked_songs(sp: spotipy.Spotify, limit: int = 1000) -> List[dict]:
    """Fetch up to ``limit`` saved tracks from the current user's library."""
    tracks: List[dict] = []
    offset = 0
    while len(tracks) < limit:
        batch = sp.current_user_saved_tracks(limit=min(50, limit - len(tracks)), offset=offset)
        items = batch.get("items", [])
        if not items:
            break
        tracks.extend(items)
        offset += len(items)
    return tracks


def get_audio_features(sp: spotipy.Spotify, tracks: List[dict]) -> Dict[str, dict]:
    """Retrieve audio features and artist genres for provided tracks."""
    features: Dict[str, dict] = {}
    track_ids = [t["track"]["id"] for t in tracks if t.get("track")]

    for chunk in range(0, len(track_ids), 100):
        ids = track_ids[chunk : chunk + 100]
        audio_feats = sp.audio_features(ids)
        for af in audio_feats:
            if not af:
                continue
            features[af["id"]] = {
                "valence": af.get("valence"),
                "energy": af.get("energy"),
                "danceability": af.get("danceability"),
                "tempo": af.get("tempo"),
            }

    # fetch artist genres (only first artist per track for speed)
    artist_ids = [t["track"]["artists"][0]["id"] for t in tracks if t.get("track") and t["track"].get("artists")]
    for chunk in range(0, len(artist_ids), 50):
        ids = artist_ids[chunk : chunk + 50]
        artists = sp.artists(ids)["artists"]
        for track, artist in zip(tracks[chunk : chunk + len(ids)], artists):
            tid = track["track"]["id"]
            if tid in features:
                features[tid]["genres"] = artist.get("genres", [])
            else:
                features[tid] = {"genres": artist.get("genres", [])}
    return features


def classify_vibe(features: dict, prompt: str | None = None, openai_api_key: str | None = None) -> str:
    """Classify a track's vibe using simple rules or GPT.

    Parameters
    ----------
    features:
        Dictionary of audio feature values and genres.
    prompt:
        Optional custom prompt for GPT-based classification.
    openai_api_key:
        API key used if GPT classification is desired.
    """
    valence = features.get("valence", 0)
    energy = features.get("energy", 0)
    dance = features.get("danceability", 0)
    tempo = features.get("tempo", 0)
    genres = [g.lower() for g in features.get("genres", [])]

    # Simple rule-based heuristics
    if valence > 0.7 and energy > 0.7:
        return "Hype Gym"
    if valence > 0.6 and dance > 0.6 and energy < 0.6:
        return "Chill Vibes"
    if valence < 0.3 and energy < 0.5:
        return "Sad Bops"
    if 100 <= tempo <= 130 and energy >= 0.5:
        return "Night Drive"
    if any("lo-fi" in g for g in genres):
        return "Lo-Fi Focus"
    if valence >= 0.5 and energy < 0.6:
        return "Romantic Mood"

    # TODO: Use GPT-4 with ``prompt`` and track metadata to refine classification
    if prompt and openai_api_key and openai:
        openai.api_key = openai_api_key
        # Example placeholder for future GPT call
        # response = openai.ChatCompletion.create(...)
        # return response['choices'][0]['message']['content']
        pass

    return "Chill Vibes"


def create_playlists(sp: spotipy.Spotify, user_id: str, vibe_tracks: Dict[str, List[str]]) -> Dict[str, str]:
    """Create playlists per vibe and add tracks."""
    playlist_ids: Dict[str, str] = {}
    for vibe, tracks in vibe_tracks.items():
        if not tracks:
            continue
        playlist = sp.user_playlist_create(user=user_id, name=vibe, public=False, description=f"VibePilot - {vibe}")
        sp.playlist_add_items(playlist["id"], tracks)
        playlist_ids[vibe] = playlist["id"]
    return playlist_ids


def save_logs(data: dict) -> None:
    """Save log data to ``logs/`` directory with timestamp."""
    os.makedirs("logs", exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = os.path.join("logs", f"log_{ts}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="VibePilot - create vibe playlists from your liked songs")
    parser.add_argument("--prompt", help="Optional custom vibe prompt for GPT filtering", type=str)
    args = parser.parse_args()

    sp = auth_spotify()
    user_id = sp.current_user()["id"]

    liked_tracks = fetch_liked_songs(sp)
    features = get_audio_features(sp, liked_tracks)

    vibe_tracks: Dict[str, List[str]] = defaultdict(list)
    log_entries = []
    openai_key = os.getenv("OPENAI_API_KEY")

    for item in liked_tracks:
        track = item.get("track")
        if not track:
            continue
        tid = track["id"]
        vibe = classify_vibe(features.get(tid, {}), prompt=args.prompt, openai_api_key=openai_key)
        vibe_tracks[vibe].append(tid)
        log_entries.append({"id": tid, "name": track.get("name"), "vibe": vibe})

    playlists = create_playlists(sp, user_id, vibe_tracks)

    log_data = {
        "tracks_processed": len(log_entries),
        "playlists": playlists,
        "entries": log_entries,
    }
    save_logs(log_data)


if __name__ == "__main__":
    main()
