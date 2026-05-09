import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def remux_song(file_path: Path, new_path: Path) -> None:

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
            creationflags=cf_flag
        )
        if result.returncode != 0:
            logger.critical(f"ffmpeg encountered an issue. Stderr: {result.stderr}")
            
    except Exception as e:
        logger.exception(e)

    else:
        logger.debug("Remuxing process run succesufully")
        if file_path == new_path:
            os.remove("temp")
