// System Design - Interactive 3D Globe Visualization
// Every page, every URL, every button connected in a living globe
'use strict';

// ─── State ────────────────────────────────────────────────────────────────────
let scene, camera, renderer;
let interactiveMeshes = [];
let raycaster, mouse;
let hoveredObject = null;
let selectedObject = null;
let globeGroup, particleSystem;
let infoPanelEl, tooltipEl;
let clock;
let dataFlowParticles = [];
let connectionLines = [];
let nodeMap = {};
let autoRotate = true;
const liveButtonsCache = new Map();

const orbit = { theta: 25, phi: 65, distance: 920, targetDistance: 920 };
let isDragging = false, lastPointer = { x: 0, y: 0 };

// ─── Complete Project URL Map ─────────────────────────────────────────────────
const PROJECT_NODES = [
  // ── CENTRAL HUB
  {
    id: 'admin_hub',
    name: 'Admin Hub',
    icon: 'server',
    category: 'core',
    status: 'central',
    url: '/dashboard/admin/overview/',
    description: 'Central admin control center for the entire platform',
    buttons: [
      { label: 'Overview', url: '/dashboard/admin/overview/' },
      { label: 'Analytics', url: '/dashboard/admin/analytics/' },
      { label: 'Activity', url: '/dashboard/admin/activity/' },
    ],
    connections: ['overview','analytics','activity','projects','volunteers','users','notifications','settings','announcements','faqs','donations','contacts','partners','communities','system_design','reports'],
    lat: 0, lng: 0,
  },
  // ── OVERVIEW / DASHBOARD
  {
    id: 'overview',
    name: 'Overview',
    icon: 'chart',
    category: 'dashboard',
    status: 'primary',
    url: '/dashboard/admin/overview/',
    description: 'Main dashboard overview with live stats and summaries',
    buttons: [
      { label: 'View Dashboard', url: '/dashboard/admin/overview/' },
      { label: 'Analytics', url: '/dashboard/admin/analytics/' },
      { label: 'Activity Log', url: '/dashboard/admin/activity/' },
    ],
    connections: ['analytics','activity','donations','volunteers'],
    lat: 35, lng: 45,
  },
  // ── ANALYTICS
  {
    id: 'analytics',
    name: 'Analytics',
    icon: 'analytics',
    category: 'dashboard',
    status: 'primary',
    url: '/dashboard/admin/analytics/',
    description: 'Platform analytics — charts, graphs and KPIs',
    buttons: [
      { label: 'View Analytics', url: '/dashboard/admin/analytics/' },
      { label: 'Monthly Report', url: '/dashboard/admin/reports/monthly/' },
      { label: 'Volunteer Report', url: '/dashboard/admin/reports/volunteers/' },
      { label: 'Project Report', url: '/dashboard/admin/reports/projects/' },
    ],
    connections: ['overview','reports'],
    lat: 55, lng: -30,
  },
  // ── ACTIVITY
  {
    id: 'activity',
    name: 'Activity Log',
    icon: 'activity',
    category: 'dashboard',
    status: 'secondary',
    url: '/dashboard/admin/activity/',
    description: 'Real-time log of platform events and user actions',
    buttons: [
      { label: 'View Activity', url: '/dashboard/admin/activity/' },
    ],
    connections: ['overview','users'],
    lat: 20, lng: 80,
  },
  // ── REPORTS
  {
    id: 'reports',
    name: 'Reports',
    icon: 'report',
    category: 'dashboard',
    status: 'primary',
    url: '/dashboard/admin/reports/monthly/',
    description: 'Monthly, volunteer and project analytic reports',
    buttons: [
      { label: 'Monthly Report', url: '/dashboard/admin/reports/monthly/' },
      { label: 'Volunteers Report', url: '/dashboard/admin/reports/volunteers/' },
      { label: 'Projects Report', url: '/dashboard/admin/reports/projects/' },
    ],
    connections: ['analytics','projects','volunteers'],
    lat: 70, lng: 10,
  },
  // ── PROJECTS
  {
    id: 'projects',
    name: 'Projects',
    icon: 'folder',
    category: 'content',
    status: 'primary',
    url: '/dashboard/admin/projects/',
    description: 'Manage all community projects — approve, reject, or review',
    buttons: [
      { label: 'All Projects', url: '/dashboard/admin/projects/' },
      { label: 'Pending', url: '/dashboard/admin/projects/pending/' },
      { label: 'Approved', url: '/dashboard/admin/projects/approved/' },
      { label: 'Rejected', url: '/dashboard/admin/projects/rejected/' },
      { label: 'Events', url: '/dashboard/events/' },
      { label: 'Create Event', url: '/dashboard/events/create/' },
    ],
    connections: ['volunteers','categories','reports','events'],
    lat: -20, lng: 50,
  },
  // ── EVENTS
  {
    id: 'events',
    name: 'Events',
    icon: 'calendar',
    category: 'content',
    status: 'primary',
    url: '/dashboard/events/',
    description: 'Community events — create, manage and handle requests',
    buttons: [
      { label: 'All Events', url: '/dashboard/events/' },
      { label: 'Create Event', url: '/dashboard/events/create/' },
      { label: 'Event Requests', url: '/dashboard/requests/' },
      { label: 'Approve Request', url: '/dashboard/requests/' },
    ],
    connections: ['projects','contacts'],
    lat: -40, lng: 30,
  },
  // ── VOLUNTEERS
  {
    id: 'volunteers',
    name: 'Volunteers',
    icon: 'users',
    category: 'people',
    status: 'warning',
    url: '/dashboard/admin/volunteers/',
    description: 'Volunteer management, applications and opportunities',
    buttons: [
      { label: 'All Volunteers', url: '/dashboard/admin/volunteers/' },
      { label: 'Applications', url: '/dashboard/admin/volunteers/applications/' },
      { label: 'Opportunities', url: '/dashboard/volunteers/opportunities/' },
      { label: 'Create Opportunity', url: '/dashboard/volunteers/opportunities/create/' },
      { label: 'Approve Application', url: '/dashboard/volunteers/applications/' },
    ],
    connections: ['users','projects','reports','communities'],
    lat: -10, lng: -60,
  },
  // ── USERS
  {
    id: 'users',
    name: 'Users',
    icon: 'user',
    category: 'people',
    status: 'secondary',
    url: '/dashboard/admin/users/',
    description: 'User management — profiles, roles, bans and warnings',
    buttons: [
      { label: 'All Users', url: '/dashboard/admin/users/' },
      { label: 'Roles', url: '/dashboard/admin/users/roles/' },
      { label: 'Profiles', url: '/dashboard/admin/users/profiles/' },
      { label: 'Public Login', url: '/users/login/' },
      { label: 'Public Register', url: '/users/register/' },
      { label: 'My Profile', url: '/users/profile/' },
    ],
    connections: ['volunteers','notifications','activity','contacts'],
    lat: 30, lng: -90,
  },
  // ── NOTIFICATIONS
  {
    id: 'notifications',
    name: 'Notifications',
    icon: 'bell',
    category: 'system',
    status: 'secondary',
    url: '/dashboard/admin/notifications/',
    description: 'Platform-wide notifications and system alerts',
    buttons: [
      { label: 'All Notifications', url: '/dashboard/admin/notifications/' },
      { label: 'Mark All Read', url: '/dashboard/admin/notifications/mark-all-read/' },
    ],
    connections: ['settings','users','announcements'],
    lat: 60, lng: -70,
  },
  // ── SETTINGS
  {
    id: 'settings',
    name: 'Settings',
    icon: 'gear',
    category: 'system',
    status: 'secondary',
    url: '/dashboard/admin/settings/',
    description: 'Platform configuration, profile and security settings',
    buttons: [
      { label: 'Admin Settings', url: '/dashboard/admin/settings/' },
      { label: 'My Profile', url: '/users/profile/' },
      { label: 'Password Reset', url: '/users/password-reset/' },
    ],
    connections: ['notifications','users'],
    lat: 80, lng: 100,
  },
  // ── ANNOUNCEMENTS
  {
    id: 'announcements',
    name: 'Announcements',
    icon: 'megaphone',
    category: 'content',
    status: 'primary',
    url: '/dashboard/announcements/',
    description: 'Post and manage community announcements',
    buttons: [
      { label: 'All Announcements', url: '/dashboard/announcements/' },
      { label: 'Create Announcement', url: '/dashboard/announcements/create/' },
      { label: 'Public View', url: '/announcements/' },
    ],
    connections: ['notifications','contacts','faqs'],
    lat: -50, lng: -20,
  },
  // ── FAQs
  {
    id: 'faqs',
    name: 'FAQs',
    icon: 'help',
    category: 'content',
    status: 'primary',
    url: '/dashboard/faqs/',
    description: 'Manage frequently asked questions',
    buttons: [
      { label: 'All FAQs', url: '/dashboard/faqs/' },
      { label: 'Create FAQ', url: '/dashboard/faqs/create/' },
      { label: 'Public FAQ', url: '/faq/' },
    ],
    connections: ['announcements','contacts'],
    lat: -60, lng: 70,
  },
  // ── DONATIONS
  {
    id: 'donations',
    name: 'Donations',
    icon: 'donation',
    category: 'finance',
    status: 'success',
    url: '/dashboard/donations/',
    description: 'Donation tracking, verification and management',
    buttons: [
      { label: 'All Donations', url: '/dashboard/donations/' },
      { label: 'Create Record', url: '/dashboard/donations/create/' },
      { label: 'Donate Now', url: '/donate/' },
    ],
    connections: ['overview','analytics','contacts'],
    lat: 10, lng: 130,
  },
  // ── CONTACTS
  {
    id: 'contacts',
    name: 'Contacts',
    icon: 'contact',
    category: 'people',
    status: 'secondary',
    url: '/dashboard/contact-messages/',
    description: 'Manage contact form submissions and inquiries',
    buttons: [
      { label: 'All Messages', url: '/dashboard/contact-messages/' },
      { label: 'Create Message', url: '/dashboard/contact-messages/create/' },
      { label: 'Public Contact', url: '/contact/' },
    ],
    connections: ['users','announcements','faqs','events'],
    lat: -30, lng: -120,
  },
  // ── PARTNERS
  {
    id: 'partners',
    name: 'Partners',
    icon: 'handshake',
    category: 'content',
    status: 'primary',
    url: '/dashboard/partners/',
    description: 'Manage partner organizations and collaborators',
    buttons: [
      { label: 'All Partners', url: '/dashboard/partners/' },
      { label: 'Add Partner', url: '/dashboard/partners/create/' },
      { label: 'Public View', url: '/partners/' },
    ],
    connections: ['communities','donations'],
    lat: 45, lng: 160,
  },
  // ── COMMUNITIES
  {
    id: 'communities',
    name: 'Communities',
    icon: 'community',
    category: 'content',
    status: 'primary',
    url: '/communities/',
    description: 'Community groups and ethnic organizations directory',
    buttons: [
      { label: 'View Communities', url: '/communities/' },
    ],
    connections: ['partners','volunteers','projects'],
    lat: -70, lng: -80,
  },
  // ── CATEGORIES
  {
    id: 'categories',
    name: 'Categories',
    icon: 'tag',
    category: 'system',
    status: 'secondary',
    url: '/dashboard/admin/categories/',
    description: 'Content categorization and taxonomy management',
    buttons: [
      { label: 'All Categories', url: '/dashboard/admin/categories/' },
      { label: 'Create Category', url: '/dashboard/admin/categories/create/' },
    ],
    connections: ['projects','faqs'],
    lat: 75, lng: -140,
  },
  // ── PUBLIC HOME
  {
    id: 'public_home',
    name: 'Public Site',
    icon: 'home',
    category: 'public',
    status: 'public',
    url: '/',
    description: 'Public-facing website homepage',
    buttons: [
      { label: 'Home', url: '/' },
      { label: 'About', url: '/about/' },
      { label: 'Search', url: '/search/' },
      { label: 'Privacy Policy', url: '/privacy/' },
      { label: 'Terms of Use', url: '/terms/' },
      { label: 'Accessibility', url: '/accessibility/' },
    ],
    connections: ['overview','users','communities','programs','partners','announcements','donations','contacts'],
    lat: -45, lng: 150,
  },
  // ── PROGRAMS
  {
    id: 'programs',
    name: 'Programs',
    icon: 'program',
    category: 'public',
    status: 'public',
    url: '/programs/',
    description: 'Community programs and services listing',
    buttons: [
      { label: 'All Programs', url: '/programs/' },
    ],
    connections: ['public_home','communities','volunteers'],
    lat: -15, lng: -170,
  },
  // ── SYSTEM DESIGN
  {
    id: 'system_design',
    name: 'System Design',
    icon: 'system',
    category: 'system',
    status: 'central',
    url: '/dashboard/admin/system-design/',
    description: 'This page — interactive 3D globe architecture map',
    buttons: [
      { label: 'This Page', url: '/dashboard/admin/system-design/' },
    ],
    connections: ['admin_hub','settings'],
    lat: -80, lng: -40,
  },
];

