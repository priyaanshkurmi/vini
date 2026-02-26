import os
import tempfile
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import whisper

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

# Load once on import — takes ~5 seconds first time
print("Loading Whisper model...")
_model = whisper.load_model(WHISPER_MODEL)
print("Whisper ready.")


def record_audio(duration: int = 5, sample_rate: int = 16000) -> np.ndarray:
    """Record audio from microphone for given duration in seconds."""
    print(f"Recording for {duration} seconds...")
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
    )
    sd.wait()
    print("Recording done.")
    return audio.flatten()


def transcribe(audio: np.ndarray, sample_rate: int = 16000) -> str:
    """Transcribe numpy audio array to text using Whisper."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name

    try:
        # Convert float32 to int16 for wav file
        audio_int16 = (audio * 32767).astype(np.int16)
        wav.write(tmp_path, sample_rate, audio_int16)
        result = _model.transcribe(tmp_path)
        return result["text"].strip()
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)