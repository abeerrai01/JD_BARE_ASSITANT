import sys
import socket
import time
import requests
import json
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import threading
import queue

# =============================
# CONFIG
# =============================
OLLAMA_URL = "http://localhost:11434/api/generate"

# =============================
# CONNECT TO JD ROBOT
# =============================
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("127.0.0.1", 5005))

print("✅ Connected to JD Robot")


def send(cmd):
    client.send((cmd + "\n").encode())


# =============================
# 🎭 EMOTION SYSTEM
# =============================
current_emotion = "neutral"


def detect_emotion(text):
    text = text.lower()

    if any(word in text for word in ["good job", "great", "awesome", "nice"]):
        return "happy"
    elif any(word in text for word in ["bad", "useless", "stupid", "worst"]):
        return "angry"
    elif any(word in text for word in ["wow", "amazing", "exciting"]):
        return "excited"
    elif any(word in text for word in ["sad", "sorry", "unhappy"]):
        return "sad"
    return "neutral"


def express_emotion(emotion):
    global current_emotion
    current_emotion = emotion

    if emotion == "happy":
        send("Servo(D1,60)")
        time.sleep(0.3)
        send("Servo(D1,120)")
        time.sleep(0.3)

    elif emotion == "angry":
        for _ in range(2):
            send("Servo(D1,70)")
            time.sleep(0.2)
            send("Servo(D1,110)")
            time.sleep(0.2)

    elif emotion == "excited":
        for _ in range(3):
            send("Servo(D0,70)")
            time.sleep(0.2)
            send("Servo(D0,110)")
            time.sleep(0.2)

    elif emotion == "sad":
        send("Servo(D0,130)")
        time.sleep(0.5)

    else:
        send("Servo(D0,90)")
        send("Servo(D1,90)")


# =============================
# 🗣️ SPEAK WITH EMOTION
# =============================
def speak(text):
    global current_emotion

    text = text.replace('"', "'")[:120]

    if current_emotion == "happy":
        delay = len(text) / 14
    elif current_emotion == "excited":
        delay = len(text) / 16
    elif current_emotion == "sad":
        delay = len(text) / 10
    else:
        delay = len(text) / 12

    send(f'SayEZB("{text}")')
    print("🤖:", text)

    time.sleep(delay + 0.5)


# =============================
# SERVO + MOVEMENT
# =============================
def move_head_lr(pos):
    send(f"Servo(D1,{int(pos)})")


def move_head_ud(pos):
    send(f"Servo(D0,{int(pos)})")


def forward():
    send("Forward()")


def stop():
    send("Stop()")


# =============================
# 🤖 BOW
# =============================
def bow():
    move_head_ud(120)
    time.sleep(0.5)
    move_head_ud(60)
    time.sleep(0.5)
    move_head_ud(90)


# =============================
# ✍️ DRAW SHAPES
# =============================
def draw_shape(shape):
    speak(f"I am drawing a {shape}")

    send("ServoSpeed(D7, 3)")
    send("ServoSpeed(D8, 3)")

    send("Servo(D0, 130)")
    send("Servo(D1, 90)")

    send("Servo(D9, 150)")
    time.sleep(3)

    send("Servo(D7, 120)")
    send("Servo(D8, 100)")
    time.sleep(2)

    if shape == "square":
        for _ in range(4):
            forward()
            time.sleep(2)
            stop()
            send("Right()")
            time.sleep(1.5)
            stop()

    elif shape == "rectangle":
        for _ in range(2):
            forward()
            time.sleep(3)
            stop()
            send("Right()")
            time.sleep(1.5)
            stop()

            forward()
            time.sleep(1.5)
            stop()
            send("Right()")
            time.sleep(1.5)
            stop()

    elif shape == "triangle":
        for _ in range(3):
            forward()
            time.sleep(2)
            stop()
            send("Right()")
            time.sleep(2)
            stop()

    else:  # house
        for _ in range(4):
            forward()
            time.sleep(2)
            stop()
            send("Right()")
            time.sleep(1.5)
            stop()

    send("Servo(D7, 90)")
    send("Servo(D0, 90)")
    send("Servo(D9, 90)")

    speak(f"Finished drawing {shape}")


# =============================
# 🤖 LLM
# =============================
def ask_llm(prompt):
    try:
        prompt = f"Answer in 1 short sentence: {prompt}"

        res = requests.post(OLLAMA_URL, json={
            "model": "phi3",
            "prompt": prompt,
            "stream": False
        }, timeout=60)

        return res.json().get("response", "No answer")

    except:
        return "Brain not responding"


# =============================
# 🎤 INPUT SYSTEM
# =============================
model = Model(r"D:\JD\model\vosk-model-small-en-us-0.15\vosk-model-small-en-us-0.15")
recognizer = KaldiRecognizer(model, 16000)

input_queue = queue.Queue()


def keyboard_listener():
    while True:
        try:
            text = sys.stdin.readline().strip()
            if text:
                input_queue.put(text)
        except:
            break


threading.Thread(target=keyboard_listener, daemon=True).start()


def listen_or_keyboard(duration=5):
    print(f"🎤 Listening {duration}s...")

    text_result = ""
    keyboard_result = None

    def callback(indata, frames, time_info, status):
        nonlocal text_result
        if recognizer.AcceptWaveform(bytes(indata)):
            result = json.loads(recognizer.Result())
            text = result.get("text", "").strip()
            if text:
                text_result += " " + text

    with sd.RawInputStream(
            samplerate=16000,
            blocksize=8000,
            dtype='int16',
            channels=1,
            callback=callback
    ):
        start = time.time()
        while time.time() - start < duration:
            try:
                keyboard_result = input_queue.get_nowait()
                break
            except queue.Empty:
                time.sleep(0.1)

    return keyboard_result if keyboard_result else text_result.strip()


# =============================
# 🚀 START
# =============================
print("🚀 JD AI STARTED")

bow()
speak("Hello I am JD Robot from Centre of Excellence Robotics Lab DIT University")

# =============================
# MAIN LOOP
# =============================
try:
    while True:
        speak("Listening")
        user = listen_or_keyboard(5)

        if not user:
            speak("No input detected")
            continue

        print("💬:", user)
        u = user.lower()

        # 🎭 Emotion
        emotion = detect_emotion(user)
        express_emotion(emotion)

        # =============================
        # 🎤 CUSTOM COMMANDS
        # =============================
        if "introduce innovators" in u:
            speak("We are Abeer, Pushpendra, and Pankaj")

        elif "introduce yourself" in u:
            speak("I am JD Bare Robot from DIT University")

        elif "introduce faculty" in u:
            speak("our Doctor Himani Sharma is Assistant Professor at DIT University")

        elif "dean" in u:
            speak("our Doctor Debopam Acharya is Professor and Dean of School of Computing at DIT University")

        # =============================
        # 🎨 DRAW
        # =============================
        elif "draw square" in u:
            draw_shape("square")

        elif "draw rectangle" in u:
            draw_shape("rectangle")

        elif "draw triangle" in u:
            draw_shape("triangle")

        elif "draw house" in u:
            draw_shape("house")

        # =============================
        # 🤖 AI RESPONSE
        # =============================
        else:
            reply = ask_llm(user)
            speak(reply)

        time.sleep(1)

except KeyboardInterrupt:
    print("Stopped manually")

client.close()