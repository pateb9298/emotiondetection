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

# --- VERY TOP: inject CSS for round buttons ---
st.markdown(
    """
    <style>
    /* Make every st.button circular */
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

# Initialize Spotify client
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET")
))

# Emotion → keywords map
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
if "regenerate" not in st.session_state:
    st.session_state.regenerate = False
if "last_emotion" not in st.session_state:
    st.session_state.last_emotion = None
if "last_playlist" not in st.session_state:
    st.session_state.last_playlist = None

# Helper: emotion analysis
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

# App config
st.set_page_config(page_title="Moodify", page_icon="📸", layout="centered")
if "gallery" not in st.session_state:
    st.session_state.gallery = []

# Header
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

# Tabs for camera/upload
tab1, tab2 = st.tabs(["📷 Camera", "📁 Upload"])
image_data = tab1.camera_input("Start your camera") or tab2.file_uploader("Upload an image", type=["png","jpg","jpeg","gif"])

# Process image
if image_data:
    img = Image.open(image_data) if not isinstance(image_data, tuple) else Image.open(image_data[0])
    st.image(img, caption="Analyzed Image", use_column_width=True)

    st.info("Analyzing emotions... 🤔")
    emotions = analyze_emotions(image_data)

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

    # Snapshot to gallery
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    buf = io.BytesIO(); img.save(buf, format="JPEG")
    st.session_state.gallery.insert(0, {"image":buf.getvalue(),"emoji":icon,"timestamp":ts})

    # Remember emotion
    st.session_state.last_emotion = emotions[0]["emotion"]

    # 🎵 Playlist header + circular reload button
    col1, col2 = st.columns([9,1])
    with col1:
        st.markdown("### 🎵 Your Mood‑Based Playlist")
    with col2:
        if st.button("↻", key="reload"):
            st.session_state.regenerate = True

    # Fetch or reuse playlist
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

    # Display
    if playlist:
        name = playlist.get("name","Playlist")
        url  = playlist["external_urls"]["spotify"]
        eid  = playlist["id"]
        st.markdown(f"**[{name}]({url})**")
        st.components.v1.iframe(f"https://open.spotify.com/embed/playlist/{eid}", height=400)
    else:
        st.warning("No matching playlist found on Spotify.")

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


# # importing necessary libraries
# import streamlit as st
# from PIL import Image
# import io
# from datetime import datetime
# from deepface import DeepFace
# import numpy as np
# import os
# from spotipy.oauth2 import SpotifyClientCredentials
# import spotipy
# import random

# # Initialize Spotify API client
# sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
#     client_id=os.getenv("SPOTIPY_CLIENT_ID"),
#     client_secret=os.getenv("SPOTIPY_CLIENT_SECRET")
# ))

# # Emotion to playlist genre map

# emotion_to_genre = {
#     "Happy": ["happy", "pop", "feel good", "upbeat", "party"],
#     "Sad": ["Sad Songs"],
#     "Angry": ["metal", "hard rock", "punk", "rock", "alternative"],
#     "Surprised": ["electronic", "dance", "edm", "house", "party"],
#     "Neutral": ["lofi", "chill", "study", "relax", "ambient"],
#     "Fear": ["ambient", "calm", "meditation", "relax", "instrumental"],
#     "Disgust": ["punk", "grunge", "alternative", "hard rock", "garage rock"]
# }


# # emotion_to_genre = {
# #     "Happy": "pop",
# #     "Sad": "acoustic",
# #     "Angry": "metal",
# #     "Surprised": "electronic",
# #     "Neutral": "chill",
# #     "Fear": "ambient",
# #     "Disgust": "punk"
# # }

# # ---- Helper Functions ----
# def analyze_emotions(image):
#     try:
#         img_array = np.array(image)
#         result = DeepFace.analyze(img_array, actions=["emotion"], enforce_detection=False)

#         data = result[0] if isinstance(result, list) else result
#         dominant_emotion = data.get("dominant_emotion", "Unknown")
#         confidence = data["emotion"].get(dominant_emotion, 0)

#         return [{
#             "emotion": dominant_emotion.capitalize(),
#             "confidence": confidence / 100
#         }]
    
#     except Exception as e:
#         st.error(f"Emotion Detection Failed: {e}")
#         return [{
#             "emotion": "Unknown",
#             "confidence": 0
#         }]

# # ---- App Initialization ----
# st.set_page_config(
#     page_title="Emotion Detection Camera",
#     page_icon="📸",
#     layout="centered"
# )

# if "gallery" not in st.session_state:
#     st.session_state.gallery = []

# # ---- Header ----
# st.markdown(
#     """
#     <div style='text-align: center;'>
#         <h1 style='font-size:2.5rem; margin-bottom:0.25rem;'>📸 Emotion Detection</h1>
#         <p style='font-size:1.1rem; color: gray;'>Capture or upload a photo to analyze emotions</p>
#     </div>
#     """,
#     unsafe_allow_html=True
# )

# # ---- Tabs for Camera or Upload ----
# tab1, tab2 = st.tabs(["📷 Camera Capture", "📁 Upload Photo"])

# image_data = None
# with tab1:
#     image_data = st.camera_input("Start your camera")

# with tab2:
#     uploaded = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg", "gif"])
#     if uploaded:
#         image_data = uploaded

# # ---- Process Image ----
# if image_data:
#     image = Image.open(image_data)
#     st.image(image, caption="Analyzed Image", use_column_width=True)

#     st.info("Analyzing emotions... 🤔")
#     emotions = analyze_emotions(image)

#     st.markdown("---")
#     st.subheader("🎭 Emotion Analysis Results")
#     for result in emotions:
#         emo = result['emotion']
#         conf = int(result['confidence'] * 100)
#         emoji_map = {
#             'Happy': '😊',
#             'Sad': '😢',
#             'Angry': '😠',
#             'Surprised': '😲',
#             'Neutral': '😐',
#             'Fear': '😨',
#             'Disgust': '🤢'
#         }
#         emoji = emoji_map.get(emo, '🤔')
#         st.markdown(
#             f"<div style='display: flex; align-items: center; padding: 1rem; "
#             f"border-radius: 1rem; background: rgba(102, 126, 234, 0.2);'>"
#             f"<span style='font-size:2rem; margin-right:1rem;'>{emoji}</span>"
#             f"<div><strong style='font-size:1.5rem;'>{emo}</strong><br/>"
#             f"<span style='font-size:1.2rem;'>{conf}% confidence</span></div></div>",
#             unsafe_allow_html=True
#         )

#     # Save image to gallery
#     timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     buf = io.BytesIO()
#     image.save(buf, format="JPEG")
#     img_bytes = buf.getvalue()
#     st.session_state.gallery.insert(0, {
#         'image': img_bytes,
#         'emoji': emoji,
#         'timestamp': timestamp
#     })

#     # 🎵 Spotify Playlist Section
#     detected_emotion = emotions[0]["emotion"]
#     # genre = emotion_to_genre.get(detected_emotion, "mood")
#     # results = sp.search(q=f"{genre} playlist", type="playlist", limit=1)

#     keywords = emotion_to_genre.get(detected_emotion, ["mood"])
#     # Shuffle and join two keywords randomly for better search results
#     random.shuffle(keywords)
#     query = " ".join(keywords[:2]) + " playlist"  # Use top 2 random keywords

#     # Search Spotify with more expressive query and multiple results
#     results = sp.search(q=query, type="playlist", limit=5)

#     st.markdown("---")
#     st.subheader("🎵 Your Mood-Based Playlist")

#     if results["playlists"]["items"]:
#         # playlist = results["playlists"]["items"][0]
#         playlist = random.choice(results["playlists"]["items"])
#         playlist_name = playlist["name"]
#         playlist_url = playlist["external_urls"]["spotify"]
#         playlist_embed_url = f"https://open.spotify.com/embed/playlist/{playlist['id']}"

#         st.markdown(f"**[{playlist_name}]({playlist_url})**")
#         st.components.v1.iframe(src = playlist_embed_url, height=400)
#     else:
#         st.warning("No matching playlist found on Spotify.")

# # ---- Gallery Section ----
# st.markdown("---")
# st.header("🖼️ Saved Images")
# if st.session_state.gallery:
#     cols = st.columns(4)
#     for idx, item in enumerate(st.session_state.gallery):
#         col = cols[idx % 4]
#         col.image(item['image'], use_column_width=True)
#         col.caption(f"{item['emoji']} {item['timestamp']}")
# else:
#     st.write("No images saved yet. Capture or upload to get started!")
