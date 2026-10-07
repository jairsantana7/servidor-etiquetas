import os
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from printer_session import PrinterSession


class SessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_reuses_one_connection_for_multiple_prints(self):
        printer = type('Printer', (), {'print_file': AsyncMock(), 'disconnect': AsyncMock()})()
        with patch.dict(os.environ, {'PRINT_BLUETOOTH_ADDRESS': '00000000-0000-0000-0000-000000000001'}), patch('printer_session.connect_printer', new_callable=AsyncMock, return_value=printer) as connect:
            session = PrinterSession()
            await session.ensure_connected()
            await session.send(Path('one.png'))
            await session.send(Path('two.png'))
            connect.assert_awaited_once()
            self.assertEqual(printer.print_file.await_count, 2)
            printer.disconnect.assert_not_awaited()
            self.assertEqual(session.state['status'], 'connected')
            await session.close()
            printer.disconnect.assert_awaited_once()

    async def test_failure_closes_and_next_send_reconnects_without_reprinting(self):
        broken = type('Printer', (), {'print_file': AsyncMock(side_effect=RuntimeError('Conexão perdida')), 'disconnect': AsyncMock()})()
        healthy = type('Printer', (), {'print_file': AsyncMock(), 'disconnect': AsyncMock()})()
        with patch.dict(os.environ, {'PRINT_BLUETOOTH_ADDRESS': '00000000-0000-0000-0000-000000000001'}), patch('printer_session.connect_printer', new_callable=AsyncMock, side_effect=[broken, healthy]) as connect:
            session = PrinterSession()
            with self.assertRaisesRegex(RuntimeError, 'Conexão perdida'):
                await session.send(Path('failed.png'))
            broken.print_file.assert_awaited_once()
            broken.disconnect.assert_awaited_once()
            self.assertEqual(session.state['status'], 'disconnected')
            await session.send(Path('next.png'))
            self.assertEqual(connect.await_count, 2)
            healthy.print_file.assert_awaited_once()
            await session.close()
