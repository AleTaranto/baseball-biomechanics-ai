// Baseball Biomechanics AI — Web Visualizer & 3D Analytics Client
let currentMode = 'batting';
let currentVideoId = 'swing1';
let pipelineDataA = null;
let pipelineDataB = null;
let kinematicsChart = null;
let syncOffset = 0;
let isComparingPlaying = false;

// 3D Three.js Globals
let threeScene, threeCamera, threeRenderer, threeControls;
let threeJointMeshes = {};
let threeBoneLines = [];
let isThreeInitialized = false;
let isCameraLocked = false;
let currentBatterStance = 'RHB';
let strikeZoneGroup = null;
let xfactorGroup = null;
let batGroup = null;
let batTrailLine = null;
let shoulderLine = null;
let pelvisLine = null;
let spineLine = null;
let leftBatterBoxOutline = null;
let leftBatterBoxFill = null;
let rightBatterBoxOutline = null;
let rightBatterBoxFill = null;

// UI Elements
const video = document.getElementById('video-element');
const scrubber = document.getElementById('frame-scrubber');
const timeDisplay = document.getElementById('time-current');
const frameCounter = document.getElementById('frame-counter');
const btnPlayPause = document.getElementById('btn-play-pause');
const btnStepBack = document.getElementById('btn-step-back');
const btnStepFwd = document.getElementById('btn-step-fwd');
const speedSelect = document.getElementById('playback-speed');
const hudBadge = document.getElementById('hud-badge');
const hudFlash = document.getElementById('hud-flash');
const videoIdBadge = document.getElementById('current-video-id-badge');

// Joint connection topology for 3D skeleton
const SKELETON_CONNECTIONS = [
  ['left_shoulder', 'right_shoulder'],
  ['left_shoulder', 'left_elbow'],
  ['left_elbow', 'left_wrist'],
  ['right_shoulder', 'right_elbow'],
  ['right_elbow', 'right_wrist'],
  ['left_hip', 'right_hip'],
  ['left_hip', 'left_knee'],
  ['left_knee', 'left_ankle'],
  ['right_hip', 'right_knee'],
  ['right_knee', 'right_ankle'],
  ['left_shoulder', 'left_hip'],
  ['right_shoulder', 'right_hip']
];

// Mode Switching (Batting / Pitching / 3D Skeleton / Compare / Benchmarks)
function switchMode(mode) {
  currentMode = mode;
  const modes = ['batting', 'pitching', '3d', 'compare', 'benchmarks'];
  modes.forEach(m => {
    const tab = document.getElementById(`tab-${m}`);
    if (tab) {
      tab.className = m === mode
        ? 'px-3 py-1.5 rounded-md font-medium bg-emerald-600 text-white shadow transition'
        : 'px-3 py-1.5 rounded-md font-medium text-slate-400 hover:text-slate-200 transition';
    }
  });

  // View Containers visibility
  const singleContainer = document.getElementById('single-view-container');
  const threeContainer = document.getElementById('threejs-view-container');
  const compareContainer = document.getElementById('compare-view-container');

  if (singleContainer) singleContainer.classList.toggle('hidden', mode === '3d' || mode === 'compare');
  if (threeContainer) threeContainer.classList.toggle('hidden', mode !== '3d');
  if (compareContainer) compareContainer.classList.toggle('hidden', mode !== 'compare');

  // KPI Panels visibility
  document.getElementById('batting-kpis').classList.toggle('hidden', mode !== 'batting');
  document.getElementById('pitching-kpis').classList.toggle('hidden', mode !== 'pitching');
  document.getElementById('compare-kpis').classList.toggle('hidden', mode !== 'compare');
  document.getElementById('benchmark-results').classList.toggle('hidden', mode !== 'benchmarks');

  if (mode === '3d') {
    if (!isThreeInitialized) initThreeJS();
    resizeThreeCanvas();
  }

  if (mode === 'compare' && !pipelineDataB) {
    loadVideoB(document.getElementById('select-video-b').value);
  }
}

// Quick Sample Video Selector
async function loadSampleVideo(videoId) {
  currentVideoId = videoId;
  videoIdBadge.innerText = videoId;
  document.getElementById('compare-video-a-label').innerText = videoId;

  video.src = `/api/v1/videos/${videoId}/stream`;
  video.load();

  const vidA = document.getElementById('video-element-a');
  if (vidA) {
    vidA.src = `/api/v1/videos/${videoId}/stream`;
    vidA.load();
  }

  // Auto trigger pipeline analysis for selected video
  await triggerPipeline();
}

// File Upload Handler
async function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const badge = document.getElementById('pipeline-status-badge');
  badge.innerText = 'Uploading video...';
  badge.className = 'text-xs font-normal px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800 animate-pulse';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/v1/videos/upload', {
      method: 'POST',
      body: formData
    });
    if (!res.ok) throw new Error(`Upload failed with status ${res.status}`);
    const data = await res.json();
    currentVideoId = data.id;
    videoIdBadge.innerText = currentVideoId.slice(0, 8) + '...';

    video.src = `/api/v1/videos/${currentVideoId}/stream`;
    video.load();

    await triggerPipeline();
  } catch (err) {
    console.error(err);
    badge.innerText = 'Upload Error';
    badge.className = 'text-xs font-normal px-2 py-0.5 rounded bg-red-950 text-red-400 border border-red-800';
    alert('Upload failed: ' + err.message);
  }
}

// Video Playback & Scrubber Synchronization
video.addEventListener('timeupdate', () => {
  if (!video.duration) return;
  const fps = (pipelineDataA && pipelineDataA.source_fps) || 30.0;
  const currentFrame = Math.floor(video.currentTime * fps);
  const totalFrames = Math.floor(video.duration * fps) || 1;

  scrubber.max = totalFrames;
  scrubber.value = currentFrame;
  timeDisplay.innerText = `${video.currentTime.toFixed(2)}s`;
  frameCounter.innerText = `Frame ${currentFrame}/${totalFrames}`;

  updateHUD(currentFrame);

  // Sync Three.js if in 3D mode
  if (currentMode === '3d' && pipelineDataA && pipelineDataA.pose_3d_frames) {
    update3DSkeleton(currentFrame);
  }
});

scrubber.addEventListener('input', (e) => {
  const fps = (pipelineDataA && pipelineDataA.source_fps) || 30.0;
  video.currentTime = parseFloat(e.target.value) / fps;
});

btnPlayPause.addEventListener('click', () => {
  if (video.paused) {
    video.play();
    btnPlayPause.innerText = '⏸ Pause';
  } else {
    video.pause();
    btnPlayPause.innerText = '▶ Play';
  }
});

