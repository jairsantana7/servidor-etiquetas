# Build nativo em macOS, Windows ou Linux.
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules, copy_metadata

root = Path(SPECPATH).parent
vendor = root / 'vendor' / 'TiMini-Print'
sys.path.insert(0, str(vendor))
datas = [(str(root / 'templates'), 'templates'), (str(root / '.env.example'), '.'),
         (str(root / 'docs'), 'docs'), (str(root / 'README.md'), '.'),
         (str(vendor / 'LICENSE'), 'licenses/TiMini-Print'),
         (str(vendor / 'NOTICE'), 'licenses/TiMini-Print'),
         (str(vendor / 'THIRD_PARTY_NOTICES.md'), 'licenses/TiMini-Print')]
binaries, hidden = [], ['server', 'printer_session']
for package in ['timiniprint', 'bleak', 'pymupdf', 'pypdfium2', 'pypdfium2_raw']:
    package_data, package_bins, package_hidden = collect_all(package)
    datas += package_data
    binaries += package_bins
    hidden += package_hidden
if sys.platform == 'darwin':
    hidden += ['objc', 'IOBluetooth', 'Foundation', 'CoreBluetooth', 'libdispatch']
elif sys.platform == 'win32':
    hidden += collect_submodules('winsdk')
else:
    package_data, package_bins, package_hidden = collect_all('dbus_fast')
    datas += package_data
    binaries += package_bins
    hidden += package_hidden
for distribution in ['Flask', 'Pillow', 'PyMuPDF', 'waitress', 'bleak', 'platformdirs', 'python-dotenv']:
    datas += copy_metadata(distribution, recursive=True)
a = Analysis([str(root / 'launcher.py')], pathex=[str(root), str(vendor)],
             binaries=binaries, datas=datas, hiddenimports=hidden,
             excludes=['tkinter', 'pytest'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='ServidorEtiquetas',
          debug=False, strip=False, upx=False, console=sys.platform != 'darwin',
          argv_emulation=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='ServidorEtiquetas')
if sys.platform == 'darwin':
    app = BUNDLE(coll, name='ServidorEtiquetas.app', bundle_identifier='local.servidoretiquetas',
                 info_plist={
                     'CFBundleDisplayName': 'Servidor de Etiquetas',
                     'CFBundleShortVersionString': '0.1.0',
                     'NSBluetoothAlwaysUsageDescription': 'Conecta à impressora PD01 para imprimir etiquetas.',
                     'NSBluetoothPeripheralUsageDescription': 'Conecta à impressora PD01 para imprimir etiquetas.',
                     'NSLocalNetworkUsageDescription': 'Recebe documentos de outros sistemas na rede local.',
                 })
