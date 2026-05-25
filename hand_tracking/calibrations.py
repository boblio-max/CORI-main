import cv2
import mediapipe as mp
import math

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.5)
cap = cv2.VideoCapture(0)

print("--- DIAGNOSTIC MODE ---")
print("1. Push your hand as FAR BACK as you realistically want to control the robot.")
print("2. Pull your hand as CLOSE to the webcam as you realistically want to go.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            # Extract wrist (0) and middle knuckle (9)
            wrist = hand_landmarks.landmark[0]
            knuckle = hand_landmarks.landmark[9]
            
            # Convert normalized coordinates to pixel coordinates
            w_x, w_y = int(wrist.x * w), int(wrist.y * h)
            k_x, k_y = int(knuckle.x * w), int(knuckle.y * h)
            
            # Calculate pixel distance (Our Z-axis proxy)
            palm_pixel_distance = math.sqrt((w_x - k_x)**2 + (w_y - k_y)**2)
            
            # Print to console and display on screen
            print(f"Current Palm Pixel Distance: {palm_pixel_distance:.1f}")
            cv2.line(frame, (w_x, w_y), (k_x, k_y), (0, 0, 255), 3)
            cv2.putText(frame, f"Z-Value: {int(palm_pixel_distance)}", (50, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.imshow("Z-Axis Finder", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()