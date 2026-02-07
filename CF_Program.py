import json
import logging
import unicodedata
from json import JSONDecodeError
from pathlib import Path
from typing import TypedDict

from mutagen.id3 import (
    APIC,
    COMM,
    ID3,
    TALB,
    TDRC,
    TIT2,
    TPE1,
    TPE2,
    TPOS,
    TRCK,
    ID3NoHeaderError,
)
from mutagen.mp3 import MP3

from .engraver import get_content_from_tags

logger = logging.getLogger(__name__)

class Song:
    # Those variables do NOT refer to the raw information, but to the ID3v2 tags.
    # e.g., 'comment' is never "None" but instead could be "2025-06-07"
    filename: str = ''
    title: str = ''
    artist: str = ''
    date: str = ''
    album: str = ''
    comment: str = '' 
    track: str = ''

    def __init__(self, path: str | Path):
        self.path = path

REPLACEMENT_MAP = { "%t":"Title",
                    "%a":"Artist",
                    "%D":"Date",
                    "%c":"CoverArtist",
                    "%v":"Version",
                    "%A":"Discnumber",
                    "%T_n":"Track",
                    "%C":"Comment"
                    }

def get_track_number(song_data: dict[str, str]) -> str:

    """Extract track number from track info or filename, or use sequential numbering"""

    # Try to extract from track info (like "12/279")
    track_info = song_data["Track"]
    if track_info and '/' in track_info:
        track_num = track_info.split('/')[0]
        return track_num.zfill(3)  # 3-digit padding
    return track_info.zfill(3)

secondary_map = { "%N": get_track_number}

class Patterns(TypedDict):
    filename: tuple[str, str]
    title: str
    artist: tuple[str, str]
    date: str
    album: str
    comment: tuple[str, str] | str
    track: str

pattern_defaults: Patterns = {
    "filename": ("%N. %a - %t (%c.v%v)", "%N. %a - %t (Duet.v%v) (%c)"),
    "title": "%t",
    "artist": ("%c - %a", "Duet (%c) - %a"),
    "date": "%D",
    "album": "Disc %A",
    "comment": ("%D //%C", "%D"),
    "track": "%T_n"
}

def get_all_mp3_as_obj(directory: str) -> list[Song]: 
    """
    Returns as Song objects all mp3 files from a directory and it's sub-directories.
    """
    p = Path(directory)
    return [(Song(f)) for f in p.rglob('*.mp3') if f.is_file()]

# if user input is %title, replace with title
def _substitution(new_filename_pattern: str, song_data: dict[str, str]) -> str: 
    new_value = new_filename_pattern
    for r_key in REPLACEMENT_MAP:
        new_value = new_value.replace(r_key, song_data[REPLACEMENT_MAP[r_key]])
    for s_key in secondary_map:
        new_value = new_value.replace(s_key, secondary_map[s_key](song_data))
    return new_value

def get_song_data(song_path: str | Path) -> tuple[str, dict[str, str], ID3]:
    song_payload = None
    song_data = {}

    audio = MP3(song_path, ID3=ID3)

    if audio.tags is None:
        audio.add_tags()

    if not isinstance(audio.tags, ID3):
        msg = "Program unable to initialize ID3 tags for song"
        logger.error(msg)
        raise TypeError(msg)

    song_payload = get_content_from_tags(audio.tags, "COMM::ved")

    try:
        if song_payload:
            song_data : dict[str, str] = json.loads(song_payload)
    except JSONDecodeError:
        logger.exception("File couldn't be processed! Error decoding the comment!")
        raise
    
    return song_payload, song_data, audio.tags

def set_tags(path: str, song: Song, image_type: (str | None), image_data: (bytes | None) = None) -> None:

    audio = MP3(path, ID3=ID3)
    
    if audio.tags is None:
        audio.add_tags()

    if not isinstance(audio.tags, ID3):
        msg = "Program unable to initialize ID3 tags for song"
        logger.error(msg)
        raise TypeError(msg)

    audio.tags.delall("TXXX")
    audio.tags.add(TPE1(encoding=3, text=[song.artist]))
    audio.tags.add(TALB(encoding=3, text=[song.album]))
    audio.tags.add(TIT2(encoding=3, text=[song.title]))
    audio.tags.add(TRCK(encoding=3, text=[song.track]))
    audio.tags.add(TPE2(encoding=3, text=["QueenPb + vedal987"]))
    audio.tags.add(TDRC(encoding=3, text=[song.comment[:4]]))
    audio.tags.add(TPOS(encoding=3, text=[song.album.replace("Disc ", "")]))

    NEW_COMM_ENG_FRAME = COMM(encoding=2,lang='eng', desc='',text=[song.comment])
    audio.tags.add(NEW_COMM_ENG_FRAME)
    NEW_COMM_V1_ENG_FRAME = COMM(encoding=2,lang='eng', desc='ID3v1 Comment',text=[song.comment])
    audio.tags.add(NEW_COMM_V1_ENG_FRAME)
    
    if image_data and image_type and (image_type.lower() in ("jpeg", "png")):

        audio.tags.delall('APIC') 
            
        audio.tags.add(
            APIC(
                encoding=3,       
                mime=f'image/{image_type}', 
                type=3, 
                desc='Cover (Front)', 
                data=image_data
            )
        )
        logger.debug("Image added to APIC frame")
    # else:
        # logger.debug(
        #     f"image_data: {image_data[:10] if isinstance(image_data, bytes) else None}; "
        #     f"image_type: {image_type};\n"
        #     "No image was added to song"
        # )

    audio.save()
    
