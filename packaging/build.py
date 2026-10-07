"""Gera o executável para o sistema/arquitetura atual e arquivos de distribuição."""
import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TIMINI_COMMIT = '9bfc1b582c4d6492c74725f459a5843f8e8f66f8'


def run(*command):
    subprocess.run(command, cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--install', action='store_true', help='Instalar dependências de aplicação e build')
    parser.add_argument('--prepare-only', action='store_true', help='Preparar o TiMini e dependências da aplicação sem gerar pacote')
    args = parser.parse_args()
    vendor = ROOT / 'vendor' / 'TiMini-Print'
    if not vendor.exists():
        vendor.parent.mkdir(exist_ok=True)
        run('git', 'clone', 'https://github.com/Dejniel/TiMini-Print', str(vendor))
        run('git', '-C', str(vendor), 'checkout', TIMINI_COMMIT)
    commit = subprocess.check_output(['git', '-C', str(vendor), 'rev-parse', 'HEAD'], text=True).strip()
    if commit != TIMINI_COMMIT:
        raise RuntimeError(f'TiMini deve estar no commit {TIMINI_COMMIT}; encontrado {commit}.')
    if args.install:
        command = [sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt', '-r', str(vendor / 'requirements.txt')]
        if not args.prepare_only:
            command += ['-r', 'packaging/requirements-build.txt']
        run(*command)
    if args.prepare_only:
        print('Dependências e TiMini preparados.')
        return
    run(sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', 'packaging/ServidorEtiquetas.spec')
    system = platform.system()
    arch = {'AMD64': 'x86_64', 'aarch64': 'arm64'}.get(platform.machine(), platform.machine())
    name = f'ServidorEtiquetas-{system}-{arch}'
    dist = ROOT / 'dist'
    if system == 'Darwin':
        app = dist / 'ServidorEtiquetas.app'
        run('ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(app), str(dist / f'{name}.zip'))
        stage = ROOT / 'build' / 'dmg'
        if stage.exists():
            shutil.rmtree(stage)
        stage.mkdir(parents=True)
        shutil.copytree(app, stage / app.name, symlinks=True)
        (stage / 'Applications').symlink_to('/Applications')
        run('hdiutil', 'create', '-ov', '-volname', 'Servidor de Etiquetas', '-srcfolder', str(stage), '-format', 'UDZO', str(dist / f'{name}.dmg'))
    else:
        folder = dist / 'ServidorEtiquetas'
        archive_format = 'zip' if system == 'Windows' else 'gztar'
        shutil.make_archive(str(dist / name), archive_format, root_dir=dist, base_dir=folder.name)
    print(f'Pacotes disponíveis em {dist}')


if __name__ == '__main__':
    main()
