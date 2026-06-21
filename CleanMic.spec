# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

df_hidden = collect_submodules('df')
df_datas = collect_data_files('df')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('widgets', 'widgets'),
        ('studio_profiles.json', '.'),           # profile data
        ('styles.py', '.'),
        ('constants.py', '.'),
        ('compat.py', '.'),
        ('profiles.py', '.'),
        ('dialogs.py', '.'),
        (r'C:\Users\Nani\AppData\Local\DeepFilterNet\DeepFilterNet\Cache\DeepFilterNet3', 'DeepFilterNet3'),
        *df_datas,
    ],
    hiddenimports=[
        *df_hidden,
        'df.deepfilternet3',
        'noisereduce',
        'sounddevice',
        'scipy.signal',
        'scipy.io.wavfile',
        'torch',
        'torchaudio',
        'PyQt6.QtSvg',
        'PyQt6.QtSvgWidgets',
        'widgets',
        'widgets.profile_slot',
        'widgets.tuning_drawer',
        'widgets.peak_meter_bar',
        'widgets.title_bar',
        'widgets.accent_divider',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CleanMic',
    debug=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='CleanMic',
)