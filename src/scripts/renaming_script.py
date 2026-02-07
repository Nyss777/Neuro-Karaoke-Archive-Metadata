from pathlib import Path
from sys import argv
from typing import cast

import hjson
from metadata_utils.CF_Program import Song, process_new_tags

# Assuming Song and process_new_tags are defined in your environment or local utils
# For now, I'll focus on the renaming logic you provided

def get_metadata(hjson_path: str) -> (dict[str, str | int | float] | None):
    try:
        with open(hjson_path, 'r', encoding='utf-8') as f:
            metadata = cast(dict[str, (str | int | float)], hjson.load(f))
        return metadata
    except Exception as e:
        print(f"Error processing {hjson_path}: {e}")
        return None

def main():
    # argv[0] is the script name, argv[1:] are the files passed from the shell
    files = argv[1:]

    for file_path in files:
        path = Path(file_path)
        if not path.exists():
            continue

        metadata = get_metadata(file_path)
        if not metadata:
            continue

        # Transform into dict[str, str]
        new_song_data = {k: str(v) for k, v in metadata.items()}

        # --- Your Custom Logic ---
        song_obj = Song(file_path)
        process_new_tags(song_obj, new_song_data)
        # -------------------------

        new_stem = Path(song_obj.filename).stem
        new_name = path.with_stem(new_stem)
        
        print(f"Renaming: {path.name} -> {new_name.name}")
        path.rename(new_name)

if __name__ == "__main__":
    main()