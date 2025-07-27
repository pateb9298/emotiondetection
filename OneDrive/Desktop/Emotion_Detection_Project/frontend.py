# importing necessary libraries
import streamlit as st
# Pillow loads and processess images
from PIL import Image
import io
from datetime import datetime
from deepface import DeepFace
import numpy as np

# # ---- Helper Functions ----
def analyze_emotions(image):
    try:
        # converts the PIL image into a numpy array
        img_array = np.array(image)

        # runs deepface
        result = DeepFace.analyze(img_array, actions=["emotion"], enforce_detection=False)

        if isinstance(result, list):
            data = result[0]
        else:
            data = result

        dominant_emotion = data.get("dominant_emotion", "Unknown")
        confidence = data["emotion"].get(dominant_emotion, 0)

        return [{
            "emotion": dominant_emotion.capitalize(),
            "confidence": confidence/100
        }]
    
    except Exception as e:
        st.error(f"Emotion Detection Failed: {e}")
        return [{
            "emotion": "Unknown",
            "confidence": "0"
        }]
# ---- App Initialization ----

st.set_page_config(
    page_title="Emotion Detection Camera",
    page_icon="📸",
    layout="centered"
)

# Initialize session state for saved images
if "gallery" not in st.session_state:
    # st.session_state.gallery is like a memory for the app while it runs
    st.session_state.gallery = []

# ---- Header ----
st.markdown(
    """
    <div style='text-align: center;'>
        <h1 style='font-size:2.5rem; margin-bottom:0.25rem;'>📸
Emotion Detection</h1>
        <p style='font-size:1.1rem; color: gray;'>Capture or upload a
photo to analyze emotions</p>
    </div>
    """,
    unsafe_allow_html=True
)

# ---- Tabs for Camera or Upload ----
tab1, tab2 = st.tabs(["📷 Camera Capture", "📁 Upload Photo"])

image_data = None
with tab1:
    # opens webcam and returns a photo as soon as its taken
    image_data = st.camera_input("Start your camera")

with tab2:
    # allows for the user to uploaf an image
    uploaded = st.file_uploader("Upload an image", type=["png", "jpg",
"jpeg", "gif"])
    if uploaded:
        image_data = uploaded

# ---- Process Image ----
if image_data:
    # Display the chosen image
    image = Image.open(image_data)
    # shows it on the page
    st.image(image, caption="Analyzed Image", use_column_width=True)

    # Analyze emotion (demo)
    st.info("Analyzing emotions... 🤔")
    emotions = analyze_emotions(image)

    # Display results
    st.markdown("---")
    st.subheader("🎭 Emotion Analysis Results")
    for result in emotions:
        emo = result['emotion']
        conf = int(result['confidence'] * 100)
        emoji_map = {
            'Happy': '😊',
            'Sad': '😢',
            'Angry': '😠',
            'Surprised': '😲',
            'Neutral': '😐',
            'Fear': '😨',
            'Disgust': '🤢'
        }
        emoji = emoji_map.get(emo, '🤔')
        st.markdown(
            f"<div style='display: flex; align-items: center; padding: 1rem; "
            f"border-radius: 1rem; background: rgba(102, 126, 234, 0.2);'>"
            f"<span style='font-size:2rem; margin-right:1rem;'>{emoji}</span>"
            f"<div><strong style='font-size:1.5rem;'>{emo}</strong><br/>"
            f"<span style='font-size:1.2rem;'>{conf}%confidence</span></div></div>",
            unsafe_allow_html=True
        )

    # Save to gallery
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    buf = io.BytesIO()
    image.save(buf, format="JPEG")
    img_bytes = buf.getvalue()
    st.session_state.gallery.insert(0, {
        'image': img_bytes,
        'emoji': emoji,
        'timestamp': timestamp
    })

# ---- Gallery Section ----
st.markdown("---")
st.header("🖼️ Saved Images")
if st.session_state.gallery:
    cols = st.columns(4)
    for idx, item in enumerate(st.session_state.gallery):
        col = cols[idx % 4]
        col.image(item['image'], use_column_width=True)
        col.caption(f"{item['emoji']} {item['timestamp']}")
else:
    st.write("No images saved yet. Capture or upload to get started!")