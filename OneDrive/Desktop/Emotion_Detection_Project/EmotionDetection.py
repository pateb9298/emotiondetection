import cv2
import time
from deepface import DeepFace

def analyze_image(image_path):
    try:
        img = cv2.imread(image_path)

        if img is None:
            raise ValueError("Image could not be read. Double-check the path.")

        print("✅ Image loaded. Running DeepFace analysis...")

        result = DeepFace.analyze(img, actions=["emotion", "age", "gender"], enforce_detection=False)

        if isinstance(result, list) and len(result) > 0:
            data = result[0]
        elif isinstance(result, dict):
            data = result
        else:
            raise ValueError("Unexpected result format from DeepFace.")

        emotion = data.get("dominant_emotion", "unknown")
        age = data.get("age", "unknown")
        gender_data = data.get("gender", {})
        if isinstance(gender_data, dict):
            gender = max(gender_data, key=gender_data.get)
        else:
            gender = gender_data

        print(f"\n✅ Analysis Complete:")
        print(f"Emotion: {emotion}")
        print(f"Age: {age}")
        print(f"Gender: {gender}")

        # Overlay text
        cv2.putText(img, f'Emotion: {emotion}', (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
        cv2.putText(img, f'Age: {age}', (50, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
        cv2.putText(img, f'Gender: {gender}', (50, 130),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 255), 2)

        # Display image
        print("📷 Displaying image. Press any key in the window to exit.")
        cv2.imshow("Emotion Detection - Image", img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    except Exception as e:
        print("❌ Error analyzing image:", e)


def analyze_webcam():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Error: Cannot open camera")
        return

    start_time = time.time()
    last_emotion = "unknown"

    print("🎥 Showing webcam for 5 seconds...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        try:
            result = DeepFace.analyze(frame, actions=["emotion"], enforce_detection=False)
            if isinstance(result, list):
                dominant_emotion = result[0].get("dominant_emotion", "unknown")
            else:
                dominant_emotion = result.get("dominant_emotion", "unknown")
            print(f'Emotion: {dominant_emotion}')
            cv2.putText(frame, f'Emotion: {dominant_emotion}', (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
        except Exception as e:
            cv2.putText(frame, 'No emotion detected', (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)

        cv2.imshow("Real-time Emotion Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        if time.time() - start_time > 5:  # Stop after 5 seconds
            break
        

    cap.release()
    cv2.destroyAllWindows()



# ----------- USER OPTION -----------
if __name__ == "__main__":
    print("Select mode:\n1. Webcam\n2. Upload image")
    choice = input("Enter 1 or 2: ")

    if choice == "1":
        analyze_webcam()
    elif choice == "2":
        image_path = input("Enter path to the image file: ")
        analyze_image(image_path)
    else:
        print("Invalid choice.")
