from enum import Enum
from typing import NamedTuple


class EngineType(str, Enum):
    DEEP_FILTER = "DeepFilterNet (Studio Engine)"
    STFT = "STFT NoiseReduce (Low Latency)"
    STFT_DF = "STFT + DeepFilter (Best of both worlds)"


class ProfileKey(str, Enum):
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"
    C1 = "c1"
    C2 = "c2"
    C3 = "c3"
    C4 = "c4"
    CUSTOM_1 = "Custom 1"
    CUSTOM_2 = "Custom 2"
    CUSTOM_3 = "Custom 3"
    CUSTOM_4 = "Custom 4"


PRESET_MAP = {
    ProfileKey.P1: {"name": "◈ Heavy Fan Noise", "vals": [5, 98, 21, 100, 650]},
    ProfileKey.P2: {"name": "◈ Office Chatter", "vals": [4, 94, 17, 80, 500]},
    ProfileKey.P3: {"name": "◈ Keyboard Typing", "vals": [3, 96, 25, 40, 300]},
}

SDF_PRESET_MAP = {
    ProfileKey.P1: {"name": "◈ Heavy Fan Noise", "vals": [5, 98, 21, 100, 650]},
    ProfileKey.P2: {"name": "◈ Office Chatter", "vals": [4, 94, 17, 80, 500]},
    ProfileKey.P3: {"name": "◈ Keyboard Typing", "vals": [3, 96, 25, 40, 300]},
}

DEFAULT_CUSTOM_VALUES = [4, 95, 20, 90, 400]
PROFILE_NAME_PREFIX = "◈ "

CORE_PRESETS = (ProfileKey.P1, ProfileKey.P2, ProfileKey.P3)
CUSTOM_SLOTS = (ProfileKey.CUSTOM_1, ProfileKey.CUSTOM_2, ProfileKey.CUSTOM_3, ProfileKey.CUSTOM_4)
CUSTOM_UI_PROFILES = (ProfileKey.C1, ProfileKey.C2, ProfileKey.C3, ProfileKey.C4)

UI_PROFILE_TO_SLOT = {
    ProfileKey.C1: ProfileKey.CUSTOM_1,
    ProfileKey.C2: ProfileKey.CUSTOM_2,
    ProfileKey.C3: ProfileKey.CUSTOM_3,
    ProfileKey.C4: ProfileKey.CUSTOM_4,
}

SLOT_TO_UI_PROFILE = {slot: ui for ui, slot in UI_PROFILE_TO_SLOT.items()}


# UI timing and layout
VISUAL_TIMER_MS = 30
FFT_DISPLAY_BINS = 200
FFT_SMOOTHING_BEFORE = 0.7
FFT_SMOOTHING_AFTER = 0.7
CALIBRATION_OVERLAY_TEXT_COLOR = "#00D2C4"
VU_METER_SCALE = 500
VU_METER_MAX = 100
DRAWER_GAP = 5
SAVE_FEEDBACK_MS = 1500
DEVICE_NAME_MAX_LEN = 25
WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 700
# Meter
PEAK_HOLD_FRAMES = 13        # frames before peak marker starts falling
PEAK_DECAY_RATE = 0.06      # how fast peak falls per frame
METER_MIN_DB = -60.0
METER_MAX_DB = 0.0
BOTTOM_BAR_HEIGHT = 90

# Engine tuning parameter mapping (drawer slider index → engine attribute) STFT
ENGINE_TUNING_ATTRS = (
    "scan_time_seconds",
    "scrub_power",
    "hunting_focus",
    "word_fade_ms",
    "voice_shield_hz",
)
ENGINE_TUNING_SCALE = (1, 1 / 100, 1 / 10, 1, 1)


# Engine presets for DeepFilter
DF_PRESET_MAP = {
    "df1": {"name": "Full Suppression", "atten_lim_db": None},
    "df2": {"name": "Voice Safe", "atten_lim_db": 30},
    "df3": {"name": "Light Touch", "atten_lim_db": 15},
}

class TuningParam(NamedTuple):
    label: str
    min_v: int
    max_v: int
    default: int
    is_float: bool


TUNING_PARAMS: tuple[TuningParam, ...] = (
    TuningParam("Train Time (s)", 1, 10, 4, False),
    TuningParam("Scrub Power (%)", 0, 100, 95, False),
    TuningParam("Hunting Focus", 10, 30, 20, True),
    TuningParam("Word Fade (ms)", 10, 200, 90, False),
    TuningParam("Voice Shield (Hz)", 50, 800, 400, False),
)


def is_custom_ui_profile(profile: ProfileKey) -> bool:
    return profile in UI_PROFILE_TO_SLOT


def ui_profile_to_slot(profile: ProfileKey) -> ProfileKey:
    return UI_PROFILE_TO_SLOT[profile]


def slot_to_ui_profile(slot: ProfileKey) -> ProfileKey:
    return SLOT_TO_UI_PROFILE[slot]
