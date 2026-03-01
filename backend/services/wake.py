import os
import struct
import threading
import logging
import numpy as np
import pvporcupine
import sounddevice as sd

logger = logging.getLogger("vini.wake")

PICOVOICE_KEY = os.getenv("PICOVOICE_KEY", "")
WAKE_WORD     = "hey siri"   # We'll use built-in "hey siri" as placeholder


class WakeWordListener:
    def __init__(self, on_wake):
        self.on_wake  = on_wake   # callback fired when wake word detected
        self._running = False
        self._thread  = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        logger.info("Wake word listener started.")

    def stop(self):
        self._running = False

    def _listen(self):
        try:
            porcupine = pvporcupine.create(
                access_key = PICOVOICE_KEY,
                keyword_paths = ["models/hey_vini.ppn"],
            )
            logger.info(f"Porcupine ready. Say 'Hey Vini' to wake Vini.")

            def callback(indata, frames, time, status):
                if not self._running:
                    return
                # Convert float32 to int16 PCM
                pcm = struct.unpack_from("h" * porcupine.frame_length,
                                         (indata * 32768).astype(np.int16).tobytes())
                result = porcupine.process(pcm)
                if result >= 0:
                    logger.info("Wake word detected!")
                    self.on_wake()

            with sd.InputStream(
                samplerate  = porcupine.sample_rate,
                channels    = 1,
                dtype       = "float32",
                blocksize   = porcupine.frame_length,
                callback    = callback,
            ):
                while self._running:
                    sd.sleep(100)

            porcupine.delete()

        except Exception as e:
            logger.error(f"Wake word error: {e}")