// ─── Color Palettes ───────────────────────────────────────────────────────────
const STATUS_COLORS = {
  central:   0x00d4ff,
  primary:   0x4a90e2,
  secondary: 0x7c6cff,
  warning:   0xff6b4a,
  success:   0x4caf50,
  public:    0x29b6f6,
};

// Root node highlight color (node only, not transmission lines)
const ROOT_NODE_IDS = new Set(['admin_hub']);
const ROOT_NODE_COLOR = 0xffd700;

function getNodeColor(nodeData) {
  if (nodeData && ROOT_NODE_IDS.has(nodeData.id)) return ROOT_NODE_COLOR;
  return STATUS_COLORS[nodeData && nodeData.status] || 0x4a90e2;
}

// ─── Connection line colours ──────────────────────────────────────────────────
const COLOR_CONN_OK  = 0x00e676;  // bright green  — healthy / active connection
const COLOR_CONN_ERR = 0xff1744;  // bright red    — broken / issue connection

// Pairs that should render as RED (broken / issue).  Key = sorted IDs joined by '|'.
const BROKEN_PAIRS = new Set([
  // Examples — add or remove pairs here to flag connection issues:
  // ['programs','public_home'].sort().join('|'),
]);

const CATEGORY_META = {
  core:      { color: '#00d4ff', label: 'Core' },
  dashboard: { color: '#4a90e2', label: 'Dashboard' },
  content:   { color: '#4caf50', label: 'Content' },
  people:    { color: '#ff6b4a', label: 'People' },
  system:    { color: '#7c6cff', label: 'System' },
  finance:   { color: '#ffd700', label: 'Finance' },
  public:    { color: '#29b6f6', label: 'Public' },
};

