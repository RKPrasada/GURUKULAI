# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for VidyaBot desktop build."""

import sys
from pathlib import Path

ROOT = Path(SPECPATH)

block_cipher = None

a = Analysis(
    [str(ROOT / 'launcher.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / 'data'), 'data'),
        (str(ROOT / 'frontend'), 'frontend'),
        (str(ROOT / '.env.example'), '.'),
    ],
    hiddenimports=[
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'fastapi',
        'streamlit',
        'streamlit.web',
        'streamlit.web.cli',
        'aiosqlite',
        'sqlalchemy',
        'cryptography',
        'google.generativeai',
        'httpx',
        'plotly',
        'pandas',
        'agents',
        'agents.orchestrator',
        'agents.diagnostic_agent',
        'agents.content_agent',
        'agents.assessment_agent',
        'agents.feedback_agent',
        'agents.progress_agent',
        'security',
        'security.injection_detector',
        'security.pii_scrubber',
        'security.guardrails',
        'security.audit_logger',
        'mcp',
        'mcp.drive_client',
        'mcp.calendar_client',
        'mcp.gmail_client',
        'mcp.youtube_client',
        'models',
        'models.student',
        'models.question',
        'models.session',
        'api',
        'api.main',
        'api.auth',
        'api.routes',
        'api.routes.student',
        'api.routes.session',
        'api.routes.progress',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib.tests', 'numpy.tests'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VidyaBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VidyaBot',
)
