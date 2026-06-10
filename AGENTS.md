# Repository Guidelines

## Project Overview

This is a small Windows desktop tray app built with Python and PySide6. The app reminds the user to stand up during configured work hours, persists settings in the user app config directory, and uses a single-instance guard.

## Key Files

- `main.py`: application entry point, tray menu, single-instance behavior, and top-level scheduling.
- `config.py`: config dataclass, UTF-8 JSON persistence, path handling, and value normalization.
- `reminder.py`: reminder timing, work-hour checks, pause/mute state, and elapsed-time formatting.
- `startup.py`: current-user Windows auto-start registration.
- `widgets.py`: PySide6 reminder popup, mascot image widget, and settings window.
- `create_icon.py`: generates `assets/app_icon.ico` for packaging.
- `build_exe.bat`: Windows packaging script that runs icon generation and PyInstaller.
- `StandingReminder.spec`: PyInstaller spec file.
- `requirements.txt`: pinned runtime/build dependencies.
- `assets/`: generated icon and mascot image assets. `app_icon.ico` is generated; `standing_mascot.png` is a required runtime asset.

## Common Commands

Run from the repository root:

```powershell
python .\main.py
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Build the Windows executable:

```powershell
.\build_exe.bat
```

The packaged executable is written to:

```text
dist\StandingReminder.exe
```

Quick syntax check:

```powershell
python -m py_compile main.py config.py reminder.py startup.py widgets.py create_icon.py
```

Run unit tests:

```powershell
python -m unittest discover -s tests
```

## Development Notes

- Keep changes small and focused; the app is intentionally compact, with UI in `widgets.py`, scheduling in `reminder.py`, and persistence in `config.py`.
- Preserve the Windows/PySide6 behavior when changing UI or startup code.
- Do not commit generated build outputs such as `build/`, `dist/`, `__pycache__/`, generated icons/images, or source ZIPs.
- If changing packaging, verify both `build_exe.bat` and `StandingReminder.spec` still agree on the app name, icon, and bundled assets.
- When editing user-facing Chinese strings, be careful with file encoding. Some terminal output may display mojibake even when the file bytes are valid.