def set_tags_fast(path: str, song: Song, image_type: (str | None), image_data: (bytes | None) = None) -> None:

    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        # If no tags exist, create a blank ID3 object
        tags = ID3()
 
    tags.delall("TXXX")
    tags.add(TPE1(encoding=3, text=[song.artist]))
    tags.add(TALB(encoding=3, text=[song.album]))
    tags.add(TIT2(encoding=3, text=[song.title]))
    tags.add(TRCK(encoding=3, text=[song.track]))
    tags.add(TPE2(encoding=3, text=["QueenPb + vedal987"]))
    tags.add(TDRC(encoding=3, text=[song.comment[:4]]))
    tags.add(TPOS(encoding=3, text=[song.album.replace("Disc ", "")]))

    NEW_COMM_ENG_FRAME = COMM(encoding=2,lang='eng', desc='',text=[song.comment])
    tags.add(NEW_COMM_ENG_FRAME)
    NEW_COMM_V1_ENG_FRAME = COMM(encoding=2,lang='eng', desc='ID3v1 Comment',text=[song.comment])
    tags.add(NEW_COMM_V1_ENG_FRAME)
    
    if image_data and image_type and (image_type.lower() in ("jpeg", "png")):

        tags.delall('APIC') 
            
        tags.add(
            APIC(
                encoding=3,       
                mime=f'image/{image_type}', 
                type=3, 
                desc='Cover (Front)', 
                data=image_data
            )
        )
        logger.debug("Image added to APIC frame")
    # else:
        # logger.debug(
        #     f"image_data: {image_data[:10] if isinstance(image_data, bytes) else None}; "
        #     f"image_type: {image_type};\n"
        #     "No image was added to song"
        # )

    tags.save(path)


def sanitize_filename(filename: str) -> str:
    FORBIDDEN_CHARS = {
        '\\': ' backslash ',
        '/': ' slash ',
        ':': ' ', 
        '*': '_', 
        '?': ' ',
        '"': "'",
        '<': '[',
        '>': ']',
        '|': '_'
    }

    for char in FORBIDDEN_CHARS:
        filename = filename.replace(char, FORBIDDEN_CHARS[char])

    while("  " in filename):
        filename = filename.replace("  ", " ")

    ## some kanji were getting divided into two symbols: ヴ -> ウ  ゙
    filename = unicodedata.normalize('NFC', filename)

    return filename

def process_new_tags(song: Song, song_data: (dict[str, str] | None) = None) -> None :
    # added song parameter just in the case of wanting to skip the get_song_data overhead 

    if not song_data:
        _, song_data, _ = get_song_data(song.path)

        if not song_data:
            logger.debug(f"No existing payload found for {song.path}")
            return None
    
    song.title = _substitution(pattern_defaults["title"], song_data)

    if "&" in song_data["CoverArtist"]:
        temp_filename = _substitution(pattern_defaults["filename"][1], song_data)
        song.artist = _substitution(pattern_defaults["artist"][1], song_data)
    else:
        song.artist = _substitution(pattern_defaults["artist"][0], song_data)
        temp_filename = _substitution(pattern_defaults["filename"][0], song_data)

    song.date = _substitution(pattern_defaults["date"], song_data)
    song.album = _substitution(pattern_defaults["album"], song_data)
    song.track = _substitution(pattern_defaults["track"], song_data)

    if not song_data["Comment"]:
        song_data["Comment"] = "None"

    if song_data["Comment"] != "None":
        song.comment = _substitution(pattern_defaults["comment"][0], song_data)
    else:
        song.comment = _substitution(pattern_defaults["comment"][1], song_data)  

    new_filename = sanitize_filename(temp_filename)
    new_filename += '.mp3'

    song.filename = new_filename