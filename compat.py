"""
compat.py — Compatibility shims for broken third-party dependencies.

WHY THIS EXISTS:
Some versions of `df` (DeepFilterNet) import `torchaudio.backend.common.AudioMetaData`
which no longer exists in recent torchaudio builds. This patch stubs the missing
module into sys.modules before `df` is imported, preventing an ImportError.

This must be imported before any `df.*` import.
"""

import sys
import types


def patch_torchaudio_backend() -> None:
    """Inject a stub torchaudio.backend module if the real one is missing."""
    if "torchaudio.backend" not in sys.modules:
        dummy_backend = types.ModuleType("backend")
        dummy_common = types.ModuleType("common")
        dummy_common.AudioMetaData = type("AudioMetaData", (object,), {})  # type: ignore[attr-defined]
        dummy_backend.common = dummy_common  # type: ignore[attr-defined]
        sys.modules["torchaudio.backend"] = dummy_backend
        sys.modules["torchaudio.backend.common"] = dummy_common