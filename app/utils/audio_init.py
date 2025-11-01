import os

import ffprobe8_binaries  # 或 ffprobe_binaries_only
from imageio_ffmpeg import get_ffmpeg_exe
from pydub import AudioSegment

ffprobe_path = os.path.join(os.path.dirname(ffprobe8_binaries.__file__), "bin", "ffprobe")

AudioSegment.converter = get_ffmpeg_exe()
AudioSegment.ffprobe = ffprobe_path  # 👈 指定 ffprobe 路径

print(f"[INIT] ffmpeg: {AudioSegment.converter}")
print(f"[INIT] ffprobe: {AudioSegment.ffprobe}")