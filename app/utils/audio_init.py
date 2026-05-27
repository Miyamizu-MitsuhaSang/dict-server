import os
import shutil

import ffprobe8_binaries  # 或 ffprobe_binaries_only
from imageio_ffmpeg import get_ffmpeg_exe
from pydub import AudioSegment

def _find_bundled_ffprobe() -> str:
    package_dir = os.path.dirname(ffprobe8_binaries.__file__)
    for root, _dirs, files in os.walk(package_dir):
        if "ffprobe" in files:
            return os.path.join(root, "ffprobe")
    return "ffprobe"

ffmpeg_path = get_ffmpeg_exe()
ffprobe_path = shutil.which("ffprobe") or _find_bundled_ffprobe()
ffprobe_dir = os.path.dirname(ffprobe_path)

if ffprobe_dir and os.path.exists(ffprobe_dir):
    os.environ["PATH"] = f"{ffprobe_dir}{os.pathsep}{os.environ.get('PATH', '')}"

AudioSegment.converter = ffmpeg_path
AudioSegment.ffmpeg = ffmpeg_path
AudioSegment.ffprobe = ffprobe_path

print(f"[INIT] ffmpeg: {ffmpeg_path}")
print(f"[INIT] ffprobe: {ffprobe_path}")