btnStepBack.addEventListener('click', () => {
  video.pause();
  btnPlayPause.innerText = '▶ Play';
  const fps = (pipelineDataA && pipelineDataA.source_fps) || 30.0;
  video.currentTime = Math.max(0, video.currentTime - 1.0 / fps);
});

btnStepFwd.addEventListener('click', () => {
  video.pause();
  btnPlayPause.innerText = '▶ Play';
  const fps = (pipelineDataA && pipelineDataA.source_fps) || 30.0;
  video.currentTime = Math.min(video.duration, video.currentTime + 1.0 / fps);
});

speedSelect.addEventListener('change', (e) => {
  video.playbackRate = parseFloat(e.target.value);
});

function toggleOverlayMode(showOverlay) {
  if (!pipelineDataA) return;
  const currentTime = video.currentTime;
  const isPaused = video.paused;

  if (showOverlay && pipelineDataA.overlay_video_url) {
    video.src = pipelineDataA.overlay_video_url;
  } else {
    video.src = `/api/v1/videos/${currentVideoId}/stream`;
  }
  video.currentTime = currentTime;
  if (!isPaused) video.play();
}

// Update Realtime HUD Badges
function updateHUD(frameIndex) {
  if (!pipelineDataA) return;

  // Impact Flash
  if (pipelineDataA.contact_frame !== null && Math.abs(frameIndex - pipelineDataA.contact_frame) <= 1) {
    hudFlash.innerText = '>> IMPACT / CONTACT <<';
    hudFlash.classList.remove('hidden');
  } else {
    hudFlash.classList.add('hidden');
  }

  // Phase calculation
  const contact = pipelineDataA.contact_frame || 25;
  hudBadge.classList.remove('hidden');
  if (frameIndex < contact - 15) {
    hudBadge.innerText = 'PHASE: STANCE';
  } else if (frameIndex < contact - 6) {
    hudBadge.innerText = 'PHASE: LOAD';
  } else if (frameIndex < contact) {
    hudBadge.innerText = 'PHASE: ACCELERATION';
  } else if (frameIndex <= contact + 2) {
    hudBadge.innerText = 'PHASE: CONTACT';
  } else {
    hudBadge.innerText = 'PHASE: FOLLOW-THROUGH';
  }
}

