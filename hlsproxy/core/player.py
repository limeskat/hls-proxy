import subprocess
import shutil

def launch_mpv(url: str, title: str = "Stream", extra_args: list = None):
    """Launch mpv with the stream URL."""
    if not shutil.which("mpv"):
        raise FileNotFoundError("mpv is not installed or not found in $PATH.")
    
    cmd = [
        "mpv",
        "--no-ytdl",
        "--hwdec=auto",
        "--cache=yes",
        "--cache-secs=60",
        "--demuxer-max-bytes=150M",
        "--demuxer-readahead-secs=30",
        "--stream-lavf-o=reconnect=1,reconnect_streamed=1,reconnect_delay_max=5",
        f"--title={title}",
        url,
    ]
    
    if extra_args:
        cmd.extend(extra_args)
    
    subprocess.run(cmd)
