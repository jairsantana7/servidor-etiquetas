import argparse
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import launcher


class LauncherTests(unittest.TestCase):
    def args(self, **changes):
        values = dict(data_dir=None, config=None, host=None, port=None, simulate=False)
        values.update(changes)
        return argparse.Namespace(**values)

    def test_packaged_data_is_outside_bundle_and_defaults_to_simulation(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True), patch.object(launcher.sys, 'frozen', True, create=True), patch('launcher.user_data_dir', return_value=folder):
            config, home = launcher.configure(self.args())
            self.assertEqual(config, Path(folder) / 'settings.env')
            self.assertEqual(home, Path(folder))
            self.assertTrue(config.is_file())
            self.assertEqual(os.environ['PRINT_DATA'], folder)
            self.assertEqual(os.environ['PRINT_DRY_RUN'], '1')
            self.assertEqual(os.environ['PRINT_BLUETOOTH_ADDRESS'], '')

    def test_existing_configuration_persists_and_cli_overrides(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            config = Path(folder) / 'custom.env'
            config.write_text("PRINT_PORT=9000\nPRINT_TOKEN='token with spaces'\nPRINT_DRY_RUN=0\n")
            original = config.read_text()
            launcher.configure(self.args(data_dir=folder, config=str(config), port=9090, simulate=True))
            self.assertEqual(config.read_text(), original)
            self.assertEqual(os.environ['PRINT_PORT'], '9090')
            self.assertEqual(os.environ['PRINT_DRY_RUN'], '1')
            self.assertEqual(os.environ['PRINT_TOKEN'], 'token with spaces')

    def test_missing_explicit_configuration_is_an_error(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, 'Configuração não encontrada'):
                launcher.configure(self.args(data_dir=folder, config=str(Path(folder) / 'missing.env')))
