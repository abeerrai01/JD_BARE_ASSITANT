import cv2
import socket
import time

# =========================
# CONFIG
# =========================
ARC_IP = "127.0.0.1"
ARC_PORT = 5005

CAMERA_URL = "http://192.168.1.24:8080/?action=stream"

# =========================
# CONNECT TO ARC
# =========================
def connect_arc():
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((ARC_IP, ARC_PORT))
        print("✅ Connected to ARC")
        return client
    except Exception as e:
        print("❌ ARC connection failed:", e)
        return None

# =========================
# SEND COMMAND TO ROBOT
# =========================
def send_to_robot(client, text, servo_pos):
    try:
        # Speech
        cmd1 = f'SayEZB("{text}")\n'
        client.send(cmd1.encode())

        # Servo (D0)
        cmd2 = f'Servo(D0,{servo_pos})\n'
        client.send(cmd2.encode())

        print(f"🤖 Sent → {text} | Servo: {servo_pos}")

    except Exception as e:
        print("❌ Send failed:", e)

# =========================
# MAIN SYSTEM
# =========================
def main():

    print("🚀 System Starting...")

    # Connect ARC
    client = connect_arc()
    if client is None:
        return

    # Open Camera
    cap = cv2.VideoCapture(CAMERA_URL)

    if not cap.isOpened():
        print("❌ Camera failed")
        return

    print("📷 Camera working")

    last_action_time = 0

    while True:
        ret, frame = cap.read()

        if not ret:
            print("⚠️ Frame error")
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Simple face detection
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        # =========================
        # DEBUG INFO
        # =========================
        print(f"👀 Faces detected: {len(faces)}")

        # Draw faces
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x,y), (x+w,y+h), (0,255,0), 2)

        # =========================
        # DECISION LOGIC
        # =========================
        current_time = time.time()

        if current_time - last_action_time > 3:

            if len(faces) > 0:
                send_to_robot(client, "Hello Abeer, I see you!", 90)
            else:
                send_to_robot(client, "I cannot see anyone", 40)

            last_action_time = current_time

        # =========================
        # DISPLAY
        # =========================
        cv2.imshow("JD Robot Vision", frame)

        # Exit on ESC
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    client.close()


# =========================
# RUN
# =========================
if __name__ == "__main__":
    main()