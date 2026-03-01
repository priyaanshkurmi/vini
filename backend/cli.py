#!/usr/bin/env python3
"""
VINI Interactive CLI — Text + Voice modes
"""

import os
import sys
import httpx
import tempfile
import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np

BASE        = "http://localhost:8000"
SAMPLE_RATE = 16000


# ── VOICE ─────────────────────────────────────────────────────────────────────

def record_audio(duration: int = 5) -> bytes:
    print(f"\n  🎤 Recording for {duration} seconds... speak now!")
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
    )
    sd.wait()
    print("  ✓ Done recording.")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav.write(f.name, SAMPLE_RATE, audio)
        with open(f.name, "rb") as wf:
            data = wf.read()
    return data


def play_audio(audio_bytes: bytes):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        tmp = f.name
    os.system(f"afplay {tmp}")
    os.unlink(tmp)


def voice_turn(duration: int = 5):
    audio_bytes = record_audio(duration)

    print("  Thinking...\n")
    with httpx.Client(timeout=60) as client:
        r = client.post(
            f"{BASE}/voice",
            files={"audio": ("voice.wav", audio_bytes, "audio/wav")},
        )

    if r.status_code == 200 and len(r.content) > 0:
        print("  Vini is speaking...")
        play_audio(r.content)
    else:
        print(f"  Error: {r.status_code} — {r.text}")


# ── TEXT ──────────────────────────────────────────────────────────────────────

def text_turn(message: str):
    with httpx.Client(timeout=30) as client:
        with client.stream("POST", f"{BASE}/chat",
                           json={"message": message}) as r:
            print("\n  Vini: ", end="", flush=True)
            for chunk in r.iter_text():
                print(chunk, end="", flush=True)
            print("\n")


def show_emotion():
    with httpx.Client(timeout=5) as client:
        e = client.get(f"{BASE}/emotion").json()
        print(f"\n  Emotion → happiness:{e['happiness']:.0f}  "
              f"trust:{e['trust']:.0f}  "
              f"energy:{e['energy']:.0f}  "
              f"attachment:{e['attachment']:.0f}\n")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    # Detect mode from argument
    mode = sys.argv[1] if len(sys.argv) > 1 else "voice"

    if mode == "voice":
        print("\n  ─────────────────────────────────────")
        print("  VINI VOICE MODE")
        print("  Press Enter to speak  |  type /text to switch to text")
        print("  Commands: /emotion  /quit  /5  /10  /15 (recording seconds)")
        print("  ─────────────────────────────────────\n")

        duration = 5

        while True:
            try:
                cmd = input("  [ Press Enter to speak ] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n  Goodbye.")
                sys.exit(0)

            if cmd == "/quit":
                print("  Goodbye.")
                sys.exit(0)
            elif cmd == "/text":
                mode = "text"
                print("\n  Switched to text mode.\n")
                break
            elif cmd == "/emotion":
                show_emotion()
            elif cmd in ("/5", "/10", "/15"):
                duration = int(cmd[1:])
                print(f"  Recording duration set to {duration} seconds.\n")
            else:
                # Any other input or just Enter — start voice turn
                try:
                    voice_turn(duration)
                except Exception as e:
                    print(f"  Error: {e}\n")

    if mode == "text":
        print("\n  ─────────────────────────────────────")
        print("  VINI TEXT MODE")
        print("  Type your message  |  /voice to switch to voice mode")
        print("  Commands: /emotion  /history  /clear  /quit")
        print("  ─────────────────────────────────────\n")

        while True:
            try:
                user_input = input("  You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n  Goodbye.")
                sys.exit(0)

            if not user_input:
                continue
            if user_input == "/quit":
                print("  Goodbye.")
                sys.exit(0)
            elif user_input == "/voice":
                main_voice()
            elif user_input == "/emotion":
                show_emotion()
            elif user_input == "/history":
                with httpx.Client(timeout=5) as client:
                    h = client.get(f"{BASE}/history").json()
                    print(f"\n  Last {len(h['history'])} messages:\n")
                    for m in h["history"]:
                        role = "You  " if m["role"] == "user" else "Vini "
                        print(f"    {role}: {m['content'][:80]}")
                    print()
            elif user_input == "/clear":
                with httpx.Client(timeout=5) as client:
                    client.delete(f"{BASE}/history")
                print("  History cleared.\n")
            else:
                try:
                    text_turn(user_input)
                except httpx.ConnectError:
                    print("  Error: Backend not reachable.\n")
                except Exception as e:
                    print(f"  Error: {e}\n")


def main_voice():
    """Restart in voice mode."""
    os.execv(sys.executable, [sys.executable, __file__, "voice"])


if __name__ == "__main__":
    main()