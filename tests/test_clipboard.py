# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class ClipboardTests(unittest.TestCase):
    def test_png_is_saved_privately_without_changing_clipboard(self):
        spec = importlib.util.spec_from_file_location('astro_clipboard', ROOT / 'config/astro_clipboard.py')
        assert spec is not None and spec.origin is not None and spec.loader is not None
        self.assertTrue(Path(spec.origin).exists(), 'image paste kitten is missing')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        png = b'\x89PNG\r\n\x1a\n' + b'test clipboard image'
        calls = []

        def run(args, limit, timeout):
            calls.append(args)
            return b'image/png\ntext/plain\n' if '--list-types' in args else png

        with tempfile.TemporaryDirectory() as cache, patch.dict(os.environ, XDG_CACHE_HOME=cache, WAYLAND_DISPLAY='wayland-0'), patch.object(module, 'read_bounded', side_effect=run):
            result = module.clipboard_image()
            self.assertEqual(Path(result).read_bytes(), png)
            self.assertEqual(Path(result).stat().st_mode & 0o777, 0o600)
            self.assertEqual(Path(result).parent.stat().st_mode & 0o777, 0o700)
            self.assertEqual(len(calls), 2)
            self.assertTrue(all(args[0] == 'wl-paste' for args in calls))

    def test_text_empty_invalid_and_failed_clipboards_do_not_create_files(self):
        spec = importlib.util.spec_from_file_location('astro_clipboard', ROOT / 'config/astro_clipboard.py')
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for types, data, error in [(b'text/plain\n', b'', None), (b'image/png\n', b'', None), (b'image/png\n', b'not png', None), (b'', b'', FileNotFoundError()), (b'', b'', subprocess.TimeoutExpired('wl-paste', 2))]:
            with self.subTest(types=types, data=data, error=error), tempfile.TemporaryDirectory() as cache:
                responses = [types, data]
                with patch.dict(os.environ, XDG_CACHE_HOME=cache, WAYLAND_DISPLAY='wayland-0'), patch.object(module, 'read_bounded', side_effect=error or responses):
                    self.assertEqual(module.clipboard_image(), '')
                    self.assertEqual(list(Path(cache).iterdir()), [])

    def test_result_pastes_quoted_path_to_original_window_only(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        import shlex
        spec = importlib.util.spec_from_file_location('astro_clipboard', ROOT / 'config/astro_clipboard.py')
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        window = Mock(child=SimpleNamespace(foreground_processes=[]))
        boss = SimpleNamespace(window_id_map={42: window})
        path = "/home/example/cache dir/it's a screenshot.png"
        module.handle_result([], path, 42, boss)
        window.paste_with_actions.assert_called_once_with(shlex.quote(path) + ' ')
        module.handle_result([], path, 999, boss)
        with patch('kitty.clipboard.get_clipboard_string', return_value='plain text\n'):
            module.handle_result([], '', 42, boss)
        self.assertEqual(window.paste_with_actions.call_args.args, ('plain text\n',))

    def test_screenshot_cache_prunes_stale_and_excess_files_while_keeping_recent_ones(self):
        import time
        spec = importlib.util.spec_from_file_location('astro_clipboard', ROOT / 'config/astro_clipboard.py')
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        png = b'\x89PNG\r\n\x1a\n' + b'test clipboard image'
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / 'astro' / 'clipboard'
            cache_dir.mkdir(parents=True, mode=0o700)
            now = time.time()
            stale = cache_dir / 'screenshot-stale.png'
            stale.write_bytes(png)
            os.utime(stale, (now - 8 * 86400, now - 8 * 86400))
            for i in range(52):
                item = cache_dir / f'screenshot-{i:03d}.png'
                item.write_bytes(png)
                os.utime(item, (now - 3600 + i, now - 3600 + i))
            unrelated = cache_dir / 'notes.txt'
            unrelated.write_text('keep')
            with patch.dict(os.environ, XDG_CACHE_HOME=tmp, WAYLAND_DISPLAY='wayland-0'), patch.object(
                module, 'read_bounded', side_effect=[b'image/png\n', png]
            ):
                saved = Path(module.clipboard_image())
            self.assertTrue(saved.exists())
            self.assertFalse(stale.exists(), 'screenshots older than 7 days must be pruned')
            remaining = sorted(p.name for p in cache_dir.glob('screenshot-*.png'))
            self.assertEqual(len(remaining), module.MAX_SAVED_IMAGES)
            self.assertNotIn('screenshot-000.png', remaining)
            self.assertNotIn('screenshot-001.png', remaining)
            self.assertIn('screenshot-051.png', remaining)
            self.assertTrue(unrelated.exists())


if __name__ == '__main__':
    unittest.main()