// ─── Math Helpers ─────────────────────────────────────────────────────────────
function latLngToXYZ(lat, lng, r) {
  const phi   = THREE.MathUtils.degToRad(90 - lat);
  const theta = THREE.MathUtils.degToRad(lng);
  return new THREE.Vector3(
    r * Math.sin(phi) * Math.cos(theta),
    r * Math.cos(phi),
    r * Math.sin(phi) * Math.sin(theta)
  );
}

function hexToRGB(hex) {
  return { r: (hex >> 16) & 0xff, g: (hex >> 8) & 0xff, b: hex & 0xff };
}

function hslToRgb(h, s, l) {
  let r, g, b;
  if (s === 0) { r = g = b = l; }
  else {
    const hue2rgb = (p, q, t) => {
      if (t < 0) t += 1; if (t > 1) t -= 1;
      if (t < 1/6) return p + (q-p)*6*t;
      if (t < 1/2) return q;
      if (t < 2/3) return p + (q-p)*(2/3-t)*6;
      return p;
    };
    const q = l < 0.5 ? l*(1+s) : l+s-l*s, p = 2*l-q;
    r = hue2rgb(p,q,h+1/3); g = hue2rgb(p,q,h); b = hue2rgb(p,q,h-1/3);
  }
  return [r, g, b];
}

// ─── Texture Generation ───────────────────────────────────────────────────────
function buildEarthTex(w, h) {
  const cvs = document.createElement('canvas');
  cvs.width = w; cvs.height = h;
  const ctx = cvs.getContext('2d');

  // Ocean
  const og = ctx.createLinearGradient(0,0,w,h);
  og.addColorStop(0,'#051020'); og.addColorStop(0.5,'#092040'); og.addColorStop(1,'#0c3060');
  ctx.fillStyle = og; ctx.fillRect(0,0,w,h);

  // Continents
  const lands = [
    [0.13,0.33,0.08],[0.23,0.28,0.06],[0.31,0.36,0.055],
    [0.48,0.38,0.11],[0.53,0.54,0.07],[0.61,0.36,0.09],
    [0.73,0.41,0.06],[0.81,0.37,0.05],[0.86,0.60,0.07],
    [0.26,0.64,0.09],[0.36,0.69,0.06],[0.66,0.69,0.08],
  ];
  lands.forEach(([xf,yf,sf]) => {
    ctx.globalAlpha = 0.6;
    const g = ctx.createRadialGradient(xf*w,yf*h,0,xf*w,yf*h,sf*w);
    g.addColorStop(0,'rgba(55,110,55,0.95)'); g.addColorStop(0.5,'rgba(40,80,40,0.6)'); g.addColorStop(1,'rgba(25,55,25,0)');
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(xf*w,yf*h,sf*w,0,Math.PI*2); ctx.fill();
  });
  ctx.globalAlpha = 1;

  // Grid
  ctx.strokeStyle = 'rgba(74,144,226,0.10)'; ctx.lineWidth = 1;
  for (let ly = 0; ly <= h; ly += h/12) { ctx.beginPath(); ctx.moveTo(0,ly); ctx.lineTo(w,ly); ctx.stroke(); }
  for (let lx = 0; lx <= w; lx += w/24) { ctx.beginPath(); ctx.moveTo(lx,0); ctx.lineTo(lx,h); ctx.stroke(); }

  // City glow dots
  PROJECT_NODES.forEach(n => {
    const nx = ((n.lng + 180)/360)*w;
    const ny = ((90 - n.lat)/180)*h;
    const col = getNodeColor(n);
    const { r,g,b } = hexToRGB(col);
    const gd = ctx.createRadialGradient(nx,ny,0,nx,ny,10);
    gd.addColorStop(0,`rgba(${r},${g},${b},0.9)`);
    gd.addColorStop(1,`rgba(${r},${g},${b},0)`);
    ctx.fillStyle = gd; ctx.beginPath(); ctx.arc(nx,ny,10,0,Math.PI*2); ctx.fill();
    ctx.fillStyle = 'rgba(255,240,80,0.9)'; ctx.beginPath(); ctx.arc(nx,ny,3,0,Math.PI*2); ctx.fill();
  });

  return cvs;
}

