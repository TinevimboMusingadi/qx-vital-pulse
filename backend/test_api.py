# test_api.py
import httpx
import sys
import wave
import time

# Generate a dummy 1-second 16kHz mono audio file
def create_dummy_wav(filename):
    with wave.open(filename, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(b'\x00\x00' * 16000)

create_dummy_wav('dummy_audio.wav')

url = "http://127.0.0.1:8000/predict"
print("Sending mock data to /predict...")

max_retries = 10
for i in range(max_retries):
    try:
        with open('dummy_audio.wav', 'rb') as f:
            response = httpx.post(
                url,
                data={
                    "age": 45,
                    "gender": "male",
                    "symptoms": "cough, fever"
                },
                files={"audio": ("dummy_audio.wav", f, "audio/wav")}
            )
            
        print(f"Status Code: {response.status_code}")
        print("Response JSON:")
        print(response.json())
        break
    except httpx.ConnectError:
        print(f"Failed to connect (attempt {i+1}/{max_retries}). Server might still be downloading model weights...")
        time.sleep(5)

