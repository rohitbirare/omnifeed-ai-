import Download from 'lucide-react/dist/esm/icons/download.js';
import Pause from 'lucide-react/dist/esm/icons/pause.js';
import Play from 'lucide-react/dist/esm/icons/play.js';
import Volume2 from 'lucide-react/dist/esm/icons/volume-2.js';
import { useEffect, useRef, useState } from 'react';

function formatTime(seconds) {
  if (!Number.isFinite(seconds)) return '0:00';
  const minutes = Math.floor(seconds / 60);
  const remainder = Math.floor(seconds % 60).toString().padStart(2, '0');
  return `${minutes}:${remainder}`;
}

export default function VideoPreview({ src, caption, jobId, status, error, progress }) {
  const videoRef = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    setPlaying(false);
    setCurrentTime(0);
    setDuration(0);
  }, [src]);

  async function togglePlayback() {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      await videoRef.current.play();
    } else {
      videoRef.current.pause();
    }
  }

  function seek(event) {
    if (!videoRef.current || !duration) return;
    const nextTime = Number(event.target.value);
    videoRef.current.currentTime = nextTime;
    setCurrentTime(nextTime);
  }

  return (
    <section className="preview-panel" aria-label="Video preview and render status">
      <div className="preview-heading">
        <div>
          <p className="eyebrow">Output / 9:16</p>
          <h2>Preview</h2>
        </div>
        {src && (
          <a className="icon-button" href={src} download={`omnifeed-${jobId || 'video'}.mp4`} aria-label="Download rendered video" title="Download video">
            <Download size={17} />
          </a>
        )}
      </div>

      <div className={`preview-frame${status === 'rendering' ? ' is-rendering' : ''}`}>
        {src ? (
          <video
            ref={videoRef}
            src={src}
            playsInline
            preload="metadata"
            onPlay={() => setPlaying(true)}
            onPause={() => setPlaying(false)}
            onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
            onLoadedMetadata={(event) => setDuration(event.currentTarget.duration)}
            onEnded={() => setPlaying(false)}
          />
        ) : (
          <div className="preview-placeholder">
            <div className="placeholder-mark"><span /><span /><span /></div>
            <p>YOUR STORY, IN MOTION</p>
            <span>Rendered video appears here</span>
          </div>
        )}
        {status === 'rendering' && (
          <div className="render-overlay" role="status" aria-live="polite">
            <span className="spinner" />
            <strong>Rendering your short</strong>
            <span>Voiceover and frames are being assembled</span>
            <div className="render-progress"><span style={{ width: `${progress}%` }} /></div>
            <small>{Math.round(progress)}%</small>
          </div>
        )}
        {!src && status !== 'rendering' && caption && (
          <div className="caption-preview">{caption}</div>
        )}
      </div>

      {src ? (
        <div className="player-controls">
          <button className="player-play" onClick={togglePlayback} aria-label={playing ? 'Pause video' : 'Play video'}>
            {playing ? <Pause size={16} fill="currentColor" /> : <Play size={16} fill="currentColor" />}
          </button>
          <span className="time-readout">{formatTime(currentTime)}</span>
          <input
            className="timeline"
            aria-label="Seek video"
            type="range"
            min="0"
            max={duration || 0}
            step="0.1"
            value={Math.min(currentTime, duration || 0)}
            onChange={seek}
          />
          <span className="time-readout">{formatTime(duration)}</span>
          <Volume2 size={16} className="volume-icon" aria-hidden="true" />
        </div>
      ) : (
        <div className="preview-placeholder-meta">
          <span><span className="tiny-dot" /> 1080 × 1920</span>
          <span>MP4 / H.264</span>
        </div>
      )}

      <div className={`queue-status${error ? ' has-error' : ''}`} aria-live="polite">
        <div className="queue-status-icon">{error ? '!' : status === 'rendering' ? <span className="spinner spinner-small" /> : <span className="queue-dot" />}</div>
        <div className="queue-copy">
          <strong>{error ? 'Render failed' : status === 'rendering' ? 'In progress' : src ? 'Render complete' : 'Queue is ready'}</strong>
          <span>{error || (jobId ? `Job ${jobId}` : 'Your next render will show here')}</span>
        </div>
        <span className={`queue-state${error ? ' state-error' : status === 'rendering' ? ' state-active' : src ? ' state-done' : ''}`}>
          {error ? 'Error' : status === 'rendering' ? 'Rendering' : src ? 'Done' : 'Idle'}
        </span>
      </div>
    </section>
  );
}
