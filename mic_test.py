import os
from vosk import Model

model_path = r"D:\JD\model\vosk-model-small-en-us-0.15"

print("📂 Model contents:", os.listdir(model_path))

model = Model(model_path)

print("✅ Model loaded successfully!")