function buildStarfieldTex(w, h) {
  const cvs = document.createElement('canvas');
  cvs.width = w; cvs.height = h;
  const ctx = cvs.getContext('2d');
  ctx.fillStyle = '#000308'; ctx.fillRect(0,0,w,h);

  for (let i = 0; i < 2000; i++) {
    const x = Math.random()*w, y = Math.random()*h;
    const s = Math.random()*1.8+0.2;
    ctx.globalAlpha = Math.random()*0.9+0.1;
    ctx.fillStyle = `hsl(${200+Math.random()*60},${40+Math.random()*50}%,${70+Math.random()*30}%)`;
    ctx.beginPath(); ctx.arc(x,y,s,0,Math.PI*2); ctx.fill();
  }
  ctx.globalAlpha = 1;

  // Nebulas
  [[0.2,0.4,'rgba(80,20,150,0.07)'],[0.7,0.6,'rgba(20,80,180,0.06)'],[0.5,0.2,'rgba(150,40,80,0.05)']].forEach(([xf,yf,c]) => {
    const g = ctx.createRadialGradient(xf*w,yf*h,0,xf*w,yf*h,w*0.22);
    g.addColorStop(0,c); g.addColorStop(1,'rgba(0,0,0,0)');
    ctx.fillStyle = g; ctx.fillRect(0,0,w,h);
  });
  return cvs;
}

// ─── Materials ────────────────────────────────────────────────────────────────
const _matCache = {};
function nodeMat(color, ei = 0.55) {
  const key = `${color}_${ei}`;
  if (!_matCache[key]) {
    _matCache[key] = new THREE.MeshStandardMaterial({
      color, emissive: color, emissiveIntensity: ei,
      metalness: 0.8, roughness: 0.2,
    });
  }
  return _matCache[key].clone();
}

// ─── Label Sprite ─────────────────────────────────────────────────────────────
function makeLabel(text, color, scale = 1) {
  const W = 350, H = 78;
  const cvs = document.createElement('canvas');
  cvs.width = W; cvs.height = H;
  const ctx = cvs.getContext('2d');
  const {r,g,b} = hexToRGB(color);

  ctx.fillStyle = 'rgba(5,10,22,0.90)';
  if (ctx.roundRect) { ctx.beginPath(); ctx.roundRect(3,3,W-6,H-6,9); ctx.fill(); }
  else { ctx.fillRect(3,3,W-6,H-6); }

  ctx.strokeStyle = `rgb(${r},${g},${b})`; ctx.lineWidth = 2;
  if (ctx.roundRect) { ctx.beginPath(); ctx.roundRect(3,3,W-6,H-6,9); ctx.stroke(); }
  else { ctx.strokeRect(3,3,W-6,H-6); }

  ctx.font = `bold ${Math.round(21*scale)}px 'Segoe UI',system-ui,sans-serif`;
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillStyle = `rgb(${r},${g},${b})`;
  ctx.fillText(text, W/2, H/2);

  const tex = new THREE.CanvasTexture(cvs);
  tex.needsUpdate = true;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map:tex, transparent:true, depthTest:false }));
  sp.scale.set(W*0.22, H*0.22, 1);
  sp.renderOrder = 5;
  return sp;
}

// ─── Node Mesh ────────────────────────────────────────────────────────────────
function buildNode(nodeData, pos) {
  const color  = getNodeColor(nodeData);
  const central = nodeData.status === 'central';
  const nr     = central ? 22 : 12;

  const grp = new THREE.Group();
  grp.position.copy(pos);
  grp.userData = { nodeData, isNode: true };

  // Core sphere
  const core = new THREE.Mesh(
    new THREE.SphereGeometry(nr, 36, 36),
    nodeMat(color, central ? 1.3 : 0.65)
  );
  core.userData = { nodeData, isNode: true };
  core.name = nodeData.id;
  grp.add(core);
  interactiveMeshes.push(core);

  // Glow ring
  const ringMat = new THREE.MeshBasicMaterial({ color, transparent:true, opacity:0.22, side:THREE.DoubleSide });
  const ring = new THREE.Mesh(new THREE.RingGeometry(nr*1.35, nr*1.65, 32), ringMat);
  ring.lookAt(pos.clone().normalize().multiplyScalar(999));
  grp.add(ring);

  // Pulse ring
  const pulseMat = new THREE.MeshBasicMaterial({ color, transparent:true, opacity:0.10, side:THREE.DoubleSide });
  const pulse = new THREE.Mesh(new THREE.RingGeometry(nr*1.9, nr*2.25, 32), pulseMat);
  pulse.lookAt(pos.clone().normalize().multiplyScalar(999));
  pulse.userData = { isPulse:true, base:0.10, _t:Math.random()*Math.PI*2 };
  grp.add(pulse);

  // Spike (antenna outward from globe)
  const spikeH = central ? 40 : 20;
  const spike = new THREE.Mesh(
    new THREE.CylinderGeometry(0, nr*0.28, spikeH, 8),
    new THREE.MeshBasicMaterial({ color, transparent:true, opacity:0.5 })
  );
  spike.position.copy(pos.clone().normalize().multiplyScalar(spikeH*0.5));
  spike.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0), pos.clone().normalize());
  grp.add(spike);

  // Label
  const lbl = makeLabel(nodeData.name, color, central ? 1.1 : 0.88);
  lbl.position.copy(pos.clone().normalize().multiplyScalar(nr + 42));
  grp.add(lbl);

  return { grp, core };
}

