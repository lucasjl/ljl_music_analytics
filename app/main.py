import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from config import CLIENT_ID, CLIENT_SECRET
from fastapi import FastAPI, HTTPException

app = FastAPI()

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=CLIENT_ID,client_secret=CLIENT_SECRET))

@app.get("/")
def read_root():
    return {"Hello": "World of Music"}

#Spotify Routes

@app.get("/artist/{artist_name}")
def artist_data(artist_name: str):
    results = sp.search(q=artist_name, type="artist", limit=1)
    if not results['artists']['items']:
        raise HTTPException(status_code=404, detail="Artist not found")
    return results['artists']['items'][0]

@app.get("/audio_features/{track_id}")
def audio_features(track_id: str):
    features = sp.audio_features([track_id])
    if not features or features[0] is None:
        raise HTTPException(status_code=404, detail="Track not found")
    return features[0]