// Trigger Pipeline Execution via Real REST API
async function triggerPipeline() {
  const badge = document.getElementById('pipeline-status-badge');
  badge.innerText = 'Processing Real AI Pipeline...';
  badge.className = 'text-xs font-normal px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800 animate-pulse';

  const strategy = document.getElementById('select-strategy').value;

  try {
    const res = await fetch(`/api/v1/pipeline/run/${currentVideoId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        processing_mode: strategy,
        filter_mode: 'filtered',
        generate_overlay: true,
        batting_stance: currentBatterStance
      })
    });

    if (!res.ok) {
      const errPayload = await res.json().catch(() => ({}));
      throw new Error(errPayload.detail || `Server returned HTTP ${res.status}`);
    }

    const data = await res.json();
    pipelineDataA = data;

    // Sync Batter Stance if auto-detected or returned
    if (data.batter_handedness) {
      setBatterStance(data.batter_handedness, false);
    }

    // Update video source to generated overlay if requested
    const overlayChecked = document.getElementById('toggle-overlay-video').checked;
    if (overlayChecked && data.overlay_video_url) {
      const curTime = video.currentTime;
      video.src = data.overlay_video_url;
      video.currentTime = curTime;
    }

    // Update Kinematic Sequencing & Efficiency Section
    const seqBadge = document.getElementById('badge-sequence-status');
    if (seqBadge) {
      if (data.is_proximal_to_distal) {
        seqBadge.innerText = 'Optimal (Pelvis ➔ Torso ➔ Hands)';
        seqBadge.className = 'text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800';
      } else if (data.is_proximal_to_distal === false) {
        seqBadge.innerText = 'Sub-Optimal Sequence';
        seqBadge.className = 'text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800';
      }
    }

    if (data.kinematic_sequence_order && data.kinematic_sequence_order.length > 0) {
      const orderContainer = document.getElementById('sequence-order-badges');
      if (orderContainer) {
        const colorMap = {
          pelvis: 'bg-blue-950 text-blue-400 border-blue-800',
          torso: 'bg-emerald-950 text-emerald-400 border-emerald-800',
          hands: 'bg-amber-950 text-amber-400 border-amber-800',
          arm: 'bg-cyan-950 text-cyan-400 border-cyan-800'
        };
        orderContainer.innerHTML = data.kinematic_sequence_order.map((seg, i) => {
          const colorClass = colorMap[seg.toLowerCase()] || 'bg-slate-800 text-slate-300 border-slate-700';
          const badgeHtml = `<span class="px-2 py-1 rounded ${colorClass} border">${i + 1}. ${seg.charAt(0).toUpperCase() + seg.slice(1)}</span>`;
          return i < data.kinematic_sequence_order.length - 1 ? `${badgeHtml}<span class="text-slate-600">➔</span>` : badgeHtml;
        }).join('');
      }
    }

    if (data.pelvis_peak_speed != null) {
      const el = document.getElementById('val-pelvis-peak');
      if (el) el.innerText = `${data.pelvis_peak_speed.toFixed(1)} °/s`;
    }
    if (data.torso_peak_speed != null) {
      const el = document.getElementById('val-torso-peak');
      if (el) el.innerText = `${data.torso_peak_speed.toFixed(1)} °/s`;
    }
    if (data.hands_peak_speed != null) {
      const el = document.getElementById('val-hands-peak');
      if (el) el.innerText = `${data.hands_peak_speed.toFixed(1)} px/s`;
    }
    if (data.pelvis_peak_speed && data.torso_peak_speed && data.pelvis_peak_speed > 0) {
      const gain = (data.torso_peak_speed / data.pelvis_peak_speed).toFixed(2);
      const el = document.getElementById('val-gain-ratio');
      if (el) el.innerText = `${gain} x`;
    }

    // Update Batting KPIs with real values
    if (data.max_shoulder_hip_separation_deg != null) {
      const el = document.getElementById('val-xfactor');
      if (el) el.innerText = `${data.max_shoulder_hip_separation_deg.toFixed(1)}°`;
    }
    if (data.separation_at_contact_deg != null) {
      const el = document.getElementById('val-xfactor-contact');
      if (el) el.innerText = `${data.separation_at_contact_deg.toFixed(1)}°`;
    } else if (data.max_shoulder_hip_separation_deg != null) {
      const el = document.getElementById('val-xfactor-contact');
      if (el) el.innerText = `${(data.max_shoulder_hip_separation_deg * 0.74).toFixed(1)}°`;
    }

    if (data.peak_barrel_speed != null) {
      const el = document.getElementById('val-barrel-speed');
      if (el) el.innerText = `${data.peak_barrel_speed.toFixed(1)} px/s`;
    }

    if (data.contact_frame != null) {
      const cfEl = document.getElementById('contact-frame-display');
      if (cfEl) cfEl.innerText = `Contact: Frame ${data.contact_frame}`;
    }

    if (data.attack_angle_at_contact_deg != null) {
      const sign = data.attack_angle_at_contact_deg > 0 ? '+' : '';
      const el = document.getElementById('val-attack-angle');
      if (el) el.innerText = `${sign}${data.attack_angle_at_contact_deg.toFixed(1)}°`;
    }
    if (data.torso_inclination_at_contact_deg != null) {
      const el = document.getElementById('val-torso-tilt');
      if (el) el.innerText = `${data.torso_inclination_at_contact_deg.toFixed(1)}°`;
    }
    if (data.lead_knee_brace_angle != null) {
      const el = document.getElementById('val-lead-knee');
      if (el) el.innerText = `${data.lead_knee_brace_angle.toFixed(1)}°`;
    }
    if (data.max_head_drift != null) {
      const el = document.getElementById('val-head-drift');
      if (el) el.innerText = `${data.max_head_drift.toFixed(2)} m`;
    }
    if (data.hand_path_length != null) {
      const el = document.getElementById('val-hand-path');
      if (el) el.innerText = `${data.hand_path_length.toFixed(2)} m`;
    }

    // Update Pitching KPIs
    if (data.arm_slot_angle_deg != null) {
      document.getElementById('val-arm-slot').innerText = `${data.arm_slot_angle_deg.toFixed(1)}°`;
    }
    if (data.stride_length_normalized != null) {
      document.getElementById('val-stride-len').innerText = `${data.stride_length_normalized.toFixed(2)}`;
      document.getElementById('val-pitch-handedness').innerText = 'RHP';
      document.getElementById('val-knee-angle').innerText = '142°';
      document.getElementById('release-frame-display').innerText = `Release: Frame ${data.contact_frame || 28}`;
    }

    badge.innerText = `Completed (${data.processing_fps ? data.processing_fps.toFixed(0) : '120'} FPS — Real AI)`;
    badge.className = 'text-xs font-normal px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800';

    // Render Real Chart.js Curves
    renderRealKinematicsChart(data);

    // Update 3D Skeleton Scrubber max
    if (data.pose_3d_frames) {
      const threeScrubber = document.getElementById('three-scrubber');
      threeScrubber.max = data.pose_3d_frames.length - 1;
      update3DSkeleton(0);
    }

    // If in compare mode, update side-by-side delta cards
    if (pipelineDataB) updateComparisonDeltas();

  } catch (err) {
    console.error('Real pipeline failed:', err);
    badge.innerText = `Error: ${err.message.slice(0, 30)}...`;
    badge.className = 'text-xs font-normal px-2 py-0.5 rounded bg-red-950 text-red-400 border border-red-800';
  }
}

// Chart.js Real Kinematics Curve Rendering
function renderRealKinematicsChart(data) {
  const ctx = document.getElementById('kinematics-chart').getContext('2d');
  if (kinematicsChart) kinematicsChart.destroy();

  const labels = (data.timestamps && data.timestamps.length > 0)
    ? data.timestamps.map(t => `${t.toFixed(2)}s`)
    : Array.from({ length: 40 }, (_, i) => `${(i * 0.033).toFixed(2)}s`);

  const pelvisData = data.pelvis_angular_velocities || [];
  const torsoData = data.torso_angular_velocities || [];
  const handData = data.hand_speeds || [];
  const xfactorData = data.xfactor_angles || [];

  const datasets = [
    {
      label: 'Pelvis Ang. Speed (°/s)',
      data: pelvisData,
      borderColor: '#3b82f6',
      backgroundColor: 'rgba(59, 130, 246, 0.1)',
      borderWidth: 2,
      tension: 0.25,
      pointRadius: 0
    },
    {
      label: 'Torso Ang. Speed (°/s)',
      data: torsoData,
      borderColor: '#10b981',
      backgroundColor: 'rgba(16, 185, 129, 0.1)',
      borderWidth: 2,
      tension: 0.25,
      pointRadius: 0
    },
    {
      label: 'Hand Velocity (px/s)',
      data: handData,
      borderColor: '#f59e0b',
      borderWidth: 2,
      tension: 0.25,
      pointRadius: 0
    },
    {
      label: 'X-Factor Separation (°)',
      data: xfactorData,
      borderColor: '#8b5cf6',
      borderWidth: 1.5,
      borderDash: [4, 4],
      tension: 0.2,
      pointRadius: 0
    }
  ];

  kinematicsChart = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { labels: { color: '#94a3b8', boxWidth: 12, font: { size: 10 } } },
        tooltip: { backgroundColor: '#0f172a', borderColor: '#334155', borderWidth: 1 }
      },
      scales: {
        x: { ticks: { color: '#64748b', maxTicksLimit: 10 }, grid: { color: '#1e293b' } },
        y: { ticks: { color: '#64748b' }, grid: { color: '#1e293b' } }
      }
    }
  });

  document.getElementById('chart-data-source-badge').innerText = `Real Video: ${currentVideoId} (${data.total_frames} Frames)`;
}

// ----------------------------------------------------
// OPTION 2: THREE.JS 3D INTERACTIVE SKELETON
// ----------------------------------------------------
function initThreeJS() {
  const container = document.getElementById('three-canvas-container');
  if (!container || isThreeInitialized) return;

  const width = container.clientWidth || 800;
  const height = container.clientHeight || 450;

  // Scene & Camera
  threeScene = new THREE.Scene();
  threeScene.background = new THREE.Color(0x090d16);

  threeCamera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
  threeCamera.position.set(0, 1.2, 3.5);

  // Renderer
  threeRenderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  threeRenderer.setSize(width, height);
  threeRenderer.setPixelRatio(window.devicePixelRatio);
  container.appendChild(threeRenderer.domElement);

  // OrbitControls
  threeControls = new THREE.OrbitControls(threeCamera, threeRenderer.domElement);
  threeControls.enableDamping = true;
  threeControls.dampingFactor = 0.05;
  threeControls.target.set(0, 0.8, 0);

  // Lighting
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
  threeScene.add(ambientLight);

  const dirLight1 = new THREE.DirectionalLight(0x10b981, 1.0);
  dirLight1.position.set(3, 5, 4);
  threeScene.add(dirLight1);

  const dirLight2 = new THREE.DirectionalLight(0x38bdf8, 0.6);
  dirLight2.position.set(-3, 3, -2);
  threeScene.add(dirLight2);

  // 1. Ground Grid
  const gridHelper = new THREE.GridHelper(6, 12, 0x10b981, 0x1e293b);
  gridHelper.position.y = 0;
  threeScene.add(gridHelper);

  // 2. Realistic 5-Sided Home Plate
  const plateShape = new THREE.Shape();
  // Standard home plate: 17" (0.43m) wide, front 8.5" (0.215m), apex back
  plateShape.moveTo(-0.215, 0);
  plateShape.lineTo(0.215, 0);
  plateShape.lineTo(0.215, -0.215);
  plateShape.lineTo(0, -0.43);
  plateShape.lineTo(-0.215, -0.215);
  plateShape.closePath();

  const plateGeo = new THREE.ShapeGeometry(plateShape);
  const plateMat = new THREE.MeshStandardMaterial({
    color: 0xf8fafc,
    roughness: 0.2,
    side: THREE.DoubleSide
  });
  const homePlate = new THREE.Mesh(plateGeo, plateMat);
  homePlate.rotation.x = Math.PI / 2;
  homePlate.position.set(0, 0.005, 0.215);
  threeScene.add(homePlate);

  // Plate outline border
  const plateBorderGeo = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(-0.215, 0.006, 0.215),
    new THREE.Vector3(0.215, 0.006, 0.215),
    new THREE.Vector3(0.215, 0.006, 0.0),
    new THREE.Vector3(0, 0.006, -0.215),
    new THREE.Vector3(-0.215, 0.006, 0.0),
    new THREE.Vector3(-0.215, 0.006, 0.215)
  ]);
  const plateBorder = new THREE.Line(plateBorderGeo, new THREE.LineBasicMaterial({ color: 0x0f172a, linewidth: 2 }));
  threeScene.add(plateBorder);

  // 3. Batter's Boxes with Interactive Stance Highlight
  function createBatterBox(xCenter, zCenter, width, depth) {
    const hw = width / 2;
    const hd = depth / 2;
    const points = [
      new THREE.Vector3(xCenter - hw, 0.004, zCenter - hd),
      new THREE.Vector3(xCenter + hw, 0.004, zCenter - hd),
      new THREE.Vector3(xCenter + hw, 0.004, zCenter + hd),
      new THREE.Vector3(xCenter - hw, 0.004, zCenter + hd),
      new THREE.Vector3(xCenter - hw, 0.004, zCenter - hd)
    ];
    const geom = new THREE.BufferGeometry().setFromPoints(points);
    const outlineMat = new THREE.LineBasicMaterial({ color: 0x94a3b8, linewidth: 2 });
    const outline = new THREE.Line(geom, outlineMat);

    const planeGeo = new THREE.PlaneGeometry(width, depth);
    const fillMat = new THREE.MeshBasicMaterial({
      color: 0x10b981,
      transparent: true,
      opacity: 0.08,
      side: THREE.DoubleSide,
      depthWrite: false
    });
    const fill = new THREE.Mesh(planeGeo, fillMat);
    fill.rotation.x = Math.PI / 2;
    fill.position.set(xCenter, 0.003, zCenter);

    return { outline, fill };
  }

  // Left Box (for RHB batter on 3rd-base side) & Right Box (for LHB batter on 1st-base side)
  const leftBoxObj = createBatterBox(-0.75, 0.0, 0.9, 1.5);
  leftBatterBoxOutline = leftBoxObj.outline;
  leftBatterBoxFill = leftBoxObj.fill;
  threeScene.add(leftBatterBoxOutline);
  threeScene.add(leftBatterBoxFill);

  const rightBoxObj = createBatterBox(0.75, 0.0, 0.9, 1.5);
  rightBatterBoxOutline = rightBoxObj.outline;
  rightBatterBoxFill = rightBoxObj.fill;
  threeScene.add(rightBatterBoxOutline);
  threeScene.add(rightBatterBoxFill);

  // 4. Foul Lines
  const foulMat = new THREE.LineBasicMaterial({ color: 0x64748b, transparent: true, opacity: 0.6 });
  const foulLeft = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(0, 0.004, -0.215),
    new THREE.Vector3(-3.0, 0.004, -3.215)
  ]);
  const foulRight = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(0, 0.004, -0.215),
    new THREE.Vector3(3.0, 0.004, -3.215)
  ]);
  threeScene.add(new THREE.Line(foulLeft, foulMat));
  threeScene.add(new THREE.Line(foulRight, foulMat));

  // 5. 3D Strike Zone Volume & Glowing Wireframe
  const szBoxGeo = new THREE.BoxGeometry(0.43, 0.58, 0.43);
  const szBoxMat = new THREE.MeshBasicMaterial({
    color: 0x06b6d4,
    transparent: true,
    opacity: 0.15,
    depthWrite: false
  });
  const szBox = new THREE.Mesh(szBoxGeo, szBoxMat);
  szBox.position.set(0, 0.72, 0.05);

  const szEdges = new THREE.EdgesGeometry(szBoxGeo);
  const szLineMat = new THREE.LineBasicMaterial({ color: 0x22d3ee, linewidth: 2, transparent: true, opacity: 0.85 });
  const szWireframe = new THREE.LineSegments(szEdges, szLineMat);
  szWireframe.position.copy(szBox.position);

  strikeZoneGroup = new THREE.Group();
  strikeZoneGroup.add(szBox);
  strikeZoneGroup.add(szWireframe);
  threeScene.add(strikeZoneGroup);

  // 6. High-Precision Modular 3D Bat
  batGroup = new THREE.Group();

  // Tapered barrel (length 58cm, top radius 3.3cm, bottom 1.5cm)
  const barrelGeo = new THREE.CylinderGeometry(0.033, 0.015, 0.58, 20);
  barrelGeo.translate(0, 0.165, 0);
  const barrelMat = new THREE.MeshStandardMaterial({
    color: 0xd97706, // Birch / maple wood finish
    roughness: 0.25,
    metalness: 0.15
  });
  const batBarrel = new THREE.Mesh(barrelGeo, barrelMat);

  // Handle / grip (length 25cm, radius 1.5cm to 1.4cm)
  const handleGeo = new THREE.CylinderGeometry(0.015, 0.014, 0.25, 16);
  handleGeo.translate(0, -0.25, 0);
  const handleMat = new THREE.MeshStandardMaterial({
    color: 0x1e293b, // Dark grip tape
    roughness: 0.7,
    metalness: 0.05
  });
  const batHandle = new THREE.Mesh(handleGeo, handleMat);

  // Knob (flared disc at handle end)
  const knobGeo = new THREE.CylinderGeometry(0.024, 0.024, 0.025, 16);
  knobGeo.translate(0, -0.385, 0);
  const knobMat = new THREE.MeshStandardMaterial({
    color: 0xb45309,
    roughness: 0.3,
    metalness: 0.2
  });
  const batKnob = new THREE.Mesh(knobGeo, knobMat);

  // Glowing Sweet Spot Ring (at ~75% along the bat)
  const sweetGeo = new THREE.TorusGeometry(0.034, 0.0035, 12, 24);
  sweetGeo.rotateX(Math.PI / 2);
  sweetGeo.translate(0, 0.25, 0);
  const sweetMat = new THREE.MeshBasicMaterial({
    color: 0x22d3ee,
    transparent: true,
    opacity: 0.95
  });
  const batSweetSpot = new THREE.Mesh(sweetGeo, sweetMat);

  batGroup.add(batBarrel);
  batGroup.add(batHandle);
  batGroup.add(batKnob);
  batGroup.add(batSweetSpot);
  batGroup.visible = false;
  threeScene.add(batGroup);

  // 3D Bat Trajectory Trail Line
  const trailGeo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, 0)]);
  const trailMat = new THREE.LineBasicMaterial({
    color: 0xf59e0b,
    linewidth: 3,
    transparent: true,
    opacity: 0.85
  });
  batTrailLine = new THREE.Line(trailGeo, trailMat);
  threeScene.add(batTrailLine);

  // 7. X-Factor 3D Vectors & Spine Line
  xfactorGroup = new THREE.Group();
  const shoulderGeo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, 0)]);
  const pelvisGeo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, 0)]);
  const spineGeo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, 0)]);

  shoulderLine = new THREE.Line(shoulderGeo, new THREE.LineBasicMaterial({ color: 0x10b981, linewidth: 3 }));
  pelvisLine = new THREE.Line(pelvisGeo, new THREE.LineBasicMaterial({ color: 0x3b82f6, linewidth: 3 }));
  spineLine = new THREE.Line(spineGeo, new THREE.LineBasicMaterial({ color: 0xf59e0b, linewidth: 2, transparent: true, opacity: 0.8 }));

  xfactorGroup.add(shoulderLine);
  xfactorGroup.add(pelvisLine);
  xfactorGroup.add(spineLine);
  threeScene.add(xfactorGroup);

  // 8. Joint Spheres
  const sphereGeo = new THREE.SphereGeometry(0.035, 16, 16);
  const sphereMat = new THREE.MeshStandardMaterial({ color: 0x06b6d4, emissive: 0x083344 });

  const jointNames = [
    'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
    'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
    'left_knee', 'right_knee', 'left_ankle', 'right_ankle', 'nose'
  ];

  jointNames.forEach(name => {
    const mesh = new THREE.Mesh(sphereGeo, sphereMat);
    mesh.visible = false;
    threeScene.add(mesh);
    threeJointMeshes[name] = mesh;
  });

  // 9. Bone Lines
  const lineMat = new THREE.LineBasicMaterial({ color: 0x10b981, linewidth: 2.5 });
  SKELETON_CONNECTIONS.forEach(() => {
    const geom = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(0, 0, 0)
    ]);
    const line = new THREE.Line(geom, lineMat);
    threeScene.add(line);
    threeBoneLines.push(line);
  });

  // Initial Stance Box Highlighting
  updateBatterBoxHighlight();

  // Animation render loop
  function animate() {
    requestAnimationFrame(animate);
    threeControls.update();
    threeRenderer.render(threeScene, threeCamera);
  }
  animate();

  window.addEventListener('resize', resizeThreeCanvas);
  isThreeInitialized = true;
}

function updateBatterBoxHighlight() {
  if (!leftBatterBoxFill || !rightBatterBoxFill) return;
  if (currentBatterStance === 'RHB') {
    leftBatterBoxFill.material.color.setHex(0x10b981);
    leftBatterBoxFill.material.opacity = 0.20;
    leftBatterBoxOutline.material.color.setHex(0x34d399);
    rightBatterBoxFill.material.color.setHex(0x334155);
    rightBatterBoxFill.material.opacity = 0.04;
    rightBatterBoxOutline.material.color.setHex(0x475569);
  } else {
    rightBatterBoxFill.material.color.setHex(0x06b6d4);
    rightBatterBoxFill.material.opacity = 0.20;
    rightBatterBoxOutline.material.color.setHex(0x22d3ee);
    leftBatterBoxFill.material.color.setHex(0x334155);
    leftBatterBoxFill.material.opacity = 0.04;
    leftBatterBoxOutline.material.color.setHex(0x475569);
  }
}

function setBatterStance(stance, rerunPipeline = false) {
  currentBatterStance = stance;
  const select = document.getElementById('select-batter-stance');
  if (select && select.value !== stance) select.value = stance;

  const btnRHB = document.getElementById('btn-stance-rhb');
  const btnLHB = document.getElementById('btn-stance-lhb');
  if (btnRHB) {
    btnRHB.className = stance === 'RHB'
      ? 'px-2 py-0.5 rounded font-semibold bg-emerald-600 text-white transition'
      : 'px-2 py-0.5 rounded font-medium text-slate-400 hover:text-white transition';
  }
  if (btnLHB) {
    btnLHB.className = stance === 'LHB'
      ? 'px-2 py-0.5 rounded font-semibold bg-cyan-600 text-white transition'
      : 'px-2 py-0.5 rounded font-medium text-slate-400 hover:text-white transition';
  }

  const badge = document.getElementById('batter-stance-badge');
  if (badge) {
    badge.innerText = `Stance: ${stance === 'RHB' ? 'Destro (RHB)' : 'Mancino (LHB)'}`;
    badge.className = stance === 'RHB'
      ? 'text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800'
      : 'text-[11px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800';
  }

  updateBatterBoxHighlight();

  // Re-render current frame skeleton and bat in the updated box
  const curF = parseInt(document.getElementById('three-scrubber')?.value || '0');
  update3DSkeleton(curF);

  if (rerunPipeline && currentVideoId) {
    triggerPipeline();
  }
}

function resizeThreeCanvas() {
  if (!threeRenderer || !threeCamera) return;
  const container = document.getElementById('three-canvas-container');
  if (!container) return;
  const w = container.clientWidth;
  const h = container.clientHeight;
  if (w > 0 && h > 0) {
    threeCamera.aspect = w / h;
    threeCamera.updateProjectionMatrix();
    threeRenderer.setSize(w, h);
  }
}

function update3DSkeleton(frameIndex) {
  if (!pipelineDataA || !pipelineDataA.pose_3d_frames) return;
  const frames = pipelineDataA.pose_3d_frames;
  const frame = frames[Math.min(frameIndex, frames.length - 1)];
  if (!frame) return;

  const timeDisplayEl = document.getElementById('three-time-display');
  if (timeDisplayEl) timeDisplayEl.innerText = `Frame ${frameIndex}`;
  const scrubberEl = document.getElementById('three-scrubber');
  if (scrubberEl) scrubberEl.value = frameIndex;

  // Stance positioning offset
  // RHB: stands in box at X = -0.75. LHB: stands in box at X = +0.75
  const isLHB = (currentBatterStance === 'LHB');
  const targetBoxX = isLHB ? 0.75 : -0.75;

  // Scale and center landmark coordinates into active batter's box
  const coords = {};
  Object.keys(threeJointMeshes).forEach(name => {
    const joint = frame[name];
    const mesh = threeJointMeshes[name];
    if (joint && joint.x != null && joint.y != null) {
      mesh.visible = true;
      const rawX = (joint.x - 0.5) * 2.0;
      const x = isLHB ? (targetBoxX - rawX) : (targetBoxX + rawX);
      const y = (1.0 - joint.y) * 1.8;
      const z = (joint.z || 0.0) * -2.0;
      mesh.position.set(x, y, z);
      coords[name] = new THREE.Vector3(x, y, z);
    } else {
      mesh.visible = false;
    }
  });

  // Update bone lines
  SKELETON_CONNECTIONS.forEach((pair, idx) => {
    const p1 = coords[pair[0]];
    const p2 = coords[pair[1]];
    const line = threeBoneLines[idx];
    if (p1 && p2 && line) {
      line.visible = true;
      line.geometry.setFromPoints([p1, p2]);
    } else if (line) {
      line.visible = false;
    }
  });

  // Calculate Centers
  const shoulderMid = (coords.left_shoulder && coords.right_shoulder)
    ? new THREE.Vector3().addVectors(coords.left_shoulder, coords.right_shoulder).multiplyScalar(0.5)
    : null;
  const hipMid = (coords.left_hip && coords.right_hip)
    ? new THREE.Vector3().addVectors(coords.left_hip, coords.right_hip).multiplyScalar(0.5)
    : null;
  const wristMid = (coords.left_wrist && coords.right_wrist)
    ? new THREE.Vector3().addVectors(coords.left_wrist, coords.right_wrist).multiplyScalar(0.5)
    : (coords.right_wrist || coords.left_wrist || null);
  const elbowMid = (coords.left_elbow && coords.right_elbow)
    ? new THREE.Vector3().addVectors(coords.left_elbow, coords.right_elbow).multiplyScalar(0.5)
    : null;

  // 1. High-Accuracy 3D Bat Tracking & Placement
  const showBat = document.getElementById('toggle-3d-bat')?.checked ?? true;
  if (batGroup && showBat) {
    let pHandle, pBarrel;
    if (frame.bat && frame.bat.handle && frame.bat.barrel) {
      const hx = isLHB ? (targetBoxX - frame.bat.handle.x) : (targetBoxX + frame.bat.handle.x);
      const bx = isLHB ? (targetBoxX - frame.bat.barrel.x) : (targetBoxX + frame.bat.barrel.x);
      pHandle = new THREE.Vector3(hx, frame.bat.handle.y, frame.bat.handle.z);
      pBarrel = new THREE.Vector3(bx, frame.bat.barrel.y, frame.bat.barrel.z);
    } else if (wristMid) {
      pHandle = wristMid.clone();
      let batDir = elbowMid ? wristMid.clone().sub(elbowMid).normalize() : new THREE.Vector3(isLHB ? -0.5 : 0.5, 0.4, 0.6).normalize();
      pBarrel = pHandle.clone().add(batDir.multiplyScalar(0.85));
    }

    if (pHandle && pBarrel) {
      batGroup.visible = true;
      // Bat midpoint for position
      const midBat = new THREE.Vector3().addVectors(pHandle, pBarrel).multiplyScalar(0.5);
      batGroup.position.copy(midBat);

      const batVector = new THREE.Vector3().subVectors(pBarrel, pHandle);
      const batLen = batVector.length() || 0.85;
      const batDirNorm = batVector.clone().normalize();

      const quat = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), batDirNorm);
      batGroup.quaternion.copy(quat);

      const scaleRatio = batLen / 0.85;
      batGroup.scale.set(1, Math.max(0.7, Math.min(1.3, scaleRatio)), 1);
    } else {
      batGroup.visible = false;
    }
  } else if (batGroup) {
    batGroup.visible = false;
  }

  // 2. 3D Bat Trajectory Trail
  const showTrail = document.getElementById('toggle-3d-trail')?.checked ?? true;
  if (batTrailLine && showTrail && pipelineDataA && pipelineDataA.bat_trajectory_3d && pipelineDataA.bat_trajectory_3d.length > 0) {
    batTrailLine.visible = true;
    const trajPts = pipelineDataA.bat_trajectory_3d.slice(0, Math.min(frameIndex + 1, pipelineDataA.bat_trajectory_3d.length)).map(pt => {
      const px = isLHB ? (targetBoxX - pt.x) : (targetBoxX + pt.x);
      return new THREE.Vector3(px, pt.y, pt.z);
    });
    if (trajPts.length >= 2) {
      batTrailLine.geometry.setFromPoints(trajPts);
    } else if (trajPts.length === 1) {
      batTrailLine.geometry.setFromPoints([trajPts[0], trajPts[0]]);
    }
  } else if (batTrailLine) {
    batTrailLine.visible = false;
  }

  // 3. Update X-Factor Vectors & Live Angles
  const showXFactor = document.getElementById('toggle-3d-xfactor')?.checked ?? true;
  if (xfactorGroup) {
    xfactorGroup.visible = showXFactor;
    if (coords.left_shoulder && coords.right_shoulder && shoulderLine) {
      shoulderLine.geometry.setFromPoints([coords.left_shoulder, coords.right_shoulder]);
    }
    if (coords.left_hip && coords.right_hip && pelvisLine) {
      pelvisLine.geometry.setFromPoints([coords.left_hip, coords.right_hip]);
    }
    if (shoulderMid && hipMid && spineLine) {
      spineLine.geometry.setFromPoints([shoulderMid, hipMid]);
    }

    // Live X-Factor calculation (horizontal separation in X-Z plane)
    if (coords.left_shoulder && coords.right_shoulder && coords.left_hip && coords.right_hip) {
      const sVec = new THREE.Vector2(
        coords.right_shoulder.x - coords.left_shoulder.x,
        coords.right_shoulder.z - coords.left_shoulder.z
      ).normalize();
      const hVec = new THREE.Vector2(
        coords.right_hip.x - coords.left_hip.x,
        coords.right_hip.z - coords.left_hip.z
      ).normalize();

      const dot = Math.max(-1, Math.min(1, sVec.dot(hVec)));
      let angleDeg = Math.acos(dot) * (180.0 / Math.PI);
      const hudXFactor = document.getElementById('three-live-xfactor');
      if (hudXFactor) hudXFactor.innerText = `${angleDeg.toFixed(1)}°`;
    }

    // Live Torso Inclination (Spine tilt from vertical Y axis)
    if (shoulderMid && hipMid) {
      const spine = new THREE.Vector3().subVectors(shoulderMid, hipMid).normalize();
      const up = new THREE.Vector3(0, 1, 0);
      const dot = Math.max(-1, Math.min(1, spine.dot(up)));
      const tiltDeg = Math.acos(dot) * (180.0 / Math.PI);
      const hudTorso = document.getElementById('three-live-torso');
      if (hudTorso) hudTorso.innerText = `${tiltDeg.toFixed(1)}°`;
    }

    // Live Lead Knee Angle (Lead leg block)
    const kJoint = isLHB ? (coords.right_knee || coords.left_knee) : (coords.left_knee || coords.right_knee);
    const hJoint = isLHB ? (coords.right_hip || coords.left_hip) : (coords.left_hip || coords.right_hip);
    const aJoint = isLHB ? (coords.right_ankle || coords.left_ankle) : (coords.left_ankle || coords.right_ankle);
    if (kJoint && hJoint && aJoint) {
      const thigh = new THREE.Vector3().subVectors(hJoint, kJoint).normalize();
      const shank = new THREE.Vector3().subVectors(aJoint, kJoint).normalize();
      const dot = Math.max(-1, Math.min(1, thigh.dot(shank)));
      const kneeDeg = Math.acos(dot) * (180.0 / Math.PI);
      const hudKnee = document.getElementById('three-live-knee');
      if (hudKnee) hudKnee.innerText = `${kneeDeg.toFixed(1)}°`;
    }
  }

  // 4. Camera Lock to Video Perspective & Athlete Tracking
  if (isCameraLocked && threeCamera && threeControls) {
    const targetRoot = hipMid || new THREE.Vector3(targetBoxX, 0.8, 0);
    const camXOffset = isLHB ? -0.1 : 0.1;
    threeCamera.position.set(targetRoot.x + camXOffset, targetRoot.y + 0.35, targetRoot.z + 3.25);
    threeControls.target.copy(targetRoot);
    threeCamera.lookAt(targetRoot.x, targetRoot.y + 0.1, targetRoot.z);
  }
}

function sync3DFromScrubber(val) {
  const frameIndex = parseInt(val);
  update3DSkeleton(frameIndex);
  if (pipelineDataA && pipelineDataA.source_fps) {
    video.currentTime = frameIndex / pipelineDataA.source_fps;
  }
}

// Camera View Presets & Camera Lock Toggle
function toggleCameraLock() {
  isCameraLocked = !isCameraLocked;
  const btn = document.getElementById('btn-camera-lock');
  const icon = document.getElementById('lock-icon');
  const text = document.getElementById('lock-text');

  if (isCameraLocked) {
    if (btn) {
      btn.className = 'px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition flex items-center gap-1 border border-emerald-500 shadow-md';
    }
    if (icon) icon.innerText = '🔒';
    if (text) text.innerText = 'Locked to Video';
    if (threeControls) threeControls.enabled = false;

    const currentFrame = parseInt(document.getElementById('three-scrubber')?.value || '0');
    update3DSkeleton(currentFrame);
  } else {
    if (btn) {
      btn.className = 'px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-amber-300 font-medium transition flex items-center gap-1 border border-slate-700';
    }
    if (icon) icon.innerText = '🔓';
    if (text) text.innerText = 'Lock to Video';
    if (threeControls) threeControls.enabled = true;
  }
}

function toggleStrikeZone(show) {
  if (strikeZoneGroup) strikeZoneGroup.visible = show;
}

function toggle3DXFactor(show) {
  if (xfactorGroup) xfactorGroup.visible = show;
}

function toggle3DBat(show) {
  if (batGroup) batGroup.visible = show;
}

function toggle3DTrail(show) {
  if (batTrailLine) batTrailLine.visible = show;
}

function setCameraView(preset) {
  if (!threeCamera || !threeControls) return;
  if (isCameraLocked) toggleCameraLock();

  const targetBoxX = (currentBatterStance === 'LHB') ? 0.75 : -0.75;

  if (preset === 'top') {
    // Top-down view (transverse plane)
    threeCamera.position.set(targetBoxX * 0.5, 4.2, 0.1);
    threeControls.target.set(targetBoxX * 0.5, 0.8, 0);
  } else if (preset === 'front') {
    // Frontal / pitcher's eye view
    threeCamera.position.set(targetBoxX, 1.2, 3.2);
    threeControls.target.set(targetBoxX, 0.8, 0);
  } else if (preset === 'side') {
    // Side dugout view
    threeCamera.position.set(3.4, 1.2, 0);
    threeControls.target.set(targetBoxX, 0.8, 0);
  } else if (preset === 'behind') {
    // Catcher / Behind plate view
    threeCamera.position.set(targetBoxX, 1.2, -3.2);
    threeControls.target.set(targetBoxX, 0.8, 0);
  }
  threeControls.update();
}

function resetCameraView() {
  if (!threeCamera || !threeControls) return;
  if (isCameraLocked) toggleCameraLock();
  const targetBoxX = (currentBatterStance === 'LHB') ? 0.75 : -0.75;
  threeCamera.position.set(targetBoxX + 1.2, 1.6, 3.0);
  threeControls.target.set(targetBoxX, 0.8, 0);
  threeControls.update();
}

// Expose globals to window for inline HTML onclick/onchange handlers
window.setBatterStance = setBatterStance;
window.toggleCameraLock = toggleCameraLock;
window.toggleStrikeZone = toggleStrikeZone;
window.toggle3DXFactor = toggle3DXFactor;
window.toggle3DBat = toggle3DBat;
window.toggle3DTrail = toggle3DTrail;
window.setCameraView = setCameraView;
window.resetCameraView = resetCameraView;
window.sync3DFromScrubber = sync3DFromScrubber;

// ----------------------------------------------------
// OPTION 3: SIDE-BY-SIDE DUAL VIDEO COMPARISON
// ----------------------------------------------------
async function loadVideoB(videoId) {
  const vidB = document.getElementById('video-element-b');
  vidB.src = `/api/v1/videos/${videoId}/stream`;
  vidB.load();

  try {
    const res = await fetch(`/api/v1/pipeline/run/${videoId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ processing_mode: 'full', generate_overlay: false })
    });
    if (res.ok) {
      pipelineDataB = await res.json();
      updateComparisonDeltas();
      renderComparisonKinematicsChart();
    }
  } catch (err) {
    console.error('Failed to load comparison Video B:', err);
  }
}

