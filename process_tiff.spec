# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['process_tiff.py'],
             pathex=['C:\\code\\angiogenesis-analyzer'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
            )
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='process_tiff',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )

app = BUNDLE(exe,
         name='process_tiff.app',
         icon=None,
         bundle_identifier=None,
         info_plist={
            'NSHighResolutionCapable': 'True'
            },
         )
