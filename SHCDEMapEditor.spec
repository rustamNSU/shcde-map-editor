# Build on Windows: python -m PyInstaller --noconfirm SHCDEMapEditor.spec
from pathlib import Path
from runpy import run_path
from PyInstaller.utils.win32.versioninfo import (
    VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct,
    VarFileInfo, VarStruct,
)
root = Path(SPECPATH)
app_version = run_path(str(root / 'editor/version.py'))['__version__']
version_parts = tuple(int(part) for part in app_version.split('.')) + (0,)
version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=version_parts, prodvers=version_parts,
        mask=0x3f, flags=0, OS=0x40004, fileType=0x1, subtype=0, date=(0, 0)),
    kids=[
        StringFileInfo([StringTable('040904B0', [
            StringStruct('FileDescription', 'SHC DE Map Editor'),
            StringStruct('FileVersion', app_version),
            StringStruct('InternalName', 'SHCDEMapEditor'),
            StringStruct('OriginalFilename', 'SHCDEMapEditor.exe'),
            StringStruct('ProductName', 'SHC DE Map Editor'),
            StringStruct('ProductVersion', app_version),
        ])]),
        VarFileInfo([VarStruct('Translation', [1033, 1200])]),
    ],
)
a = Analysis([str(root / 'app.py')], pathex=[str(root)],
    datas=[(str(root / 'editor/assets/templates'), 'editor/assets/templates'),
           (str(root / 'editor/assets/patterns'), 'editor/assets/patterns'),
           (str(root / 'editor/assets/app-icon.ico'), 'editor/assets')],
    binaries=[(str(root / 'editor/assets/native/navigation.dll'), 'editor/assets/native')],
    hiddenimports=[], excludes=['tkinter','matplotlib','PySide6.QtWebEngineCore',
                               'PySide6.QtWebEngineWidgets','PySide6.QtQml'],
    noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz,a.scripts,a.binaries,a.datas,[],name='SHCDEMapEditor',
    debug=False,strip=False,upx=False,console=False,
    icon=str(root / 'editor/assets/app-icon.ico'), version=version_info)
