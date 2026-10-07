"""Uma sessão TiMini reutilizada pelo único consumidor da fila."""
import asyncio
import json
import os
import sys
from pathlib import Path

if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'vendor' / 'TiMini-Print'))
from timiniprint.devices import PrinterCatalog, BluetoothTarget
from timiniprint.devices.device import BluetoothEndpoint, BluetoothEndpointTransport
from timiniprint.printing.connected import connect_printer
from timiniprint.printing.settings import PrintSettings
from timiniprint.transport.bluetooth import BluetoothDiscovery, BleakBluetoothConnector


class PrinterSession:
    def __init__(self):
        self.printer = None
        self.device = None
        self.state = {'status': 'disconnected', 'name': os.environ.get('PRINT_BLUETOOTH', 'PD01'), 'error': ''}

    async def ensure_connected(self):
        if self.printer is not None:
            return self.printer
        self.state.update(status='connecting', error='')
        try:
            if self.device is None:
                catalog = PrinterCatalog.load()
                name = self.state['name']
                address = os.environ.get('PRINT_BLUETOOTH_ADDRESS')
                if address:
                    endpoint = BluetoothEndpoint(name=name, address=address, transport=BluetoothEndpointTransport.BLE)
                    target = BluetoothTarget(classic_endpoint=None, ble_endpoint=endpoint,
                                             display_address=address, transport_badge='ble')
                    self.device = catalog.device_from_key(os.environ.get('PRINT_MODEL') or 'pd01_v5g',
                                                          display_name=name, transport_target=target)
                else:
                    self.device = await BluetoothDiscovery(catalog).resolve_device(name)
                if os.environ.get('PRINT_CONFIG'):
                    config = json.loads(Path(os.environ['PRINT_CONFIG']).read_text())
                    self.device = catalog.device_from_printer_config(config, transport_target=self.device.transport_target)
                elif os.environ.get('PRINT_MODEL') and not address:
                    self.device = catalog.device_from_key(os.environ['PRINT_MODEL'], transport_target=self.device.transport_target)
            self.printer = await asyncio.wait_for(connect_printer(self.device, BleakBluetoothConnector()), timeout=60)
            self.state.update(status='connected', error='')
            return self.printer
        except Exception as exc:
            self.state.update(status='disconnected', error=str(exc))
            raise

    async def send(self, path):
        printer = await self.ensure_connected()
        settings = PrintSettings(image_mode=os.environ.get('PRINT_IMAGE_MODE', 'threshold'),
                                 trim_side_margins=False, trim_top_bottom_margins=False,
                                 page_gap_mm=0, paper_preset_key=os.environ.get('PRINT_PAPER') or None)
        try:
            await asyncio.wait_for(printer.print_file(str(path), settings=settings), timeout=120)
        except Exception as exc:
            await self.close()
            self.state.update(error=str(exc))
            # Não repetir: o envio pode ter impresso parcialmente.
            raise

    async def close(self):
        printer, self.printer = self.printer, None
        self.state.update(status='disconnected')
        if printer is not None:
            try:
                await asyncio.wait_for(printer.disconnect(), timeout=10)
            except Exception:
                pass