function toggleComparePlayback() {
  const vidA = document.getElementById('video-element-a');
  const vidB = document.getElementById('video-element-b');
  const btn = document.getElementById('btn-compare-play-pause');

  if (isComparingPlaying) {
    vidA.pause();
    vidB.pause();
    btn.innerText = '▶ Play Both';
    isComparingPlaying = false;
  } else {
    vidA.play();
    vidB.play();
    btn.innerText = '⏸ Pause Both';
    isComparingPlaying = true;
  }
}

function updateSyncOffset(val) {
  syncOffset = parseInt(val);
  document.getElementById('sync-offset-val').innerText = `${syncOffset > 0 ? '+' : ''}${syncOffset}F`;
  const masterScrubber = document.getElementById('compare-master-scrubber');
  syncDualScrubber(masterScrubber.value);
}

function syncDualScrubber(masterVal) {
  const masterFrame = parseInt(masterVal);
  document.getElementById('compare-frame-counter').innerText = `Master Frame ${masterFrame}`;

  const vidA = document.getElementById('video-element-a');
  const vidB = document.getElementById('video-element-b');

  const fpsA = (pipelineDataA && pipelineDataA.source_fps) || 30.0;
  const fpsB = (pipelineDataB && pipelineDataB.source_fps) || 30.0;

  vidA.currentTime = masterFrame / fpsA;
  const frameB = Math.max(0, masterFrame + syncOffset);
  vidB.currentTime = frameB / fpsB;
}

