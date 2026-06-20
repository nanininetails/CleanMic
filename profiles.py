from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Self

from constants import ProfileKey, CUSTOM_SLOTS, DEFAULT_CUSTOM_VALUES, PROFILE_NAME_PREFIX


PROFILES_FILENAME = "studio_profiles.json"
TUNING_VALUE_COUNT = 5


@dataclass
class CustomProfile:
    name: str
    values: list[int]
    is_empty: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "values": self.values,
            "is_empty": self.is_empty,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(
            name=str(data["name"]),
            values=list(data["values"]),
            is_empty=bool(data["is_empty"]),
        )

    @classmethod
    def empty(cls, slot_key: ProfileKey) -> Self:
        slot_num = slot_key.value[-1]
        return cls(
            name=f"{PROFILE_NAME_PREFIX}Empty Slot {slot_num}",
            values=DEFAULT_CUSTOM_VALUES.copy(),
            is_empty=True,
        )

    @classmethod
    def saved(cls, name: str, values: list[int]) -> Self:
        return cls(name=name, values=values, is_empty=False)


CustomProfiles = dict[ProfileKey, CustomProfile]


def profiles_file_path() -> Path:
    return Path(__file__).resolve().parent / PROFILES_FILENAME


def default_custom_profiles() -> CustomProfiles:
    return {slot: CustomProfile.empty(slot) for slot in CUSTOM_SLOTS}


def is_legacy_profile_format(data: dict) -> bool:
    if not data:
        return False
    for slot in CUSTOM_SLOTS:
        entry = data.get(slot.value) or data.get(slot)
        if isinstance(entry, list):
            return True
    return False


def profiles_from_json(data: dict) -> CustomProfiles:
    profiles = default_custom_profiles()
    for slot in CUSTOM_SLOTS:
        raw = data.get(slot.value) or data.get(slot)
        if isinstance(raw, dict):
            profiles[slot] = CustomProfile.from_dict(raw)
    return profiles


def profiles_to_json(profiles: CustomProfiles) -> dict[str, dict]:
    return {slot.value: profile.to_dict() for slot, profile in profiles.items()}


def strip_profile_prefix(name: str) -> str:
    return name.replace(PROFILE_NAME_PREFIX, "")


class RecordButtonState(str, Enum):
    IDLE = 0
    RECORDING = 1