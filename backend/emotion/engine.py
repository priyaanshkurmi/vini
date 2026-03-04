import time
import math
from dataclasses import dataclass, asdict


@dataclass
class EmotionState:
    happiness: float = 60.0
    trust: float = 40.0
    energy: float = 75.0
    attachment: float = 20.0
    last_update: float = 0.0

    def __post_init__(self):
        self.last_update = time.time()

    def decay(self):
        elapsed = time.time() - self.last_update
        factor = math.exp(-0.0001 * elapsed)
        for field in ["happiness", "trust", "energy", "attachment"]:
            current = getattr(self, field)
            setattr(self, field, 50 + (current - 50) * factor)
        self.last_update = time.time()

    def apply_event(self, event: str):
        events = {
            # Conversation tone events
            "positive_interaction":  {"happiness": +8,  "trust": +3,  "energy": +2},
            "negative_interaction":  {"happiness": -12, "trust": -6,  "energy": -3},
            "exciting_news":         {"happiness": +18, "energy": +15, "trust": +2},
            "sad_topic":             {"happiness": -18, "energy": -8,  "trust": +3},
            "surprise":              {"happiness": +5,  "energy": +20, "trust": +1},
            "long_absence":          {"attachment": +8, "energy": -5,  "happiness": -5},
            "task_completed":        {"happiness": +10, "energy": +5,  "trust": +3},
            "user_frustrated":       {"happiness": -15, "trust": -8,   "energy": -5},
            "joke_or_fun":           {"happiness": +20, "energy": +12, "trust": +4},
            "deep_conversation":     {"trust": +10,     "attachment": +5, "energy": -3},
            "greeting":              {"happiness": +12, "energy": +8,  "attachment": +3},
            "goodbye":               {"happiness": -5,  "attachment": +8, "energy": -5},
        }
        if event in events:
            for k, v in events[event].items():
                current = getattr(self, k)
                setattr(self, k, max(0.0, min(100.0, current + v)))

    def to_prompt_context(self) -> str:
        self.decay()
        return (
            f"Your current emotional state: "
            f"happiness={self.happiness:.0f}/100, "
            f"trust={self.trust:.0f}/100, "
            f"energy={self.energy:.0f}/100. "
            f"Let this subtly influence your tone."
        )

    def to_dict(self) -> dict:
        return {
            "happiness": round(self.happiness, 2),
            "trust": round(self.trust, 2),
            "energy": round(self.energy, 2),
            "attachment": round(self.attachment, 2),
        }


# Single instance shared across the whole app
emotion = EmotionState()