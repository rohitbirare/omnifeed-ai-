import os
import json
import uuid
import shutil
import traceback
import subprocess
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
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
    GenerateJobResponse
)
from video_engine import generate_voiceover, render_vertical_video

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
client = None
if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
    from google import genai
    client = genai.Client(api_key=GEMINI_API_KEY)

@app.get("/")
def health_check():
    ffmpeg_detected = shutil.which("ffmpeg") is not None
    return {
        "status": "healthy",
        "service": "OmniFeed AI Backend",
        "ffmpeg_available": ffmpeg_detected
    }

@app.post("/api/hooks", response_model=HookResponse)
async def generate_hooks(req: TopicRequest):
    if not client:
        return HookResponse(
            community=req.community,
            topic=req.topic,
            hooks=[
                HookItem(id=1, text=f"AI is disrupting {req.topic} faster than predicted.", score=94),
                HookItem(id=2, text=f"How headless pipelines render {req.topic} in under 60s.", score=89),
                HookItem(id=3, text=f"Three critical {req.topic} realities you need to know today.", score=83)
            ]
        )

    prompt = f"Target Community: {req.community}\nTopic: {req.topic}\nGenerate 3 short viral 3-second opening hooks with scores 80-98. Return strictly JSON: {{\"hooks\": [{{\"id\": 1, \"text\": \"...\", \"score\": 94}}]}}"
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
                Scene(scene=1, duration=4, visual="High-tech glowing servers and data streams", voice=req.selected_hook),
                Scene(scene=2, duration=5, visual="Asynchronous decoupled pipeline processing", voice=f"Analyzing {req.topic} through automated workflows."),
                Scene(scene=3, duration=5, visual="Live mobile video feed with kinetic captions", voice="Follow the global feed for real-time updates.")
            ]
        )

    prompt = f"Community: {req.community}\nTopic: {req.topic}\nSelected Hook: {req.selected_hook}\nGenerate 3-scene vertical short video plan. Scene 1 voice must be the hook. Return JSON: {{\"title\": \"{req.topic}\", \"hook\": \"{req.selected_hook}\", \"scenes\": [{{\"scene\": 1, \"duration\": 4, \"visual\": \"...\", \"voice\": \"{req.selected_hook}\"}}]}}"
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

@app.post("/api/generate", response_model=GenerateJobResponse)
async def trigger_generation(req: GenerateRequest):
    job_id = str(uuid.uuid4())[:8]
    audio_path = os.path.join(STATIC_DIR, f"audio_{job_id}.mp3")
    video_path = os.path.join(STATIC_DIR, f"video_{job_id}.mp4")
    image_path = os.path.join(STATIC_DIR, "background.jpg")

    try:
        # Create default background frame safely if it does not exist
        if not os.path.exists(image_path):
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", "color=c=0x0E131F:s=1080x1920:d=1",
                "-vframes", "1", image_path
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # 1. Voice generation (<1s)
        await generate_voiceover(req.hook, audio_path)

        # 2. FFmpeg headless vertical video render (<10s)
        render_vertical_video(image_path, audio_path, video_path, req.hook)

        return GenerateJobResponse(
            job_id=job_id,
            status="completed",
            video_url=f"http://127.0.0.1:8000/static/video_{job_id}.mp4"
        )
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print("GENERATION ERROR:\n", traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
