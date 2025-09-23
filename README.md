# File Organizer

Automatically categorizes and organizes files into appropriate category folders with both CLI and Web UI support.

## Features
- **Dual Mode**: Command-line interface or Web UI
- **Zero Dependencies for CLI**: Works without any package installation
- **Smart Organization**: Organizes files by extension into predefined categories
- **Folder Selection**: Choose any folder to organize (not just Downloads)
- **Daily Scheduling**: Runs daily via Windows Task Scheduler
- **Safe Operation**: Handles duplicate files, preserves existing folders
- **Comprehensive Logging**: Detailed logs for all operations

## File Categories
- **Pictures**: jpg, png, gif, svg, avif, etc.
- **Video**: mp4, avi, mkv, mov, etc.
- **Music**: mp3, wav, flac, aac, etc.
- **Documents**: pdf, doc, txt, rtf, xls, xlsx, csv, ppt, pptx, etc.
- **Compressed**: zip, rar, 7z, tar, tgz, iso, ini, etc.
- **Programs**: exe, msi, deb, dmg, etc.
- **Code**: py, js, html, css, java, etc.
- **Others**: All unmatched files

## Usage Options

### CLI Mode (No Dependencies Required)
```bash
# Organize Downloads folder (default)
python file_organizer.py

# Organize specific folder
python file_organizer.py --folder "C:/Users/username/Documents"
python file_organizer.py -f "D:/MyFiles"

# Show help
python file_organizer.py --help
```

### Web UI Mode
```bash
# Install Flask (one-time setup)
pip install flask

# Start web server
python file_organizer.py --web

# Custom port
python file_organizer.py --web --port 8080

# Don't auto-open browser
python file_organizer.py --web --no-browser
```

## Setup Instructions

### 1. Schedule Daily Execution
Run as Administrator:
```bash
setup_scheduler.bat
```

This creates a Windows Task Scheduler task that runs daily at 9:00 AM.

### 2. Customize Schedule
- Open Windows Task Scheduler
- Find "FileOrganizerDaily" task
- Modify timing as needed

## Logs
Check `Downloads/file_organizer_logs/` for daily operation logs.

## Safety
- Only moves files, never deletes
- Skips hidden files and folders
- Handles file name conflicts automatically
- Creates category folders as needed