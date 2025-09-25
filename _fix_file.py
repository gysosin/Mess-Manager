from pathlib import Path

path = Path("file_organizer.py")
text = path.read_text()
text = text.replace('[\\n', '[\n')
path.write_text(text)
