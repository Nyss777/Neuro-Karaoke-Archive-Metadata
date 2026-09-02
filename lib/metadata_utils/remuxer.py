import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def remux_song(input: Path|bytes, output: Path) -> None:

    if isinstance(input, Path): 
        remux_file(input, output)
    else:
        remux_bytes(input, output)
        

def remux_file(file_path: Path, new_path: Path) -> None:

    if file_path == new_path:
        os.rename(file_path, "temp")

    if sys.platform == "win32":
        # Windows-specific flag to hide the console
        cf_flag = 0x08000000
    else:
        # Linux/macOS don't need extra flags to stay hidden
        cf_flag = 0

    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", file_path,
                "-map_metadata", "0", 
                "-c:a", "copy",
                "-write_xing", "1",
                new_path
            ],
            shell=False,
            capture_output=True, 
            text=True,
            encoding='utf-8',
            creationflags=cf_flag,
            check=True
        )
        if result.returncode != 0:
            logger.critical(f"ffmpeg encountered an issue. Stderr: {result.stderr}")
            
    except Exception:
        logger.exception("Error")

    else:
        logger.debug("Remuxing process run succesufully")
        if file_path == new_path:
            os.remove("temp")


def remux_bytes(audio_data: bytes, new_path: Path) -> None:
    """
    Remux audio data from memory (via stdin) to a file on disk.
    
    Args:
        audio_data: Raw audio file bytes (MP3, FLAC, etc.)
        new_path: Output file path
    """
    if sys.platform == "win32":
        cf_flag = 0x08000000
    else:
        cf_flag = 0

    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", "pipe:0",  # Read from stdin
                "-map_metadata", "0",
                "-c:a", "copy",
                "-write_xing", "1",
                new_path 
            ],
            shell=False,
            input=audio_data,  # Pass raw bytes to stdin
            capture_output=True,
            creationflags=cf_flag,
            check=True
        )
        
        if result.returncode != 0:
            logger.critical(f"ffmpeg encountered an issue. Stderr: {result.stderr}")
                
    except Exception:
        logger.exception("Error")
        raise

    else:
        logger.debug("Remuxing process run succesufully")

