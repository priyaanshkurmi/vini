import os
import asyncio
import logging
import tempfile
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
from services.wake import WakeWordListener

logger = logging.getLogger("vini.voiceloop")

BASE        = "http://localhost:8000"
SAMPLE_RATE = 16000
BLOCK_SIZE  = 512


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
        if self._active:
            return
        asyncio.run_coroutine_threadsafe(self._handle_voice_turn(), self._loop)

    async def _handle_voice_turn(self):
        self._active = True
        try:
            # Notify avatar — listening
            await self._broadcast({"type": "listening", "animation": "listening"})

            # Record immediately — no chime delay
            audio_bytes = await asyncio.to_thread(self._record_with_silence)

            if audio_bytes is None:
                await self._broadcast({"animation": "idle", "type": "idle"})
                return

            # Notify avatar — thinking
            await self._broadcast({"animation": "thinking", "type": "thinking"})

            # Send to voice endpoint and process
            import httpx
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

    def _record_with_silence(self, max_duration: int = 8) -> bytes | None:
        """
        Record until silence detected or max_duration reached.
        Key improvements:
        - Silence window cut from 1.5s → 0.6s
        - Higher threshold to ignore background noise
        - Faster polling (30ms vs 50ms)
        - Minimum speech detection before silence kicks in
        """
        logger.info("Recording...")
        chunks         = []
        silent_frames  = 0
        speech_frames  = 0
        threshold      = 0.020   # higher = ignores more background noise
        # 0.6s silence window — was 1.5s
        silence_limit  = int(SAMPLE_RATE * 0.6 / BLOCK_SIZE)
        # Must detect at least 0.3s of speech before silence detection activates
        speech_minimum = int(SAMPLE_RATE * 0.3 / BLOCK_SIZE)

        def callback(indata, frames, time, status):
            nonlocal silent_frames, speech_frames
            chunks.append(indata.copy())
            rms = float(np.sqrt(np.mean(indata ** 2)))
            if rms >= threshold:
                speech_frames += 1
                silent_frames  = 0   # reset silence counter on speech
            else:
                if speech_frames >= speech_minimum:
                    silent_frames += 1
                # Don't count silence before speech starts

        with sd.InputStream(
            samplerate = SAMPLE_RATE,
            channels   = 1,
            dtype      = "float32",
            blocksize  = BLOCK_SIZE,
            callback   = callback,
        ):
            max_chunks = int(SAMPLE_RATE * max_duration / BLOCK_SIZE)
            while len(chunks) < max_chunks:
                sd.sleep(30)   # poll every 30ms — was 50ms
                if (speech_frames >= speech_minimum
                        and silent_frames >= silence_limit):
                    break

        # Need at least 0.5s of actual audio
        if len(chunks) < 10 or speech_frames < speech_minimum:
            logger.info("No speech detected.")
            return None

        audio       = np.concatenate(chunks).flatten()
        audio_int16 = (audio * 32767).astype(np.int16)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav.write(f.name, SAMPLE_RATE, audio_int16)
            with open(f.name, "rb") as wf:
                data = wf.read()

        logger.info(f"Recorded {len(chunks)*BLOCK_SIZE/SAMPLE_RATE:.1f}s of audio "
                    f"({speech_frames} speech frames)")
        return data

    def _play_audio(self, audio_bytes: bytes):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            tmp = f.name
        os.system(f"afplay {tmp}")
        os.unlink(tmp)

    async def _broadcast(self, payload: dict):
        try:
            from api.websocket import broadcast
            await broadcast(payload)
        except Exception:
            pass


# Singleton
voice_loop = VoiceLoop()