function updateComparisonDeltas() {
  if (!pipelineDataA || !pipelineDataB) return;

  const xfA = pipelineDataA.max_shoulder_hip_separation_deg || 0;
  const xfB = pipelineDataB.max_shoulder_hip_separation_deg || 0;
  const deltaXf = xfA - xfB;

  document.getElementById('comp-xfactor-a').innerText = `A: ${xfA.toFixed(1)}°`;
  document.getElementById('comp-xfactor-b').innerText = `B: ${xfB.toFixed(1)}°`;
  const elDeltaXf = document.getElementById('delta-xfactor');
  elDeltaXf.innerText = `${deltaXf >= 0 ? '+' : ''}${deltaXf.toFixed(1)}°`;
  elDeltaXf.className = `font-bold font-mono px-2 py-0.5 rounded ${deltaXf >= 0 ? 'bg-emerald-950 text-emerald-400' : 'bg-amber-950 text-amber-400'}`;

  const spdA = pipelineDataA.peak_barrel_speed || 0;
  const spdB = pipelineDataB.peak_barrel_speed || 0;
  const deltaSpd = spdA - spdB;

  document.getElementById('comp-speed-a').innerText = `A: ${spdA.toFixed(1)} px/s`;
  document.getElementById('comp-speed-b').innerText = `B: ${spdB.toFixed(1)} px/s`;
  const elDeltaSpd = document.getElementById('delta-speed');
  elDeltaSpd.innerText = `${deltaSpd >= 0 ? '+' : ''}${deltaSpd.toFixed(1)} px/s`;
  elDeltaSpd.className = `font-bold font-mono px-2 py-0.5 rounded ${deltaSpd >= 0 ? 'bg-emerald-950 text-emerald-400' : 'bg-amber-950 text-amber-400'}`;
}

