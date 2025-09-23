import os
import shutil
from pathlib import Path
import logging
from datetime import datetime
import argparse
import threading
import time

# Optional imports for web UI
try:
    import webbrowser
    from flask import Flask, render_template, request, jsonify, redirect, url_for
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

class FileOrganizer:
    def __init__(self, downloads_path=None):
        self.downloads_path = downloads_path or os.path.join(os.path.expanduser("~"), "Downloads")
        self.setup_logging()

        self.categories = {
            'Pictures': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.svg', '.webp', '.ico', '.avif'],
            'Video': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp'],
            'Music': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'],
            'Documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.pages', '.xls', '.xlsx', '.csv', '.ods', '.numbers', '.ppt', '.pptx', '.odp', '.key'],
            'Compressed': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.tgz', '.iso', '.ini'],
            'Programs': ['.exe', '.msi', '.deb', '.dmg', '.pkg', '.app'],
            'Code': ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.php', '.rb', '.go', '.rs'],
            'Others': []
        }

    def setup_logging(self):
        log_dir = Path(self.downloads_path) / "file_organizer_logs"
        log_dir.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / f"organizer_{datetime.now().strftime('%Y%m%d')}.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def get_file_category(self, file_extension):
        for category, extensions in self.categories.items():
            if file_extension.lower() in extensions:
                return category
        return 'Others'

    def create_category_folders(self):
        for category in self.categories.keys():
            category_path = Path(self.downloads_path) / category
            category_path.mkdir(exist_ok=True)
            self.logger.info(f"Ensured category folder exists: {category_path}")

    def organize_files(self):
        downloads_path = Path(self.downloads_path)
        if not downloads_path.exists():
            self.logger.error(f"Downloads folder not found: {downloads_path}")
            return

        # Get existing folders to preserve
        existing_folders = {folder.name for folder in downloads_path.iterdir() if folder.is_dir() and not folder.name.startswith('.')}
        self.logger.info(f"Found existing folders: {existing_folders}")

        self.create_category_folders()
        moved_files = 0
        skipped_files = 0

        for file_path in downloads_path.iterdir():
            if file_path.is_file() and not file_path.name.startswith('.'):
                # Skip files already in category folders
                if file_path.parent.name in self.categories or file_path.parent.name in existing_folders:
                    skipped_files += 1
                    self.logger.debug(f"Skipped: {file_path.name} (already in folder)")
                    continue

                file_extension = file_path.suffix
                category = self.get_file_category(file_extension)

                destination_folder = downloads_path / category
                destination_path = destination_folder / file_path.name

                if destination_path.exists():
                    base_name = file_path.stem
                    extension = file_path.suffix
                    counter = 1
                    while destination_path.exists():
                        new_name = f"{base_name}_{counter}{extension}"
                        destination_path = destination_folder / new_name
                        counter += 1

                try:
                    shutil.move(str(file_path), str(destination_path))
                    moved_files += 1
                    self.logger.info(f"Moved: {file_path.name} -> {category}/")
                except Exception as e:
                    self.logger.error(f"Error moving {file_path.name}: {str(e)}")

        self.logger.info(f"Organization complete! Moved {moved_files} files, skipped {skipped_files} files.")
        return moved_files

# Flask Web UI (only if Flask is available)
if FLASK_AVAILABLE:
    app = Flask(__name__)
    organizer_instance = None

    @app.route('/')
    def index():
        return render_template('index.html', default_folder=os.path.join(os.path.expanduser("~"), "Downloads"))

    @app.route('/organize', methods=['POST'])
    def organize():
        folder_path = request.form.get('folder_path')
        if not folder_path or not os.path.exists(folder_path):
            return jsonify({'error': 'Invalid folder path'}), 400

        global organizer_instance
        organizer_instance = FileOrganizer(folder_path)
        moved_files = organizer_instance.organize_files()

        return jsonify({
            'success': True,
            'message': f'Successfully organized {moved_files} files!',
            'folder': folder_path
        })

    @app.route('/browse')
    def browse():
        folder_path = request.args.get('path', os.path.expanduser("~"))
        try:
            items = []
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isdir(item_path):
                    items.append({
                        'name': item,
                        'path': item_path,
                        'type': 'folder'
                    })

            parent_path = os.path.dirname(folder_path) if folder_path != os.path.dirname(folder_path) else None

            return jsonify({
                'current_path': folder_path,
                'parent_path': parent_path,
                'items': sorted(items, key=lambda x: x['name'].lower())
            })
        except PermissionError:
            return jsonify({'error': 'Permission denied'}), 403
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    def run_web_server(port=5000, debug=False):
        app.run(host='127.0.0.1', port=port, debug=debug)

def main():
    parser = argparse.ArgumentParser(description='File Organizer - Organize files into categories')
    parser.add_argument('--folder', '-f', type=str,
                       help='Folder path to organize (default: Downloads folder)')
    parser.add_argument('--web', '-w', action='store_true',
                       help='Start web UI server')
    parser.add_argument('--port', '-p', type=int, default=5000,
                       help='Port for web server (default: 5000)')
    parser.add_argument('--no-browser', action='store_true',
                       help='Don\'t auto-open browser when starting web UI')

    args = parser.parse_args()

    if args.web:
        if not FLASK_AVAILABLE:
            print("Error: Flask is required for web UI mode.")
            print("Install Flask with: pip install flask")
            print("Or use CLI mode without --web flag")
            return

        print(f"Starting File Organizer Web UI on http://127.0.0.1:{args.port}")
        print("Press Ctrl+C to stop the server")

        if not args.no_browser:
            def open_browser():
                time.sleep(1)
                webbrowser.open(f'http://127.0.0.1:{args.port}')

            threading.Thread(target=open_browser, daemon=True).start()

        try:
            run_web_server(port=args.port)
        except KeyboardInterrupt:
            print("\nShutting down web server...")
    else:
        folder_path = args.folder
        organizer = FileOrganizer(folder_path)
        moved_files = organizer.organize_files()
        print(f"Organization complete! Moved {moved_files} files.")

if __name__ == "__main__":
    main()