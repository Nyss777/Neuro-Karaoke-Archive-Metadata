import json
import os
from pathlib import Path
from typing import cast

import hjson
from metadata_utils.CF_Program import Song, process_new_tags

# Define the path where the Action writes the file
# GitHub Actions usually puts it here relative to the repo root
INPUT_JSON_PATH = ".github/outputs/all_changed_files.json"

def get_metadata(hjson_path: str) -> (dict[str, str | int | float] | None):
    try:
        with open(hjson_path, 'r', encoding='utf-8') as f:
            metadata = cast(dict[str, (str | int | float)], hjson.load(f))
        return metadata
    except Exception as e:
        print(f"Error processing {hjson_path}: {e}")
        return None

def main():
    # 1. Read from the file instead of ENV
    if not os.path.exists(INPUT_JSON_PATH):
        print(f"No changed files log found at {INPUT_JSON_PATH}")
        return

    c = ""
    try:
        with open(INPUT_JSON_PATH, 'r', encoding='utf-8') as f:
            c = f.read()
            f.seek(0)
            files = json.load(f)

    except Exception as e:
        print(f"JSON File Parsing Error: {e}")
        print(c)
        return

    print(f"Processing {len(files)} files...")

    for file_path in files:
        path = Path(file_path)
        
        # Security check: Ensure we only touch existing files
        if not path.exists():
            print(f"Skipping missing file: {file_path}")
            continue

        metadata = get_metadata(file_path)
        if not metadata:
            continue

        # Transform into dict[str, str]
        new_song_data = {k: str(v) for k, v in metadata.items()}

        # --- Your Custom Logic ---
        try:
            song_obj = Song(file_path)
            process_new_tags(song_obj, new_song_data)
        except Exception as e:
            print(f"Failed to process tags for {path.name}: {e}")
            continue
        # -------------------------

        new_stem = Path(song_obj.filename).stem
        new_name = path.with_stem(new_stem)
        
        # Skip if name is identical
        if path.name == new_name.name:
            continue
        
        # Handle collision (if new filename already exists)
        if new_name.exists():
            print(f"Cannot rename: Target {new_name.name} already exists.")
            continue

        print(f"Renaming: [{path.name}] -> [{new_name.name}]")
        path.rename(new_name)

if __name__ == "__main__":
    main()