// ─── Arc Connection ───────────────────────────────────────────────────────────
function buildArc(from, to, color, opacity = 0.70) {
  const mid = from.clone().add(to).multiplyScalar(0.5);
  mid.normalize().multiplyScalar(290 + from.distanceTo(to) * 0.38);
  const curve = new THREE.QuadraticBezierCurve3(from.clone(), mid, to.clone());
  const pts = curve.getPoints(72);
  const geom = new THREE.BufferGeometry().setFromPoints(pts);

  // Two-layer line: bright core + wide glow for maximum visibility
  const group = new THREE.Group();
  group.add(new THREE.Line(
    geom.clone(),
    new THREE.LineBasicMaterial({ color, transparent: true, opacity })
  ));
  group.add(new THREE.Line(
    geom,
    new THREE.LineBasicMaterial({ color, transparent: true, opacity: opacity * 0.30 })
  ));
  return group;
}

// ─── Data-flow particle ───────────────────────────────────────────────────────
function buildFlowParticle(from, to, color) {
  const mid = from.clone().add(to).multiplyScalar(0.5);
  mid.normalize().multiplyScalar(290 + from.distanceTo(to) * 0.38);
  const curve = new THREE.QuadraticBezierCurve3(from.clone(), mid, to.clone());
  const mesh = new THREE.Mesh(
    new THREE.SphereGeometry(2.8, 8, 8),
    new THREE.MeshBasicMaterial({ color, transparent:true, opacity:0.85 })
  );
  mesh.userData = { curve, t: Math.random(), speed: 0.004 + Math.random()*0.007 };
  return mesh;
}

// ─── Nebula particles ─────────────────────────────────────────────────────────
function buildNebula() {
  const N = 900;
  const geo = new THREE.BufferGeometry();
  const pos = new Float32Array(N*3), col = new Float32Array(N*3);
  for (let i = 0; i < N; i++) {
    const r = 1100 + Math.random()*1600;
    const ph = Math.acos(2*Math.random()-1), th = Math.random()*Math.PI*2;
    pos[i*3] = r*Math.sin(ph)*Math.cos(th);
    pos[i*3+1] = r*Math.cos(ph);
    pos[i*3+2] = r*Math.sin(ph)*Math.sin(th);
    const [cr,cg,cb] = hslToRgb(0.55+Math.random()*0.3, 0.7, 0.5);
    col[i*3]=cr; col[i*3+1]=cg; col[i*3+2]=cb;
  }
  geo.setAttribute('position', new THREE.BufferAttribute(pos,3));
  geo.setAttribute('color',    new THREE.BufferAttribute(col,3));
  return new THREE.Points(geo, new THREE.PointsMaterial({
    size:2.5, vertexColors:true, transparent:true, opacity:0.5, sizeAttenuation:true,
  }));
}

