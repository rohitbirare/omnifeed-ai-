import os
import subprocess
import edge_tts

async def generate_voiceover(text: str, output_path: str, voice: str = "en-US-ChristopherNeural") -> str:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
    return output_path

def render_vertical_video(image_path: str, audio_path: str, output_path: str, caption_text: str):
    clean_caption = caption_text.replace("'", "").replace(":", "-").replace("\\", "").strip()
    
    # 1080x1920 layout with smooth zoom motion + stylized caption overlay + AI Safety Tag
    filter_complex = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "zoompan=z='min(zoom+0.0012,1.25)':d=125:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920[vbg];"
        f"[vbg]drawtext=text='{clean_caption}':fontsize=54:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-80:"
        "box=1:boxcolor=black@0.7:boxborderw=24,"
        "drawtext=text='AI GENERATED CONTENT':fontsize=26:fontcolor=white@0.75:x=(w-text_w)/2:y=h-130:"
        "box=1:boxcolor=black@0.55:boxborderw=10[vout]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-i", audio_path,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        output_path
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        # Fallback without complex zoom if host CPU is resource-constrained
        simple_filter = (
            f"drawtext=text='{clean_caption}':fontsize=52:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-80:"
            "box=1:boxcolor=black@0.7:boxborderw=20,"
            "drawtext=text='AI GENERATED CONTENT':fontsize=24:fontcolor=white@0.7:x=(w-text_w)/2:y=h-120:"
            "box=1:boxcolor=black@0.5:boxborderw=8"
        )
        fallback_cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", image_path,
            "-i", audio_path,
            "-vf", simple_filter,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            output_path
        ]
        fallback_run = subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if fallback_run.returncode != 0:
            raise RuntimeError(f"FFmpeg render error: {fallback_run.stderr}")

    return output_path
