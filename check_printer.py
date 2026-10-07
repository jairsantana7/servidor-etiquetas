"""Verifica descoberta e conexão Bluetooth sem enviar um trabalho de impressão."""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'vendor' / 'TiMini-Print'))
from timiniprint.devices import PrinterCatalog
from timiniprint.printing.connected import connect_printer
from timiniprint.transport.bluetooth import BluetoothDiscovery, BleakBluetoothConnector


async def check():
    name = os.environ.get('PRINT_BLUETOOTH', 'PD01')
    device = await BluetoothDiscovery(PrinterCatalog.load()).resolve_device(name)
    async with await connect_printer(device, BleakBluetoothConnector()) as connected:
        resolved = connected.printer_device()
        print(f'Conexão estabelecida: {name}; modelo={resolved.model_key}', flush=True)
    print('Conexão encerrada corretamente.', flush=True)


if __name__ == '__main__':
    asyncio.run(asyncio.wait_for(check(), timeout=60))