// ─── Main Init ────────────────────────────────────────────────────────────────
function initSystemChain() {
  const container = document.getElementById('systemChain3D');
  if (!container) return;

  infoPanelEl = document.getElementById('systemChainPanel');
  tooltipEl   = document.getElementById('sc_tooltip');

  if (typeof THREE === 'undefined') {
    if (infoPanelEl) {
      infoPanelEl.style.display = 'block';
      infoPanelEl.innerHTML = '<h3 style="color:#ff4444">Three.js not loaded</h3><p>Check your internet connection.</p>';
    }
    return;
  }

  clock = new THREE.Clock();
  scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x000308, 0.00022);

  camera = new THREE.PerspectiveCamera(50, container.offsetWidth / container.offsetHeight, 0.5, 7000);

  renderer = new THREE.WebGLRenderer({ antialias:true, alpha:false, powerPreference:'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(container.offsetWidth, container.offsetHeight);
  renderer.setClearColor(0x000308, 1);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.1;
  container.appendChild(renderer.domElement);

  // Skybox
  scene.add(new THREE.Mesh(
    new THREE.SphereGeometry(5500, 64, 32),
    new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(buildStarfieldTex(4096, 2048)), side: THREE.BackSide })
  ));

  // Lights
  scene.add(new THREE.AmbientLight(0xffffff, 0.4));
  const sun = new THREE.DirectionalLight(0xfff0cc, 1.8);
  sun.position.set(1200,800,800); sun.castShadow = true;
  sun.shadow.mapSize.setScalar(2048);
  scene.add(sun);
  const bl = new THREE.PointLight(0x4a90e2, 1.2, 2800);
  bl.position.set(-800,400,-600); scene.add(bl);
  const pl = new THREE.PointLight(0x7c3aed, 0.8, 2200);
  pl.position.set(600,-600,800); scene.add(pl);

  // Nebula
  particleSystem = buildNebula();
  scene.add(particleSystem);

  // Globe group
  globeGroup = new THREE.Group();
  scene.add(globeGroup);

  // Earth
  const earthMesh = new THREE.Mesh(
    new THREE.SphereGeometry(280, 128, 64),
    new THREE.MeshStandardMaterial({
      map: new THREE.CanvasTexture(buildEarthTex(4096, 2048)),
      metalness: 0.1, roughness: 0.7,
      emissive: 0x081830, emissiveIntensity: 0.18,
    })
  );
  earthMesh.castShadow = true; earthMesh.receiveShadow = true;
  globeGroup.add(earthMesh);

  // Atmosphere
  globeGroup.add(new THREE.Mesh(
    new THREE.SphereGeometry(296, 64, 32),
    new THREE.MeshStandardMaterial({
      transparent:true, opacity:0.30,
      color: 0x4a90e2, emissive: 0x4a90e2, emissiveIntensity: 0.10,
      side: THREE.FrontSide, depthWrite: false,
    })
  ));

  // Clouds
  const clouds = new THREE.Mesh(
    new THREE.SphereGeometry(284, 64, 32),
    new THREE.MeshStandardMaterial({ transparent:true, opacity:0.07, color:0xffffff, depthWrite:false })
  );
  clouds.userData.isClouds = true;
  globeGroup.add(clouds);

  // Equator ring
  const eqPts = [];
  for (let i = 0; i <= 128; i++) { const a = (i/128)*Math.PI*2; eqPts.push(new THREE.Vector3(Math.cos(a)*298,0,Math.sin(a)*298)); }
  globeGroup.add(new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(eqPts),
    new THREE.LineBasicMaterial({ color:0x4a90e2, transparent:true, opacity:0.14 })
  ));

  // Nodes
  const GR = 290;
  PROJECT_NODES.forEach(nd => {
    const pos = latLngToXYZ(nd.lat, nd.lng, GR);
    const { grp, core } = buildNode(nd, pos);
    globeGroup.add(grp);
    nodeMap[nd.id] = { grp, core, pos, nodeData: nd };
  });

  // Connections + flow particles
  const seenPairs = new Set();
  PROJECT_NODES.forEach(nd => {
    const fromE = nodeMap[nd.id];
    if (!fromE) return;
    (nd.connections||[]).forEach(tid => {
      const toE = nodeMap[tid];
      if (!toE) return;
      const key = [nd.id, tid].sort().join('|');
      if (seenPairs.has(key)) return;
      seenPairs.add(key);
      const isBroken = BROKEN_PAIRS.has(key);
      const col      = isBroken ? COLOR_CONN_ERR : COLOR_CONN_OK;
      const baseOp   = isBroken ? 0.85 : 0.70;
      const arc = buildArc(fromE.pos, toE.pos, col, baseOp);
      arc.userData.pairKey   = key;
      arc.userData.fromId    = nd.id;
      arc.userData.toId      = tid;
      arc.userData.baseColor = col;
      arc.userData.baseOp    = baseOp;
      globeGroup.add(arc);
      connectionLines.push(arc);
      const fp = buildFlowParticle(fromE.pos, toE.pos, col);
      fp.userData.fromId = nd.id;
      fp.userData.toId   = tid;
      globeGroup.add(fp);
      dataFlowParticles.push(fp);
    });
  });

  // Events
  raycaster = new THREE.Raycaster();
  mouse = new THREE.Vector2();
  container.addEventListener('pointerdown',  onPointerDown);
  container.addEventListener('pointermove',  onPointerMove);
  container.addEventListener('pointerup',    onPointerUp);
  container.addEventListener('pointerleave', onPointerUp);
  container.addEventListener('wheel',        onWheel, { passive:false });
  container.addEventListener('click',        onPointerClick);
  window.addEventListener('resize',          onWindowResize);

  // Wire up UI controls (buttons in template)
  const rotBtn   = document.getElementById('sc_rotate');
  const resetBtn = document.getElementById('sc_reset');
  const searchEl = document.getElementById('sc_search');

  if (rotBtn)   rotBtn.addEventListener('click', () => { autoRotate = !autoRotate; rotBtn.classList.toggle('active', autoRotate); });
  if (resetBtn) resetBtn.addEventListener('click', () => {
    orbit.theta = 25; orbit.phi = 65; orbit.distance = 920; orbit.targetDistance = 920;
    updateCamera(); hideInfoPanel();
    if (selectedObject) { resetHighlight(selectedObject); selectedObject = null; }
    resetConnectionHighlights();
  });
  if (searchEl) searchEl.addEventListener('input', e => filterNodes(e.target.value.trim().toLowerCase()));

  document.querySelectorAll('.sc-filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.sc-filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      filterByCategory(btn.dataset.category || 'all');
    });
  });

  updateCamera();
  animate();
}

// ─── Filters ──────────────────────────────────────────────────────────────────
function filterNodes(q) {
  Object.values(nodeMap).forEach(({ grp, nodeData }) => {
    grp.visible = !q || nodeData.name.toLowerCase().includes(q) || nodeData.category.includes(q);
  });
  syncConnectionVisibility();
}

function filterByCategory(cat) {
  Object.values(nodeMap).forEach(({ grp, nodeData }) => {
    grp.visible = cat === 'all' || nodeData.category === cat;
  });
  syncConnectionVisibility();
}

function syncConnectionVisibility() {
  connectionLines.forEach(l => {
    const from = nodeMap[l.userData.fromId];
    const to   = nodeMap[l.userData.toId];
    l.visible = !!(from && to && from.grp.visible && to.grp.visible);
  });

  dataFlowParticles.forEach(p => {
    const from = nodeMap[p.userData.fromId];
    const to   = nodeMap[p.userData.toId];
    p.visible = !!(from && to && from.grp.visible && to.grp.visible);
  });
}

// ─── Pointer ──────────────────────────────────────────────────────────────────
function onPointerDown(e) {
  if (e.button !== 0) return;
  isDragging = true;
  lastPointer = { x: e.clientX, y: e.clientY };
}

function onPointerMove(e) {
  const rect = renderer.domElement.getBoundingClientRect();
  mouse.x =  ((e.clientX - rect.left) / rect.width)  * 2 - 1;
  mouse.y = -((e.clientY - rect.top)  / rect.height) * 2 + 1;

  if (isDragging) {
    const dx = e.clientX - lastPointer.x;
    const dy = e.clientY - lastPointer.y;
    lastPointer = { x: e.clientX, y: e.clientY };
    orbit.theta += dx * 0.28;
    orbit.phi    = Math.max(5, Math.min(175, orbit.phi - dy * 0.28));
    updateCamera();
    return;
  }

  raycaster.setFromCamera(mouse, camera);
  const hits = raycaster.intersectObjects(interactiveMeshes, false);
  if (hits.length) {
    const obj = hits[0].object;
    if (hoveredObject !== obj) {
      if (hoveredObject) doResetHighlight(hoveredObject);
      hoveredObject = obj;
      doHighlight(obj, false, false);
      showTooltip(obj, e.clientX, e.clientY);
      renderer.domElement.style.cursor = 'pointer';
    }
  } else {
    if (hoveredObject) { doResetHighlight(hoveredObject); hoveredObject = null; hideTooltip(); }
    renderer.domElement.style.cursor = 'grab';
  }
}

function onPointerUp()  { isDragging = false; }

