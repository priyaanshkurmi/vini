import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np
import httpx
import io
import tempfile
import os

SAMPLE_RATE = 16000
DURATION    = 5


def record() -> bytes:
    print("Speak now (5 seconds)...")
    audio = sd.rec(
        int(DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
    )
    sd.wait()
    print("Done recording.")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav.write(f.name, SAMPLE_RATE, audio)
        with open(f.name, "rb") as wf:
            return wf.read(), f.name


def play(audio_bytes: bytes):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        tmp = f.name
    os.system(f"afplay {tmp}")
    os.unlink(tmp)


if __name__ == "__main__":
    audio_bytes, tmp_path = record()

    print("Sending to Vini...")
    with httpx.Client(timeout=30) as client:
        response = client.post(
            "http://localhost:8000/voice",
            files={"audio": ("voice.wav", audio_bytes, "audio/wav")},
        )

    os.unlink(tmp_path)

    if response.status_code == 200 and len(response.content) > 0:
        print("Playing Vini's response...")
        play(response.content)
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
