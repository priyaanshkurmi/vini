import os
import subprocess
import tempfile
import numpy as np

TTS_MODEL = os.getenv("TTS_MODEL", "models/tts/en_US-lessac-medium.onnx")


def synthesize(text: str) -> bytes:
    """Convert text to WAV audio bytes using Piper."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        out_path = f.name

    try:
        subprocess.run(
            ["piper", "--model", TTS_MODEL, "--output_file", out_path],
            input=text.encode(),
            check=True,
            capture_output=True,
        )
        with open(out_path, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(out_path):
            os.unlink(out_path)


def extract_amplitude_frames(audio_bytes: bytes, frame_ms: int = 20) -> list[float]:
    """Extract RMS amplitude per 20ms frame for lip sync."""
    import struct
    import wave
    import io

    with wave.open(io.BytesIO(audio_bytes)) as wf:
        sr         = wf.getframerate()
        raw        = wf.readframes(wf.getnframes())
        samples    = np.frombuffer(raw, dtype=np.int16).astype(np.float32)

    frame_size = int(sr * frame_ms / 1000)
    frames     = []

    for i in range(0, len(samples), frame_size):
        chunk = samples[i:i + frame_size]
        if len(chunk) == 0:
            continue
        rms = float(np.sqrt(np.mean(chunk ** 2))) / 32768.0
        frames.append(round(rms, 4))

    return frames