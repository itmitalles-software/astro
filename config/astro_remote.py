# SPDX-License-Identifier: GPL-3.0-or-later
"""Key and mouse gestures that only change their meaning inside an ssh client.

Terminal programs that own the mouse keep every click, and an agent CLI running
remotely cannot open a browser or read this machine's clipboard. Everywhere
else these gestures stay exactly what they were.
"""
from pathlib import Path

from kittens.tui.handler import result_handler


def in_ssh_client(window) -> bool:
    return any(
        Path((process.get('cmdline') or [''])[0]).name == 'ssh'
        for process in window.child.foreground_processes
    )


def clipboard_has_image(boss) -> bool:
    return 'image/png' in boss.clipboard.get_available_mime_types_for_paste()


def paste_image_over_ssh(boss, window) -> bool:
    if not (in_ssh_client(window) and clipboard_has_image(boss)):
        return False
    boss.run_kitten_with_metadata('astro_clipboard.py', window=window)
    return True


def main(args: list[str]) -> None:
    pass


@result_handler(no_ui=True)
def handle_result(args, answer, target_window_id, boss):
    window = boss.window_id_map.get(target_window_id)
    if window is None:
        return
    gesture = args[1] if len(args) > 1 else ''
    if gesture == 'open-link':
        # kitty cannot pass this click on: the program received press and
        # release already. A local agent CLI opens the link on its own.
        if in_ssh_client(window):
            window.mouse_handle_click('link')
    elif gesture == 'ctrl+v':
        if not paste_image_over_ssh(boss, window):
            window.send_key('ctrl+v')
    elif gesture == 'ctrl+shift+v':
        if not paste_image_over_ssh(boss, window):
            boss.paste_from_clipboard()