function onPointerClick() {
  if (!hoveredObject) return;
  const nd = hoveredObject.userData.nodeData;
  if (!nd) return;
  if (selectedObject && selectedObject !== hoveredObject) doResetHighlight(selectedObject);
  selectedObject = hoveredObject;
  doHighlight(selectedObject, false, true);
  showInfoPanel(nd);
}

function onWheel(e) {
  e.preventDefault();
  orbit.targetDistance = Math.min(1500, Math.max(350, orbit.targetDistance + e.deltaY * 0.85));
}

// ─── Camera ───────────────────────────────────────────────────────────────────
function updateCamera() {
  const phi   = THREE.MathUtils.degToRad(orbit.phi);
  const theta = THREE.MathUtils.degToRad(orbit.theta);
  const d = orbit.distance;
  camera.position.set(d*Math.sin(phi)*Math.cos(theta), d*Math.cos(phi), d*Math.sin(phi)*Math.sin(theta));
  camera.lookAt(0, 0, 0);
}

// ─── Highlight ────────────────────────────────────────────────────────────────
function doHighlight(obj, isHover, isSelect) {
  if (!obj) return;
  if (!obj.userData._oScale) obj.userData._oScale = obj.scale.clone();
  if (obj.userData._oEI === undefined) obj.userData._oEI = obj.material ? obj.material.emissiveIntensity : 0;
  obj.scale.setScalar(isSelect ? 1.75 : 1.38);
  if (obj.material) obj.material.emissiveIntensity = isSelect ? 2.2 : 1.5;
  if (obj.userData.nodeData) highlightConns(obj.userData.nodeData.id);
}

function doResetHighlight(obj) {
  if (!obj) return;
  if (obj.userData._oScale) obj.scale.copy(obj.userData._oScale);
  if (obj.material && obj.userData._oEI !== undefined) obj.material.emissiveIntensity = obj.userData._oEI;
  if (obj !== selectedObject) resetConnectionHighlights();
}

function highlightConns(nodeId) {
  connectionLines.forEach(l => {
    const isRelated = l.userData.pairKey && l.userData.pairKey.includes(nodeId);
    // Traverse the two-layer group
    l.traverse(child => {
      if (!child.isMesh && child.type !== 'Line') return;
      if (!child.material) return;
      if (isRelated) {
        child.material.opacity = child === l.children[0] ? 1.0 : 0.40;
        child.material.color.setHex(0xffffff);
      } else {
        child.material.opacity = 0.03;
      }
    });
  });
}

function resetConnectionHighlights() {
  connectionLines.forEach(l => {
    const col    = l.userData.baseColor || COLOR_CONN_OK;
    const baseOp = l.userData.baseOp    || 0.70;
    l.traverse(child => {
      if (!child.material) return;
      child.material.color.setHex(col);
      // Core line = full baseOp, glow line = 30 % of that
      child.material.opacity = child === l.children[0] ? baseOp : baseOp * 0.30;
    });
  });
}

// ─── Tooltip ──────────────────────────────────────────────────────────────────
function showTooltip(obj, cx, cy) {
  if (!tooltipEl) return;
  const nd = obj.userData.nodeData;
  if (!nd) return;
  tooltipEl.innerHTML = `<strong>${nd.name}</strong><br><em>${nd.category}</em> — ${nd.description}`;
  tooltipEl.style.left = (cx + 16) + 'px';
  tooltipEl.style.top  = (cy - 14) + 'px';
  tooltipEl.style.display = 'block';
}

function hideTooltip() { if (tooltipEl) tooltipEl.style.display = 'none'; }

function escapeHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function isButtonLikeAnchor(el) {
  const cls = (el.className || '').toString();
  const role = (el.getAttribute('role') || '').toLowerCase();
  return role === 'button' || /(btn|button|action|assign|approve|reject|delete|create|save|submit|filter)/i.test(cls);
}

function extractLiveButtonsFromHTML(html, baseUrl) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, 'text/html');

  const root =
    doc.querySelector('main') ||
    doc.querySelector('.content-wrapper') ||
    doc.querySelector('.content') ||
    doc.body;

  const nodes = root.querySelectorAll("button, input[type='button'], input[type='submit'], [role='button'], a");
  const out = [];
  const seen = new Set();

  nodes.forEach(el => {
    if (el.hidden || el.getAttribute('aria-hidden') === 'true') return;

    const tag = el.tagName;
    if (tag === 'A' && !isButtonLikeAnchor(el)) return;

    let label = '';
    if (tag === 'INPUT') label = (el.value || '').trim();
    if (!label) label = (el.textContent || '').replace(/\s+/g, ' ').trim();
    if (!label) label = (el.getAttribute('aria-label') || el.getAttribute('title') || '').trim();
    if (!label) return;

    let href = '';
    if (tag === 'A') {
      const raw = (el.getAttribute('href') || '').trim();
      if (!raw || raw === '#' || raw.startsWith('javascript:')) return;
      try {
        href = new URL(raw, baseUrl).pathname;
      } catch {
        href = raw;
      }
    }

    const key = `${label}__${href}`;
    if (seen.has(key)) return;
    seen.add(key);
    out.push({ label, url: href });
  });

  return out.slice(0, 80);
}

async function fetchLiveButtons(nd) {
  if (!nd || !nd.id || !nd.url) return [];
  if (liveButtonsCache.has(nd.id)) return liveButtonsCache.get(nd.id);

  const resp = await fetch(nd.url, { credentials: 'same-origin' });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const html = await resp.text();

  const finalPath = new URL(resp.url, window.location.origin).pathname;
  if (finalPath.startsWith('/users/login')) throw new Error('Login redirect');

  const buttons = extractLiveButtonsFromHTML(html, resp.url);
  liveButtonsCache.set(nd.id, buttons);
  return buttons;
}

