# frontend.py

import streamlit as st
from PIL import Image
import io
from datetime import datetime
from deepface import DeepFace
import numpy as np
import os
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
import random

# 1) Page config must come first
st.set_page_config(page_title="Moodify", page_icon="📸", layout="centered")

# 2) (Optional) Your existing CSS for circular buttons can stay if you like,
#    but since we're moving regenerate down, you can remove or keep it. I'll leave it:
st.markdown(
    """
    <style>
    div.stButton > button {
        border: 2px solid #666;
        border-radius: 50%;
        padding: 8px 10px;
        font-size: 1.25rem;
        background-color: white;
        width: 48px;
        height: 48px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    div.stButton > button:hover {
        background-color: #f0f0f0;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Initialize Spotify
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET")
))

# Emotion → playlist keywords
emotion_to_genre = {
    "Happy":    ["happy", "pop", "feel good", "upbeat", "party"],
    "Sad":      ["sad songs", "acoustic", "emotional", "heartbreak", "soft rock"],
    "Angry":    ["metal", "hard rock", "punk", "grunge", "alternative"],
    "Surprise": ["electronic", "dance", "edm", "house", "party"],
    "Neutral":  ["lofi", "chill", "study", "relax", "ambient"],
    "Fear":     ["ambient", "calm", "meditation", "relax", "instrumental"],
    "Disgust":  ["punk", "garage rock", "grunge", "heavy", "alt rock"]
}

# Session‐state flags
st.session_state.setdefault("regenerate", False)
st.session_state.setdefault("last_emotion", None)
st.session_state.setdefault("last_playlist", None)
st.session_state.setdefault("gallery", [])

# Helper to detect emotion
def analyze_emotions(img_input):
    try:
        if isinstance(img_input, tuple):
            img_input = img_input[0]
        if isinstance(img_input, (bytes, bytearray)):
            img_input = io.BytesIO(img_input)
        if not isinstance(img_input, Image.Image):
            image = Image.open(img_input)
        else:
            image = img_input
        image = image.convert("RGB")
        arr = np.asarray(image)

        res = DeepFace.analyze(
            arr,
            actions=["emotion"],
            detector_backend="retinaface",
            enforce_detection=False
        )
        data = res[0] if isinstance(res, list) else res
        emo = data.get("dominant_emotion", "Unknown").capitalize()
        conf = data["emotion"].get(data.get("dominant_emotion",""), 0) / 100
        return [{"emotion": emo, "confidence": conf}]
    except Exception as e:
        st.error(f"Emotion Detection Failed: {e}")
        return [{"emotion": "Unknown", "confidence": 0}]

# App header
st.markdown(
    """
    <div style='text-align: center;'>
      <h1 style='font-size:2.5rem; margin-bottom:0.25rem;'>📸 Moodify</h1>
      <p style='font-size:1.1rem; color:gray;'>
        Capture or upload a photo to detect emotion & get a playlist
      </p>
    </div>
    """,
    unsafe_allow_html=True
)

# Camera / Upload tabs
tab1, tab2 = st.tabs(["📷 Camera", "📁 Upload"])
image_data = tab1.camera_input("Start your camera") or tab2.file_uploader("Upload an image", type=["png","jpg","jpeg","gif"])

# When we have an image...
if image_data:
    # Show it
    img = Image.open(image_data) if not isinstance(image_data, tuple) else Image.open(image_data[0])
    st.image(img, caption="Analyzed Image", use_column_width=True)

    # Analyze
    st.info("Analyzing emotions... 🤔")
    emotions = analyze_emotions(image_data)

    # Display results
    st.markdown("---")
    st.subheader("🎭 Emotion Analysis Results")
    for r in emotions:
        e, c = r["emotion"], int(r["confidence"]*100)
        emoji_map = {
            "Happy":"😊","Sad":"😢","Angry":"😠",
            "Surprise":"😲","Neutral":"😐","Fear":"😨","Disgust":"🤢"
        }
        icon = emoji_map.get(e,"🤔")
        st.markdown(
            f"<div style='display:flex; align-items:center; padding:1rem; "
            f"border-radius:1rem; background:rgba(102,126,234,0.2);'>"
            f"<span style='font-size:2rem; margin-right:1rem;'>{icon}</span>"
            f"<div><strong style='font-size:1.5rem;'>{e}</strong><br>"
            f"<span style='font-size:1.2rem;'>{c}% confidence</span></div></div>",
            unsafe_allow_html=True
        )

    # Save to gallery
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    buf = io.BytesIO(); img.save(buf, format="JPEG")
    st.session_state.gallery.insert(0, {"image":buf.getvalue(),"emoji":icon,"timestamp":ts})

    # Remember emotion
    st.session_state.last_emotion = emotions[0]["emotion"]

    # 🎵 Playlist header
    st.markdown("### 🎵 Your Mood‑Based Playlist")

    # Fetch (or reuse) playlist
    playlist = st.session_state.last_playlist
    if st.session_state.regenerate or playlist is None:
        kw = emotion_to_genre.get(st.session_state.last_emotion, ["mood"])
        random.shuffle(kw)
        playlist = None
        for i in range(len(kw)):
            for j in range(i+1, len(kw)):
                q = f"{kw[i]} {kw[j]} playlist"
                res = sp.search(q=q, type="playlist", limit=5)
                items = res.get("playlists",{}).get("items",[])
                if items:
                    playlist = random.choice(items)
                    break
            if playlist: break
        st.session_state.last_playlist = playlist
        st.session_state.regenerate = False

    # Show embed or warning
    if playlist:
        name = playlist.get("name","Playlist")
        url  = playlist["external_urls"]["spotify"]
        eid  = playlist["id"]
        st.markdown(f"**[{name}]({url})**")
        st.components.v1.iframe(f"https://open.spotify.com/embed/playlist/{eid}", height=400)
    else:
        st.warning("No matching playlist found on Spotify.")

    # ←— Here’s your new button, at the **bottom** of the playlist block:
    if st.button("Regenerate Playlist"):
        st.session_state.regenerate = True
        st.experimental_rerun()

# Gallery
st.markdown("---")
st.header("🖼️ Saved Images")
if st.session_state.gallery:
    cols = st.columns(4)
    for idx, item in enumerate(st.session_state.gallery):
        c = cols[idx%4]
        c.image(item["image"], use_column_width=True)
        c.caption(f"{item['emoji']} {item['timestamp']}")
else:
    st.write("No images saved yet. Capture or upload to get started!")
