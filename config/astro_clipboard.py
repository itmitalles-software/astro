# SPDX-License-Identifier: GPL-3.0-or-later
"""Paste clipboard screenshots as private files without changing the clipboard.

In a pane running an ssh client the file is uploaded over a second connection
with the same options, so the pasted path exists where the remote program runs.
"""
import os
from pathlib import Path
import select
import shlex
import signal
import subprocess
import tempfile
import time

from kittens.tui.handler import result_handler

MAX_IMAGE_BYTES = 64 * 1024 * 1024
MAX_SAVED_IMAGES = 50
MAX_IMAGE_AGE_SECONDS = 7 * 86400
UPLOAD_TIMEOUT_SECONDS = 30
UPLOAD_POLL_SECONDS = 0.05

# Options that decide where and how ssh connects. Everything else, such as
# port forwards, must not be repeated by the upload connection.
SSH_CONNECTION_OPTIONS = frozenset('BbcFiJlmoPpS')
SSH_VALUE_OPTIONS = SSH_CONNECTION_OPTIONS | frozenset('DEeILOQRWw')
SSH_CONNECTION_FLAGS = frozenset('46')
# ssh keeps the first value of an option, so these win over the user's config.
SSH_UPLOAD_OPTIONS = ('-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', '-o', 'ClearAllForwardings=yes',
                      '-o', 'RemoteCommand=none', '-o', 'RequestTTY=no')
# POSIX sh: same private directory and limits as the local cache, which also
# leaves symlinks alone.
REMOTE_SAVE_SCRIPT = (
    'umask 077; dir="${XDG_CACHE_HOME:-$HOME/.cache}/astro/clipboard"; mkdir -p "$dir" || exit; '
    'file=$(mktemp "$dir/screenshot-XXXXXXXXXX") || exit; '
    'if ! cat >"$file" || ! mv "$file" "$file.png"; then rm -f "$file"; exit 1; fi; '
    'saved() { find "$dir" -maxdepth 1 -type f -name "screenshot-*.png" "$@"; }; '
    f'saved -mtime +{MAX_IMAGE_AGE_SECONDS // 86400} -exec rm -f {{}} +; '
    f'saved -exec ls -1t {{}} + | tail -n +{MAX_SAVED_IMAGES + 1} | '
    'while IFS= read -r old; do rm -f "$old"; done; printf "%s\\n" "$file.png"'
)


def _prune_clipboard_cache(cache: Path, keep: Path | None = None) -> None:
    """Keep up to MAX_SAVED_IMAGES recent regular screenshot files for 7 days."""
    import stat

    cutoff_ns = (time.time() - MAX_IMAGE_AGE_SECONDS) * 1_000_000_000
    entries: list[tuple[int, str, Path]] = []
    try:
        with os.scandir(cache) as it:
            for entry in it:
                if not (entry.name.startswith('screenshot-') and entry.name.endswith('.png')):
                    continue
                try:
                    st = entry.stat(follow_symlinks=False)
                except OSError:
                    continue
                if stat.S_ISREG(st.st_mode):
                    entries.append((st.st_mtime_ns, entry.name, Path(entry.path)))
    except OSError:
        return
    entries.sort(reverse=True)
    for index, (mtime_ns, _, path) in enumerate(entries):
        if keep is not None and path == keep:
            continue
        if index >= MAX_SAVED_IMAGES or mtime_ns < cutoff_ns:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass


def read_bounded(command: list[str], limit: int, timeout: float) -> bytes:
    """Bound clipboard output while reading, not after buffering the whole image."""
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, start_new_session=True)
    assert process.stdout is not None
    deadline = time.monotonic() + timeout
    data = bytearray()
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([process.stdout], [], [], remaining)[0]:
                raise subprocess.TimeoutExpired(command, timeout)
            chunk = os.read(process.stdout.fileno(), min(65536, limit - len(data) + 1))
            if not chunk:
                status = process.wait(timeout=max(0, deadline - time.monotonic()))
                if status:
                    raise subprocess.CalledProcessError(status, command)
                return bytes(data)
            data.extend(chunk)
            if len(data) > limit:
                raise ValueError('Clipboard output exceeds the size limit')
    finally:
        process.stdout.close()
        try:
            # start_new_session makes this PID the private process-group ID.
            # Its descendants may retain stdout after the leader has exited.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        finally:
            process.wait(timeout=1)