async function renderLiveButtons(nd) {
  if (!infoPanelEl) return;
  const mount = infoPanelEl.querySelector('[data-sc-live-buttons]');
  if (!mount) return;

  mount.innerHTML = '<span class="sc-inline-note">Scanning page buttons...</span>';

  try {
    const buttons = await fetchLiveButtons(nd);
    if (!infoPanelEl || infoPanelEl.dataset.nodeId !== nd.id) return;

    if (!buttons.length) {
      mount.innerHTML = '<span class="sc-inline-note">No button controls detected on this page.</span>';
      return;
    }

    mount.innerHTML = buttons.map(btn => {
      const label = escapeHtml(btn.label);
      const url = escapeHtml(btn.url || nd.url);
      return `<a href="${url}" class="sc-btn sc-btn-live" target="_top">${label}</a>`;
    }).join('');
  } catch {
    if (!infoPanelEl || infoPanelEl.dataset.nodeId !== nd.id) return;
    mount.innerHTML = '<span class="sc-inline-note">Could not fetch live buttons for this page.</span>';
  }
}

// ─── Info Panel ───────────────────────────────────────────────────────────────
function showInfoPanel(nd) {
  if (!infoPanelEl) return;
  const col  = getNodeColor(nd);
  const {r,g,b} = hexToRGB(col);
  const cs   = `rgb(${r},${g},${b})`;
  const cm   = CATEGORY_META[nd.category] || { label: nd.category, color: cs };
  const catC = cm.color;

  const btnsHTML = (nd.buttons||[]).map(btn =>
    `<a href="${btn.url}" class="sc-btn" style="--bc:${cs}" target="_top">${btn.label}</a>`
  ).join('');

  const connsHTML = (nd.connections||[]).map(cid => {
    const cn = PROJECT_NODES.find(n => n.id === cid);
    if (!cn) return '';
    const cc = getNodeColor(cn);
    const {r:cr,g:cg,b:cb} = hexToRGB(cc);
    return `<button class="sc-conn-tag" style="border-color:rgb(${cr},${cg},${cb})" onclick="focusNode('${cn.id}')">${cn.name}</button>`;
  }).join('');

  infoPanelEl.innerHTML = `
    <button class="sc-close-btn" onclick="window.hideInfoPanelPublic()">✕</button>
    <div class="sc-panel-cat" style="color:${catC}">${cm.label}</div>
    <div class="sc-panel-title" style="color:${cs}">${nd.name}</div>
    <div class="sc-panel-desc">${nd.description}</div>
    <div class="sc-panel-url">
      <span>URL</span>
      <code><a href="${nd.url}" target="_top" style="color:${cs}">${nd.url}</a></code>
    </div>
    <div class="sc-conns"><div class="sc-conns-label">Configured Buttons</div></div>
    ${btnsHTML ? `<div class="sc-btns">${btnsHTML}</div>` : ''}
    <div class="sc-conns"><div class="sc-conns-label">Live Buttons In This Page</div><div class="sc-btns" data-sc-live-buttons></div></div>
    ${connsHTML ? `<div class="sc-conns"><div class="sc-conns-label">Connected to:</div><div class="sc-conns-list">${connsHTML}</div></div>` : ''}
  `;
  infoPanelEl.dataset.nodeId = nd.id;
  infoPanelEl.style.display = 'block';
  infoPanelEl.style.borderColor = cs;
  infoPanelEl.style.setProperty('--pc', cs);
  renderLiveButtons(nd);
}

function hideInfoPanel() { if (infoPanelEl) infoPanelEl.style.display = 'none'; }

window.hideInfoPanelPublic = function() {
  hideInfoPanel();
  if (selectedObject) { doResetHighlight(selectedObject); selectedObject = null; }
  resetConnectionHighlights();
};

window.focusNode = function(nodeId) {
  const e = nodeMap[nodeId];
  if (!e) return;
  const p = e.pos.clone().normalize();
  orbit.phi   = THREE.MathUtils.radToDeg(Math.acos(Math.max(-1, Math.min(1, p.y))));
  orbit.theta = THREE.MathUtils.radToDeg(Math.atan2(p.z, p.x));
  orbit.targetDistance = 620;
  updateCamera();
  if (selectedObject) doResetHighlight(selectedObject);
  selectedObject = e.core;
  doHighlight(e.core, false, true);
  showInfoPanel(e.nodeData);
};

// ─── Resize ───────────────────────────────────────────────────────────────────
function onWindowResize() {
  const p = renderer.domElement.parentElement;
  if (!p) return;
  camera.aspect = p.offsetWidth / p.offsetHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(p.offsetWidth, p.offsetHeight);
}

// ─── Animation ────────────────────────────────────────────────────────────────
function animate() {
  requestAnimationFrame(animate);
  const dt = clock.getDelta();
  const t  = clock.getElapsedTime();

  // Smooth zoom
  orbit.distance += (orbit.targetDistance - orbit.distance) * 0.06;
  updateCamera();

  // Auto-rotate
  if (autoRotate && !isDragging) globeGroup.rotation.y += 0.0012;

  // Clouds drift
  globeGroup.children.forEach(c => { if (c.userData.isClouds) c.rotation.y += 0.00045; });

  // Nebula drift
  if (particleSystem) particleSystem.rotation.y += 0.00007;

  // Node pulse rings
  Object.values(nodeMap).forEach(({ grp }) => {
    grp.children.forEach(c => {
      if (c.userData.isPulse) {
        c.userData._t += dt * 1.8;
        c.material.opacity = c.userData.base * (0.4 + 0.6 * Math.sin(c.userData._t));
        c.scale.setScalar(1 + 0.14 * Math.sin(c.userData._t * 0.65));
      }
    });
  });

  // Central node pulse
  Object.values(nodeMap).forEach(({ core, nodeData }) => {
    if (nodeData.status === 'central') core.scale.setScalar(1 + 0.07 * Math.sin(t * 2.8));
  });

  // Data-flow particles
  dataFlowParticles.forEach(p => {
    p.userData.t = (p.userData.t + p.userData.speed) % 1;
    p.position.copy(p.userData.curve.getPoint(p.userData.t));
    p.material.opacity = 0.25 + 0.7 * Math.sin(p.userData.t * Math.PI);
  });

  renderer.render(scene, camera);
}

// ─── Bootstrap ────────────────────────────────────────────────────────────────
if (document.readyState === 'complete' || document.readyState === 'interactive') {
  initSystemChain();
} else {
  window.addEventListener('DOMContentLoaded', initSystemChain);
}
