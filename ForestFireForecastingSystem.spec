# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import os
import importlib

a = Analysis(['ForestFireForecastingSystem.py'],
             pathex=['C:\\Users\\Gen\\PycharmProjects\\ForestFireForecastingSystem'],
             binaries=[],
             datas=[
             (".\\venv\\Lib\\site-packages\\branca\\*.json","branca"),
             (".\\venv\\Lib\\site-packages\\branca\\templates","templates"),
             (".\\venv\\Lib\\site-packages\\folium\\templates","templates"),
             (os.path.join(os.path.dirname(importlib.import_module('tensorflow').__file__),
             "lite/experimental/microfrontend/python/ops/_audio_microfrontend_op.so"),
             "tensorflow/lite/experimental/microfrontend/python/ops/")
             ],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='ForestFireForecastingSystem',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False , icon='app.ico')