def clipboard_image() -> str:
    """Return a saved PNG path, or an empty string for native text fallback."""
    if os.environ.get('WAYLAND_DISPLAY'):
        types_cmd = ['wl-paste', '--list-types']
        image_cmd = ['wl-paste', '--no-newline', '--type', 'image/png']
    else:
        types_cmd = ['xclip', '-selection', 'clipboard', '-out', '-target', 'TARGETS']
        image_cmd = ['xclip', '-selection', 'clipboard', '-out', '-target', 'image/png']
    saved = None
    try:
        types = read_bounded(types_cmd, 64 * 1024, 2)
        if b'image/png' not in types.splitlines():
            return ''
        data = read_bounded(image_cmd, MAX_IMAGE_BYTES, 5)
        if not data.startswith(b'\x89PNG\r\n\x1a\n'):
            return ''
        cache = Path(os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache') / 'astro' / 'clipboard'
        cache.mkdir(parents=True, exist_ok=True, mode=0o700)
        cache.chmod(0o700)
        # Unique files must survive subsequent copies and the kitten process.
        with tempfile.NamedTemporaryFile(prefix='screenshot-', suffix='.png', dir=cache, delete=False) as image:
            saved = Path(image.name)
            image.write(data)
        # Closing/flushing the file must succeed before handing its path to a CLI.
        resolved = str(saved.resolve())
        _prune_clipboard_cache(cache, keep=saved)
        return resolved
    except (OSError, ValueError, subprocess.SubprocessError):
        if saved is not None:
            try:
                saved.unlink(missing_ok=True)
            except OSError:
                pass
        return ''


def ssh_connection_args(cmdline: list[str]) -> list[str] | None:
    """Return the options and destination of an ssh client command line."""
    connection: list[str] = []
    arguments = iter(cmdline[1:])
    for argument in arguments:
        if argument == '--':
            argument = next(arguments, '')
        elif argument.startswith('-') and len(argument) > 1:
            letters = argument[1:]
            for index, letter in enumerate(letters):
                if letter in SSH_VALUE_OPTIONS:
                    value = letters[index + 1:] or next(arguments, None)
                    if value is None:
                        return None
                    if letter in SSH_CONNECTION_OPTIONS:
                        connection += [f'-{letter}', value]
                    break
                if letter in SSH_CONNECTION_FLAGS:
                    connection.append(f'-{letter}')
            continue
        return connection + ['--', argument] if argument else None
    return None


def ssh_upload_command(cmdline: list[str]) -> list[str] | None:
    """Build the command that stores stdin next to the remote program."""
    connection = ssh_connection_args(cmdline)
    if connection is None:
        return None
    return [cmdline[0], *SSH_UPLOAD_OPTIONS, *connection, 'sh -c ' + shlex.quote(REMOTE_SAVE_SCRIPT)]


def window_ssh_cmdline(window) -> list[str] | None:
    """Return the command line of the ssh client running in the pane, if any."""
    for process in window.child.foreground_processes:
        cmdline = process.get('cmdline') or []
        if cmdline and Path(cmdline[0]).name == 'ssh':
            return list(cmdline)
    return None


def report_upload_failure(boss, detail: str) -> None:
    german = (os.environ.get('LC_ALL') or os.environ.get('LC_MESSAGES') or os.environ.get('LANG', '')).startswith('de')
    title = 'Bild nicht eingefügt' if german else 'Image not pasted'
    text = 'Upload über SSH fehlgeschlagen' if german else 'Upload over SSH failed'
    boss.show_error(title, f'{text}: {detail}' if detail else text)


def upload_image(boss, window_id: int, image_path: str, command: list[str]) -> None:
    """Upload without blocking kitty, then paste the remote path."""
    from kitty.fast_data_types import add_timer, remove_timer

    local = Path(image_path)
    output = tempfile.TemporaryFile()
    errors = tempfile.TemporaryFile()
    try:
        with local.open('rb') as image:
            process = subprocess.Popen(command, stdin=image, stdout=output, stderr=errors, start_new_session=True)
    except OSError as error:
        output.close()
        errors.close()
        local.unlink(missing_ok=True)
        report_upload_failure(boss, str(error))
        return
    deadline = time.monotonic() + UPLOAD_TIMEOUT_SECONDS

    def poll(timer_id: int) -> None:
        status = process.poll()
        if status is None:
            if time.monotonic() < deadline:
                return
            process.kill()
            status = process.wait()
        remove_timer(timer_id)
        output.seek(0)
        errors.seek(0)
        lines = output.read(4096).decode(errors='replace').strip().splitlines()
        detail = errors.read(4096).decode(errors='replace').strip()
        output.close()
        errors.close()
        local.unlink(missing_ok=True)
        remote = lines[-1] if lines else ''
        if status != 0 or not (remote.startswith('/') and remote.endswith('.png')):
            report_upload_failure(boss, detail.splitlines()[-1] if detail else f'exit {status}')
            return
        window = boss.window_id_map.get(window_id)
        if window is not None:
            window.paste_with_actions(shlex.quote(remote) + ' ')

    add_timer(poll, UPLOAD_POLL_SECONDS, True)


def main(args: list[str]) -> str:
    return clipboard_image()


@result_handler()
def handle_result(args, image_path, target_window_id, boss):
    window = boss.window_id_map.get(target_window_id)
    if window is None:
        return
    if image_path:
        ssh_cmdline = window_ssh_cmdline(window)
        if ssh_cmdline is None:
            window.paste_with_actions(shlex.quote(image_path) + ' ')
            return
        command = ssh_upload_command(ssh_cmdline)
        if command is None:
            Path(image_path).unlink(missing_ok=True)
            report_upload_failure(boss, ' '.join(ssh_cmdline))
            return
        upload_image(boss, target_window_id, image_path, command)
    else:
        # Target the clicked pane, not whichever pane is now active.
        from kitty.clipboard import get_clipboard_string
        text = get_clipboard_string()
        if text:
            window.paste_with_actions(text)
