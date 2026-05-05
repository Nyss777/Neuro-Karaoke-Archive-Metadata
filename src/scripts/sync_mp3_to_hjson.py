"""
Full sync script: compares MP3s in the archive to HJSONs in the project by xxHash.

For each MP3:
  - If an HJSON with the same xxHash exists:
      - Rename/move the HJSON if the filename or disc folder doesn't match the MP3
      - Update the HJSON content if the metadata has changed
  - If no HJSON with that xxHash exists: create a new one

After processing all MP3s, any remaining HJSONs that have no matching MP3 are deleted.

Usage:
    Put "Neuro Karaoke Archive V3" (the folder with MP3s) one directory above this
    project, then run:
        python sync_mp3_to_hjson.py
"""
import json
import sys
from pathlib import Path

import hjson
from mutagen.id3 import ID3, ID3NoHeaderError

# Project root (two levels up from this file: src/scripts/ -> src/ -> project root)
PROJECT_ROOT = Path(__file__).parent.parent.parent
ARCHIVE_ROOT = PROJECT_ROOT.parent / "Neuro Karaoke Archive V3"

# Fields written to the HJSON, in this order.
# Optional fields are omitted when their value is absent or "None".
# "Special" is omitted unless it is exactly "1".
FIELD_ORDER = [
    "Date",
    "Title",
    "TitleOG",    # optional
    "Identify",   # optional
    "Artist",
    "ArtistOG",   # optional
    "CoverArtist",
    "Version",
    "Discnumber",
    "Track",
    "Comment",    # optional
    "Special",    # optional — only written when "1"
    "xxHash",
]

OPTIONAL_FIELDS = {"TitleOG", "ArtistOG", "Identify", "Comment"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_ved_metadata(mp3_path: Path) -> dict | None:
    """Extract JSON metadata from the COMM::ved ID3 tag of an MP3 file."""
    try:
        tags = ID3(str(mp3_path))
    except ID3NoHeaderError:
        print(f"  [WARN] No ID3 tags: {mp3_path.name}")
        return None
    except Exception as e:
        print(f"  [ERROR] Cannot open {mp3_path.name}: {e}")
        return None

    frame = tags.get("COMM::ved")
    if not frame:
        print(f"  [WARN] No COMM::ved tag: {mp3_path.name}")
        return None

    try:
        return json.loads(str(frame.text[0]))
    except json.JSONDecodeError as e:
        print(f"  [ERROR] Bad JSON in COMM::ved for {mp3_path.name}: {e}")
        return None


def format_hjson(data: dict) -> str:
    """Format a metadata dict as a HJSON string matching the project's style."""
    lines = ["{"]
    for field in FIELD_ORDER:
        value = data.get(field)
        if value is None:
            continue
        value = str(value)
        if field in OPTIONAL_FIELDS and (not value or value == "None"):
            continue
        if field == "Special" and value != "1":
            continue
        lines.append(f"  {field}: {value}")
    lines.append("}")
    return "\n".join(lines)


def build_hjson_index(project_root: Path) -> dict[str, Path]:
    """
    Scan all DISC* folders in the project and return a dict mapping
    xxHash -> hjson_path for every HJSON that has an xxHash field.
    """
    index: dict[str, Path] = {}
    for hjson_file in sorted(project_root.rglob("DISC*/*.hjson")):
        try:
            with open(hjson_file, encoding="utf-8") as f:
                data = hjson.load(f)
            h = str(data.get("xxHash", "")).strip()
            if h:
                index[h] = hjson_file
        except Exception as e:
            print(f"  [WARN] Cannot read {hjson_file.relative_to(project_root)}: {e}")
    return index


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not ARCHIVE_ROOT.exists():
        print(f"Archive folder not found: {ARCHIVE_ROOT}")
        sys.exit(1)

    print("Building HJSON index by xxHash…")
    hjson_index: dict[str, Path] = build_hjson_index(PROJECT_ROOT)
    # Track which hashes were matched by an MP3 so we can delete orphans later
    matched_hashes: set[str] = set()

    created = updated = renamed = skipped = errors = 0

    for disc_folder in sorted(ARCHIVE_ROOT.glob("DISC*")):
        if not disc_folder.is_dir():
            continue

        project_disc = PROJECT_ROOT / disc_folder.name
        if not project_disc.exists():
            print(f"  [MKDIR] {disc_folder.name}")
            project_disc.mkdir()

        for mp3_file in sorted(disc_folder.glob("*.mp3")):
            metadata = get_ved_metadata(mp3_file)
            if not metadata:
                errors += 1
                continue

            xxhash = str(metadata.get("xxHash", "")).strip()
            if not xxhash:
                print(f"  [WARN] No xxHash in tag: {mp3_file.name}")
                errors += 1
                continue

            matched_hashes.add(xxhash)
            expected_path = project_disc / (mp3_file.stem + ".hjson")
            new_content = format_hjson(metadata)

            existing_path = hjson_index.get(xxhash)

            if existing_path is None:
                # Brand-new song — create HJSON
                expected_path.write_text(new_content, encoding="utf-8")
                hjson_index[xxhash] = expected_path
                print(f"  [CREATE] {expected_path.relative_to(PROJECT_ROOT)}")
                created += 1

            else:
                # Song already has an HJSON — check filename and content
                needs_rename = existing_path != expected_path
                current_content = existing_path.read_text(encoding="utf-8")
                needs_update = current_content != new_content

                if needs_rename:
                    if expected_path.exists():
                        print(f"  [CONFLICT] Cannot rename to {expected_path.name} — target already exists; skipping rename")
                    else:
                        print(f"  [RENAME] {existing_path.relative_to(PROJECT_ROOT)}")
                        print(f"        -> {expected_path.relative_to(PROJECT_ROOT)}")
                        existing_path.rename(expected_path)
                        hjson_index[xxhash] = expected_path
                        existing_path = expected_path
                        renamed += 1

                if needs_update:
                    existing_path.write_text(new_content, encoding="utf-8")
                    print(f"  [UPDATE] {existing_path.relative_to(PROJECT_ROOT)}")
                    updated += 1

                if not needs_rename and not needs_update:
                    skipped += 1

    # Delete HJSONs whose hash was never matched by any MP3
    deleted = 0
    for h, hjson_path in hjson_index.items():
        if h not in matched_hashes and hjson_path.exists():
            print(f"  [DELETE] {hjson_path.relative_to(PROJECT_ROOT)}  (no matching MP3)")
            hjson_path.unlink()
            deleted += 1

    print(
        f"\nDone: {created} created, {updated} updated, {renamed} renamed, "
        f"{deleted} deleted, {skipped} unchanged, {errors} errors"
    )


if __name__ == "__main__":
    main()