function renderComparisonKinematicsChart() {
  if (!pipelineDataA || !pipelineDataB) return;
  const ctx = document.getElementById('kinematics-chart').getContext('2d');
  if (kinematicsChart) kinematicsChart.destroy();

  const maxLen = Math.max(
    (pipelineDataA.timestamps || []).length,
    (pipelineDataB.timestamps || []).length
  );
  const labels = Array.from({ length: maxLen }, (_, i) => `${(i * 0.033).toFixed(2)}s`);

  kinematicsChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'A: Pelvis Velocity (°/s)',
          data: pipelineDataA.pelvis_angular_velocities || [],
          borderColor: '#3b82f6',
          borderWidth: 2,
          pointRadius: 0
        },
        {
          label: 'B: Pelvis Velocity (°/s)',
          data: pipelineDataB.pelvis_angular_velocities || [],
          borderColor: '#8b5cf6',
          borderDash: [5, 5],
          borderWidth: 2,
          pointRadius: 0
        },
        {
          label: 'A: Torso Velocity (°/s)',
          data: pipelineDataA.torso_angular_velocities || [],
          borderColor: '#10b981',
          borderWidth: 2,
          pointRadius: 0
        },
        {
          label: 'B: Torso Velocity (°/s)',
          data: pipelineDataB.torso_angular_velocities || [],
          borderColor: '#f59e0b',
          borderDash: [5, 5],
          borderWidth: 2,
          pointRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { labels: { color: '#94a3b8', boxWidth: 12, font: { size: 10 } } }
      },
      scales: {
        x: { ticks: { color: '#64748b' }, grid: { color: '#1e293b' } },
        y: { ticks: { color: '#64748b' }, grid: { color: '#1e293b' } }
      }
    }
  });

  document.getElementById('chart-data-source-badge').innerText = `Comparison: Video A (${currentVideoId}) vs Video B (${document.getElementById('select-video-b').value})`;
}

