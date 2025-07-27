# importing necessary libraries
import streamlit as st
from PIL import Image
import io
from datetime import datetime
from deepface import DeepFace
import numpy as np
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import random

# --- Spotify Setup ---
SPOTIFY_CLIENT_ID = "YOUR_SPOTIFY_CLIENT_ID"
SPOTIFY_CLIENT_SECRET = "YOUR_SPOTIFY_CLIENT_SECRET"
SPOTIFY_REDIRECT_URI = "http://localhost:8501"

# --- Spotify Auth ---
sp = None
if "token_info" not in st.session_state:
    auth_manager = SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope="user-read-playback-state,user-modify-playback-state,user-read-currently-playing",
        cache_path=".cache"
    )
    if code := st.experimental_get_query_params().get("code"):
        token_info = auth_manager.get_access_token(code[0])
        if token_info:
            st.session_state.token_info = token_info
            sp = spotipy.Spotify(auth=token_info["access_token"])
else:
    sp = spotipy.Spotify(auth=st.session_state.token_info["access_token"])

# --- Emotion Analysis Function ---
def analyze_emotions(image):
    try:
        img_array = np.array(image)
        result = DeepFace.analyze(img_array, actions=["emotion"], enforce_detection=False)
        data = result[0] if isinstance(result, list) else result
        dominant_emotion = data.get("dominant_emotion", "Unknown")
        confidence = data["emotion"].get(dominant_emotion, 0)
        return [{"emotion": dominant_emotion.capitalize(), "confidence": confidence / 100}]
    except Exception as e:
        st.error(f"Emotion Detection Failed: {e}")
        return [{"emotion": "Unknown", "confidence": 0}]

# --- Get Song Based on Emotion ---
def get_track_for_emotion(emotion):
    mood_keywords = {
        "Happy": ["happy", "upbeat", "energetic"],
        "Sad": ["sad", "melancholy", "blue"],
        "Angry": ["angry", "aggressive", "rock"],
        "Surprised": ["wow", "surprise", "eclectic"],
        "Neutral": ["chill", "ambient", "background"],
        "Fear": ["dark", "intense", "haunting"],
        "Disgust": ["cleanse", "detox", "calm"]
    }
    if emotion not in mood_keywords:
        return None
    query = random.choice(mood_keywords[emotion])
    results = sp.search(q=query, type="track", limit=10)
    if results["tracks"]["items"]:
        return random.choice(results["tracks"]["items"])
    return None

# --- Streamlit UI Setup ---
st.set_page_config(page_title="Emotion Detection Camera", page_icon="📸", layout="centered")

if "gallery" not in st.session_state:
    st.session_state.gallery = []
if "last_tracks" not in st.session_state:
    st.session_state.last_tracks = []

st.markdown("<h1 style='text-align:center;'>📸 Emotion Detection + 🎶 Spotify Music</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:gray;'>Analyze your face & get a song for your vibe.</p>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📷 Camera Capture", "📁 Upload Photo"])
image_data = None
with tab1:
    image_data = st.camera_input("Start your camera")
with tab2:
    uploaded = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])
    if uploaded:
        image_data = uploaded

# --- Process Image ---
if image_data:
    image = Image.open(image_data)
    st.image(image, caption="Analyzed Image", use_column_width=True)
    st.info("Analyzing emotions... 🤔")
    emotions = analyze_emotions(image)

    st.markdown("---")
    st.subheader("🎭 Emotion Analysis Results")

    for result in emotions:
        emo = result["emotion"]
        conf = int(result["confidence"] * 100)
        emoji_map = {
            "Happy": "😊", "Sad": "😢", "Angry": "😠", "Surprised": "😲",
            "Neutral": "😐", "Fear": "😨", "Disgust": "🤢"
        }
        emoji = emoji_map.get(emo, "🤔")
        st.markdown(
            f"<div style='display: flex; align-items: center; padding: 1rem; "
            f"border-radius: 1rem; background: rgba(102, 126, 234, 0.2);'>"
            f"<span style='font-size:2rem; margin-right:1rem;'>{emoji}</span>"
            f"<div><strong style='font-size:1.5rem;'>{emo}</strong><br/>"
            f"<span style='font-size:1.2rem;'>{conf}% confidence</span></div></div>",
            unsafe_allow_html=True
        )

        # Save image to gallery
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        buf = io.BytesIO()
        image.save(buf, format="JPEG")
        img_bytes = buf.getvalue()
        st.session_state.gallery.insert(0, {
            'image': img_bytes,
            'emoji': emoji,
            'timestamp': timestamp
        })

        # --- Spotify Results ---
        if sp:
            st.markdown("### 🎶 Your Mood Song")
            if "track_index" not in st.session_state:
                st.session_state.track_index = 0
            if not st.session_state.last_tracks:
                for _ in range(5):
                    track = get_track_for_emotion(emo)
                    if track:
                        st.session_state.last_tracks.append(track)

            track = st.session_state.last_tracks[st.session_state.track_index]
            name = track["name"]
            artist = track["artists"][0]["name"]
            preview_url = track["preview_url"]
            external_url = track["external_urls"]["spotify"]

            st.write(f"**{name}** by *{artist}*")
            if preview_url:
                st.audio(preview_url, format="audio/mp3")
            else:
                st.markdown(f"[Open in Spotify]({external_url})")

            if st.button("⏭️ Next Song"):
                st.session_state.track_index = (st.session_state.track_index + 1) % len(st.session_state.last_tracks)
        else:
            st.warning("Spotify not authenticated. Please restart the app and authorize.")

# --- Gallery ---
st.markdown("---")
st.header("🖼️ Saved Images")
if st.session_state.gallery:
    cols = st.columns(4)
    for idx, item in enumerate(st.session_state.gallery):
        col = cols[idx % 4]
        col.image(item["image"], use_column_width=True)
        col.caption(f"{item['emoji']} {item['timestamp']}")
else:
    st.write("No images saved yet.")
