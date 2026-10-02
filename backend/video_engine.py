import os
import re
import subprocess
import requests
import edge_tts
from faster_whisper import WhisperModel

whisper_instance = None

def get_whisper():
    global whisper_instance
    if whisper_instance is None:
        # Load lightweight CPU optimized model
        whisper_instance = WhisperModel("tiny", device="cpu", compute_type="int8")
    return whisper_instance

async def generate_voiceover(text: str, output_path: str, voice: str = "en-US-ChristopherNeural") -> str:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
    return output_path

def fetch_stock_video_clip(query: str, output_path: str, pexels_api_key: str = None) -> bool:
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
        print(f"Stock video fetch failed: {e}")
    return False

def format_timestamp_ass(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    return f"{hrs:01d}:{mins:02d}:{secs:02d}.{centis:02d}"

def generate_kinetic_ass_subtitles(audio_path: str, output_ass_path: str):
    """Faster-Whisper वापरून अचूक वर्ड-लेव्हल टाईमस्टॅम्प्स आणि ASS फाईल बनवणे."""
    model = get_whisper()
    segments, _ = model.transcribe(audio_path, word_timestamps=True)
    
    ass_header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Kinetic,Arial,64,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,2,40,40,960,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    events = []
    for segment in segments:
        words = getattr(segment, "words", None)
        if words:
            for w in words:
                start = format_timestamp_ass(w.start)
                end = format_timestamp_ass(w.end)
                clean_w = re.sub(r'[^A-Za-z0-9\s!?.,]', '', w.word).upper().strip()
                events.append(f"Dialogue: 0,{start},{end},Kinetic,,0,0,0,,{{\\c&H00FFFF&}}{clean_w}")
        else:
            start = format_timestamp_ass(segment.start)
            end = format_timestamp_ass(segment.end)
            text = segment.text.strip().upper()
            events.append(f"Dialogue: 0,{start},{end},Kinetic,,0,0,0,,{text}")

    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(events))

def render_vertical_video_with_audio(visual_source: str, voice_path: str, bgm_path: str, output_path: str, caption_text: str, is_video: bool = False, ass_path: str = None):
    escaped_ass = ass_path.replace("\\", "/").replace(":", "\\:") if ass_path and os.path.exists(ass_path) else None
    sub_filter = f",subtitles='{escaped_ass}'" if escaped_ass else ""

    if is_video:
        video_filter = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920{sub_filter},"
            "drawtext=text='AI GENERATED CONTENT':fontsize=26:fontcolor=white@0.8:x=(w-text_w)/2:y=h-130:"
            "box=1:boxcolor=black@0.55:boxborderw=10[v]"
        )
        video_inputs = ["-stream_loop", "-1", "-i", visual_source]
    else:
        video_filter = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"zoompan=z='min(zoom+0.0012,1.25)':d=125:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920[vbg];"
            f"[vbg]{sub_filter[1:] if sub_filter else 'null'},"
            "drawtext=text='AI GENERATED CONTENT':fontsize=26:fontcolor=white@0.8:x=(w-text_w)/2:y=h-130:"
            "box=1:boxcolor=black@0.55:boxborderw=10[v]"
        )
        video_inputs = ["-loop", "1", "-i", visual_source]

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
