# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Сбор скрытых импортов
hidden_imports = [
    'google.auth',
    'google.auth.compute_engine',
    'google.oauth2',
    'google.oauth2.service_account',
    'googleapiclient',
    'googleapiclient.discovery',
    'googleapiclient.errors',
    'gspread',
    'gspread.utils',
    'gspread.exceptions',
    'bs4',
    'lxml',
    'lxml.etree',
    'lxml._elementpath',
    'dateutil',
    'dateutil.parser',
    'dateutil.relativedelta',
    'dateutil.tz',
    'pytz',
    'requests',
    'urllib3',
    'chardet',
    'idna',
    'certifi',
    'cryptography',
    'cryptography.hazmat',
    'cryptography.hazmat.backends',
    'cryptography.hazmat.primitives',
    'ssl',
]

# Сбор данных
datas = []
datas.extend(collect_data_files('certifi'))
datas.extend(collect_data_files('google'))
datas.extend(collect_data_files('gspread'))

a = Analysis(
    ['main.py'],
    pathex=[os.getcwd()],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='MyApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Измените на False для скрытия консоли
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.icns',
)