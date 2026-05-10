import json
import os
import sys
from pathlib import Path
from typing import cast

import hjson
from metadata_utils.CF_Program import Song

# Define the path where the Action writes the file
# GitHub Actions usually puts it here relative to the repo root
INPUT_JSON_PATH = ".github/outputs/all_changed_files.json"

def get_metadata(hjson_path: Path) -> (dict[str, str | int | float] | None):
    try:
        with open(hjson_path, 'r', encoding='utf-8') as f:
            metadata = cast(dict[str, (str | int | float)], hjson.load(f))
        return metadata
    except Exception as e:
        print(f"Error processing {hjson_path}: {e}")
        return None

def main():
    
    # 1. Read from the file instead of ENV
    if os.path.exists(INPUT_JSON_PATH):

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

    else:        
        print(f"No changed files log found at {INPUT_JSON_PATH}")
        files = sys.argv[1:]

    print(f"Processing {len(files)} files...")

    for file_path in files:

        try:
            song_obj = Song(file_path, allow_imcompatible=True)
        except ValueError as e:
            print(e)
            continue
        
        metadata = get_metadata(song_obj.path)
        if not metadata:
            continue

        song_obj.load_hjson(metadata)

        new_stem = song_obj.filename[:-4] # remove the suffix
        new_filepath = song_obj.path.with_stem(new_stem)
        
        # Skip if name is identical
        if song_obj.path.name == new_filepath.name:
            continue
        
        # Handle collision (if new filename already exists)
        if new_filepath.exists():
            print(f"Cannot rename: Target {new_filepath.name} already exists.")
            continue

        print(f"Renaming: [{song_obj.path.name}] -> [{new_filepath.name}]")
        #song_obj.path.rename(new_filepath)

if __name__ == "__main__":
    main()