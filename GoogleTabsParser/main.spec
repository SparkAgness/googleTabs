# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py', 'corp.py', 'petrol_private.py', 'sheets_transfer.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('2025-11-18_b2c.json', '.'),
        ('credentials.json', '.'),
        ('b2b_regions.json', '.'),
        ('regions.json', '.'),
        ('fake_useragent_data', 'fake_useragent/data'),
    ],
    hiddenimports=[
        'logging',
        'logging.handlers',
        'gspread',
        'google.oauth2.service_account',
        'selenium.webdriver.common.by',
        'selenium.webdriver.support.ui',
        'selenium.webdriver.support.expected_conditions',
        'selenium.webdriver.chrome.options',
        'bs4',
        'lxml.html',
        'fake_useragent',
        'fake_useragent.data',
        'urllib3',
        'charset_normalizer',
        'importlib.resources',
        'importlib.metadata',
        'corp',
        'petrol_private',
        'sheets_transfer'
    ],
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
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)