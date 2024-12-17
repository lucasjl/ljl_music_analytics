import spotipy
import pandas as pd

access_token = 'BQBIMWp_iBQktZ0NtTehb8itZD1qx7T4oBBv0qy-VD8Q2ZiDVRJUPeB0FgsgpAggJrFF3jXdoO41tejsCxj0dorMxqs40WuepTGW55q0aZn0N0LIvZTIYdn3kZp9y27LMBOPNM0ay-dJgOW7f3h3d4RslFoUoRpb57arAUB4NGATsbFIxz5_HUm-g8hH4YyVMM5Ab_hza4eF5m123K1YJTbDpulLnuAd3ZN5zbY2havzYQ_ZKm0kovVLPo0ItijV_RVSpzmvQ-rEpWA4P8wIxDBAFBPkNGTuS7_g__rRFr23YuZUlLRfGhRTHEOzKv22QzLjvZqqIX8Rxbg'
sp = spotipy.Spotify(auth=access_token)

def get_artist_albums(artist_name):
    """Get all albums of an artist by name."""
    results = sp.search(q=f"artist:{artist_name}", type="artist", limit=1)
    artist_id = results['artists']['items'][0]['id']  # Get artist ID
    albums = sp.artist_albums(artist_id, album_type="album,single", limit=50)
    return albums['items']

def get_album_tracks(album_id):
    """Get all tracks from an album."""
    tracks = sp.album_tracks(album_id)['items']
    return tracks

def get_audio_features_in_chunks(track_ids, chunk_size=100):
    """Get audio features for track IDs in chunks of specified size."""
    audio_features = []
    for i in range(0, len(track_ids), chunk_size):
        chunk = track_ids[i:i + chunk_size]
        features = sp.audio_features(chunk)
        audio_features.extend(features)
    return audio_features

def fetch_discography_audio_features(artist_name):
    """Fetch all audio features for an artist's discography."""
    albums = get_artist_albums(artist_name)
    all_tracks = []

    for album in albums:
        album_tracks = get_album_tracks(album['id'])
        for track in album_tracks:
            track_data = {
                "track_name": track['name'],
                "album_name": album['name'],
                "artist_name": artist_name,
                "release_date": album['release_date'],
                "track_id": track['id']
            }
            all_tracks.append(track_data)

    # Get audio features for all tracks
    track_ids = [track['track_id'] for track in all_tracks]
    audio_features = get_audio_features_in_chunks(track_ids)

    # Combine track details with audio features
    for i, features in enumerate(audio_features):
        if features:  # Handle cases where features might be None
            all_tracks[i].update(features)

    return all_tracks

# Fetch audio features for both artists
arctic_monkeys_data = fetch_discography_audio_features("Arctic Monkeys")
the_strokes_data = fetch_discography_audio_features("The Strokes")

# Combine data and save to CSV
all_data = arctic_monkeys_data + the_strokes_data
df = pd.DataFrame(all_data)

# Save to CSV
output_file = "arctic_monkeys_the_strokes_audio_features.csv"
df.to_csv(output_file, index=False)

print(f"Data saved to {output_file}")
