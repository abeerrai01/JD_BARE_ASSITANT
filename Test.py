import google.generativeai as genai

genai.configure(api_key="AIzaSyD0Rsl6bpyDBBMUVXUQn4LrrgKLpv2ecsQ")

models = genai.list_models()

for m in models:
    print(m.name)