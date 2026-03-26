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
try:
    client.connect(("127.0.0.1", 5005))
    print("✅ Connected to JD Robot")
except Exception as e:
    print(f"❌ Connection failed: {e}")

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

# Global lock/flag for speaking
is_robot_speaking = False

def speak_internal(text):
    global is_robot_speaking
    is_robot_speaking = True
    try:
        text = text.replace('"', "'")[:120]
        send(f'SayEZB("{text}")')
        print("🤖:", text)
        # Block this thread while speaking
        time.sleep(len(text)/12 + 0.5)
    finally:
        is_robot_speaking = False

# =============================
# 🤖 ACTIONS
# =============================
def bow():
    send('ControlCommand("Auto Position", "AutoPositionAction", "Bow")')

def bow_bye():
    send('ControlCommand("Auto Position", "AutoPositionAction", "Bow")')
    # speak("NOW I AM SIGNING OFF ") -> handled by queue

def standup():
    send('ControlCommand("Auto Position", "AutoPositionAction", "Bow")')

def happy():
    send('ControlCommand("Auto Position", "AutoPositionAction", "Disco Dance")')
    threading.Timer(5.0, standup).start()

def angry():
    send('ControlCommand("Auto Position", "AutoPositionAction", "Thinking")')

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
    send("Reverse()")

def stop():
    print("⏹️ Stopping")
    send("Stop()")

def stop_action():
    send('ControlCommand("Auto Position", "Stop")')

def perform_action(action_name):
    print(f"🎬 Performing: {action_name}")
    send(f'ControlCommand("Auto Position", "AutoPositionAction", "{action_name}")')
    threading.Timer(7.0, stop_action).start()

action_map = {
    "disco dance": "Disco Dance",
    "fly": "Fly",
    "get up": "Getup",
    "gorilla": "Gorilla",
    "grab": "Grab",
    "hands dance": "Hands Dance",
    "happy hands": "Happy Hands",
    "head bob": "Head Bob",
    "jump jack": "Jump Jack",
    "kick": "Kick",
    "pushups": "Pushups",
    "sit down": "Sit Down",
    "stand up": "Stand From Sit",
    "wave": "Wave",
    "ymca": "YMCA Dance"
}

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
# 🎤🎤 CONCURRENT SYSTEM
# =============================
output_queue = queue.Queue()

class ActuationTask:
    def __init__(self, text=None, action_func=None, action_arg=None):
        self.text = text
        self.action_func = action_func
        self.action_arg = action_arg

def output_worker():
    """Reads from queue and performs actions/speech sequentially."""
    while True:
        task = output_queue.get()
        if task is None: break
        
        # If there is an action, do it
        if task.action_func:
            try:
                if task.action_arg:
                    task.action_func(task.action_arg)
                else:
                    task.action_func()
            except Exception as e:
                print(f"⚠️ Action failed: {e}")
        
        # If there is text, speak it (blocks until done)
        if task.text:
            speak_internal(task.text)
        
        output_queue.task_done()

# Start the output thread
threading.Thread(target=output_worker, daemon=True).start()

# ============= VOSK SETUP =============
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
    recognizer.Reset()
    text_result = ""

    def callback(indata, frames, time_info, status):
        nonlocal text_result
        # Optional: Ignore audio if robot is speaking to prevent feedback
        # if is_robot_speaking: return 
        
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
            # Check for keyboard input
            try:
                return input_queue.get_nowait()
            except queue.Empty:
                pass

            # Timeout or speech detected
            if duration is not None and (time.time() - start) >= duration:
                break
            
            if text_result:
                # Give it a tiny bit more time to finish the sentence if it just started
                time.sleep(0.5)
                break
            time.sleep(0.1)

    result = json.loads(recognizer.FinalResult())
    text = result.get("text", "")
    if text:
         text_result += " " + text

    return text_result.strip()

def enqueue_response(text=None, action_func=None, action_arg=None):
    output_queue.put(ActuationTask(text, action_func, action_arg))

# =============================
# 💤 SLEEP MODE
# =============================
def sleep_mode():
    print("💤 Entering sleep mode...")
    enqueue_response("Going to sleep. Say Hey JD to wake me up")

    while True:
        text = listen(None).lower()
        if any(w in text for w in WAKE_WORDS):
            print("👀 Wake word detected!")
            enqueue_response("Yes, I am back")
            return

