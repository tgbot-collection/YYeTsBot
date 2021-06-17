# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['server.py'],
             pathex=['C:\\Users\\Benny\\Desktop\\yyetsweb\\yyetsweb'],
             binaries=[],
             datas=[
                ('*.html', '.'),
                ('js/*.js', 'js'),
                ('css/*.css', 'css'),
                ('css/3rd/*.css', 'css/3rd'),
                ('img/*.png', 'img'),
                ('yyets.sqlite', '.'),
            ],
             hiddenimports=['SQLite'],
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
          name='server',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )
