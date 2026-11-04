# Astro

![Astro — quiet company, sharp tools](assets/astro-logo.svg)

Astro turns [kitty](https://sw.kovidgoyal.net/kitty/) into a workspace for
agent CLIs such as Claude Code, Codex and Hermes. It is not a fork of kitty's
source code: it is a configuration plus a title-bar extension that runs inside
an unmodified kitty.

## Features

**Meet Astro**

The mascot is based on Astro, a real long-haired brown/grey tabby: tall ears,
a dark forehead M, a pink nose and a cream ruff. In the owner's front-facing
reference, the missing/closed eye is on the viewer's left and the single open
pale green eye is on the viewer's right. The icon and both ASCII cat poses keep
that exact orientation; do not mirror them. The cat stays minimal, without
detailed whiskers or cheek stripes. Its background is a terminal window with
only slightly rounded corners (16px radius on a 512px canvas), a title bar and
a small prompt. The entire cat head sits 24 SVG units lower beneath the title
bar. GNOME palette colors connect the frame and wordmark to the terminal;
the cat retains its natural fur and eye colors.
Reference photographs are personal and are not distributed in this repository.

New Bash terminal panes greet you with an animated cat action: First contact,
Cursor hunt, Star jump, Tail chase, Cat nap, Zoomies, Grooming, Yarn physics,
Box inspector or Window watch. Each has its own articulated poses and props,
not the same portrait with different particles. Zoomies retains its original
running sprite and motion. A persistent shuffle bag shows all ten before repeating,
including when several panes open together. The selected action loops until you
start typing; there is no automatic dismissal timer. The first input is left in
its terminal queue for the shell. Rendering updates only changed rows at 12 fps.
Cycle coordination is best effort: an unavailable/unsafe cache or a lock held
for more than 200 ms selects a random action instead of waiting indefinitely
for another pane. Cache symlinks and non-regular files are not followed.
The greeting adds no scrollback. Descendant Bash
shells skip the greeting in the same pane. Command shells such as `bash -ic`
start their agent or monitor immediately; their greeting waits until a real
interactive prompt is opened. Direct non-shell command launches,
tiny panes, redirected output and `TERM=dumb` skip it too. Bash remains the
normal login shell, preserving kitty's native shell integration.

```sh
# Disable greetings for terminals started from this environment.
export ASTRO_ANIMATION=off
# Alternatively set `env ASTRO_ANIMATION=off` in kitty.conf.
# REDUCE_MOTION=1 also disables them; NO_COLOR disables their colors.

# List or preview a specific effect (1–10).
python3 ~/.config/kitty/astro_intro.py --list
python3 ~/.config/kitty/astro_intro.py --effect 6 --duration 3
```

**Astro Bash prompt**

The familiar `user@host:path$` layout uses the owner's reference colors:
purple username (`#a76fc1`), grey `@` and colon (`#9a968f`), golden hostname
(`#fabd2f`), a quiet neutral path (`#bebdba`) and a softer gold prompt symbol
(`#caaa68`). These explicit RGB roles affect only the prompt; applications keep
the GNOME Soft ANSI palette and the neutral `#191919` background.
This is scoped to interactive Kitty Bash sessions; other terminals
are unchanged. Readline wrapping and kitty's native shell integration remain
intact. In interactive Kitty shells where `TERM` is `xterm-kitty`, Astro also
defines a lightweight `nvtop` wrapper (`TERM=xterm-256color`) unless you already
define `nvtop`, so capability-enabled `nvtop` binaries (`cap_perfmon`) work when
`xterm-kitty` is not installed in system-wide terminfo. Set `ASTRO_PROMPT=off`
to keep your existing prompt; `NO_COLOR` or a dumb terminal selects a plain
prompt. To update an already open Bash shell, run:

```sh
source ~/.config/kitty/astro_prompt.bash
```

**Pane controls in every title bar**

| Control | Shortcut | Action |
| --- | --- | --- |
| `+→` / `+↓` | `Ctrl+Alt+R` / `Ctrl+Alt+D` (`+Shift`: column / row) | Open a terminal to the right / below in the current directory |
| `▦` | `Ctrl+Alt+P` | Cycle the pane's group: none → 1 → 2 → 3 → 4 → none (colored) |
| `\|↔\|` | `Ctrl+Alt+=` | Give every pane of this group the same width |
| `⇕` | `Ctrl+Alt+Shift+=` | Give every pane of this group the same height |
| copy | `Ctrl+Shift+C` | Copy the selection |
| `>_` | `Ctrl+Alt+O` | Copy the last shell command with its output |
| keyboard | `Ctrl+Alt+/` | Show kitty's keyboard shortcuts in a separate tab |
| zoom | `Ctrl+Shift+Z` | Zoom the pane (stack layout) and back |
| `✕` | `Ctrl+Shift+W` | Close the pane (asks when a job is running) |

Ordinary `+→` and `+↓` clicks split the clicked pane right or below. Shift-clicking
(or `Ctrl+Alt+Shift+R` / `Ctrl+Alt+Shift+D`) adds a full-height column at the tab's
right edge or a full-width row at its bottom, respectively, scaling the existing
layout while preserving its proportions.
Move between terminals with `Alt+arrow keys` (or `Alt+Shift+arrow keys`), jump to
one with `Alt+1` … `Alt+9`, or pick one by label with `Ctrl+Shift+Space`.
New terminals inherit the clicked pane's working directory. Only the "Codex below"
launcher button is removed; running Codex panes and their title badges remain unchanged.

**Reload without restarting:** press Ctrl+Shift+F5 to reload configuration and
refresh cached pane controls. When upgrading from the previous default binding,
press it twice: the first reload installs the new binding; the second refreshes
the title bars. Existing panes and running jobs remain open.
Reload also releases cached pointer backends so native-pointer fixes take effect
without restarting the terminal.

- **Groups:** equalizing changes only the panes of the clicked pane's group;
  every other pane keeps its size. On an ungrouped pane the buttons equalize
  the whole tab along that axis only. Some nested or mixed-size groups cannot
  be equalized without resizing other panes; Astro leaves the layout untouched
  and explains why rather than applying a partial change.
- **Folding:** when the title would otherwise be cut, all controls except close
  fold behind `‹`. Click it to unfold; the controls stay open until you click
  the fold button again. Moving the pointer away does not close them.
- **Hover hints:** the title bar describes the control under the pointer.
  Hints are English or German, following the system locale; put `de` or `en`
  into `~/.config/kitty/pane_controls_lang` to pin a language.

**Agent-aware panes**

- Panes running `claude`, `codex` or `hermes` get a neutral GNOME-colored badge
  (✻ Claude, ›_ Codex, ☤ Hermes). Codex session ids give way to the working
  directory.
- `agy` panes show their session's `/rename` title. Astro reads only the regular
  title annotation file associated with that process's open presence lock;
  renames refresh within two seconds, including when several sessions share a
  directory.
- A red dot marks a pane whose program rang the bell (an agent finished or
  waits for input); `•` marks background output since the pane last had focus.

**Configuration** (`config/kitty.conf`)

- Splits layout with proportional sizing, a 3 × 3 agent workspace session
  (`config/sessions/default.conf`) plus a monitor column.
- GNOME Soft retains GNOME Terminal 3.58.0's color family while blending bright
  highlights up to 15% toward the background and default text by 10%. Already
  dark colors are not dimmed further; modified colors keep at least 4.5:1 contrast
  against the background. The original neutral background `#191919` stays fixed.
  Original and softened palettes are recorded in `tests/fixtures/gnome-palette.json`
  and `tests/fixtures/gnome-soft-palette.json`. Default text is `#bebdba`, with
  GNOME blue `#2a7bde`. No GNOME desktop theme switching is implied.
  Rounded tabs (shown from two tabs on), dimmed inactive panes,
  beam cursor with a short trail, hover-only link underlines.
- Desktop notification when a long shell command finishes in an unfocused
  pane; trailing spaces are stripped when copying from TUIs.
- **Right click:** paste a PNG screenshot copied by Flameshot as a quoted file
  path into the clicked pane; otherwise paste clipboard text. Agent CLIs can
  read the image at that path. This does not emulate a native image attachment.
- **Middle click:** paste the primary text selection, including in mouse-aware
  TUIs. Both mouse bindings take precedence over application mouse handling.
  Ctrl+Shift+V keeps kitty's native clipboard behavior outside SSH.
- **Over SSH:** in a pane running an `ssh` client, right click, Ctrl+Shift+V
  and Ctrl+V upload a clipboard PNG over a second connection with the same
  options and paste the remote path, so remote agent CLIs attach it like a
  local screenshot. A left click on a link opens it on this machine, even when
  a full-screen TUI owns the mouse; the program still receives the click.
  Text pastes and remote OSC 52 clipboard writes work as usual. The second
  connection must log in without a prompt (key or agent); a failed upload shows
  an error and pastes nothing. Only the outermost `ssh` is known, so with nested
  sessions the image lands on the first host. `config/ssh_input.conf` with both
  kittens can be included from a kitty that does not use Astro.

Screenshots stay in `${XDG_CACHE_HOME:-~/.cache}/astro/clipboard` with private
permissions. When saving a new screenshot, Astro retains up to 50 recent
`screenshot-*.png` files from the last 7 days and prunes older or excess
regular screenshot files automatically so earlier pasted paths in active
sessions keep working without unbounded disk growth. The
clipboard itself is never replaced. PNG extraction requires `wl-paste`
(`wl-clipboard`) in a Wayland desktop, or `xclip` in a pure X11 session.
PNG reads are limited to 64 MiB while streaming, with a five-second deadline;
oversized payloads, data without a PNG signature or unavailable clipboard owners
fall back to native clipboard text.
An incomplete file is removed if writing or closing it fails.
Clipboard producer process groups are terminated on completion or failure, so
a wrapper's background pipe owner cannot outlive a completed PNG read.

Terminal programs may read the normal system clipboard without a permission
dialog (`clipboard_control ... read-clipboard`). This also includes programs
running remotely over SSH, so only use trusted programs when the clipboard may
contain sensitive data. Reading the primary selection still requires permission;
paste-safety confirmations remain enabled.

## Tests

Run the standard source, shell-syntax and unit checks from the repository root:

```sh
python3 tools/check.py
```

The runner uses kitty's Python runtime for unit tests and clears display variables
for those tests. ShellCheck runs when installed; `--require-shellcheck` makes it
mandatory. Full verification also rebuilds assets in a temporary clone and runs
real mouse input against a private Xvfb, never the owner's desktop:

```sh
python3 tools/check.py --require-shellcheck --assets --integration
```

The asset check needs the system Python with PyGObject, Rsvg, Cairo and fontTools.
The integration check needs Xvfb and libXtst; `--kitty`, `--xvfb` and
`--xvfb-library-path` support private tool installations. It verifies stale X11
IDs, reloads, normal and Shift splits, source directories, existing processes
and layout proportions. It starts no real agent CLIs and touches no desktop
clipboard. GitHub Actions configures the same checks with a checksum-pinned Kitty
0.49.2 binary and a commit-pinned checkout action.
Whitespace checks cover all tracked source, including in a clean CI checkout.
Shell syntax and ShellCheck also inspect the installer body actually executed
by the lock-owning launcher, not just its outer here-document wrapper. Website
artifact, native/diagram parity and Node website unit tests run automatically
when Node.js is available; see [docs/website.md](docs/website.md) for browser QA.

To run only the unit suite directly:

```sh
kitty +runpy 'import unittest; r = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover("tests")); raise SystemExit(not r.wasSuccessful())'
```

## Requirements

- Python **3.10+** for installation and the optional startup greetings, plus Bash;
  the renderer uses only the standard library and does not use the GPU.
- kitty **0.49.2**. The title-bar mouse handler, `Window._title_bar_screen`
  and the splits layout internals are not public APIs; check Astro after every
  kitty upgrade.
- Linux with kitty on X11 (`linux_display_server x11`, also under Xwayland).
  An isolated native Wayland run with headless Sway and Kitty 0.49.2 verified
  controls, splits, reload, clipboard and dummy-agent badges; [issue #1](https://github.com/itmitalles-de/astro/issues/1)
  records that bounded result. This does not verify real GNOME/KDE desktops,
  decorations or a GPU/hardware matrix. Hover hints remain X11-only.
  On X11, hover hints use checked XCB queries so a stale ID cannot terminate Kitty.
- Optional: Python 3 with [fontTools](https://github.com/fonttools/fonttools)
  to rebuild the icon font.

## Install

```sh
git clone https://github.com/itmitalles-de/astro.git
cd astro
./install.sh
```

The installer copies `config/` into `~/.config/kitty` (or
`$KITTY_CONFIG_DIRECTORY`), backs up replaced files, installs the icon font,
Astro's desktop entry, application icons and `~/.local/bin/astro`. It adds one
managed, Kitty-only source block to `~/.bashrc` (backed up first). It keeps your
shell and aliases unchanged, applies Astro's prompt palette only in Kitty, and
does not modify other terminal emulators. Source files and Bash hook markers are
validated before replacing user files, including write access when the hook needs
an update. An already-current read-only hook requires no write. The update is atomic and preserves
managed-dotfile symlinks, existing permissions and unrelated line endings.
Installation locks reject concurrent runs sharing configuration, data or launcher
directories and the managed Bash hook. Concurrent hook edits are detected before
replacement. Output destinations are checked before installed files are replaced;
outputs must not overwrite the source checkout, including through a symlinked
parent directory or an `ASTRO_BASHRC` target inside the checkout.
Backup directories are private (0700); failures after installation starts remove
any half-written destination file, print the backup location and show the exact
`./install.sh --restore BACKUP_DIR` command to restore backed-up files, symlinks
and `.bashrc`. This is a bounded restore mechanism, not a full filesystem CAS or
power-loss transaction.

**Upgrades preserve `sessions/default.conf`**, including your personal pane layout.
The sample workspace is only copied on first installation. To deliberately reset
it to the sample, use `ASTRO_REPLACE_SESSION=1 ./install.sh`; the previous session
is backed up first. No running panes are closed. For a staged
install, set `KITTY_CONFIG_DIRECTORY`, `XDG_DATA_HOME`, `ASTRO_BIN_DIRECTORY`
and `ASTRO_BASHRC` to staging paths.
`./install.sh --help` only prints help; unknown arguments fail without installing.

Open **Astro** from the application launcher, or run `astro`. At each app
start, the launcher copies the literal `/resume` (without a newline) into the
clipboard and primary selection (set `ASTRO_SEED_CLIPBOARD=off` to disable).
Opening another pane or tab does not overwrite
the clipboard again. Kitty informational options, including help, version and
debugging output, its `@` / `+` command modes, and unsupported `-c`/`-o`
short-option cluster prefixes (which trigger a native parser crash in Kitty
0.49.2) bypass clipboard initialization and are passed through unchanged.
Info-looking text used as another option's value does not turn an ordinary
launch into an informational invocation.
Each clipboard command has a two-second deadline (override with
`ASTRO_CLIPBOARD_TIMEOUT`, positive decimal seconds up to 30 with at most six
fractional digits and an optional `s`). An invalid override skips initialization;
missing GNU `timeout` skips initialization instead of
running an unbounded helper. Clipboard failure never prevents the terminal from opening.
New Kitty processes use `kitty.app.png` as their window icon. Existing processes may
need a restart before their icon changes; no running sessions are closed by
the installer.

## Brand assets

`assets/astro.svg` is the app-icon source; `assets/astro-logo.svg` is the
self-contained wordmark. PNGs are supplied at 32, 64, 128, 256 and 512 pixels.
Rebuild them with the system Python and PyGObject, Rsvg and Cairo installed:

```sh
/usr/bin/python3 tools/build_brand.py
```

## Icon font

All controls use one outline icon font, `fonts/AstroPaneControls.ttf`
(private use area U+E900–U+E90E). Edit the paths in
`tools/build_pane_icons.py` and rebuild it with:

```sh
python3 tools/build_pane_icons.py fonts/AstroPaneControls.ttf
```

Without an output argument, the builder writes to this repository's `fonts/`,
not your installed user fonts. The build is reproducible byte for byte for a
given toolchain; `tools/check_assets.py` checks repeated builds and validates the
shipped glyph outlines and metrics without modifying the working tree.

## License

Copyright (C) 2026 itmitalles.de

Astro is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version. See [LICENSE](LICENSE).
