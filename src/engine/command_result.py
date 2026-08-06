"""
command_result.py — The Lost Temple of Rudra

Defines GameResult — the structured response returned by the Game Engine
after executing a Command.

The Game Engine returns a GameResult to whatever caller submitted the command
(UI, test, future AI agent). The caller uses it to update the display.

Blueprint Reference:
    Chapter 8.8  — Command Execution
    Chapter 15.7 — Turn-Based Execution Pipeline
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .command import Action, Command


class ResultStatus(Enum):
    """
    High-level outcome of a command execution.

    SUCCESS    — Command executed; world updated.
    FAILURE    — Command was valid but could not be executed
                 (e.g. door is locked, object not present).
    INVALID    — Command could not be interpreted or is not supported.
    SYSTEM     — A system action was performed (save, help, quit…).
    INFO       — Informational response; world unchanged (inventory, status…).
    """
    SUCCESS = "success"
    FAILURE = "failure"
    INVALID = "invalid"
    SYSTEM  = "system"
    INFO    = "info"


@dataclass
class GameResult:
    """
    Structured response produced by the Game Engine after executing a Command.

    Fields:
        status          High-level outcome.
        message         Natural-language response shown to the player.
                        Never a raw technical error message.
        command         The Command that was executed (or attempted).
        turn            The turn number after execution (0 if unchanged).
        world_changed   True when the World Model was modified.
        actions_taken   List of World Model write operations performed,
                        useful for debugging and testing.
        data            Optional dict for additional structured data
                        (e.g. inventory list, debug dump).
    """
    status: ResultStatus
    message: str
    command: Optional[Command] = None
    turn: int = 0
    world_changed: bool = False
    actions_taken: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    @classmethod
    def success(
        cls,
        message: str,
        command: Optional[Command] = None,
        turn: int = 0,
        actions_taken: Optional[list[str]] = None,
        data: Optional[dict] = None,
    ) -> GameResult:
        return cls(
            status=ResultStatus.SUCCESS,
            message=message,
            command=command,
            turn=turn,
            world_changed=True,
            actions_taken=actions_taken or [],
            data=data or {},
        )

    @classmethod
    def failure(
        cls,
        message: str,
        command: Optional[Command] = None,
        turn: int = 0,
    ) -> GameResult:
        return cls(
            status=ResultStatus.FAILURE,
            message=message,
            command=command,
            turn=turn,
            world_changed=False,
        )

    @classmethod
    def invalid(cls, message: str, command: Optional[Command] = None) -> GameResult:
        return cls(
            status=ResultStatus.INVALID,
            message=message,
            command=command,
            world_changed=False,
        )

    @classmethod
    def info(
        cls,
        message: str,
        command: Optional[Command] = None,
        turn: int = 0,
        data: Optional[dict] = None,
    ) -> GameResult:
        return cls(
            status=ResultStatus.INFO,
            message=message,
            command=command,
            turn=turn,
            world_changed=False,
            data=data or {},
        )

    @classmethod
    def system(cls, message: str, command: Optional[Command] = None) -> GameResult:
        return cls(
            status=ResultStatus.SYSTEM,
            message=message,
            command=command,
            world_changed=False,
        )

    def __str__(self) -> str:
        return f"[{self.status.value.upper()}] {self.message}"
