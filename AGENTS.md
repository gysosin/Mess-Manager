# Repository Guidelines

## Project Structure & Module Organization
- Root contains `file_organizer.py`, the CLI and optional Flask UI entrypoint.
- `templates/index.html` renders the web interface; keep assets inline or add to `templates/` for now.
- `setup_scheduler.bat` installs a Windows Task Scheduler job; update the path if relocating the repo.
- Logs are persisted under `<Downloads>/file_organizer_logs/` at runtime; avoid checking them into Git.

## Build, Test, and Development Commands
- `python -m venv .venv` and `.\.venv\Scripts\Activate` set up an isolated environment; target Python 3.10+.
- `pip install -r requirements.txt` installs the optional web UI dependency (Flask).
- `python file_organizer.py --help` lists CLI switches; default target is Downloads.
- `python file_organizer.py --web [--port 5050] [--no-browser]` boots the Flask UI.
- `python file_organizer.py --folder C:\path\to\sandbox` is the quickest regression check after changes.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation; keep imports grouped stdlib -> third-party -> local.
- Use `snake_case` for functions and module-level variables, `PascalCase` for classes, and constants in `UPPER_CASE`.
- Prefer `pathlib.Path` and structured logging; reuse the existing `FileOrganizer` methods instead of adding globals.
- Keep user-facing messages neutral and actionable; log details via `logging` instead of `print`.

## Testing Guidelines
- No automated suite yet: validate CLI changes by running `python file_organizer.py --folder <temp>`.
- For web features, exercise the `/organize` and `/browse` endpoints via the UI and check the log output.
- Place future automated tests under `tests/` using `pytest`; mirror scenarios for each category mapping.
- Ensure new categories or behaviors document coverage expectations in README and here.

## Commit & Pull Request Guidelines
- Write imperative, descriptive commit subjects <= 72 chars (e.g., `Add duplicate handling for video files`); keep emojis optional.
- Squash work-in-progress commits before review and explain behavioural changes in the body.
- PRs must describe the motivation, outline manual test results, and link any tracking issues.
- Attach screenshots or terminal captures when touching the Flask UI or scheduler script.
- Request review once linting/manual checks pass and mention follow-up work in a checklist if needed.

## Scheduling & Automation Tips
- Run `setup_scheduler.bat` from an elevated shell to create the `FileOrganizerDaily` task at 09:00.
- Update the script's hard-coded path if the repository moves, or manually adjust it via Task Scheduler.
