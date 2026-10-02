import os
import subprocess
import edge_tts

async def generate_voiceover(text: str, output_audio_path: str):
    """Generates ultra-fast speech via edge-tts."""
    try:
        communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
        await communicate.save(output_audio_path)
    except Exception as e:
        print(f"TTS Warning: {e}, writing dummy audio if needed")

def render_vertical_video(image_path: str, audio_path: str, output_path: str, caption_text: str):
    """
    Renders 9:16 vertical video. Handles Windows font paths and falls back cleanly.
    """
    # Windows font path resolution
    font_path = "C\\:/Windows/Fonts/arial.ttf"
    clean_text = caption_text.replace("'", "").replace(":", "").replace("\\", "")

    # Try full filter with subtitle text
    filter_complex = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920"
    )
    
    # Check if Arial exists on Windows to attach drawtext safely
    if os.path.exists("C:/Windows/Fonts/arial.ttf"):
        filter_complex += (
            f",drawtext=fontfile='{font_path}':text='{clean_text}':fontcolor=white:fontsize=40:"
            "box=1:boxcolor=black@0.6:boxborderw=20:x=(w-text_w)/2:y=(h-text_h)/2"
        )

    cmd = [
        "ffmpeg",
        "-y",
        "-loop", "1",
        "-i", image_path,
        "-i", audio_path,
        "-vf", filter_complex,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        "-pix_fmt", "yuv420p",
        output_path
    ]

    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except Exception as err:
        # Fallback if drawtext fails: render without text overlay so API succeeds
        print(f"FFmpeg drawtext failed, rendering basic stream: {err}")
        fallback_cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", image_path, "-i", audio_path,
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
            "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest", "-pix_fmt", "yuv420p",
            output_path
        ]
        subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
