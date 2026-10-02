from typing import List, Optional
from pydantic import BaseModel

class TopicRequest(BaseModel):
    community: str
    topic: str

class HookItem(BaseModel):
    id: int
    text: str
    score: int

class HookResponse(BaseModel):
    community: str
    topic: str
    hooks: List[HookItem]

class ScriptRequest(BaseModel):
    community: str
    topic: str
    selected_hook: str

class Scene(BaseModel):
    scene: int
    duration: int
    visual: str
    voice: str

class ScriptResponse(BaseModel):
    title: str
    hook: str
    scenes: List[Scene]

class GenerateRequest(BaseModel):
    community: str
    topic: str
    hook: str

class GenerateJobResponse(BaseModel):
    job_id: str
    status: str
    video_url: Optional[str] = None
    progress: Optional[int] = 0
    message: Optional[str] = None