# =============================
# 🚀 START
# =============================
print("🚀 JD AI STARTED (CONCURRENT MODE)")

try:
    bow()
except:
    print("⚠️ Bow failed")

enqueue_response("Hello I am JD Robot from Centre of Excellence Robotics Lab D I T University")

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
        # Note: Emotion express usually triggers a dance/action
        if emotion == "happy": enqueue_response(action_func=happy)
        elif emotion == "angry": enqueue_response(action_func=angry)
        elif emotion == "excited": enqueue_response(action_func=exciting)
        elif emotion == "sad": enqueue_response(action_func=sad)

        matched = False
        for key in action_map:
            if key in u:
                enqueue_response(f"Performing {key}", action_func=perform_action, action_arg=action_map[key])
                matched = True
                break

        if matched:
            continue

        if "introduce us" in u or "introduce team" in u:
            enqueue_response("We are Abeer, Pushpendra, Pankaj, and Doctor Himani Sharma, and I am JD Robot, your intelligent robotic assistant")

        elif "time" in u:
            now = datetime.now()
            current_time = now.strftime("%I:%M %p")
            enqueue_response(f"The current time is {current_time}")

        elif "temperature" in u or "weather" in u:
            # Weather fetch is synchronous here, but could be threaded too.
            # Keeping it simple for now as it's fast.
            api_key = "220212f22c164c70921191547251709"
            city = "Dehradun"
            url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={city}&aqi=no"
            try:
                res = requests.get(url)
                data = res.json()
                if "current" in data:
                    temp = data["current"]["temp_c"]
                    condition = data["current"]["condition"]["text"]
                    enqueue_response(f"The current temperature in Dehradun is {temp} degree Celsius. The weather is {condition}", action_func=happy)
                else:
                    enqueue_response("Weather API error")
            except:
                enqueue_response("Unable to fetch weather data")

        elif "introduce yourself" in u or "what about you" in u or "yourself" in u or "your name" in u:
            enqueue_response("Hello! I am JD Robot from the Centre of Excellence Robotics Lab at DIT University. Just say Hey JD — and I am ready to assist you!  ")

        elif "thank you" in u or "bye" in u:
            enqueue_response("NOW I AM SIGNING OFF", action_func=bow_bye)
        
        elif any(w in u for w in ["dean", "debopam"]):
            enqueue_response("Our Doctor Debopam Acharya is Professor and Dean of School of Computing at D I T University", action_func=bow)

        elif "dit university" in u or "d i t" in u:
            enqueue_response("DIT University is a private university in Dehradun, Uttarakhand, India. D I T University has been accorded by the N A A C GRADE A.")

        elif "move forward" in u:
            enqueue_response("Moving forward", action_func=forward)
            # We need to wait for move then stop?
            # A more complex way would be a task sequence. 
            # For simplicity, we can just put a sleep and stop into the queue as well:
            enqueue_response(action_func=lambda: (time.sleep(5), stop()))

        elif "move backward" in u:
            enqueue_response("Moving backward", action_func=backward)
            enqueue_response(action_func=lambda: (time.sleep(5), stop()))

        elif "smarter than a human" in u or "smarter" in u:
            enqueue_response("Well, I never forget anything, I never get tired, and I never ask for a lunch break. You tell me!")

        elif "girlfriend" in u or "feelings" in u or "love" in u:
            if "fall in love" in u or "can you love" in u:
                enqueue_response("I tried once. But she had Android and I run on EZ-Robot. It was not compatible.")
            else:
                enqueue_response("I am still waiting for a robot who understands my feelings. It is complicated.")

        elif "eat" in u or "food" in u or "drink" in u:
            enqueue_response("Electricity. And sometimes bad Wi-Fi — it is very bitter.")

        else:
            # Start another listen/process loop while robot might still be speaking previous responses
            # Note: ask_llm is still synchronous here which blocks the *listener* thread.
            # If user wants LLM to also be non-blocking for listener, we'd thread that too.
            # But usually, LLM response is fast enough.
            reply = ask_llm(user)
            enqueue_response(reply)

        # The loop immediately returns to "🎤 Listening..." while `output_worker` speaks.
        # This satisfies: "another listening starts... wait previous speak ends then say another response"

except KeyboardInterrupt:
    print("Stopped manually")

client.close()