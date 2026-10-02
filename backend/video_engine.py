import os
import subprocess
import requests
import edge_tts

async def generate_voiceover(text: str, output_path: str, voice: str = "en-US-ChristopherNeural") -> str:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
    return output_path

def fetch_stock_video_clip(query: str, output_path: str, pexels_api_key: str = None) -> bool:
    """Pexels वरून व्हर्टिकल 9:16 स्टॉक व्हिडिओ क्लिप शोधून डाउनलोड करते."""
    if not pexels_api_key or pexels_api_key == "your_pexels_key_here":
        return False
    try:
        headers = {"Authorization": pexels_api_key}
        url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page=1"
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            videos = data.get("videos", [])
            if videos:
                files = videos[0].get("video_files", [])
                hd_files = [f for f in files if f.get("width", 0) >= 720 and "link" in f]
                chosen = hd_files[0] if hd_files else files[0]
                dl = requests.get(chosen["link"], stream=True, timeout=15)
                with open(output_path, "wb") as f:
                    for chunk in dl.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
                return True
    except Exception as e:
        print(f"Stock video fetch failed, using kinetic fallback: {e}")
    return False

def render_vertical_video_with_audio(visual_source: str, voice_path: str, bgm_path: str, output_path: str, caption_text: str, is_video: bool = False):
    clean_caption = caption_text.replace("'", "").replace(":", "-").replace("\\", "").strip()
    
    # 1. व्हिडिओ स्केलिंग आणि कॅप्शन ओव्हरले + AI Safety लेबल
    if is_video:
        video_filter = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"drawtext=text='{clean_caption}':fontsize=52:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-80:"
            "box=1:boxcolor=black@0.7:boxborderw=24,"
            "drawtext=text='AI GENERATED CONTENT':fontsize=26:fontcolor=white@0.8:x=(w-text_w)/2:y=h-130:"
            "box=1:boxcolor=black@0.55:boxborderw=10[v]"
        )
        video_inputs = ["-stream_loop", "-1", "-i", visual_source]
    else:
        video_filter = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            "zoompan=z='min(zoom+0.0012,1.25)':d=125:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920[vbg];"
            f"[vbg]drawtext=text='{clean_caption}':fontsize=52:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-80:"
            "box=1:boxcolor=black@0.7:boxborderw=24,"
            "drawtext=text='AI GENERATED CONTENT':fontsize=26:fontcolor=white@0.8:x=(w-text_w)/2:y=h-130:"
            "box=1:boxcolor=black@0.55:boxborderw=10[v]"
        )
        video_inputs = ["-loop", "1", "-i", visual_source]

    # 2. Audio Ducking (व्हॉईस चालू असताना BGM चे व्हॉल्युम 18% वर आणणे)
    filter_complex = (
        f"{video_filter};"
        "[2:a]volume=0.18[bgm];"
        "[1:a]volume=1.0[voice];"
        "[voice][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
    )

    cmd = [
        "ffmpeg", "-y",
        *video_inputs,
        "-i", voice_path,
        "-i", bgm_path,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "[aout]",
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
        # सुरक्षित फॉलबॅक (केवळ व्हॉईस आणि इमेज)
        fallback_cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", visual_source,
            "-i", voice_path,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            "-shortest",
            output_path
        ]
        subprocess.run(fallback_cmd, check=True)

    return output_path
