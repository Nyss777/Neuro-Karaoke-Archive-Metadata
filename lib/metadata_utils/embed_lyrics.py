import re
from pathlib import Path

from tinytag import TinyTag


def get_embedded_lyrics(path: Path | str) -> set[str]:

    path = Path(path)

    tags = TinyTag.get(path, tags=True, image=False)

    lyrics = tags.other.get("lyrics") or []

    return set(lyrics)

def contains_cjk(text: str):
    # This range covers:
    # \u4e00-\u9fff: Common Chinese/Japanese Kanji
    # \u3040-\u30ff: Japanese Hiragana & Katakana
    cjk_pattern = re.compile(r'[\u4e00-\u9fff\u3040-\u30ff]')
    
    return bool(cjk_pattern.search(text))

def convert_time_to_ms(time_str: str) -> int | None:

    if ':' not in time_str:
        return
    
    try:
        column_split = time_str.split(':')

        if (lenght_split := len(column_split)) == 2:
            m, s = column_split
            total_ms = int((float(m) * 60 + float(s)) * 1000)

        elif lenght_split == 3:
            m, s, ms = column_split
            total_ms = (int(m) * 60 + int(s)) * 1000 + int(ms)

        else:
            return

        return total_ms

    except Exception as e:
        print(time_str.split(':'))
        print(e)

    return  

def convert_lyric_simple(lyrics: str) -> list[tuple[str, int]]:

    sylt_data: list[tuple[str, int]] = []
    lines = lyrics.split('\n')

    for line in lines:

        if not line.startswith('['):
            continue

        # Simple parser for [mm:ss.xx] text
        parts = line.split(']', 1)
        time_str = parts[0][1:]
        text = f"{parts[1].strip()}"

        ms = convert_time_to_ms(time_str)
        if not ms:
            continue

        sylt_data.append((text, ms))

    return sylt_data

def convert_lyric_complex(lyrics: str) -> list[tuple[str, int]]:

    sylt_data: list[tuple[str, int]] = []
    lines = iter(lyrics.strip().split('\n'))
    temp_line = ''

    while True:

        try:
            odd_line = next(lines) if not temp_line else temp_line
            odd_parts = odd_line.split(']', 1) # "[00:02:27", "abc"
            odd_time_str = odd_parts[0][1:] # "00:02:27"
        except StopIteration:
            break

        try:
            even_line = next(lines)
            even_parts = even_line.split(']', 1)
            even_time_str = even_parts[0][1:]
        except StopIteration:

            text = odd_parts[1].strip()
            
            ms = convert_time_to_ms(odd_time_str)
            if not ms:
                break

            sylt_data.append((text, ms))
            break

        if odd_time_str == even_time_str:

            text = f"{odd_parts[1].strip()}\n{even_parts[1].strip()}"
            
            ms = convert_time_to_ms(odd_time_str)
            if not ms:
                continue

            sylt_data.append((text, ms))

            temp_line = ''

        else:
            text = odd_parts[1].strip()
            
            ms = convert_time_to_ms(odd_time_str)
            if not ms:
                continue

            sylt_data.append((text, ms))

            temp_line = even_line


    return sylt_data