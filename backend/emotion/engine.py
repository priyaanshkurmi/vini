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
            "positive_interaction": {"happiness": +8, "trust": +3},
            "negative_interaction": {"happiness": -10, "trust": -5},
            "long_absence":         {"attachment": +5, "energy": -5},
            "task_completed":       {"happiness": +5, "energy": +3},
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