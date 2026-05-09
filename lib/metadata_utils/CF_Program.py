import json
import logging
import os
import re
import unicodedata
from pathlib import Path

import hjson
import xxhash
from mutagen.id3 import (
    APIC,
    COMM,
    ID3,
    SYLT,
    TALB,
    TDRC,
    TIT2,
    TPE1,
    TPE2,
    TPOS,
    TRCK,
    USLT,
    Encoding,
    ID3NoHeaderError,
)
from tinytag import TinyTag

from .embed_lyrics import (
    contains_cjk,
    convert_lyric_complex,
    convert_lyric_simple,
    get_embedded_lyrics,
)

logger = logging.getLogger(__name__)

with open( Path(__file__).parent.parent.parent / "config.txt" ) as f:
    ALBUMS_COVER_PATH = Path(f.read())

ALBUM_COVERS = {
    "1": 'Disc 1 cover art by paccha.jpg',  
    "2": 'Disc 2 cover art by kapxapius.jpg',  
    "3": 'Disc 3 cover art by paccha.jpg',     
    "4": 'Disc 4 cover art by ppchan.jpg',   
    "5": 'Disc 5 cover art by paccha.jpg',     
    "6": 'Disc 6 cover art by koilccc.jpg',
    "7": 'Disc 7 cover art by nostyx.jpg',
    "8": 'Disc 8 cover art by lukuwo.jpg',
    # "66": 'Disc 66 cover art by tanhuluu.jpg',
    "天天天国地獄国": 'Tententengoku Jigokukoku cover art by copper1ion.jpg',
}

