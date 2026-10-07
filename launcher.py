"""Inicialização portátil; configuração e fila fora do executável."""
import argparse
import logging
import os
import sys
import threading
import webbrowser
from pathlib import Path

from dotenv import dotenv_values
from platformdirs import user_data_dir


def configure(args):
    packaged = getattr(sys, 'frozen', False)
    root = Path(__file__).resolve().parent
    home = Path(args.data_dir).expanduser().resolve() if args.data_dir else (
        Path(user_data_dir('ServidorEtiquetas', appauthor=False)) if packaged else root / 'data')
    home.mkdir(parents=True, exist_ok=True)
    config = Path(args.config).expanduser().resolve() if args.config else (home / 'settings.env' if packaged else root / '.env')
    if not config.exists() and not args.config:
        config.write_text((root / '.env.example').read_text(), encoding='utf-8')
    if args.config and not config.is_file():
        raise ValueError(f'Configuração não encontrada: {config}')
    for key, value in dotenv_values(config).items():
        if key.startswith('PRINT_') and value is not None:
            os.environ.setdefault(key, value)
    os.environ.setdefault('PRINT_DATA', str(home))
    if args.host:
        os.environ['PRINT_HOST'] = args.host
    if args.port is not None:
        os.environ['PRINT_PORT'] = str(args.port)
    if args.simulate:
        os.environ['PRINT_DRY_RUN'] = '1'
    port = int(os.environ.get('PRINT_PORT', '8080'))
    if not 1 <= port <= 65535:
        raise ValueError('Porta deve estar entre 1 e 65535.')
    return config, home


def configure_logging(home):
    log = home / 'server.log'
    if sys.stdout is None:
        sys.stdout = log.open('a', encoding='utf-8', buffering=1)
    if sys.stderr is None:
        sys.stderr = log.open('a', encoding='utf-8', buffering=1)
    logging.basicConfig(level=logging.INFO, force=True, handlers=[logging.FileHandler(log, encoding='utf-8'), logging.StreamHandler()])



def main():
    parser = argparse.ArgumentParser(description='Servidor de etiquetas PD01')
    parser.add_argument('--config', help='Arquivo .env de configuração')
    parser.add_argument('--data-dir', help='Pasta persistente para fila e configuração')
    parser.add_argument('--host', help='Endereço de escuta')
    parser.add_argument('--port', type=int, help='Porta HTTP')
    parser.add_argument('--no-browser', action='store_true', help='Não abrir navegador')
    parser.add_argument('--simulate', action='store_true', help='Não enviar para impressora')
    parser.add_argument('--check', action='store_true', help='Validar recursos sem iniciar servidor')
    args = parser.parse_args()
    config, home = configure(args)
    configure_logging(home)
    import server
    if args.check:
        from printer_session import PrinterSession
        from timiniprint.devices import PrinterCatalog
        PrinterCatalog.load().device_from_key('pd01_v5g')
        with server.app.test_client() as client:
            if client.get('/').status_code != 200:
                raise RuntimeError('Interface indisponível no pacote.')
        print(f'Pacote válido. Configuração: {config}; dados: {home}')
        return
    from waitress import create_server
    # Abrir a porta antes de conectar a impressora impede dois consumidores
    # quando alguém abre uma segunda instância na mesma porta.
    http = create_server(server.app, host=os.environ.get('PRINT_HOST', '0.0.0.0'),
                         port=int(os.environ.get('PRINT_PORT', '8080')))
    server.initialize()
    threading.Thread(target=server.worker, daemon=True).start()
    port = os.environ.get('PRINT_PORT', '8080')
    print(f'Interface: http://localhost:{port}; configuração: {config}; dados: {home}')
    if not args.no_browser:
        threading.Timer(0.5, webbrowser.open, args=(f'http://localhost:{port}',)).start()
    try:
        http.run()
    except KeyboardInterrupt:
        pass
    finally:
        http.close()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        logging.exception('Falha ao iniciar servidor de etiquetas')
        raise
