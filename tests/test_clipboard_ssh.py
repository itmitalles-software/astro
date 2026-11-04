# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'config' / f'{name}.py')
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pane(*cmdline):
    return types.SimpleNamespace(
        child=types.SimpleNamespace(foreground_processes=[{'cmdline': list(cmdline)}]),
        send_key=MagicMock(), mouse_handle_click=MagicMock(), paste_with_actions=MagicMock(),
    )


class SshCommandTests(unittest.TestCase):
    def test_upload_connects_like_the_running_client(self):
        module = load('astro_clipboard')
        for cmdline, expected in [
            (['ssh', 'base'], ['--', 'base']),
            (['ssh', '-t', 'base', 'tmux', 'attach'], ['--', 'base']),
            (['ssh', '-p', '2222', '-i', 'key', 'me@host'], ['-p', '2222', '-i', 'key', '--', 'me@host']),
            (['ssh', '-p2222', '-L', '1:a:2', '-v', 'host', 'ls', '-l'], ['-p', '2222', '--', 'host']),
            (['ssh', '-4Atp', '22', 'host'], ['-4', '-p', '22', '--', 'host']),
            (['ssh', '-J', 'a,b', '-lroot', '--', 'host'], ['-J', 'a,b', '-l', 'root', '--', 'host']),
        ]:
            self.assertEqual(module.ssh_connection_args(cmdline), expected, cmdline)

    def test_clients_without_a_destination_have_no_upload(self):
        module = load('astro_clipboard')
        for cmdline in (['ssh'], ['ssh', '-N'], ['ssh', '-p'], ['ssh', '--']):
            self.assertIsNone(module.ssh_upload_command(cmdline), cmdline)

    def test_upload_options_win_over_the_ssh_config(self):
        module = load('astro_clipboard')
        command = module.ssh_upload_command(['/usr/bin/ssh', '-o', 'RequestTTY=yes', 'host'])
        self.assertEqual(command[0], '/usr/bin/ssh')
        self.assertLess(command.index('RequestTTY=no'), command.index('RequestTTY=yes'))
        for option in ('BatchMode=yes', 'ClearAllForwardings=yes', 'RemoteCommand=none'):
            self.assertLess(command.index(option), command.index('--'))
        self.assertTrue(command[-1].startswith('sh -c '))


class RemoteSaveTests(unittest.TestCase):
    def save(self, home, data):
        env = {'HOME': home, 'PATH': os.environ['PATH']}
        return subprocess.run(['sh', '-c', load('astro_clipboard').REMOTE_SAVE_SCRIPT], input=data, env=env,
                              capture_output=True, check=True).stdout.decode().strip()

    def test_image_is_stored_privately_and_reported(self):
        with tempfile.TemporaryDirectory() as home:
            path = Path(self.save(home, b'\x89PNG data'))
            self.assertEqual(path.parent, Path(home) / '.cache/astro/clipboard')
            self.assertEqual(path.suffix, '.png')
            self.assertEqual(path.read_bytes(), b'\x89PNG data')
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)

    def test_only_old_or_excess_regular_files_are_pruned(self):
        with tempfile.TemporaryDirectory() as home:
            cache = Path(home) / '.cache/astro/clipboard'
            cache.mkdir(parents=True)
            archive = Path(home) / 'archive.png'
            archive.touch()
            linked = cache / 'screenshot-linked.png'
            linked.symlink_to(archive)
            os.utime(linked, (1, 1), follow_symlinks=False)
            aged = cache / 'screenshot-aged.png'
            aged.touch()
            os.utime(aged, (1, 1))
            for index in range(55):
                (cache / f'screenshot-{index:02}.png').touch()
            self.save(home, b'new')
            self.assertTrue(linked.is_symlink())
            self.assertFalse(aged.exists())
            regular = [path for path in cache.iterdir() if not path.is_symlink()]
            self.assertEqual(len(regular), 50)


class GestureTests(unittest.TestCase):
    def setUp(self):
        self.module = load('astro_remote')
        self.boss = MagicMock()
        self.boss.clipboard.get_available_mime_types_for_paste.return_value = ['text/plain']

    def press(self, window, gesture):
        self.boss.window_id_map = {7: window}
        self.module.handle_result(['astro_remote.py', gesture], None, 7, self.boss)

    def test_links_open_only_inside_an_ssh_client(self):
        remote, local = pane('/usr/bin/ssh', 'base'), pane('claude')
        self.press(remote, 'open-link')
        self.press(local, 'open-link')
        remote.mouse_handle_click.assert_called_once_with('link')
        local.mouse_handle_click.assert_not_called()

    def test_ctrl_v_uploads_only_an_image_over_ssh(self):
        remote, local = pane('ssh', 'base'), pane('bash')
        self.press(remote, 'ctrl+v')
        remote.send_key.assert_called_once_with('ctrl+v')
        self.boss.clipboard.get_available_mime_types_for_paste.return_value = ['image/png']
        self.press(local, 'ctrl+v')
        local.send_key.assert_called_once_with('ctrl+v')
        self.boss.run_kitten_with_metadata.assert_not_called()
        remote.send_key.reset_mock()
        self.press(remote, 'ctrl+v')
        remote.send_key.assert_not_called()
        self.boss.run_kitten_with_metadata.assert_called_once_with('astro_clipboard.py', window=remote)

    def test_ctrl_shift_v_stays_native_unless_uploading(self):
        self.press(pane('ssh', 'base'), 'ctrl+shift+v')
        self.press(pane('bash'), 'ctrl+shift+v')
        self.assertEqual(self.boss.paste_from_clipboard.call_count, 2)
        self.boss.clipboard.get_available_mime_types_for_paste.return_value = ['image/png']
        self.press(pane('ssh', 'base'), 'ctrl+shift+v')
        self.assertEqual(self.boss.paste_from_clipboard.call_count, 2)
        self.boss.run_kitten_with_metadata.assert_called_once()


if __name__ == '__main__':
    unittest.main()