class Song:
    
    Date: str = ''
    Title: str = '' # Promise of English
    TitleOG: str = '' # Not english
    Identify: str = ''
    Artist: str = ''
    ArtistOG: str = ''
    CoverArtist: str = ''
    Version: str = ''
    Discnumber: str = ''
    Track: str = ''
    Comment: str = ''
    Special: str = ''
    xxHash: str = ''

    def __repr__(self) -> str:
        return self.filename

    def __eq__(self, other: object, /) -> bool:
        if not isinstance(other, Song):
            return False
        return self.filename + self.xxHash == other.filename + self.xxHash

    def __hash__(self) -> int:
        return hash(self.filename + self.xxHash)

    @property
    def filename(self) -> str:
    
        if not (self.Artist and self.Title):
            return self.path.name

        filename = f"{self.Track_Number}. {self.Artist} - {self.Title} "
        if self.Identify:
            filename += f"({self.Identify}) "


        if '&' not in self.CoverArtist:
            filename += f"({self.CoverArtist}.v{self.Version})"

        else:
            filename += f"(Duet.v{self.Version}) ({self.CoverArtist})"
            
        filename = sanitize_filename(filename)
        filename += '.mp3'

        return filename

    @property
    def TIT2(self) -> str:

        if self.TitleOG:
            TIT2 = f"{self.TitleOG} ({self.Title})"
        else:
            TIT2 = self.Title

        if self.Identify:
            TIT2 += f" - {self.Identify}"

        return TIT2

    @property
    def TPE1(self) -> str:

        artist = f"{self.ArtistOG} ({self.Artist})" if self.ArtistOG else self.Artist

        if '&' not in self.CoverArtist:
            return  f"{self.CoverArtist} - {artist}"
        else:
            return f"Duet ({self.CoverArtist}) - {artist}"

    @property
    def TALB(self) -> str:
        Discs = {
            "1": 'Humble Beginnings',    
            "2": 'A Small Upgrade',    
            "3": 'The Gold Standard',    
            "4": 'First Anniversary',   
            "5": 'Non-Stop Innovation',
            "6": 'Second Anniversary',
            "7": 'Background Running Process',
            "8": 'Third Anniversary',
        }
        return f"{Discs.get(self.Discnumber, "INVALID ALBUM NUMBER").upper()}: Neuro-Sama Karaoke Vol. {self.Discnumber}"

    @property
    def TDRC(self) -> str:
        return self.COMM_ENG[:4]

    @property
    def COMM_ENG(self) -> str:
        if not self.Comment:
            self.Comment = "None"

        if self.Comment != "None":
            return f"{self.Date} //{self.Comment}"
        else:
            return self.Date 

    @property
    def Track_Number(self) -> str:

        """Track number with 3-digit padding"""

        # Try to extract from Track info (like "12/279")
        track_info = self.Track
        if track_info and '/' in track_info:
            track_num = track_info.split('/')[0]
            return track_num.zfill(3)  # 3-digit padding
        return track_info.zfill(3)

    @property
    def TRCK(self) -> str:
        return self.Track

    FIELDS = (
            "Date", 
            "Title", 
            "TitleOG",
            "Identify",
            "Artist",
            "ArtistOG", 
            "CoverArtist", 
            "Version", 
            "Discnumber", 
            "Track", 
            "Comment",
            "Special",
            "xxHash"
            )

    def __init__(self, path: Path | str):
        self.path = Path(path)

        if not self.path.exists() or self.path.is_dir():
            raise ValueError("The specified path is invalid!",
                            f"Invalid path: {self.path}")

        if self.path.suffix != ".mp3":
            raise ValueError("Incompatible format, only compatible with mp3s!",
                            f"Invalid path: {self.path}")

        self.load()

    def load(self) -> None:
        payload = self._get_raw_json()
        if not payload:
            return

        data = json.loads(payload)
        self.load_dict(data)

    def save(self) -> None:
        self.set_tags()
        self.rename()

    def load_hjson(self, hjson_data: dict[str, (str | int | float)]) -> None:

        data = {
        field: str(hjson_data.get(field)) for field in self.FIELDS
        }

        self.load_dict(data)

    def load_dict(self, d: dict[str, str]):

        for field in self.FIELDS:
            if field in d:
                # print(f"{field} - {d[field]}")
                if d[field] == "None":
                    continue

                setattr(self, field, d[field])

        if self.Special == "":
            self.Special = "0"

            # else:            
            #     print(f"Missing key: {field} - {self.filename}")

    def get_raw(self, key: str) -> str:

        json = self._get_raw_json()

        pattern = f"\"{key}\":\"(.*?)\""

        match = re.search(pattern, json)

        if match is None:
            return ""
        else:
            return match.group(1)

    def _get_raw_json(self) -> str:

        """Return raw JSON string or an empty string."""

        path = Path(self.path)

        tags = TinyTag.get(path, tags=True, image=False)

        texts = tags.other.get("comment") or []
        if tags.comment:
            texts.append(tags.comment)

        if not texts:
            print("No comments found")
            return ""
        
        for text in texts:
            if text.startswith('{"Date":'):
                return text

        return ""

    def _get_raw_element(self, json: str, key: str) -> str:

        pattern = f"\"{key}\":\"(.*?)\""

        match = re.search(pattern, json)

        if match is None:
            return ""
        else:
            return match.group(1)

    def build_payload(self) -> str:
        
        payload = {}

        for field in self.FIELDS:
            field_value = getattr(self, field)
            field_value = field_value if field_value else "None"
            payload[field] = field_value
        
        return json.dumps(payload, separators=(',', ':'))
    
    def set_tags(self) -> None:

        try:
            tags = ID3(self.path)
        except ID3NoHeaderError:
            # If no tags exist, create a blank ID3 object
            tags = ID3()
    
        tags.delall("TXXX")
        tags.add(TPE1(encoding=3, text=[self.TPE1]))
        tags.add(TALB(encoding=3, text=[self.TALB]))
        tags.add(TIT2(encoding=3, text=[self.TIT2]))
        tags.add(TRCK(encoding=3, text=[self.TRCK]))
        tags.add(TPE2(encoding=3, text=["QueenPb + vedal987"]))
        tags.add(TDRC(encoding=3, text=[self.TDRC]))
        tags.add(TPOS(encoding=3, text=[self.Discnumber]))

        tags.add(COMM(encoding=3, lang='ved', desc='', text=[self.build_payload()]))
        tags.add(COMM(encoding=2,lang='eng', desc='',text=[self.COMM_ENG]))
        tags.add(COMM(encoding=2,lang='eng', desc='ID3v1 Comment',text=[self.COMM_ENG]))
        
        tags.save(self.path)

    def set_image(self, image_path: Path):

        if not (image_path.exists() and image_path.is_file()):
            print("Please select a valid image!")
            return

        image_data = image_path.read_bytes()

        try:
            tags = ID3(self.path)
        except ID3NoHeaderError:
            tags = ID3()

        image_type = image_path.suffix.strip(".")
        if image_type.lower() == "jpg":
            image_type = "jpeg"

        if image_data and (image_type.lower() in ("jpeg", "png")):

            tags.delall('APIC') 
                
            tags.add(
                APIC(
                    encoding=3,       
                    mime=f'image/{image_type.lower()}', 
                    type=3, 
                    desc='Cover (Front)', 
                    data=image_data
                )
            )
            logger.debug("Image added to APIC frame")

            tags.save()

    def set_album_image(self):

        cover_image = title_match if (title_match := ALBUM_COVERS.get(self.TitleOG)) else ALBUM_COVERS.get(self.Discnumber, "") 

        self.set_image(ALBUMS_COVER_PATH / cover_image)


    def rename(self) -> None:
        new_path = self.path.with_name(self.filename)

        if new_path == self.path:
            return

        if new_path.exists() and new_path.is_file():
            raise FileExistsError(f"{new_path} already exists!")
        else:
            try:
                os.rename(self.path, new_path)

            except Exception:
                raise

            else:
                self.path = new_path

    def get_hash(self) -> str | None:
        try:
            file_size = self.path.stat().st_size
            if file_size < 3000:
                print(f"{self.path.name} is too small!")
                return None

            with open(self.path, 'rb') as f:
                xxhash = get_audio_hash(f.read(), file_size)
                return xxhash
                
        except Exception as e:
            print(f"Error processing {self.path}: {e}")
            return None

    def make_hjson(self, output_folder: Path | str):

        output_folder = Path(output_folder)

        if not (output_folder.exists() and output_folder.is_dir()):
            print("Please Pass a Valid Folder!",
                 f"Invalid Folder: {output_folder}")
            return

        song_data = {field: value for field in self.FIELDS if (value := getattr(self, field))}

        if not song_data:
            print("No data found")
            return

        filename = self.filename.replace(".mp3", ".hjson")
        directory = self.path.parent.name
        output_location = output_folder / directory / filename

        song_data["Discnumber"] = int(self.Discnumber)
        song_data["Special"] = int(self.Special)

        if '.' in self.Version:
            song_data["Version"] = float(self.Version)
        else:
            song_data["Version"] = int(self.Version)

        if '/' not in self.Track:
            song_data["Track"] = int(self.Track)

        if song_data["Special"] == 0:
            del song_data["Special"]

        os.makedirs(output_location.parent, exist_ok=True)
        with open(output_location, 'w', encoding='utf-8') as f:
            hjson.dump(song_data, f)
            print(f"hjons made in {output_location}")

    def print_tags(self):

        print("filename: ", self.filename)
        print("TIT2: ", self.TIT2)
        print("TPE1: ", self.TPE1)
        print("TALB: ", self.TALB)
        print("TDRC: ", self.TDRC)
        print("COMM_ENG: ", self.COMM_ENG)
        print("TRCK: ", self.TRCK)

    def embed_lyrics(self, lrc_path: Path | str):
        tags = ID3(self.path)    

        embedded_lyrics = set(map(str.strip, get_embedded_lyrics(self.path)))
        # 1. Parse the LRC file into (text, timestamp) tuples

        with open(lrc_path, 'r', encoding='utf-8') as f:
            lyrics = f.read().strip()

        if lyrics in embedded_lyrics:
            return
            
        bilingual = contains_cjk(lyrics)
        sylt_data = convert_lyric_complex(lyrics=lyrics) if bilingual is True else convert_lyric_simple(lyrics=lyrics)  
                    
        language = "jpn" if bilingual else "eng"

        tags.delall("SYLT")
        tags.delall("USLT")

        # 2. Add the SYLT frame
        # type=1 (lyrics), format=2 (milliseconds)
        tags.add(USLT(
        encoding=Encoding.UTF8,
        lang=language, 
        text=lyrics.strip()
        ))

        tags.add(SYLT(
            encoding=Encoding.UTF8,
            lang=language, 
            format=2, 
            type=1,
            text=sylt_data
        ))
        
        # print(sylt_data)

        tags.save()
        logger.debug(f"Successfully embedded synced lyrics into {self.path}")

def get_all_mp3_as_obj(directory: Path | str) -> list[Song]: 
    """
    Returns as Song objects all mp3 files from a directory and it's sub-directories.
    """
    p = Path(directory)
    return [(Song(f)) for f in p.rglob('*.mp3') if f.is_file()]

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

def get_audio_hash(file: bytes, file_size: int) -> (str | None):
    try:

        footer_size = 0
         # Seek 128 bytes from the end (2)
        if file[-128:-128+3] == b'TAG':
            footer_size = 128

        if (file_size - footer_size - 1_000_000) > 987: # check to prevent negative indexes
            end_index = file_size - footer_size - 1_000_000 ### about a Mb offset for the audio

        else:
            end_index = int(3*(file_size - footer_size)/4)

        start_index = end_index - 987 ### reads a 987 bytes for the hash

        raw_audio = file[start_index:end_index]

        # 4. Hash the raw audio
        return xxhash.xxh64(raw_audio).hexdigest()

    except Exception:
        logging.exception
        return None
