import asyncio
import io
import os
import tempfile
import unittest

TEMP = tempfile.TemporaryDirectory()
os.environ['PRINT_DATA'] = TEMP.name
os.environ['PRINT_DRY_RUN'] = '1'
os.environ['PRINT_DPI'] = '200'
os.environ['PRINT_WIDTH_PX'] = '384'
os.environ['PRINT_HEIGHT_MM'] = '20'
import server
from PIL import Image


class ServerTests(unittest.TestCase):
    def setUp(self):
        server.initialize()
        with server.db() as con:
            con.execute('DELETE FROM jobs')
        server.TOKEN = ''
        self.client = server.app.test_client()

    def upload(self):
        raw = io.BytesIO()
        Image.new('RGB', (600, 200), 'black').save(raw, format='PNG')
        raw.seek(0)
        return self.client.post('/api/jobs', data={'file': (raw, 'etiqueta.png'), 'copies': '2'})

    def test_raster_queue_and_preview(self):
        response = self.upload()
        self.assertEqual(response.status_code, 202)
        job = response.json
        preview = self.client.get(f"/api/jobs/{job['id']}/preview")
        self.assertEqual(Image.open(io.BytesIO(preview.data)).size, (384, 157))
        preview.close()
        self.assertTrue(asyncio.run(server.process_one()))
        self.assertEqual(self.client.get('/api/jobs').json[0]['status'], 'simulated')
        self.assertFalse(asyncio.run(server.process_one()))

    def test_token_and_invalid_document(self):
        server.TOKEN = 'test-token'
        self.assertEqual(self.client.get('/api/jobs').status_code, 401)
        self.assertEqual(self.client.get('/api/jobs', headers={'Authorization': 'Bearer test-token'}).status_code, 200)
        server.TOKEN = ''
        response = self.client.post('/api/jobs', data={'file': (io.BytesIO(b'invalid'), 'bad.pdf')})
        self.assertEqual(response.status_code, 400)

    def test_pdf_and_restart(self):
        with server.pymupdf.open() as doc:
            doc.new_page(width=141.73, height=56.69)
            doc.new_page(width=141.73, height=56.69)
            images = server.rasterize(doc.tobytes())
        self.assertEqual(len(images), 2)
        job = self.upload().json
        with server.db() as con:
            con.execute("UPDATE jobs SET status='printing' WHERE id=?", (job['id'],))
        server.initialize()
        self.assertEqual(self.client.get('/api/jobs').json[0]['status'], 'interrupted')

    def test_connection_failure_is_not_retried(self):
        from unittest.mock import patch, AsyncMock
        self.upload()
        session = type('Session', (), {'send': AsyncMock(side_effect=RuntimeError('Bluetooth indisponível')), 'state': {}})()
        with patch.object(server, 'DRY_RUN', False):
            asyncio.run(server.process_one(session))
        self.assertEqual(self.client.get('/api/jobs').json[0]['status'], 'failed')
        self.assertFalse(asyncio.run(server.process_one(session)))
        session.send.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
