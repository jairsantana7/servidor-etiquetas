"""Servidor HTTP de etiquetas com fila persistente e um único consumidor."""
import io
import os
import sqlite3
import asyncio
import threading
import time
import uuid
from pathlib import Path

import pymupdf
from flask import Flask, jsonify, render_template, request, send_file
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('PRINT_DATA', ROOT / 'data')).resolve()
DATA.mkdir(parents=True, exist_ok=True)
DPI = int(os.environ.get('PRINT_DPI', '200'))
WIDTH_PX = int(os.environ.get('PRINT_WIDTH_PX', '384'))
HEIGHT_MM = float(os.environ.get('PRINT_HEIGHT_MM', '20'))
SIZE = (WIDTH_PX, round(HEIGHT_MM * DPI / 25.4))
if DPI <= 0 or not 1 <= SIZE[0] <= 4096 or not 1 <= SIZE[1] <= 4096:
    raise ValueError('Dimensões de impressão inválidas.')
DRY_RUN = os.environ.get('PRINT_DRY_RUN', '1') == '1'
TOKEN = os.environ.get('PRINT_TOKEN', '')
PRINTER_SESSION = None
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 20_000_000


def db():
    con = sqlite3.connect(DATA / 'jobs.sqlite3', timeout=30)
    con.row_factory = sqlite3.Row
    return con


def initialize():
    with db() as con:
        con.execute('''CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, name TEXT, status TEXT, created REAL,
            pages INTEGER, copies INTEGER, error TEXT DEFAULT '')''')
        # Não repetir impressão que possa ter saído antes de um reinício.
        con.execute("UPDATE jobs SET status='interrupted', error='Servidor reiniciou durante o envio; confira as etiquetas antes de reenviar.' WHERE status='printing'")


def rasterize(raw):
    if raw.startswith(b'%PDF-'):
        with pymupdf.open(stream=raw, filetype='pdf') as doc:
            if doc.needs_pass or not 1 <= len(doc) <= 30:
                raise ValueError('PDF protegido ou fora do limite de 1 a 30 páginas.')
            images = []
            for page in doc:
                factor = min(SIZE[0] / page.rect.width, SIZE[1] / page.rect.height)
                pix = page.get_pixmap(matrix=pymupdf.Matrix(factor, factor), alpha=False)
                images.append(Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB'))
    else:
        with Image.open(io.BytesIO(raw)) as source:
            if source.format not in {'PNG', 'JPEG'}:
                raise ValueError('Envie PDF, PNG ou JPEG.')
            images = [ImageOps.exif_transpose(source).convert('RGB')]
    output = []
    for image in images:
        image.thumbnail(SIZE, Image.Resampling.LANCZOS)
        canvas = Image.new('RGB', SIZE, 'white')
        canvas.paste(image, ((SIZE[0] - image.width) // 2, (SIZE[1] - image.height) // 2))
        output.append(canvas)
    return output


@app.before_request
def authenticate():
    if request.path.startswith('/api/') and TOKEN and request.headers.get('Authorization') != f'Bearer {TOKEN}':
        return jsonify(error='Token inválido.'), 401


@app.after_request
def disable_api_cache(response):
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.get('/')
def index():
    return render_template('index.html', dry_run=DRY_RUN, dpi=DPI, width_mm=f'{WIDTH_PX * 25.4 / DPI:.1f}'.replace('.', ','), height_mm=f'{HEIGHT_MM:g}'.replace('.', ','))


@app.get('/api/printer')
def printer_status():
    if DRY_RUN:
        return jsonify(status='simulated', name='PD01', error='')
    if PRINTER_SESSION is None:
        return jsonify(status='disconnected', name='PD01', error='')
    return jsonify(dict(PRINTER_SESSION.state))


@app.get('/api/jobs')
def jobs():
    with db() as con:
        rows = con.execute('SELECT * FROM jobs ORDER BY created DESC LIMIT 100').fetchall()
    return jsonify([dict(row) for row in rows])


@app.post('/api/jobs')
def submit():
    upload = request.files.get('file')
    if not upload:
        return jsonify(error='Selecione um PDF, PNG ou JPEG.'), 400
    try:
        copies = int(request.form.get('copies', '1'))
        if not 1 <= copies <= 20:
            raise ValueError('Use de 1 a 20 cópias.')
        images = rasterize(upload.read())
    except Exception as exc:
        return jsonify(error=f'Documento inválido: {exc}'), 400
    job_id = uuid.uuid4().hex
    folder = DATA / job_id
    folder.mkdir()
    try:
        for index, image in enumerate(images):
            image.save(folder / f'{index}.png', dpi=(DPI, DPI))
        with db() as con:
            con.execute('INSERT INTO jobs (id,name,status,created,pages,copies) VALUES (?,?,?,?,?,?)',
                        (job_id, (upload.filename or 'Etiqueta')[:200], 'queued', time.time(), len(images), copies))
    except Exception:
        import shutil
        shutil.rmtree(folder)
        raise
    return jsonify(id=job_id, status='queued', pages=len(images), copies=copies), 202


@app.get('/api/jobs/<job_id>/preview')
def preview(job_id):
    with db() as con:
        row = con.execute('SELECT id FROM jobs WHERE id=?', (job_id,)).fetchone()
    if not row:
        return jsonify(error='Trabalho não encontrado.'), 404
    return send_file(DATA / row['id'] / '0.png', mimetype='image/png')


@app.errorhandler(413)
def too_large(_):
    return jsonify(error='O limite por arquivo é 10 MB.'), 413


async def process_one(session=None):
    with db() as con:
        con.execute('BEGIN IMMEDIATE')
        row = con.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created LIMIT 1").fetchone()
        if not row:
            return False
        con.execute("UPDATE jobs SET status='printing' WHERE id=?", (row['id'],))
    status, error = ('simulated' if DRY_RUN else 'sent'), ''
    try:
        for _ in range(row['copies']):
            for page in range(row['pages']):
                path = DATA / row['id'] / f'{page}.png'
                if DRY_RUN:
                    continue
                if session is None:
                    raise RuntimeError('Sessão Bluetooth não inicializada.')
                started = time.monotonic()
                try:
                    await session.send(path)
                finally:
                    with (DATA / row['id'] / 'timini.log').open('a') as log:
                        log.write(f'Página {page + 1}: {time.monotonic() - started:.2f}s; {session.state}\n')
    except Exception as exc:
        status, error = 'failed', str(exc)
    with db() as con:
        con.execute('UPDATE jobs SET status=?,error=? WHERE id=?', (status, error, row['id']))
    return True


async def worker_loop():
    global PRINTER_SESSION
    if not DRY_RUN:
        from printer_session import PrinterSession
        PRINTER_SESSION = PrinterSession()
        try:
            await PRINTER_SESSION.ensure_connected()
            app.logger.warning('PD01: conexão persistente aberta')
        except Exception:
            app.logger.exception('Não foi possível abrir Bluetooth; nova tentativa no próximo trabalho')
    try:
        while True:
            try:
                if not await process_one(PRINTER_SESSION):
                    await asyncio.sleep(0.25)
            except Exception:
                app.logger.exception('Erro na fila')
                await asyncio.sleep(2)
    finally:
        if PRINTER_SESSION is not None:
            await PRINTER_SESSION.close()


def worker():
    asyncio.run(worker_loop())


if __name__ == '__main__':
    from waitress import serve
    initialize()
    threading.Thread(target=worker, daemon=True).start()
    serve(app, host=os.environ.get('PRINT_HOST', '0.0.0.0'), port=int(os.environ.get('PRINT_PORT', '8080')))
