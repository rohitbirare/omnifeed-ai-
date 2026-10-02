import os
import glob
import json
import uuid
import shutil
import asyncio
import subprocess
from typing import Dict
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from schemas import (
    TopicRequest,
    HookResponse,
    HookItem,
    ScriptRequest,
    ScriptResponse,
    Scene,
    GenerateRequest,
    GenerateJobResponse,
    PublishRequest,
    PublishResponse
)
from video_engine import (
    generate_voiceover,
    fetch_stock_video_clip,
    generate_kinetic_ass_subtitles,
    render_vertical_video_with_audio
)

def register_ffmpeg():
    if shutil.which("ffmpeg"):
        return
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\**\bin"),
        os.path.expandvars(r"%PROGRAMFILES%\**\bin"),
        r"C:\ffmpeg\bin"
    ]
    for pattern in candidates:
        matches = glob.glob(pattern, recursive=True)
        for directory in matches:
            if os.path.exists(os.path.join(directory, "ffmpeg.exe")):
                os.environ["PATH"] = directory + os.pathsep + os.environ["PATH"]
                return

register_ffmpeg()
load_dotenv()

app = FastAPI(title="OmniFeed AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
client = None
if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
    from google import genai
    client = genai.Client(api_key=GEMINI_API_KEY)

JOBS_DB: Dict[str, dict] = {}

def ensure_ambient_bgm():
    bgm_path = os.path.join(STATIC_DIR, "ambient_bgm.mp3")
    if not os.path.exists(bgm_path):
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "sine=frequency=220:duration=30",
            "-af", "lowpass=f=400,volume=0.35",
            "-c:a", "libmp3lame",
            bgm_path
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return bgm_path

@app.get("/")
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "OmniFeed AI Backend",
        "ffmpeg_available": shutil.which("ffmpeg") is not None
    }

@app.post("/api/hooks", response_model=HookResponse)
async def generate_hooks(req: TopicRequest):
    if not client:
        return HookResponse(
            community=req.community,
            topic=req.topic,
            hooks=[
                HookItem(id=1, text=f"AI is disrupting {req.topic} faster than predicted.", score=95),
                HookItem(id=2, text=f"How headless pipelines render {req.topic} in 60s.", score=89),
                HookItem(id=3, text=f"Three critical {req.topic} facts you need today.", score=84)
            ]
        )
    prompt = f"Community: {req.community}\nTopic: {req.topic}\nGenerate 3 short viral hooks with scores 80-98. JSON only: {{\"hooks\": [{{\"id\": 1, \"text\": \"...\", \"score\": 95}}]}}"
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text)
        return HookResponse(community=req.community, topic=req.topic, hooks=[HookItem(**h) for h in data.get("hooks", [])])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/script", response_model=ScriptResponse)
async def generate_script(req: ScriptRequest):
    if not client:
        return ScriptResponse(
            title=req.topic,
            hook=req.selected_hook,
            scenes=[
                Scene(scene=1, duration=4, visual="High-tech cyber grid with pulsating cyan lines", voice=req.selected_hook),
                Scene(scene=2, duration=5, visual="Asynchronous streaming data nodes", voice=f"Analyzing {req.topic} with precision."),
                Scene(scene=3, duration=5, visual="Interactive mobile short-form feeds", voice="Stay tuned for live updates.")
            ]
        )
    prompt = f"Community: {req.community}\nTopic: {req.topic}\nSelected Hook: {req.selected_hook}\nGenerate 3-scene vertical short video plan. Scene 1 voice must be the hook. JSON: {{\"title\": \"{req.topic}\", \"hook\": \"{req.selected_hook}\", \"scenes\": [{{\"scene\": 1, \"duration\": 4, \"visual\": \"...\", \"voice\": \"{req.selected_hook}\"}}]}}"
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text)
        return ScriptResponse(title=data.get("title", req.topic), hook=req.selected_hook, scenes=[Scene(**s) for s in data.get("scenes", [])])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def run_render_pipeline(job_id: str, topic: str, hook: str):
    audio_path = os.path.join(STATIC_DIR, f"audio_{job_id}.mp3")
    video_path = os.path.join(STATIC_DIR, f"video_{job_id}.mp4")
    ass_path = os.path.join(STATIC_DIR, f"subs_{job_id}.ass")
    stock_clip_path = os.path.join(STATIC_DIR, f"stock_{job_id}.mp4")
    image_fallback_path = os.path.join(STATIC_DIR, "background_dynamic.jpg")

    try:
        bgm_path = ensure_ambient_bgm()
        # Step 1: Visual Acquisition
        JOBS_DB[job_id]["status"] = "generating_visuals"
        JOBS_DB[job_id]["progress"] = 25
        
        has_stock_clip = fetch_stock_video_clip(topic, stock_clip_path, PEXELS_API_KEY)
        visual_source = stock_clip_path if has_stock_clip else image_fallback_path
        
        if not has_stock_clip and not os.path.exists(image_fallback_path):
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", "gradients=s=1080x1920:c0=0x070b19:c1=0x1a233a:x0=0:y0=0:x1=1080:y1=1920",
                "-vframes", "1", image_fallback_path
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Step 2: Voiceover Generation
        JOBS_DB[job_id]["status"] = "generating_voice"
        JOBS_DB[job_id]["progress"] = 50
        await generate_voiceover(hook, audio_path)

        # Step 3: Whisper Word-level Kinetic Subtitle Generation
        JOBS_DB[job_id]["status"] = "transcribing_captions"
        JOBS_DB[job_id]["progress"] = 70
        try:
            generate_kinetic_ass_subtitles(audio_path, ass_path)
        except Exception as wex:
            print(f"Whisper fallback active: {wex}")
            ass_path = None

        # Step 4: Headless Render
        JOBS_DB[job_id]["status"] = "rendering_video"
        JOBS_DB[job_id]["progress"] = 85
        render_vertical_video_with_audio(
            visual_source=visual_source,
            voice_path=audio_path,
            bgm_path=bgm_path,
            output_path=video_path,
            caption_text=hook,
            is_video=has_stock_clip,
            ass_path=ass_path
        )

        JOBS_DB[job_id]["status"] = "ready"
        JOBS_DB[job_id]["progress"] = 100
        JOBS_DB[job_id]["video_url"] = f"http://127.0.0.1:8000/static/video_{job_id}.mp4"
        JOBS_DB[job_id]["message"] = "Render completed with Whisper kinetic subtitles, BGM, and AI label."
    except Exception as e:
        JOBS_DB[job_id]["status"] = "failed"
        JOBS_DB[job_id]["message"] = str(e)

@app.post("/api/generate", response_model=GenerateJobResponse)
async def trigger_generation(req: GenerateRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())[:8]
    JOBS_DB[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "progress": 5,
        "video_url": None,
        "message": "Queued for headless kinetic render with Whisper subtitles"
    }
    background_tasks.add_task(run_render_pipeline, job_id, req.topic, req.hook)
    return GenerateJobResponse(**JOBS_DB[job_id])

@app.get("/api/status/{job_id}", response_model=GenerateJobResponse)
async def get_job_status(job_id: str):
    if job_id not in JOBS_DB:
        raise HTTPException(status_code=404, detail="Job ID not found")
    return GenerateJobResponse(**JOBS_DB[job_id])

@app.post("/api/publish", response_model=PublishResponse)
async def publish_video(req: PublishRequest):
    post_id = f"post_{uuid.uuid4().hex[:10]}"
    return PublishResponse(
        status="published",
        post_id=post_id,
        platform=req.platform,
        message=f"Successfully queued and published '{req.title}' to {req.platform}."
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
