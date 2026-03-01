import os
import asyncio
import logging
import threading
import tempfile
import httpx
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
from services.wake import WakeWordListener

logger = logging.getLogger("vini.voiceloop")

BASE        = "http://localhost:8000"
SAMPLE_RATE = 16000


class VoiceLoop:
    def __init__(self):
        self.wake_listener = WakeWordListener(on_wake=self._on_wake)
        self._loop         = None
        self._active       = False

    def start(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop
        self.wake_listener.start()
        logger.info("Voice loop ready. Say the wake word to start.")

    def _on_wake(self):
        """Called from wake word thread when wake word detected."""
        if self._active:
            return   # already handling a request
        # Schedule the async handler on the event loop
        asyncio.run_coroutine_threadsafe(self._handle_voice_turn(), self._loop)

    async def _handle_voice_turn(self):
        self._active = True
        try:
            # Tell avatar to switch to listening
            await self._broadcast({"type": "listening", "animation": "listening"})

            # Play a soft chime to signal Vini is listening
            self._play_ready_tone()

            # Record for up to 6 seconds, stop on silence
            audio_bytes = await asyncio.to_thread(self._record_with_silence, 6)

            if audio_bytes is None:
                await self._broadcast({"animation": "idle", "type": "idle"})
                return

            # Tell avatar to think
            await self._broadcast({"animation": "thinking", "type": "thinking"})

            # Send to voice endpoint
            async with httpx.AsyncClient(timeout=45) as client:
                r = await client.post(
                    f"{BASE}/voice",
                    files={"audio": ("voice.wav", audio_bytes, "audio/wav")},
                )

            if r.status_code == 200 and len(r.content) > 44:
                await self._broadcast({"animation": "talking", "type": "talking"})
                await asyncio.to_thread(self._play_audio, r.content)
                await self._broadcast({"animation": "idle", "type": "idle"})
            else:
                logger.warning(f"Voice endpoint error: {r.status_code}")
                await self._broadcast({"animation": "idle", "type": "idle"})

        except Exception as e:
            logger.error(f"Voice turn error: {e}")
            await self._broadcast({"animation": "idle", "type": "idle"})
        finally:
            self._active = False

    def _record_with_silence(self, max_duration: int = 6) -> bytes | None:
        """Record audio, auto-stop after 1.5s of silence."""
        logger.info("Recording...")
        chunks        = []
        silent_frames = 0
        threshold     = 0.012    # RMS silence threshold
        silence_limit = int(SAMPLE_RATE * 1.5 / 512)   # 1.5s of silence

        def callback(indata, frames, time, status):
            nonlocal silent_frames
            chunks.append(indata.copy())
            rms = float(np.sqrt(np.mean(indata**2)))
            if rms < threshold:
                silent_frames += 1
            else:
                silent_frames = 0

        with sd.InputStream(
            samplerate = SAMPLE_RATE,
            channels   = 1,
            dtype      = "float32",
            blocksize  = 512,
            callback   = callback,
        ):
            max_chunks = int(SAMPLE_RATE * max_duration / 512)
            recorded   = 0
            while recorded < max_chunks:
                sd.sleep(50)
                recorded = len(chunks)
                if silent_frames >= silence_limit and recorded > 10:
                    break

        if len(chunks) < 5:
            return None

        audio = np.concatenate(chunks).flatten()
        audio_int16 = (audio * 32767).astype(np.int16)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav.write(f.name, SAMPLE_RATE, audio_int16)
            with open(f.name, "rb") as wf:
                data = wf.read()
        return data

    def _play_audio(self, audio_bytes: bytes):
        import os, tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            tmp = f.name
        os.system(f"afplay {tmp}")
        os.unlink(tmp)

    def _play_ready_tone(self):
        """Short ascending tone to signal Vini is listening."""
        sr   = 22050
        dur  = 0.12
        t    = np.linspace(0, dur, int(sr * dur))
        tone = (np.sin(2 * np.pi * 880 * t) * 0.3).astype(np.float32)
        sd.play(tone, sr)
        sd.wait()

    async def _broadcast(self, payload: dict):
        try:
            from api.websocket import broadcast
            await broadcast(payload)
        except Exception:
            pass


# Singleton
voice_loop = VoiceLoop()