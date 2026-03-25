# =============================
# IMPORTS
# =============================
import sys
import socket
import time
import requests
import json
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import threading
import queue
from datetime import datetime

# =============================
# CONFIG
# =============================
OLLAMA_URL = "http://localhost:11434/api/generate"
WAKE_WORDS = ["hey jd", "hey j d", "hey jay dee", "hello jd", "hello j d", "hello jay dee"]

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
    if any(w in text for w in ["good job", "great", "awesome", "nice"]):
        return "happy"
    elif any(w in text for w in ["bad", "useless", "stupid"]):
        return "angry"
    elif any(w in text for w in ["wow", "amazing"]):
        return "excited"
    elif any(w in text for w in ["sad", "sorry"]):
        return "sad"
    return "neutral"

def express_emotion(emotion):
    global current_emotion
    current_emotion = emotion

    if emotion == "happy":
     try:
      happy()
     except:
        print("⚠️ FAILED")
        time.sleep(0.3)
        
    elif emotion == "angry":    
        try:
          angry()
        except:
          print("⚠️ FAILED")
          time.sleep(0.3)
    elif emotion == "excited":
        try:
         exciting()
        except:
          print("⚠️ FAILED")
          time.sleep(0.3)
    elif emotion == "sad":
        try:
          sad()
          standup()
        except:
          print("⚠️ FAILED")
          time.sleep(0.3)
    else:
        send("Servo(D0,90)")
        send("Servo(D1,90)")

# =============================
# 🗣️ SPEAK
# =============================
def speak(text):
    text = text.replace('"', "'")[:120]
    send(f'SayEZB("{text}")')
    print("🤖:", text)
    time.sleep(len(text)/12 + 0.5)

# =============================
# 🤖 BOW
# =============================
def bow():
    send('ControlCommand("Auto Position", "AutoPositionAction", "Bow")')

def happy():
    send('ControlCommand("Auto Position", "AutoPositionAction", "Disco Dance")')
    # Stop dancing after 5 seconds and return to standing pose without blocking the assistant
    threading.Timer(5.0, standup).start()

def angry():
    send('ControlCommand("Auto Position", "AutoPositionAction", "Thinking")')

def standup():
    send('ControlCommand("Auto Position", "AutoPositionAction", "Bow")')

def sad():
    send('ControlCommand("Auto Position", "AutoPositionAction", "Head Bob")')
    threading.Timer(5.0, standup).start()

def exciting():
    send('ControlCommand("Auto Position", "AutoPositionAction", "Wave")')
    threading.Timer(5.0, standup).start()

def forward():
    print("⬆️ Moving forward")
    send("Forward()")

def backward():
    print("⬇️ Moving backward")
    send("Reverse()")   # ARC uses Reverse()

def stop():
    print("⏹️ Stopping")
    send("Stop()")

def tell_time():
    now = datetime.now()
    current_time = now.strftime("%I:%M %p")
    speak(f"The current time is {current_time}")

def get_weather():
    api_key = "220212f22c164c70921191547251709"
    city = "Dehradun"
    url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={city}&aqi=no"

    try:
        res = requests.get(url)
        data = res.json()

        if "current" in data:
            temp = data["current"]["temp_c"]
            condition = data["current"]["condition"]["text"]
            speak(f"The current temperature in Dehradun is {temp} degree Celsius")
            speak(f"The weather is {condition}")
        else:
            speak("Weather API error")

    except Exception as e:
        print(f"Weather error: {e}")
        speak("Unable to fetch weather data")
# =============================
# 🤖 LLM
# =============================
def ask_llm(prompt):
    try:
        res = requests.post(OLLAMA_URL, json={
            "model": "phi3",
            "prompt": f"Answer in 1 short sentence: {prompt}",
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

def listen(duration=8):
    recognizer.Reset()   # Clear stale state from previous listen session
    text_result = ""

    def callback(indata, frames, time_info, status):
        nonlocal text_result
        if recognizer.AcceptWaveform(bytes(indata)):
            result = json.loads(recognizer.Result())
            text = result.get("text", "")
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
        while True:
            if duration is not None and (time.time() - start) >= duration:
                break
            try:
                return input_queue.get_nowait()
            except queue.Empty:
                if text_result:
                    break
                time.sleep(0.1)

    result = json.loads(recognizer.FinalResult())
    text = result.get("text", "")
    if text:
         text_result += " " + text

    return text_result.strip()

# =============================
# 💤 SLEEP MODE
# =============================
def sleep_mode():
    print("💤 Entering sleep mode...")
    speak("Going to sleep. Say Hey JD to wake me up")

    while True:
        text = listen(None).lower()
        if any(w in text for w in WAKE_WORDS):
            print("👀 Wake word detected!")
            speak("Yes, I am back")
            return

# =============================
# 🚀 START
# =============================
print("🚀 JD AI STARTED")

try:
    bow()
except:
    print("⚠️ Bow failed")

speak("Hello I am JD Robot from Centre of Excellence Robotics Lab D I T University")

# =============================
# MAIN LOOP
# =============================
try:
    while True:
        print("🎤 Listening...")
        user = listen(8)

        if not user:
            sleep_mode()
            continue

        print("💬:", user)
        u = user.lower()

        # Emotion
        emotion = detect_emotion(user)
        express_emotion(emotion)

        # =============================
        # CUSTOM COMMANDS
        # =============================
        if "introduce us" in u or "introduce team" in u:
          speak("We are Abeer, Pushpendra, Pankaj, and Doctor Himani Sharma, and I am JD Robot, your intelligent robotic assistant")

        elif "time" in u:
            tell_time()

        elif "temperature" in u or "weather" in u:
            get_weather()
            try:
                happy()
            except:
                print("⚠️ FAILED")
                time.sleep(0.3)


        elif "introduce yourself" in u:
            speak("I am JD Bare Robot from D I T University")

        elif "introduce faculty" in u or "faculty" in u:
            speak("")

        elif "dean" in u or "introduce dean" in u or "we have dean with us" in u or "aberdeen" in u or "we have been with us" in u or "Do you who is our dean" in u or "Do you who is our been" in u or "introduce been" in u or "iodine" in u:
            try:
                bow()
            except:
                print("⚠️ Bow failed")
            speak("our Doctor Debopam Acharya is Professor and Dean of School of Computing at D I T University")

        elif "D I T University" in u or "DIT University" in u or "DIT" in u or "D I T" in u:
            speak("DIT University is a private university in Dehradun, Uttarakhand, India. D I T University has been accorded by the N A A C GRADE A.")

        elif "move forward" in u or "go forward" in u:
            speak("Moving forward")
            forward()
            time.sleep(5)
            stop()

        elif "move backward" in u or "go back" in u:
            speak("Moving backward")
            backward()
            time.sleep(5)
            stop()
        # =============================
        # AI RESPONSE
        # =============================
        else:
            reply = ask_llm(user)
            speak(reply)

        time.sleep(1)

except KeyboardInterrupt:
    print("Stopped manually")

client.close()