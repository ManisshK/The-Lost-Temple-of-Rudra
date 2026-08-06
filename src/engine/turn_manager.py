from __future__ import annotations
from dataclasses import dataclass
from src.world.world_state import TemplePhase

PHASE_THRESHOLDS: dict[TemplePhase, int] = {
    TemplePhase.DISCOVERY:     0,
    TemplePhase.UNDERSTANDING: 30,
    TemplePhase.ADAPTATION:    60,
    TemplePhase.JUDGMENT:      90,
}

@dataclass
class TurnManager:
    current_turn: int = 0
    current_phase: TemplePhase = TemplePhase.DISCOVERY

    def advance(self) -> int:
        self.current_turn += 1
        self._update_phase()
        return self.current_turn

    def get_phase(self) -> TemplePhase:
        return self.current_phase

    def is_phase(self, phase: TemplePhase) -> bool:
        return self.current_phase == phase

    def reset(self) -> None:
        self.current_turn = 0
        self.current_phase = TemplePhase.DISCOVERY

    def _update_phase(self) -> None:
        for phase, threshold in sorted(
            PHASE_THRESHOLDS.items(), key=lambda x: x[1], reverse=True
        ):
            if self.current_turn >= threshold:
                self.current_phase = phase
                break
