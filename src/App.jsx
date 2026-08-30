import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  IconAlertTriangle,
  IconArrowsShuffle,
  IconCamera,
  IconChevronRight,
  IconCpu,
  IconDatabase,
  IconFocus2,
  IconGauge,
  IconLock,
  IconPlayerPlay,
  IconRoute,
  IconShieldCheck,
  IconVideo,
} from '@tabler/icons-react';
import { useLiveRuntime } from './liveRuntime';

const MEDIA = {
  A: { name: 'North Concourse', location: 'Main circulation', src: '/feeds/feed-a-clear.mp4', quality: 'CLEAR' },
  B: { name: 'East Entry', location: 'Access control', src: '/feeds/feed-b-degraded.mp4', quality: 'DEGRADED' },
  C: { name: 'Garden Gate', location: 'Perimeter', src: '/feeds/feed-c-temporal.mp4', quality: 'TEMPORAL' },
};

const DEFAULT_CAMERAS = [
  { camera_id: 'A', camera_name: 'North Concourse', location: 'Main circulation', task_id: 'PERSON', model_id: 'person-yolox-tiny', operating_mode: 'SAFETY', priority: 5, minimum_deep_rate_fps: 0.2, maximum_wait_ms: 3000, enabled: true },
  { camera_id: 'B', camera_name: 'East Entry', location: 'Access control', task_id: 'PERSON', model_id: 'person-yolox-tiny', operating_mode: 'PRIORITY', priority: 4, minimum_deep_rate_fps: 0, maximum_wait_ms: 3000, enabled: true },
  { camera_id: 'C', camera_name: 'Garden Gate', location: 'Perimeter', task_id: 'PERSON', model_id: 'person-yolox-tiny', operating_mode: 'ADAPTIVE', priority: 3, minimum_deep_rate_fps: 0, maximum_wait_ms: 3000, enabled: true },
];

const REASONS = {
  SAFETY_REQUIREMENT: 'Safety service interval reached',
  MANUAL_OVERRIDE: 'Operator override has protected priority',
  REQUIRED_MINIMUM_SERVICE: 'Minimum service commitment reached',
  PROTECTED_RATE_SATISFIED: 'Protected rate currently satisfied',
  DETERMINISTIC_PRIORITY_AGE_BASELINE: 'Priority, scene value, and wait selected this route',
  ADAPTIVE_DWELL_HOLD: 'Dispatch held to prevent rapid switching',
  MODEL_NOT_RESIDENT: 'Assigned model is not resident',
  MODEL_NOT_REGISTERED: 'Assigned model is not registered',
};

const fmt = (value, digits = 1) => (Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : '—');
const cameraId = (camera) => camera?.camera_id || camera?.id;
const clock = (value) =>
  value
    ? new Date(value).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : '—';