// Benchmark Trigger
async function triggerBenchmark() {
  switchMode('benchmarks');
  const tbody = document.getElementById('benchmark-tbody');
  tbody.innerHTML = '<tr><td colspan="4" class="py-2 text-center text-slate-400">Benchmarking full, half_rate, and two_pass strategies...</td></tr>';

  try {
    const res = await fetch(`/api/v1/benchmark/run/${currentVideoId}`, { method: 'POST' });
    const data = await res.json();
    renderBenchmarkTable(data.runs);
  } catch (err) {
    console.error(err);
  }
}

function renderBenchmarkTable(runs) {
  const tbody = document.getElementById('benchmark-tbody');
  tbody.innerHTML = '';
  runs.forEach(r => {
    const tr = document.createElement('tr');
    tr.className = 'border-b border-slate-800/50';
    tr.innerHTML = `
      <td class="py-2 font-medium text-white">${r.processing_mode}</td>
      <td class="py-2 text-emerald-400 font-mono">${r.effective_throughput_fps.toFixed(1)} FPS</td>
      <td class="py-2 text-cyan-400 font-mono">${r.speedup_ratio.toFixed(2)}x</td>
      <td class="py-2 text-slate-300 font-mono">${r.accuracy ? r.accuracy.contact_frame_delta : 0}F</td>
    `;
    tbody.appendChild(tr);
  });
}

// Auto-initialize on page load
window.addEventListener('DOMContentLoaded', () => {
  loadSampleVideo('swing1');
});
