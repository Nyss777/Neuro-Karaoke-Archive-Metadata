import os

from .data_verification import validate_payload
from .engraver import build_payload


def create_payload_from_dict(hjson_data: dict[str, (str | int | float)], song_path: str, filename: (str | None) = None) -> str:
    ARG_MAP = {
        "Date": "date",
        "Title": "title",
        "Artist": "artist",
        "CoverArtist": "cover_artist",
        "Version": "version",
        "Discnumber": "disc_number",
        "Track": "track",
        "Comment": "comment",
        "Special": "special",
        "xxHash": "xxhash"
    }

    payload_kwargs = {
    ARG_MAP[field]: str(hjson_data[field]) for field in ARG_MAP
    }

    payload_kwargs["filename"] = filename if filename else os.path.basename(song_path)

    validate_payload(payload_kwargs)
    
    return build_payload(**payload_kwargs)
