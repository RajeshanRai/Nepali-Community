// System Chain 3D Galaxy Visualization
// Uses Three.js for rendering

let scene, camera, renderer, controls;
let nodes = [], links = [];

function initSystemChain() {
    const container = document.getElementById('systemChain3D');
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(75, container.offsetWidth/container.offsetHeight, 0.1, 2000);
    camera.position.z = 600;

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setClearColor(0x101020);
    renderer.setSize(container.offsetWidth, container.offsetHeight);
    container.appendChild(renderer.domElement);

    // Add glowing galaxy background
    const starsGeometry = new THREE.BufferGeometry();
    const starCount = 2000;
    const positions = [];
    for (let i = 0; i < starCount; i++) {
        positions.push((Math.random()-0.5)*2000, (Math.random()-0.5)*2000, (Math.random()-0.5)*2000);
    }
    starsGeometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    const starsMaterial = new THREE.PointsMaterial({ color: 0x4444ff, size: 2, transparent: true, opacity: 0.5 });
    const starField = new THREE.Points(starsGeometry, starsMaterial);
    scene.add(starField);

    // Central Admin node
    const adminMaterial = new THREE.MeshBasicMaterial({ color: 0x00ffff, emissive: 0x00ffff, wireframe: false });
    const adminGeometry = new THREE.SphereGeometry(40, 32, 32);
    const adminNode = new THREE.Mesh(adminGeometry, adminMaterial);
    adminNode.position.set(0, 0, 0);
    adminNode.name = 'Admin';
    scene.add(adminNode);
    nodes.push(adminNode);

    // Example: Add feature/page nodes (replace with dynamic data)
    const features = [
        { name: 'Dashboard', status: 'green', rel: ['Admin'] },
        { name: 'Settings', status: 'yellow', rel: ['Admin'] },
        { name: 'Projects', status: 'green', rel: ['Admin', 'Dashboard'] },
        { name: 'Volunteers', status: 'red', rel: ['Admin', 'Projects'] },
        { name: 'Donations', status: 'green', rel: ['Admin', 'Projects'] },
        { name: 'FAQs', status: 'yellow', rel: ['Admin', 'Dashboard'] },
        { name: 'Partners', status: 'green', rel: ['Admin', 'Dashboard'] },
        { name: 'Contacts', status: 'green', rel: ['Admin', 'Dashboard'] },
        { name: 'Announcements', status: 'green', rel: ['Admin', 'Dashboard'] },
    ];
    const nodeMaterials = {
        green: new THREE.MeshBasicMaterial({ color: 0x00ff00, emissive: 0x00ff00 }),
        red: new THREE.MeshBasicMaterial({ color: 0xff2222, emissive: 0xff2222 }),
        yellow: new THREE.MeshBasicMaterial({ color: 0xffff00, emissive: 0xffff00 }),
    };
    const radius = 250;
    features.forEach((f, i) => {
        const angle = (i / features.length) * Math.PI * 2;
        const x = Math.cos(angle) * radius;
        const y = Math.sin(angle) * radius;
        const z = Math.sin(angle * 2) * radius * 0.5;
        const mat = nodeMaterials[f.status] || nodeMaterials.green;
        const node = new THREE.Mesh(new THREE.SphereGeometry(22, 24, 24), mat);
        node.position.set(x, y, z);
        node.name = f.name;
        scene.add(node);
        nodes.push(node);
        // Add label
        const canvas = document.createElement('canvas');
        canvas.width = 128; canvas.height = 32;
        const ctx = canvas.getContext('2d');
        ctx.font = 'bold 18px Arial';
        ctx.fillStyle = '#fff';
        ctx.textAlign = 'center';
        ctx.fillText(f.name, 64, 24);
        const texture = new THREE.CanvasTexture(canvas);
        const labelMat = new THREE.SpriteMaterial({ map: texture });
        const label = new THREE.Sprite(labelMat);
        label.position.set(x, y+30, z);
        label.scale.set(64, 16, 1);
        scene.add(label);
    });

    // Draw links
    features.forEach((f, i) => {
        const node = nodes[i+1]; // admin is nodes[0]
        f.rel.forEach(relName => {
            const target = nodes.find(n => n.name === relName);
            if (target) {
                const points = [node.position, target.position];
                const linkGeom = new THREE.BufferGeometry().setFromPoints(points);
                const color = (f.status === 'red') ? 0xff2222 : 0x00ffff;
                const linkMat = new THREE.LineBasicMaterial({ color, linewidth: 3 });
                const link = new THREE.Line(linkGeom, linkMat);
                scene.add(link);
                links.push(link);
            }
        });
    });

    // Orbit controls (drag/rotate/zoom)
    // If OrbitControls not available, fallback to basic mouse events
    // For full interactivity, include OrbitControls.js from Three.js examples

    animate();
}

function animate() {
    requestAnimationFrame(animate);
    // Pulsate admin node
    nodes[0].scale.setScalar(1 + 0.08 * Math.sin(Date.now()/300));
    renderer.render(scene, camera);
}

window.addEventListener('DOMContentLoaded', initSystemChain);

// TODO: Add raycaster for hover/click, show info panel, filter/search, real-time updates, access control
