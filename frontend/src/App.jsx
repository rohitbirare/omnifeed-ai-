import { useEffect, useState } from 'react';
import AlertCircle from 'lucide-react/dist/esm/icons/alert-circle.js';
import ArrowUpRight from 'lucide-react/dist/esm/icons/arrow-up-right.js';
import Clapperboard from 'lucide-react/dist/esm/icons/clapperboard.js';
import LoaderCircle from 'lucide-react/dist/esm/icons/loader-circle.js';
import WandSparkles from 'lucide-react/dist/esm/icons/wand-sparkles.js';
import { checkBackend, generateHooks, generateScript, getRenderStatus, renderVideo, resolveVideoUrl } from './api.js';
import HookPicker from './components/HookPicker.jsx';
import VideoPreview from './components/VideoPreview.jsx';

const SAFE_CAPTION_CHARACTERS = /[^A-Za-z0-9 .,!?()'-]/g;

function makeFallbackHooks(topic) {
  const subject = topic.trim() || 'this story';
  return [
    { id: 1, text: `The part of ${subject} nobody is talking about.`, score: 94 },
    { id: 2, text: `Here is what changes when ${subject} moves faster.`, score: 89 },
    { id: 3, text: `Three things to know before you scroll past ${subject}.`, score: 84 },
  ];
}

function makeFallbackScript(topic, hook) {
  return {
    title: topic || 'Untitled short',
    hook,
    scenes: [
      { scene: 1, duration: 4, visual: 'Open on the strongest image or surprising detail.', voice: hook },
      { scene: 2, duration: 5, visual: 'Show the context with one clear visual shift.', voice: `Here is what matters about ${topic}.` },
      { scene: 3, duration: 5, visual: 'Close on the takeaway and a direct next step.', voice: 'Follow for the next update.' },
    ],
  };
}

function App() {
  const [community, setCommunity] = useState('Technology');
  const [topic, setTopic] = useState('The new wave of small, capable AI models');
  const [hooks, setHooks] = useState([]);
  const [selectedHook, setSelectedHook] = useState('');
  const [selectedId, setSelectedId] = useState(null);
  const [script, setScript] = useState(null);
  const [scriptSource, setScriptSource] = useState('');
  const [hooksLoading, setHooksLoading] = useState(false);
  const [scriptLoading, setScriptLoading] = useState(false);
  const [service, setService] = useState({ state: 'checking', ffmpeg: null });
  const [notice, setNotice] = useState('');
  const [renderStatus, setRenderStatus] = useState('idle');
  const [renderError, setRenderError] = useState('');
  const [renderProgress, setRenderProgress] = useState(0);
  const [videoUrl, setVideoUrl] = useState('');
  const [jobId, setJobId] = useState('');

  useEffect(() => {
    let active = true;
    checkBackend()
      .then((result) => {
        if (active) setService({ state: 'online', ffmpeg: Boolean(result.ffmpeg_available) });
      })
      .catch(() => {
        if (active) setService({ state: 'offline', ffmpeg: null });
      });
    return () => { active = false; };
  }, []);

  async function handleGenerateHooks() {
    setHooksLoading(true);
    setNotice('');
    try {
      const result = await generateHooks({ community, topic: topic.trim() });
      setHooks(result.hooks ?? []);
      setSelectedId(null);
      setSelectedHook('');
      setScript(null);
      setNotice('');
    } catch (error) {
      const localHooks = makeFallbackHooks(topic);
      setHooks(localHooks);
      setSelectedId(null);
      setSelectedHook('');
      setScript(null);
      setNotice(`Using local hook suggestions. ${error.message}`);
    } finally {
      setHooksLoading(false);
    }
  }

  function handleSelectHook(hook) {
    setSelectedId(hook.id);
    setSelectedHook(hook.text.slice(0, 180));
    setScript(null);
    setNotice('');
  }

  async function handleGenerateScript() {
    if (!selectedHook.trim()) return;
    setScriptLoading(true);
    setNotice('');
    try {
      const result = await generateScript({
        community,
        topic: topic.trim(),
        selected_hook: selectedHook.trim(),
      });
      setScript(result);
      setScriptSource('Generated with backend');
    } catch (error) {
      setScript(makeFallbackScript(topic.trim(), selectedHook.trim()));
      setScriptSource('Local fallback');
      setNotice(`Showing a local script outline. ${error.message}`);
    } finally {
      setScriptLoading(false);
    }
  }

  async function handleRender() {
    const safeHook = selectedHook.replace(SAFE_CAPTION_CHARACTERS, '').slice(0, 180).trim();
    if (!safeHook) {
      setRenderStatus('error');
      setRenderError('Add a caption using letters, numbers, and basic punctuation before rendering.');
      return;
    }

    setRenderStatus('rendering');
    setRenderProgress(8);
    setRenderError('');
    setVideoUrl('');
    setJobId('');
    try {
      const initialJob = await renderVideo({ community, topic: topic.trim(), hook: safeHook });
      setJobId(initialJob.job_id);

      let job = initialJob;
      const timeoutAt = Date.now() + 10 * 60 * 1000;
      while (!['ready', 'completed', 'failed'].includes(job.status)) {
        setRenderProgress(Math.max(0, Math.min(100, Number(job.progress ?? 0))));
        if (Date.now() >= timeoutAt) throw new Error('Render timed out while waiting for the backend job.');
        await new Promise((resolve) => window.setTimeout(resolve, 1000));
        job = await getRenderStatus(initialJob.job_id);
      }

      if (job.status === 'failed') throw new Error(job.message || 'The backend render job failed.');
      if (!job.video_url) throw new Error('The render completed without returning a video URL.');

      setVideoUrl(resolveVideoUrl(job.video_url));
      setRenderProgress(Number(job.progress ?? 100));
      setRenderStatus('done');
    } catch (error) {
      setRenderError(error.message || 'The voiceover or FFmpeg render failed.');
      setRenderStatus('error');
    }
  }

  const serviceLabel = service.state === 'checking'
    ? 'Checking service'
    : service.state === 'online'
      ? service.ffmpeg ? 'Backend ready' : 'FFmpeg unavailable'
      : 'Backend offline';
  const canWork = Boolean(community.trim() && topic.trim());
  const canRender = Boolean(
    selectedHook.trim()
      && renderStatus !== 'rendering'
      && !(service.state === 'online' && service.ffmpeg === false),
  );

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="wordmark" href="#top" aria-label="OmniFeed Studio home">
          <span className="brand-mark"><Clapperboard size={18} strokeWidth={2.2} /></span>
          <span>OMNIFEED<span className="wordmark-divider">/</span>STUDIO</span>
        </a>
        <div className="topbar-right">
          <span className="mode-label">SHORT-FORM WORKSPACE</span>
          <span className={`service-indicator service-${service.state}`}>
            <span className="service-dot" />{serviceLabel}
          </span>
        </div>
      </header>

      <main id="top" className="workspace">
        <div className="page-intro">
          <div>
            <p className="eyebrow">Creator tools <span>/</span> New video</p>
            <h1>Make the first second count.</h1>
            <p className="intro-copy">Shape the idea, choose the opening, and build a vertical short.</p>
          </div>
          <div className="step-track" aria-label="Workflow steps">
            <span className="step-current"><b>01</b> Shape</span><i />
            <span><b>02</b> Script</span><i />
            <span><b>03</b> Render</span>
          </div>
        </div>

        {notice && (
          <div className="notice" role="status">
            <AlertCircle size={16} aria-hidden="true" />
            <span>{notice}</span>
            <button onClick={() => setNotice('')} aria-label="Dismiss message">Dismiss</button>
          </div>
        )}

        <div className="workbench">
          <section className="authoring-panel" aria-label="Video script and hook studio">
            <div className="studio-section source-section">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">01 / Source</p>
                  <h2>Set the direction</h2>
                </div>
                <span className="section-index">BRIEF</span>
              </div>
              <label className="field-label" htmlFor="community">Community</label>
              <input
                id="community"
                className="text-field"
                value={community}
                maxLength={60}
                onChange={(event) => setCommunity(event.target.value)}
                placeholder="e.g. Technology"
              />
              <div className="field-label-row">
                <label className="field-label" htmlFor="topic">Topic or story</label>
                <span className="char-count">{topic.length}<span> / 160</span></span>
              </div>
              <textarea
                id="topic"
                className="text-field topic-field"
                value={topic}
                maxLength={160}
                onChange={(event) => setTopic(event.target.value)}
                placeholder="What should this short be about?"
                rows={2}
              />
              <div className="source-actions">
                <span>Keep it specific. One clear idea is enough.</span>
                <button className="button button-primary" onClick={handleGenerateHooks} disabled={!canWork || hooksLoading}>
                  {hooksLoading ? <LoaderCircle className="spin" size={16} /> : <WandSparkles size={16} />}
                  {hooksLoading ? 'Generating' : 'Find opening hooks'}
                  {!hooksLoading && <ArrowUpRight size={15} />}
                </button>
              </div>
            </div>

            <HookPicker
              hooks={hooks}
              selectedId={selectedId}
              onSelect={handleSelectHook}
              loading={hooksLoading}
              onGenerate={handleGenerateHooks}
              disabled={!canWork}
            />

            <section className="studio-section script-section" aria-labelledby="script-heading">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">03 / Script</p>
                  <h2 id="script-heading">Build the short</h2>
                </div>
                {scriptSource && <span className={`source-tag${scriptSource === 'Local fallback' ? ' is-fallback' : ''}`}>{scriptSource}</span>}
              </div>

              <label className="field-label" htmlFor="caption">Selected opening / voiceover</label>
              <textarea
                id="caption"
                className="text-field caption-field"
                value={selectedHook}
                maxLength={180}
                onChange={(event) => {
                  setSelectedHook(event.target.value.replace(SAFE_CAPTION_CHARACTERS, ''));
                  setScript(null);
                }}
                placeholder="Choose a hook above or write your own."
                rows={2}
              />
              <div className="script-controls">
                <span className="char-count">{selectedHook.length}<span> / 180 characters</span></span>
                <button className="button button-outline" onClick={handleGenerateScript} disabled={!selectedHook.trim() || scriptLoading}>
                  {scriptLoading ? <LoaderCircle className="spin" size={16} /> : <WandSparkles size={16} />}
                  {scriptLoading ? 'Writing scenes' : 'Generate 3-scene script'}
                </button>
              </div>

              {script ? (
                <div className="scene-list" aria-label="Generated scene outline">
                  {script.scenes.map((scene) => (
                    <article className="scene-row" key={scene.scene}>
                      <span className="scene-number">{String(scene.scene).padStart(2, '0')}</span>
                      <div className="scene-content">
                        <div className="scene-meta"><strong>{scene.scene === 1 ? 'OPEN' : scene.scene === script.scenes.length ? 'CLOSE' : 'DEVELOP'}</strong><span>{scene.duration}s</span></div>
                        <p>{scene.voice}</p>
                        <small>{scene.visual}</small>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="script-empty">Your scene beats will appear here after script generation.</div>
              )}
            </section>
          </section>

          <aside className="output-panel" aria-label="Video preview and render controls">
            <VideoPreview
              src={videoUrl}
              caption={selectedHook}
              jobId={jobId}
              status={renderStatus}
              error={renderError}
              progress={renderProgress}
            />
            <div className="render-action">
              <div className="render-action-copy">
                <span className="eyebrow">04 / Export</span>
                <strong>Ready to make it real?</strong>
                <span>
                  {service.state === 'online' && service.ffmpeg === false
                    ? 'Install FFmpeg on the backend to enable rendering'
                    : 'Voiceover by Edge TTS · Video by FFmpeg'}
                </span>
              </div>
              <button className="button button-render" onClick={handleRender} disabled={!canRender}>
                {renderStatus === 'rendering' ? <LoaderCircle className="spin" size={17} /> : <Clapperboard size={17} />}
                {renderStatus === 'rendering' ? 'Rendering' : 'Render video'}
              </button>
            </div>
            <div className="footnote"><span>OUTPUT FORMAT</span><strong>Vertical 9:16 <i /> 1080 × 1920</strong></div>
          </aside>
        </div>

        <footer className="workspace-footer">
          <span>OMNIFEED STUDIO</span>
          <span>One idea. One short. Keep moving.</span>
        </footer>
      </main>
    </div>
  );
}

export default App;
