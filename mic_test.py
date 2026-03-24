import socket
import queue
import sounddevice as sd
import json
from vosk import Model, KaldiRecognizer

# =============================
# CONNECT TO JD ROBOT
# =============================
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("127.0.0.1", 5005))

print("✅ Connected to JD Robot")

def send(cmd):
    client.send((cmd + "\n").encode())

def speak(text):
    text = text.replace('"', "'")[:120]
    send(f'SayEZB("{text}")')
    print("🤖:", text)

# =============================
# LOAD VOSK MODEL
# =============================
model = Model(r"D:\JD\model\vosk-model-small-en-us-0.15\vosk-model-small-en-us-0.15")   # 👈 your path
recognizer = KaldiRecognizer(model, 16000)

q = queue.Queue()

# =============================
# AUDIO CALLBACK
# =============================
def callback(indata, frames, time, status):
    q.put(bytes(indata))

# =============================
# START MIC
# =============================
print("🎤 Offline Mic Ready (VOSK)")
print("🗣️ Speak now...")

with sd.RawInputStream(samplerate=16000, blocksize=8000,
                       dtype='int16', channels=1, callback=callback):

    while True:
        data = q.get()

        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            text = result.get("text", "").strip()

            if text:
                print(f"\n🗣️ You said: {text}")   # ✅ TERMINAL OUTPUT

                if text.lower() in ["exit", "stop"]:
                    speak("Stopping mic system")
                    break

                speak(text)   # repeat on robot