export default function App() {
  const runtime = useLiveRuntime();
  const snapshot = runtime.v2Snapshot;
  const usingFixtures = !snapshot;
  const decision = runtime.v2Decision;
  const configured = snapshot?.cameras?.length ? snapshot.cameras : DEFAULT_CAMERAS;

  const cameras = useMemo(
    () =>
      configured.map((camera) => ({
        ...camera,
        ...MEDIA[cameraId(camera)],
        camera_name: camera.camera_name || camera.name || MEDIA[cameraId(camera)]?.name || `Camera ${cameraId(camera)}`,
        location: camera.location || MEDIA[cameraId(camera)]?.location || 'Unassigned location',
      })),
    [configured]
  );

  const [focusedId, setFocusedId] = useState('A');
  const [busy, setBusy] = useState(null);
  const [actionError, setActionError] = useState('');

  const selectedId = decision?.selected_camera_id;
  useEffect(() => {
    if (selectedId) setFocusedId(selectedId);
  }, [selectedId]);

  const focused = cameras.find((camera) => cameraId(camera) === focusedId) || cameras[0];
  const candidates = decision?.candidates || [];
  const candidateById = Object.fromEntries(candidates.map((item) => [item.camera_id, item]));
  const overrides = new Map((snapshot?.overrides || []).map((item) => [item.camera_id || item, item]));
  const model = snapshot?.models?.find((item) => item.model_id === focused?.model_id) || snapshot?.models?.[0];
  const capacity = snapshot?.capacity;
  const protectedFps = capacity?.protected_required_fps?.[model?.model_id || focused?.model_id];
  const safeFps = capacity?.model_safe_fps?.[model?.model_id || focused?.model_id] ?? model?.safe_throughput_fps;
  const utilization =
    Number.isFinite(Number(protectedFps)) && Number.isFinite(Number(safeFps)) && Number(safeFps) > 0
      ? Math.min(100, (Number(protectedFps) / Number(safeFps)) * 100)
      : null;

  const focusedInference = runtime.inferenceByCamera[focusedId];
  const focusedCandidate = candidateById[focusedId];

  const toggleOverride = async () => {
    setBusy(focusedId);
    setActionError('');
    try {
      await runtime.override(focusedId, !overrides.has(focusedId));
    } catch (error) {
      setActionError(error.message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="app-shell">
      <SystemHeader runtime={runtime} decision={decision} usingFixtures={usingFixtures} />
      <span className="sr-only" aria-live="polite">
        {decision
          ? `Dispatch updated: Camera ${decision.selected_camera_id}, ${REASONS[decision.reason_code] || decision.reason_code}`
          : 'Waiting for a live scheduler decision'}
      </span>

      <main className="operations" id="operations">
        {/* Cockpit Region: 3-column layout where CameraIndex is sticky ONLY inside this container */}
        <section className="cockpit-layout" aria-label="Operational cockpit">
          <CameraIndex
            cameras={cameras}
            focusedId={focusedId}
            selectedId={selectedId}
            overrides={overrides}
            inference={runtime.inferenceByCamera}
            onSelect={setFocusedId}
          />

          <div className="stage-container">
            <section className="instrument-stage" aria-label="Live camera operations">
              <div className="stage-heading">
                <div>
                  <h1>{focused?.camera_name || 'Camera unavailable'}</h1>
                  <p>
                    {focused?.location} · Camera {focusedId} · Task {focused?.task_id || 'unassigned'} ·{' '}
                    {focused?.model_id || 'No model assigned'}
                    {usingFixtures ? ' · DEMONSTRATION FIXTURE' : ''}
                  </p>
                </div>
                <div className="stage-state">
                  <StateMark
                    tone={usingFixtures ? 'warn' : selectedId === focusedId ? 'active' : 'neutral'}
                    label={
                      usingFixtures
                        ? 'Runtime unconfirmed'
                        : selectedId === focusedId
                        ? 'Production inference'
                        : 'Light observation'
                    }
                  />
                  <strong>{focusedCandidate?.rank ? `RANK ${String(focusedCandidate.rank).padStart(2, '0')}` : 'UNRANKED'}</strong>
                </div>
              </div>

              <MeasuredFeed camera={focused} inference={focusedInference} active={selectedId === focusedId} />

              <div className="measurement-strip" aria-label="Focused camera measurements">
                <Measurement label="People" value={focusedInference?.person_count} />
                <Measurement
                  label="Inference"
                  value={focusedInference?.inference_ms != null ? `${fmt(focusedInference.inference_ms)} ms` : null}
                />
                <Measurement label="Utility" value={fmt(focusedCandidate?.sage_utility, 3)} />
                <Measurement label="Support" value={fmt(focusedCandidate?.sage_confidence, 2)} />
                <Measurement
                  label="Wait"
                  value={focusedCandidate?.wait_ms != null ? `${fmt(focusedCandidate.wait_ms / 1000)} s` : null}
                />
                <Measurement label="Priority" value={focused?.priority ? `${focused.priority} / 5` : null} />
              </div>

              <div className="operator-action">
                <div>
                  <span>Operator control</span>
                  <p>
                    {overrides.has(focusedId)
                      ? `Override protected until ${clock(overrides.get(focusedId)?.expires_at)}`
                      : 'Five-minute protected dispatch override'}
                  </p>
                </div>
                <button
                  className={overrides.has(focusedId) ? 'control-button release' : 'control-button'}
                  disabled={!runtime.connected || busy === focusedId}
                  onClick={toggleOverride}
                >
                  <IconLock size={15} />
                  {busy === focusedId ? 'Applying control…' : overrides.has(focusedId) ? 'Release override' : 'Take control'}
                </button>
              </div>

              {actionError && (
                <div className="inline-alert" role="alert">
                  <IconAlertTriangle size={16} />
                  <span>{actionError}. Verify the edge runtime and try again.</span>
                </div>
              )}
            </section>

            <section className="secondary-feeds" aria-labelledby="secondary-title">
              <SectionHeading
                id="secondary-title"
                title="Camera array"
                meta={
                  usingFixtures
                    ? `${cameras.length} demonstration fixtures / runtime unconfirmed`
                    : `${cameras.length} configured / ${cameras.filter((item) => item.enabled !== false).length} enabled`
                }
              />
              <div className="secondary-grid">
                {cameras.map((camera) => (
                  <CompactFeed
                    key={cameraId(camera)}
                    camera={camera}
                    active={selectedId === cameraId(camera)}
                    focused={focusedId === cameraId(camera)}
                    candidate={candidateById[cameraId(camera)]}
                    inference={runtime.inferenceByCamera[cameraId(camera)]}
                    onSelect={setFocusedId}
                  />
                ))}
              </div>
            </section>
          </div>

          <InstrumentationRail
            runtime={runtime}
            decision={decision}
            model={model}
            capacity={capacity}
            protectedFps={protectedFps}
            safeFps={safeFps}
            utilization={utilization}
            focused={focused}
            focusedCandidate={focusedCandidate}
          />
        </section>

        {/* System Traces & Analytics Region: Full-width stacked sections */}
        <section className="traces-layout" aria-label="System traces and analytics">
          <CandidateTable candidates={candidates} selectedId={selectedId} cameras={cameras} onSelect={setFocusedId} />
          <DecisionSequence
            decisions={runtime.decisionHistory.length ? runtime.decisionHistory : snapshot?.recent_decisions || []}
            cameras={cameras}
          />
          <PolicyMatrix cameras={cameras} overrides={overrides} usingFixtures={usingFixtures} />
          <EvidencePanel decision={decision} />
        </section>
      </main>

      <footer>
        <span>CAHMA Control</span>
        <span>CAHMA Arena v2 · local edge orchestration</span>
        <span>Decision evidence retained locally</span>
      </footer>
    </div>
  );
}

function SystemHeader({ runtime, decision, usingFixtures }) {
  const age = useEventAge(runtime.lastEventAt);
  const status = runtime.connected ? (age > 8 ? 'stale' : 'live') : runtime.phase;
  const labels = {
    live: 'Runtime live',
    stale: 'Events stale',
    connecting: 'Connecting',
    disconnected: 'Disconnected',
    degraded: 'Runtime unavailable',
    demo: 'Static interface',
  };
  return (
    <header className="system-header">
      <div className="header-left">
        <a className="wordmark" href="#operations" aria-label="CAHMA Control operations">
          <span className="wordmark-mark">
            <IconFocus2 size={18} />
          </span>
          <span>
            <strong>CAHMA</strong> CONTROL
            <small>ARENA V2 RUNTIME</small>
          </span>
        </a>
        <nav aria-label="Dashboard sections">
          <a href="#operations">Operations</a>
          <a href="#candidates">Candidates</a>
          <a href="#decisions">Decisions</a>
          <a href="#policies">Policies</a>
          <a href="#evidence">Evidence</a>
        </nav>
      </div>

      <div className="header-instruments">
        <span className="header-reading">
          <small>NODE</small>
          <b>{usingFixtures ? 'UNCONFIRMED' : 'EDGE-01'}</b>
        </span>
        <span className="header-reading">
          <small>CADENCE</small>
          <b>{usingFixtures ? 'UNCONFIRMED' : '0.5 Hz'}</b>
        </span>
        <span className={`connection-state ${status}`} aria-live="polite">
          <i />
          {labels[status] || status}
          {runtime.lastEventAt && <small>{age}s</small>}
        </span>
        <span className="header-reading decision-id">
          <small>DECISION</small>
          <b>{decision?.decision_id || 'AWAITING'}</b>
        </span>
      </div>
    </header>
  );
}

function CameraIndex({ cameras, focusedId, selectedId, overrides, inference, onSelect }) {
  return (
    <aside className="camera-index" aria-label="Camera index">
      <div className="index-title">
        <IconVideo size={16} />
        <span>
          CAMERA
          <br />
          INDEX
        </span>
      </div>
      <div className="camera-index-list">
        {cameras.map((camera) => {
          const id = cameraId(camera);
          const active = id === selectedId;
          return (
            <button
              key={id}
              className={`${id === focusedId ? 'focused' : ''} ${active ? 'active' : ''}`}
              onClick={() => onSelect(id)}
              aria-pressed={id === focusedId}
            >
              <span className="camera-letter">{id}</span>
              <span className="camera-index-copy">
                <b>{camera.camera_name}</b>
                <small>
                  {camera.operating_mode} · {inference[id]?.person_count ?? '—'} detected
                </small>
              </span>
              <span className="camera-flags">
                {overrides.has(id) && <IconLock size={13} aria-label="Override active" />}
                {active && <IconPlayerPlay size={13} aria-label="Selected for inference" />}
              </span>
            </button>
          );
        })}
      </div>
      <div className="index-legend">
        <span>
          <i className="legend-live" /> selected
        </span>
        <span>
          <i /> monitored
        </span>
      </div>
    </aside>
  );
}

function MeasuredFeed({ camera, inference, active }) {
  const videoRef = useRef(null);
  const [frame, setFrame] = useState({ width: 0, height: 0 });

  const updateFrame = () =>
    setFrame({ width: videoRef.current?.videoWidth || 0, height: videoRef.current?.videoHeight || 0 });

  const boxes = inference?.boxes_xyxy || [];

  return (
    <div className={`measured-feed ${active ? 'active' : ''}`}>
      {camera?.src ? (
        <video ref={videoRef} src={camera.src} autoPlay muted loop playsInline onLoadedMetadata={updateFrame} />
      ) : (
        <div className="feed-unavailable">
          <IconCamera size={30} />
          <strong>NO LOCAL FEED</strong>
          <span>Runtime camera has no mapped demonstration source</span>
        </div>
      )}
      <div className="reticle" aria-hidden="true">
        <i />
        <i />
        <i />
        <i />
      </div>
      <div className="feed-coordinate top">
        FRAME {frame.width || '—'} × {frame.height || '—'}
      </div>
      <div className="feed-coordinate bottom">
        {camera?.quality || 'RUNTIME'} / {camera?.task_id || 'UNASSIGNED'}
      </div>
      {frame.width > 0 &&
        boxes.slice(0, 12).map((box, index) => (
          <span
            key={`${box.join('-')}-${index}`}
            className="detection-box"
            style={{
              left: `${(box[0] / frame.width) * 100}%`,
              top: `${(box[1] / frame.height) * 100}%`,
              width: `${((box[2] - box[0]) / frame.width) * 100}%`,
              height: `${((box[3] - box[1]) / frame.height) * 100}%`,
            }}
          >
            <b>P{String(index + 1).padStart(2, '0')}</b>
          </span>
        ))}
      <div className="feed-tally">
        <i />
        {active ? 'INFERENCE ACTIVE' : 'OBSERVATION ONLY'}
      </div>
    </div>
  );
}

function InstrumentationRail({
  runtime,
  decision,
  model,
  capacity,
  protectedFps,
  safeFps,
  utilization,
  focused,
  focusedCandidate,
}) {
  const gpu = runtime.telemetry?.utilization ?? runtime.telemetry?.gpu_utilization ?? runtime.telemetry?.utilization_percent;
  const modelState = !model
    ? 'Unavailable'
    : model.resident && model.warmed
    ? 'Warm / resident'
    : model.resident
    ? 'Resident / cold'
    : 'Not resident';
  const capacityState = !capacity ? 'Unavailable' : capacity.accepted ? 'Admitted' : 'Rejected';

  return (
    <aside className="instrumentation" aria-label="System instrumentation">
      <section className="dispatch-readout">
        <div className="instrument-label">
          <IconRoute size={15} />
          <span>CURRENT DISPATCH</span>
        </div>
        <div className="route-diagram">
          <span>CAM {decision?.selected_camera_id || '—'}</span>
          <i />
          <IconChevronRight size={16} />
          <i />
          <span>{decision?.selected_model_id?.replace('person-', '') || 'NO MODEL'}</span>
        </div>
        <strong>{REASONS[decision?.reason_code] || 'Waiting for scheduler decision'}</strong>
        <dl>
          <DataRow label="Class" value={decision?.decision_class} />
          <DataRow label="Selector" value={decision?.sage_model} />
          <DataRow label="Fallback" value={decision?.fallback_used == null ? null : decision.fallback_used ? 'ACTIVE' : 'NOT USED'} />
          <DataRow label="Timestamp" value={clock(decision?.timestamp)} />
        </dl>
      </section>

      <section>
        <div className="instrument-label">
          <IconCpu size={15} />
          <span>RESIDENT MODEL</span>
        </div>
        <h2>{model?.model_id || focused?.model_id || 'No model reported'}</h2>
        <dl>
          <DataRow label="State" value={modelState} tone={model?.resident && model?.warmed ? 'good' : 'warn'} />
          <DataRow label="Provider" value={model?.execution_provider} />
          <DataRow label="Load events" value={model?.load_events} />
          <DataRow label="Safe profile" value={safeFps != null ? `${fmt(safeFps)} FPS` : null} />
        </dl>
      </section>

      <section>
        <div className="instrument-label">
          <IconGauge size={15} />
          <span>CAPACITY ADMISSION</span>
        </div>
        <div className={`capacity-verdict ${capacity?.accepted === false ? 'bad' : capacity?.accepted ? 'good' : ''}`}>
          <b>{capacityState}</b>
          <span>{utilization == null ? 'No capacity report' : `${fmt(utilization)}% protected`}</span>
        </div>
        <div className="linear-meter" aria-label={utilization == null ? 'Capacity unavailable' : `${fmt(utilization)} percent protected capacity`}>
          <i style={{ width: `${utilization || 0}%` }} />
        </div>
        <dl>
          <DataRow label="Protected" value={protectedFps != null ? `${fmt(protectedFps)} FPS` : null} />
          <DataRow label="Available" value={safeFps != null ? `${fmt(safeFps)} FPS` : null} />
          <DataRow label="GPU utilization" value={gpu != null ? `${fmt(Number(gpu) <= 1 ? Number(gpu) * 100 : gpu)}%` : null} />
        </dl>
        {capacity?.violations?.length > 0 && (
          <div className="capacity-violations">
            {capacity.violations.map((item) => (
              <p key={item}>{item}</p>
            ))}
          </div>
        )}
      </section>

      <section className="focused-policy">
        <div className="instrument-label">
          <IconShieldCheck size={15} />
          <span>FOCUSED POLICY</span>
        </div>
        <dl>
          <DataRow label="Mode" value={focused?.operating_mode} />
          <DataRow label="Decision class" value={focusedCandidate?.decision_class} />
          <DataRow
            label="Eligible"
            value={focusedCandidate?.eligible == null ? null : focusedCandidate.eligible ? 'YES' : 'NO'}
            tone={focusedCandidate?.eligible ? 'good' : 'bad'}
          />
          <DataRow
            label="Maximum wait"
            value={focused?.maximum_wait_ms ? `${fmt(focused.maximum_wait_ms / 1000)} s` : null}
          />
        </dl>
      </section>
    </aside>
  );
}

function CompactFeed({ camera, active, focused, candidate, inference, onSelect }) {
  const id = cameraId(camera);
  return (
    <button className={`compact-feed ${active ? 'active' : ''} ${focused ? 'focused' : ''}`} onClick={() => onSelect(id)}>
      <span className="compact-video">
        {camera.src ? <video src={camera.src} autoPlay muted loop playsInline /> : <span className="no-video">NO FEED</span>}
        <i>{camera.quality || 'RUNTIME'}</i>
      </span>
      <span className="compact-copy">
        <span>
          <b>CAM {id}</b>
          <small>{camera.camera_name}</small>
        </span>
        <strong>{active ? 'SELECTED' : candidate?.eligible === false ? 'INELIGIBLE' : 'MONITORED'}</strong>
      </span>
      <span className="compact-metrics">
        <span>
          <small>PEOPLE</small>
          <b>{inference?.person_count ?? '—'}</b>
        </span>
        <span>
          <small>UTILITY</small>
          <b>{fmt(candidate?.sage_utility, 2)}</b>
        </span>
        <span>
          <small>WAIT</small>
          <b>{candidate?.wait_ms != null ? `${fmt(candidate.wait_ms / 1000)}s` : '—'}</b>
        </span>
        <span>
          <small>RANK</small>
          <b>{candidate?.rank ? `#${candidate.rank}` : '—'}</b>
        </span>
      </span>
    </button>
  );
}

function CandidateTable({ candidates, selectedId, cameras, onSelect }) {
  const names = Object.fromEntries(cameras.map((item) => [cameraId(item), item.camera_name]));
  return (
    <section className="candidate-panel" id="candidates" aria-labelledby="candidate-title">
      <SectionHeading id="candidate-title" title="Scheduler candidate field" meta={`${candidates.length} candidates / policy-first ordering`} />
      <div className="data-table" aria-label="Scheduler candidates">
        <div className="data-row data-head" aria-hidden="true">
          <span>Rank</span>
          <span>Camera</span>
          <span>Class</span>
          <span>Mode</span>
          <span>Utility</span>
          <span>Wait</span>
          <span>Score</span>
          <span>Eligibility</span>
          <span>Reason</span>
        </div>
        {candidates.length ? (
          candidates.map((item) => (
            <button
              aria-label={`Inspect Camera ${item.camera_id}, rank ${item.rank}, ${item.decision_class}, ${item.eligible ? 'eligible' : 'blocked'}`}
              key={item.camera_id}
              className={`data-row ${item.camera_id === selectedId ? 'selected' : ''}`}
              onClick={() => onSelect(item.camera_id)}
            >
              <span data-label="Rank">
                <b>{String(item.rank || 0).padStart(2, '0')}</b>
              </span>
              <span data-label="Camera">
                <b>{item.camera_id}</b>
                <small>{names[item.camera_id]}</small>
              </span>
              <span data-label="Class">{item.decision_class}</span>
              <span data-label="Mode">{item.operating_mode}</span>
              <span data-label="Utility">{fmt(item.sage_utility, 3)}</span>
              <span data-label="Wait">{fmt(item.wait_ms / 1000)}s</span>
              <span data-label="Score">{fmt(item.scheduler_score, 3)}</span>
              <span data-label="Eligibility">
                <StateMark tone={item.eligible ? 'active' : 'bad'} label={item.eligible ? 'Eligible' : 'Blocked'} />
              </span>
              <span data-label="Reason">{REASONS[item.reason_code] || item.reason_code}</span>
            </button>
          ))
        ) : (
          <div className="table-empty">
            <IconArrowsShuffle size={20} />
            <span>No scheduler decision received</span>
            <small>The candidate field will populate when the v2 worker publishes its first decision.</small>
          </div>
        )}
      </div>
    </section>
  );
}

function DecisionSequence({ decisions, cameras }) {
  const names = Object.fromEntries(cameras.map((item) => [cameraId(item), item.camera_name]));
  return (
    <section className="decision-sequence" id="decisions" aria-labelledby="decision-title">
      <SectionHeading id="decision-title" title="Decision sequence" meta={`${decisions.length} retained in interface memory`} />
      <div className="decision-strip">
        {decisions.length ? (
          decisions.slice(0, 12).map((item, index) => (
            <article key={item.decision_id || `${item.timestamp}-${index}`} className={index === 0 ? 'current' : ''}>
              <div className="decision-time">
                <span>{clock(item.timestamp)}</span>
                <i />
              </div>
              <strong>CAM {item.selected_camera_id}</strong>
              <span>{names[item.selected_camera_id]}</span>
              <small>{item.decision_class} · {item.reason_code?.replaceAll('_', ' ')}</small>
              <code>{item.decision_id}</code>
            </article>
          ))
        ) : (
          <div className="sequence-empty">AWAITING LIVE DECISION SEQUENCE</div>
        )}
      </div>
    </section>
  );
}

function PolicyMatrix({ cameras, overrides, usingFixtures }) {
  return (
    <section className="policy-matrix" id="policies" aria-labelledby="policy-title">
      <SectionHeading
        id="policy-title"
        title="Camera policy matrix"
        meta={usingFixtures ? 'Inspect-only / demonstration fixtures / runtime unconfirmed' : 'Inspect-only / runtime configuration'}
      />
      <div className="policy-grid">
        {cameras.map((camera) => (
          <article key={cameraId(camera)}>
            <div className="policy-name">
              <span>CAM {cameraId(camera)}</span>
              <div>
                <h3>{camera.camera_name}</h3>
                <p>{camera.location}</p>
              </div>
              <StateMark
                tone={usingFixtures ? 'warn' : camera.enabled === false ? 'bad' : 'active'}
                label={usingFixtures ? 'Fixture' : camera.enabled === false ? 'Disabled' : 'Enabled'}
              />
            </div>
            <dl>
              <DataRow label="Operating mode" value={camera.operating_mode} />
              <DataRow label="Task" value={camera.task_id} />
              <DataRow label="Assigned model" value={camera.model_id} />
              <DataRow label="Priority" value={camera.priority ? `${camera.priority} / 5` : null} />
              <DataRow
                label="Minimum deep rate"
                value={camera.minimum_deep_rate_fps != null ? `${fmt(camera.minimum_deep_rate_fps)} FPS` : null}
              />
              <DataRow
                label="Maximum deep rate"
                value={camera.maximum_deep_rate_fps != null ? `${fmt(camera.maximum_deep_rate_fps)} FPS` : null}
              />
              <DataRow label="Maximum wait" value={camera.maximum_wait_ms ? `${fmt(camera.maximum_wait_ms / 1000)} s` : null} />
              <DataRow
                label="Override"
                value={overrides.has(cameraId(camera)) ? `UNTIL ${clock(overrides.get(cameraId(camera))?.expires_at)}` : 'NONE'}
                tone={overrides.has(cameraId(camera)) ? 'warn' : null}
              />
            </dl>
          </article>
        ))}
      </div>
    </section>
  );
}

function EvidencePanel({ decision }) {
  return (
    <section className="evidence-panel" id="evidence" aria-labelledby="evidence-title">
      <div className="evidence-copy">
        <IconDatabase size={20} />
        <div>
          <h2 id="evidence-title">Review-1 allocation evidence</h2>
          <p>
            Frozen equal-budget person-routing results. This evidence validates the earlier learned scalar router; it does not claim
            heterogeneous learned-SAGE performance. The live v2 scheduler identifies itself as{' '}
            <code>{decision?.sage_model || 'awaiting runtime'}</code>.
          </p>
        </div>
      </div>
      <div className="evidence-table">
        <div>
          <span>Round robin</span>
          <b>68.71</b>
        </div>
        <div>
          <span>Confidence only</span>
          <b>69.59</b>
        </div>
        <div className="best">
          <span>Learned scalar router</span>
          <b>92.80</b>
        </div>
      </div>
    </section>
  );
}

function SectionHeading({ id, title, meta }) {
  return (
    <div className="section-heading">
      <h2 id={id}>{title}</h2>
      <span>{meta}</span>
    </div>
  );
}

function Measurement({ label, value }) {
  return (
    <div>
      <span>{label}</span>
      <b>{value ?? '—'}</b>
    </div>
  );
}

function StateMark({ tone = 'neutral', label }) {
  return (
    <span className={`state-mark ${tone}`}>
      <i />
      {label}
    </span>
  );
}

function DataRow({ label, value, tone }) {
  return (
    <div className={tone || ''}>
      <dt>{label}</dt>
      <dd>{value ?? '—'}</dd>
    </div>
  );
}

function useEventAge(timestamp) {
  const [age, setAge] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setAge(timestamp ? Math.floor((Date.now() - timestamp) / 1000) : 0), 1000);
    return () => window.clearInterval(timer);
  }, [timestamp]);
  return age;
}
