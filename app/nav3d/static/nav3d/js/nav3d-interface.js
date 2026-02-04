// The 3D Navigation Portal for KPK-App

// Import Three.js from the main module file only
import * as THREE from './modules/three.module.js';
// Import GLTFLoader with explicit path (not using the import map for this one)
import { GLTFLoader } from './modules/GLTFLoader.js';
// Import our fixed renderer helper that avoids circular dependencies
import { createRenderer } from './modules/fixed-renderer.js';

// Shared loaders and resource management helpers
const textureLoader = new THREE.TextureLoader();
textureLoader.crossOrigin = 'anonymous';

const loadingManager = new THREE.LoadingManager();
loadingManager.onError = function(url) {
    return textureLoader.load('https://cdn.jsdelivr.net/gh/mrdoob/three.js@r152/examples/textures/crate.gif');
};

textureLoader.manager = loadingManager;
const persistentTextureCache = new Map();
const persistentTextures = new Set();
const FLOOR_TEXTURE_URL = '/static/nav3d/models/floor_grate_1.jpg';
const BRICK_TEXTURE_URL = 'https://cdn.jsdelivr.net/gh/mrdoob/three.js@r152/examples/textures/brick_diffuse.jpg';
const SPRITE_TEXTURE_URL = 'https://cdn.jsdelivr.net/gh/mrdoob/three.js@r152/examples/textures/sprites/circle.png';
const TERMINAL_CURSOR_CSS = `
#terminal-interface,
#terminal-interface * {
    cursor: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' style='fill:none;stroke:%2366ffaa;stroke-width:2px;'><circle cx='8' cy='8' r='6'/><circle cx='8' cy='8' r='2' style='fill:%2366ffaa'/></svg>") 8 8, auto !important;
}

#terminal-interface input,
#terminal-interface textarea,
#terminal-interface [contenteditable],
#terminal-interface iframe {
    cursor: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' style='fill:none;stroke:%2366ffaa;stroke-width:2px;'><path d='M4,12 L8,4 L12,12 L8,10 Z' style='fill:%2366ffaa'/></svg>") 8 8, text !important;
}

#terminal-interface button,
#terminal-interface a,
#terminal-interface [role='button'],
#terminal-interface .clickable {
    cursor: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' style='fill:none;stroke:%2366ffaa;stroke-width:2px;'><path d='M5,5 L20,20 M20,5 L5,20' stroke-linecap='round'/></svg>") 12 12, pointer !important;
}
`;

const CHARACTER_BASE_HEIGHT = 0.9;
const CHARACTER_HEIGHT = 1.8;
const CHARACTER_RADIUS = 0.45;
const GRAVITY = 28;
const JUMP_SPEED = 9.5;
const COYOTE_TIME = 0.12;
const JUMP_BUFFER_TIME = 0.15;
const PORTAL_ENTRY_OFFSET = CHARACTER_RADIUS * 1.1; // ~0.5 units forward (~11% of prior bump)
const DEFAULT_ENTRY_POSITION = new THREE.Vector3(0, CHARACTER_BASE_HEIGHT, -PORTAL_ENTRY_OFFSET);
const ROOM_ENTRY_DEPTH_RATIO = 1 / 3;
const MIN_ROOM_ENTRY_DISTANCE = CHARACTER_RADIUS * 2;
const DEFAULT_GROUND_HEIGHT = 0;
const GROUND_SNAP_EPSILON = 0.02;
const PLATFORM_EDGE_EPSILON = 0.02;
const PLATFORM_SURFACE_TOLERANCE = 0.08;

let currentRoomEntryPosition = DEFAULT_ENTRY_POSITION.clone();
let pendingEntryRotation = null;
let pendingApplyRoomEntry = false;

function computeDepthEntryPosition(depth, options = {}) {
    if (depth == null) {
        return DEFAULT_ENTRY_POSITION.clone();
    }

    const ratio = options.ratio ?? ROOM_ENTRY_DEPTH_RATIO;
    const minDistance = options.minDistance ?? MIN_ROOM_ENTRY_DISTANCE;
    const offsetZ = options.offsetZ ?? 0;
    const entryZ = options.absoluteZ !== undefined
        ? options.absoluteZ
        : -Math.max(depth * ratio, minDistance) + offsetZ;

    const x = options.x ?? 0;
    return new THREE.Vector3(x, CHARACTER_BASE_HEIGHT, entryZ);
}

function setCurrentRoomEntryPosition(position, options = {}) {
    if (!position) {
        return;
    }
    currentRoomEntryPosition = position.clone();
    currentRoomEntryPosition.y = CHARACTER_BASE_HEIGHT;

    if (options.immediate) {
        applyRoomEntryPosition(true);
    } else if (pendingApplyRoomEntry) {
        applyRoomEntryPosition();
    }
}

function applyRoomEntryPosition(force = false) {
    if (!character) {
        pendingApplyRoomEntry = true;
        return;
    }
    if (!force && !pendingApplyRoomEntry) {
        return;
    }

    const spawn = currentRoomEntryPosition ? currentRoomEntryPosition.clone() : DEFAULT_ENTRY_POSITION.clone();
    character.position.copy(spawn);
    resetJumpState();

    if (pendingEntryRotation !== null) {
        character.rotation.y = pendingEntryRotation;
        currentRotation = pendingEntryRotation;
        targetRotation = pendingEntryRotation;
    }

    if (camera) {
        camera.position.set(character.position.x, character.position.y + 2.5, character.position.z + 5);
        camera.lookAt(character.position);
    }

    pendingApplyRoomEntry = false;
    pendingEntryRotation = null;
}

function computeEntryFacingRotation(portalTransform, forwardHint) {
    let forward = null;

    if (forwardHint && forwardHint.lengthSq() > 0.0001) {
        forward = forwardHint.clone().normalize();
    } else if (portalTransform && portalTransform.quaternion) {
        forward = new THREE.Vector3(0, 0, 1);
        forward.applyQuaternion(portalTransform.quaternion);
        forward.normalize();
    }

    if (!forward) {
        return 0;
    }

    return Math.atan2(forward.x, forward.z);
}

function loadPersistentTexture(url, setupFn) {
    if (!persistentTextureCache.has(url)) {
        const texture = textureLoader.load(url, () => {
            if (setupFn) {
                setupFn(texture);
            }
        });
        if (setupFn) {
            setupFn(texture);
        }
        persistentTextureCache.set(url, texture);
        persistentTextures.add(texture);
    }
    return persistentTextureCache.get(url);
}

function configureGlowTexture(texture) {
    texture.minFilter = THREE.LinearFilter;
    texture.magFilter = THREE.LinearFilter;
    texture.generateMipmaps = false;
    texture.anisotropy = 1;
    texture.wrapS = THREE.ClampToEdgeWrapping;
    texture.wrapT = THREE.ClampToEdgeWrapping;
    texture.needsUpdate = true;
}

function configurePortalTexture(texture) {
    texture.minFilter = THREE.LinearFilter;
    texture.magFilter = THREE.LinearFilter;
    texture.generateMipmaps = false;
    texture.anisotropy = 1;
    texture.wrapS = THREE.ClampToEdgeWrapping;
    texture.wrapT = THREE.ClampToEdgeWrapping;
    texture.center.set(0.5, 0.5);
    texture.needsUpdate = true;
}

function createPortalVortexTextures(label, color) {
    const size = 512;
    const vortexCanvas = document.createElement('canvas');
    vortexCanvas.width = size;
    vortexCanvas.height = size;
    const vctx = vortexCanvas.getContext('2d');

    const colorObj = new THREE.Color(color);
    const baseR = Math.floor(colorObj.r * 255);
    const baseG = Math.floor(colorObj.g * 255);
    const baseB = Math.floor(colorObj.b * 255);

    vctx.clearRect(0, 0, size, size);
    const gradient = vctx.createRadialGradient(
        size / 2,
        size / 2,
        size * 0.05,
        size / 2,
        size / 2,
        size * 0.5
    );
    gradient.addColorStop(0, `rgba(${baseR}, ${baseG}, ${baseB}, 0.95)`);
    gradient.addColorStop(0.4, `rgba(${baseR}, ${baseG}, ${baseB}, 0.45)`);
    gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
    vctx.fillStyle = gradient;
    vctx.fillRect(0, 0, size, size);

    vctx.save();
    vctx.translate(size / 2, size / 2);
    vctx.globalCompositeOperation = 'lighter';
    vctx.strokeStyle = `rgba(${baseR}, ${baseG}, ${baseB}, 0.35)`;
    vctx.lineWidth = 2;

    for (let spiral = 0; spiral < 4; spiral += 1) {
        vctx.beginPath();
        const turns = 3 + spiral * 0.5;
        const maxRadius = size * 0.45;
        for (let t = 0; t <= 1; t += 0.01) {
            const angle = t * Math.PI * 2 * turns + spiral;
            const radius = t * maxRadius;
            const x = Math.cos(angle) * radius;
            const y = Math.sin(angle) * radius;
            if (t === 0) {
                vctx.moveTo(x, y);
            } else {
                vctx.lineTo(x, y);
            }
        }
        vctx.stroke();
    }
    vctx.restore();

    vctx.globalCompositeOperation = 'source-over';
    for (let i = 0; i < 200; i += 1) {
        const angle = Math.random() * Math.PI * 2;
        const radius = Math.random() * size * 0.45;
        const x = size / 2 + Math.cos(angle) * radius;
        const y = size / 2 + Math.sin(angle) * radius;
        vctx.fillStyle = `rgba(${baseR}, ${baseG}, ${baseB}, ${0.08 + Math.random() * 0.12})`;
        vctx.beginPath();
        vctx.arc(x, y, 1 + Math.random() * 2, 0, Math.PI * 2);
        vctx.fill();
    }

    const rimCanvas = document.createElement('canvas');
    rimCanvas.width = size;
    rimCanvas.height = size;
    const rctx = rimCanvas.getContext('2d');
    rctx.clearRect(0, 0, size, size);
    rctx.save();
    rctx.translate(size / 2, size / 2);

    const ringRadius = size * 0.42;
    rctx.strokeStyle = `rgba(${baseR}, ${baseG}, ${baseB}, 0.65)`;
    rctx.lineWidth = 6;
    rctx.beginPath();
    rctx.arc(0, 0, ringRadius, 0, Math.PI * 2);
    rctx.stroke();

    const text = label.toUpperCase();
    const fontSize = Math.max(22, Math.min(48, Math.floor(420 / Math.max(6, text.length))));
    rctx.font = `${fontSize}px "Old English Text MT", "Old English", "Blackletter", "UnifrakturCook", "Times New Roman", serif`;
    rctx.fillStyle = `rgba(${baseR}, ${baseG}, ${baseB}, 0.9)`;
    rctx.textAlign = 'center';
    rctx.textBaseline = 'middle';
    rctx.shadowColor = `rgba(${baseR}, ${baseG}, ${baseB}, 0.6)`;
    rctx.shadowBlur = 8;

    const totalAngle = Math.PI * 1.8;
    const angleStep = totalAngle / Math.max(1, text.length);
    let angle = -totalAngle / 2 - Math.PI / 2;
    for (const char of text) {
        rctx.save();
        rctx.rotate(angle);
        rctx.translate(0, -ringRadius);
        rctx.rotate(Math.PI / 2);
        rctx.fillText(char, 0, 0);
        rctx.restore();
        angle += angleStep;
    }
    rctx.restore();

    const vortexTexture = new THREE.CanvasTexture(vortexCanvas);
    configurePortalTexture(vortexTexture);

    const rimTexture = new THREE.CanvasTexture(rimCanvas);
    configurePortalTexture(rimTexture);

    return { vortexTexture, rimTexture };
}

const disposableTextureProps = [
    'map',
    'alphaMap',
    'aoMap',
    'bumpMap',
    'displacementMap',
    'emissiveMap',
    'envMap',
    'lightMap',
    'metalnessMap',
    'normalMap',
    'roughnessMap',
    'specularMap'
];

function disposeMaterialInstance(material) {
    if (!material) {
        return;
    }

    disposableTextureProps.forEach(prop => {
        if (material[prop] && !persistentTextures.has(material[prop])) {
            material[prop].dispose();
        }
    });

    if (material.dispose) {
        material.dispose();
    }
}

function disposeMaterial(material) {
    if (Array.isArray(material)) {
        material.forEach(disposeMaterialInstance);
    } else {
        disposeMaterialInstance(material);
    }
}

function disposeObject3D(object) {
    if (!object) {
        return;
    }

    if (object.geometry && object.geometry.dispose) {
        object.geometry.dispose();
    }

    if (object.material) {
        disposeMaterial(object.material);
    }

    if (object.texture && !persistentTextures.has(object.texture) && object.texture.dispose) {
        object.texture.dispose();
    }
}

function disposeSceneResources(root, preserve = new Set()) {
    if (!root) {
        return;
    }

    const objectsToDispose = [];
    root.traverse(child => {
        if (preserve.has(child)) {
            return;
        }
        if (child.isMesh || child.isPoints || child.isLine || child.isSprite) {
            objectsToDispose.push(child);
        }
    });

    objectsToDispose.forEach(obj => {
        disposeObject3D(obj);
        if (obj.parent) {
            obj.parent.remove(obj);
        }
    });
}

function openTerminalInterface() {
    if (!terminalInterface) {
        return;
    }

    if (!terminalCursorStylesElement) {
        terminalCursorStylesElement = document.createElement('style');
        terminalCursorStylesElement.id = 'terminal-cursor-styles';
        terminalCursorStylesElement.textContent = TERMINAL_CURSOR_CSS;
        document.head.appendChild(terminalCursorStylesElement);
    }

    terminalInterface.style.display = 'block';
    if (terminalScreenMesh) {
        terminalScreenMesh.userData.terminalActive = true;
    }
    if (terminalPrompt) {
        terminalPrompt.style.display = 'none';
    }
}

function closeTerminalInterface() {
    if (!terminalInterface) {
        return;
    }
    terminalInterface.style.display = 'none';
    document.exitPointerLock();
    if (terminalScreenMesh) {
        terminalScreenMesh.userData.terminalActive = false;
    }
    if (terminalPrompt) {
        terminalPrompt.style.display = 'none';
    }
    if (terminalCursorStylesElement && terminalCursorStylesElement.parentNode) {
        terminalCursorStylesElement.parentNode.removeChild(terminalCursorStylesElement);
    }
    terminalCursorStylesElement = null;
}

function handleTerminalInteractionKey(event) {
    if (!terminalInterface) {
        return;
    }
    
    if (event.code === 'KeyE') {
        if (!terminalScreenMesh || currentRoom !== 'room_terminal') {
            return;
        }
        const screenDistance = character ? character.position.distanceTo(terminalScreenMesh.position) : Infinity;
        if (screenDistance < 3) {
            openTerminalInterface();
        }
    } else if (event.code === 'Escape') {
        if (terminalInterface.style.display === 'block') {
            closeTerminalInterface();
        }
    }
}


// Portal Transition class for handling room transitions
class PortalTransition {
    constructor() {
        this.transitionElement = null;
        this.navbarElement = null;
        this.vignetteElement = null;
        this.isTransitioning = false;
        this.init();
    }

    init() {
        // Create expanding rectangle transition overlay
        this.transitionElement = document.createElement('div');
        this.transitionElement.className = 'portal-transition';
        this.transitionElement.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: white;
            opacity: 0;
            transform: scale(0);
            transform-origin: center;
            transition: all 0.8s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 9999;
            pointer-events: none;
        `;

        // Create navbar overlay
        this.navbarElement = document.createElement('div');
        this.navbarElement.className = 'portal-navbar';
        this.navbarElement.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 4.25%;
            background: rgb(13, 110, 253);
            opacity: 0;
            transform: translateY(-100%);
            transition: all 0.8s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 10000;
            pointer-events: none;
        `;

        // Create vignette transition overlay
        this.vignetteElement = document.createElement('div');
        this.vignetteElement.className = 'portal-vignette';
        this.vignetteElement.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: radial-gradient(circle at center, transparent 0%, black 100%);
            opacity: 0;
            transition: all 0.8s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 9999;
            pointer-events: none;
        `;

        // Add elements to DOM
        document.body.appendChild(this.transitionElement);
        document.body.appendChild(this.navbarElement);
        document.body.appendChild(this.vignetteElement);
    }

    startTransition(type = 'rectangle') {
        if (this.isTransitioning) return;
        this.isTransitioning = true;

        // Disable user input
        document.body.style.pointerEvents = 'none';

        // Start animations based on transition type
        requestAnimationFrame(() => {
            if (type === 'rectangle') {
                // Blue door transition - expanding rectangle
                this.transitionElement.style.opacity = '1';
                this.transitionElement.style.transform = 'scale(1)';
                this.navbarElement.style.opacity = '1';
                this.navbarElement.style.transform = 'translateY(0)';
                this.vignetteElement.style.opacity = '0';
            } else if (type === 'vignette') {
                // Yellow door transition - vignette fade
                this.vignetteElement.style.opacity = '1';
                this.transitionElement.style.opacity = '0';
                this.transitionElement.style.transform = 'scale(0)';
                this.navbarElement.style.opacity = '0';
                this.navbarElement.style.transform = 'translateY(-100%)';
            }
        });
    }

    endTransition(type = 'rectangle') {
        if (!this.isTransitioning) return;

        // Reset styles based on transition type
        if (type === 'rectangle') {
            this.transitionElement.style.opacity = '0';
            this.transitionElement.style.transform = 'scale(0)';
            this.navbarElement.style.opacity = '0';
            this.navbarElement.style.transform = 'translateY(-100%)';
        } else if (type === 'vignette') {
            this.vignetteElement.style.opacity = '0';
        }

        // Re-enable user input after animation
        setTimeout(() => {
            document.body.style.pointerEvents = '';
            this.isTransitioning = false;
        }, 800);
    }
}

// Create portal transition instance
const portalTransition = new PortalTransition();

// Global variables for Three.js components we need
let scene, camera, renderer, clock, mixer;
let character, controls;
let colliders = [];
let navLinks = [];
let raycaster;
let mouse;
// Enhanced mobile detection for tablets
let isMobile = window.matchMedia("(max-width: 1024px)").matches || (('ontouchstart' in window) || (navigator.maxTouchPoints > 0) || (navigator.msMaxTouchPoints > 0));
let font = null; // For text rendering

// Character movement variables
let moveForward = false;
let moveBackward = false;
let moveLeft = false;
let moveRight = false;
let canJump = false;
let isSprinting = false; // Track sprinting state
let velocity;
let direction;
let joystickDelta;
let joystickActive = false;

// Movement speed configuration
const SPEED_NORMAL = 5.0;
const SPEED_SPRINT = 11.0;

// Navigation state variables
let currentRoom = 'main'; // The current room the player is in
let previousRoom = null; // The previous room, for back navigation
let roomTransitionInProgress = false; // Flag to prevent multiple transitions
let roomData = {}; // Store data about rooms and their portals
let transitionTarget = null; // Target room for transition

// Debug overlay state for identifying lights/emitters
let debugOverlayEnabled = false;
let debugOverlayDirty = true;
let debugOverlayRoot = null;
let debugOverlayList = null;
let debugOverlayInfo = null;
let debugOverlayItems = [];
let debugSelectedObject = null;
let debugSelectionHelper = null;
let debugSelectionMaterial = null;
let debugSelectionTexture = null;
let debugSelectionOriginalMaterial = new Map();
const DEBUG_OVERLAY_HOTKEY = 'F9';

// DOM elements
const loadingScreen = document.getElementById('loading-screen');
const sceneContainer = document.getElementById('scene-container');
const tooltip = document.getElementById('tooltip');
let joystick; // Will be created dynamically
let joystickKnob; // Will be created dynamically
let terminalInterface = null;
let terminalPrompt = null;
let terminalCursorStylesElement = null;
let terminalScreenMesh = null;
let terminalKeyListenerAttached = false;
let jumpButton = null;
let isGrounded = false;
let coyoteTimer = 0;
let jumpBufferTimer = 0;

// User permissions based on groups (will be populated from Django)
let userGroups = [];

// Create global variables for post-processing
let composer;

if (!terminalKeyListenerAttached) {
    document.addEventListener('keydown', handleTerminalInteractionKey, false);
    terminalKeyListenerAttached = true;
}

const tempColliderBox = new THREE.Box3();
const expandedColliderBox = new THREE.Box3();
const tempGroundBox = new THREE.Box3();

function registerCollider(object, options = {}) {
    if (!object) {
        return;
    }
    object.userData.ignoreCollision = !!options.ignoreCollision;
    object.userData.isFloor = !!options.isFloor;
    object.userData.isPlatform = !!options.isPlatform;
    
    if (object.geometry && !object.userData._baseBoundingBox) {
        object.geometry.computeBoundingBox();
        if (object.geometry.boundingBox) {
            object.userData._baseBoundingBox = object.geometry.boundingBox.clone();
        }
    }
    
    if (!colliders.includes(object)) {
        colliders.push(object);
    }
}

function getColliderBoundingBox(collider, targetBox) {
    if (!collider) {
        return null;
    }
    const box = targetBox || new THREE.Box3();
    collider.updateMatrixWorld(true);
    
    if (collider.userData._baseBoundingBox) {
        box.copy(collider.userData._baseBoundingBox);
        box.applyMatrix4(collider.matrixWorld);
    } else {
        box.setFromObject(collider);
    }
    return box;
}

function wouldCollide(testX, testZ) {
    if (!colliders.length) {
        return false;
    }
    const currentCharacterY = character ? character.position.y : CHARACTER_BASE_HEIGHT;
    const characterBottom = currentCharacterY - CHARACTER_BASE_HEIGHT;
    const characterTop = characterBottom + CHARACTER_HEIGHT;
    
    for (const collider of colliders) {
        if (!collider || collider.userData.ignoreCollision || collider.visible === false) {
            continue;
        }
        
        const colliderBox = getColliderBoundingBox(collider, tempColliderBox);
        if (!colliderBox) {
            continue;
        }
        
        if (colliderBox.max.y < characterBottom || colliderBox.min.y > characterTop) {
            continue;
        }

        if (
            collider.userData.isPlatform &&
            characterBottom >= colliderBox.max.y - PLATFORM_SURFACE_TOLERANCE &&
            characterBottom <= colliderBox.max.y + PLATFORM_SURFACE_TOLERANCE
        ) {
            // Already standing on or above this platform; let horizontal movement continue
            continue;
        }
        
        expandedColliderBox.copy(colliderBox);
        expandedColliderBox.min.x -= CHARACTER_RADIUS;
        expandedColliderBox.max.x += CHARACTER_RADIUS;
        expandedColliderBox.min.z -= CHARACTER_RADIUS;
        expandedColliderBox.max.z += CHARACTER_RADIUS;
        
        if (
            testX >= expandedColliderBox.min.x && testX <= expandedColliderBox.max.x &&
            testZ >= expandedColliderBox.min.z && testZ <= expandedColliderBox.max.z
        ) {
            return true;
        }
    }
    
    return false;
}

function getGroundHeightAt(x, z) {
    let highestSurface = DEFAULT_GROUND_HEIGHT;
    if (!colliders.length) {
        return highestSurface;
    }
    
    for (const collider of colliders) {
        if (
            !collider ||
            (collider.userData.isFloor !== true && collider.userData.isPlatform !== true)
        ) {
            continue;
        }
        const colliderBox = getColliderBoundingBox(collider, tempGroundBox);
        if (!colliderBox) {
            continue;
        }
        const minX = colliderBox.min.x - PLATFORM_EDGE_EPSILON;
        const maxX = colliderBox.max.x + PLATFORM_EDGE_EPSILON;
        const minZ = colliderBox.min.z - PLATFORM_EDGE_EPSILON;
        const maxZ = colliderBox.max.z + PLATFORM_EDGE_EPSILON;
        if (x >= minX && x <= maxX && z >= minZ && z <= maxZ) {
            if (colliderBox.max.y > highestSurface) {
                highestSurface = colliderBox.max.y;
            }
        }
    }
    return highestSurface;
}

function queueJump() {
    jumpBufferTimer = JUMP_BUFFER_TIME;
}

function resetJumpState() {
    if (velocity) {
        velocity.y = 0;
    }
    isGrounded = true;
    canJump = true;
    coyoteTimer = COYOTE_TIME;
    jumpBufferTimer = 0;
    if (character) {
        character.position.y = CHARACTER_BASE_HEIGHT;
    }
}

document.addEventListener("DOMContentLoaded", function() {
    // Perform mobile detection again to ensure it works in all browsers
    isMobile = window.matchMedia("(max-width: 1024px)").matches || 
        (('ontouchstart' in window) || (navigator.maxTouchPoints > 0) || (navigator.msMaxTouchPoints > 0));
    
    // Initialize navigation if the sceneContainer exists
    if (sceneContainer) {
        // Initialize directly - no need to pass THREE as it's imported at the top
        initThreeJS();
    }
});

// Initialize the Three.js environment - renamed for clarity
function initThreeJS() {
    // Create raycaster and mouse objects
    raycaster = new THREE.Raycaster();
    mouse = new THREE.Vector2();
    velocity = new THREE.Vector3();
    direction = new THREE.Vector3();
    joystickDelta = new THREE.Vector2();
    
    // Create scene
    init();
}

// Store the original scene for restoration purposes
let originalScene = null;

// Create and configure the scene - removed THREE parameter since it's imported globally
function init() {
    // Create scene
    scene = new THREE.Scene();
    originalScene = scene; // Store the original scene reference
    scene.background = new THREE.Color(0x000000); // Dark background for industrial feel
    
    // Create atmospheric fog effect - reduced density for better visibility
    scene.fog = new THREE.FogExp2(0x0a2933, 0.025); // Reduced from 0.035 to 0.025
    
    // Create clock for animations
    clock = new THREE.Clock();
    
    // Create camera
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(0, 1.6, 5); // Eye level for character
    
    // Create renderer using our fixed helper function
    renderer = createRenderer({ 
        antialias: true,
        powerPreference: "high-performance"
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    sceneContainer.appendChild(renderer.domElement);
    
    // Setup scene lighting and atmosphere
    setupMainSceneLighting();
    
    // Create industrial flooring with grating texture
    console.log("🔍 [FLOOR_DEBUG] init() - Creating main floor");
    const floorTexture = loadPersistentTexture(FLOOR_TEXTURE_URL, texture => {
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.RepeatWrapping;
        texture.minFilter = THREE.NearestFilter;
        texture.magFilter = THREE.NearestFilter;
    });
    
    // IMPORTANT: Calculate proper repetition to maintain original texture resolution
    // Each grate tile should be 2x2 units in the 3D world
    const tileSize = 2;
    const groundSize = 240; // Dramatically increased from 120 for extreme depth
    
    floorTexture.repeat.set(groundSize/tileSize, groundSize/tileSize);
    
    const groundGeometry = new THREE.PlaneGeometry(groundSize, groundSize);
    const groundMaterial = new THREE.MeshStandardMaterial({ 
        map: floorTexture,
        roughness: 0.7,
        metalness: 0.8,
        color: 0x888888 // Lighter gray to preserve texture details
    });
    const ground = new THREE.Mesh(groundGeometry, groundMaterial);
    ground.rotation.x = -Math.PI / 2;
    ground.position.set(0, 0, -60); // Position it further back to eliminate void
    ground.receiveShadow = true;
    ground.name = 'mainGround'; // Give it a name to find it later
    scene.add(ground);
    registerCollider(ground, { ignoreCollision: true, isFloor: true });
    console.log("🔍 [FLOOR_DEBUG] init() - Main floor created and added to scene:", {
        name: ground.name,
        size: groundSize,
        position: ground.position,
        isInScene: scene.children.includes(ground)
    });
    
    // Create a character container
    character = new THREE.Group();
    character.castShadow = true;
    scene.add(character);
    resetJumpState();
    character.position.copy(currentRoomEntryPosition);
    
    // Create a loading indicator
    const loadingEl = document.createElement('div');
    loadingEl.style.position = 'fixed';
    loadingEl.style.top = '50%';
    loadingEl.style.left = '50%';
    loadingEl.style.transform = 'translate(-50%, -50%)';
    loadingEl.style.color = '#66ffaa';
    loadingEl.style.fontFamily = 'monospace';
    loadingEl.style.fontSize = '18px';
    loadingEl.style.zIndex = '1000';
    sceneContainer.appendChild(loadingEl);
    
    // Function to create fallback cube character
    function createFallbackCube() {
        console.warn("Using fallback cube character - beer can summoning failed!");
        loadingEl.remove();
        const characterGeometry = new THREE.BoxGeometry(0.5, 1.8, 0.5);
        const characterMaterial = new THREE.MeshStandardMaterial({ color: 0xff0000 });
        const cubeMesh = new THREE.Mesh(characterGeometry, characterMaterial);
        cubeMesh.castShadow = true;
        character.add(cubeMesh);
    }
    
    // Function to load the beer can model
    function loadBeerCan() {
        console.log("Using imported GLTFLoader to load beer can model");
        const loader = new GLTFLoader();
        loader.load('/static/nav3d/models/BeerCan.glb', 
            handleSuccessfulLoad,
            (xhr) => {
                console.log((xhr.loaded / xhr.total * 100) + '% loaded');
            },
            handleLoadError
        );
    }
    
    // Start the loading process
    loadBeerCan();
    
    // Position camera slightly behind character
    camera.position.set(0, 2.5, 5);
    
    // Create controls
    setupControls();
    
    // Add event listeners
    window.addEventListener('resize', onWindowResize, false);
    window.addEventListener('mousemove', onMouseMove, false);
    window.addEventListener('click', onMouseClick, false);
    
    // Setup joystick/buttons for touch capable devices (mobile + hybrid)
    if (deviceSupportsTouchControls()) {
        setupJoystick();
        setupSprintButton();
        setupJumpButton();
    }
    
    // Setup simple renderer for now (no post-processing)
    composer = null;
    
    // FIRST fetch user permissions, THEN create portals
    fetchUserPermissions();
    
    // Start animation loop
    animate();
    
    // Remove loading screen
    setTimeout(() => {
        loadingScreen.classList.add('fade-out');
        setTimeout(() => {
            loadingScreen.style.display = 'none';
        }, 1000);
    }, 1500);
}

// EXTRACTED LIGHTING SETUP: Central function to set up main scene lighting
function setupMainSceneLighting() {
    // Safety check for scene object - restore from original if needed
    if (!scene || typeof scene.traverse !== 'function') {
        console.warn('Scene object is unavailable during setupMainSceneLighting, restoring from original');
        if (originalScene) {
            scene = originalScene;
        } else {
            console.error('Cannot restore scene - no original reference available');
            return; // Exit if we can't fix it
        }
    }
    
    // Remove existing lights before adding new ones (safer than traverse)
    const lightsToRemove = [];
    scene.children.forEach(child => {
        if (child.isLight && child.parent !== character && !isChildOfCharacter(child)) {
            lightsToRemove.push(child);
        }
    });
    
    // Remove the lights in a separate step to avoid modifying the array during iteration
    lightsToRemove.forEach(light => {
        scene.remove(light);
    });
    
    // Enhanced Lighting for industrial Mako feel
    // Ambient light increased for better overall illumination
    const ambientLight = new THREE.AmbientLight(0x3a4a6a, 0.6); // Blueish color, 0.6 intensity
    scene.add(ambientLight);
    
    // Main directional light with bluish tint
    const directionalLight = new THREE.DirectionalLight(0x6680cc, 0.7); // Vibrant blue, 0.7 intensity
    directionalLight.position.set(10, 10, 10);
    directionalLight.castShadow = true;
    directionalLight.shadow.mapSize.width = 2048;
    directionalLight.shadow.mapSize.height = 2048;
    scene.add(directionalLight);
    
    // Add enhanced atmospheric reactor lights for the main scene
    addReactorLights();
    
    // Helper function to check if an object is a child of the character (duplicated here for safety)
    function isChildOfCharacter(object) {
        if (!character) return false;
        let parent = object.parent;
        while (parent) {
            if (parent === character) return true;
            parent = parent.parent;
        }
        return false;
    }
}

// Setup character controls
function setupControls() {
    document.addEventListener('keydown', onKeyDown, false);
    document.addEventListener('keyup', onKeyUp, false);
    document.addEventListener('keydown', onDebugKeyDown, false);
    document.addEventListener('pointerdown', onDebugPointerDown, true);
}

function onDebugKeyDown(event) {
    if (event.code !== DEBUG_OVERLAY_HOTKEY) {
        return;
    }
    if (isTypingTarget(event.target)) {
        return;
    }
    toggleDebugOverlay();
}

function isTypingTarget(target) {
    if (!target) {
        return false;
    }
    const tagName = target.tagName ? target.tagName.toUpperCase() : '';
    return target.isContentEditable || tagName === 'INPUT' || tagName === 'TEXTAREA' || tagName === 'SELECT';
}

// Handle keyboard input (keydown)
function onKeyDown(event) {
    switch (event.code) {
        case 'ArrowUp':
        case 'KeyW':
            moveForward = true;
            break;
            
        case 'ArrowDown':
        case 'KeyS':
            moveBackward = true;
            break;
            
        case 'ArrowLeft':
        case 'KeyA':
            moveLeft = true;
            break;
            
        case 'ArrowRight':
        case 'KeyD':
            moveRight = true;
            break;
            
        case 'Space':
            queueJump();
            break;
            
        case 'ShiftLeft':
        case 'ShiftRight':
            isSprinting = true;
            break;
    }
}

// Handle keyboard input (keyup)
function onKeyUp(event) {
    switch (event.code) {
        case 'KeyW':
        case 'ArrowUp':
            moveForward = false;
            break;
        case 'KeyS':
        case 'ArrowDown':
            moveBackward = false;
            break;
        case 'KeyA':
        case 'ArrowLeft':
            moveLeft = false;
            // Immediately stop rotation when left key is released
            if (!moveRight) {
                targetRotation = currentRotation;
            }
            break;
        case 'KeyD':
        case 'ArrowRight':
            moveRight = false;
            // Immediately stop rotation when right key is released
            if (!moveLeft) {
                targetRotation = currentRotation;
            }
            break;
        case 'ShiftLeft':
        case 'ShiftRight':
            isSprinting = false;
            break;
    }
}

function toggleDebugOverlay() {
    debugOverlayEnabled = !debugOverlayEnabled;
    if (!debugOverlayEnabled) {
        removeDebugOverlay();
        return;
    }
    ensureDebugOverlayRoot();
    debugOverlayDirty = true;
    refreshDebugOverlayTargets();
}

function markDebugOverlayDirty() {
    if (!debugOverlayEnabled) {
        return;
    }
    debugOverlayDirty = true;
}

function ensureDebugOverlayRoot() {
    if (debugOverlayRoot) {
        return;
    }
    debugOverlayRoot = document.createElement('div');
    debugOverlayRoot.id = 'nav3d-debug-overlay';
    debugOverlayRoot.style.position = 'absolute';
    debugOverlayRoot.style.top = '0';
    debugOverlayRoot.style.left = '0';
    debugOverlayRoot.style.width = '100%';
    debugOverlayRoot.style.height = '100%';
    debugOverlayRoot.style.pointerEvents = 'none';
    debugOverlayRoot.style.zIndex = '20';

    debugOverlayList = document.createElement('div');
    debugOverlayList.style.position = 'absolute';
    debugOverlayList.style.top = '10px';
    debugOverlayList.style.left = '10px';
    debugOverlayList.style.maxHeight = '45%';
    debugOverlayList.style.overflow = 'auto';
    debugOverlayList.style.background = 'rgba(0, 0, 0, 0.6)';
    debugOverlayList.style.border = '1px solid rgba(102, 255, 170, 0.6)';
    debugOverlayList.style.color = '#d9ffe6';
    debugOverlayList.style.fontFamily = 'monospace';
    debugOverlayList.style.fontSize = '12px';
    debugOverlayList.style.padding = '8px';
    debugOverlayList.style.pointerEvents = 'auto';
    debugOverlayList.style.whiteSpace = 'pre';

    debugOverlayInfo = document.createElement('div');
    debugOverlayInfo.style.marginBottom = '8px';
    debugOverlayInfo.style.paddingBottom = '6px';
    debugOverlayInfo.style.borderBottom = '1px solid rgba(102, 255, 170, 0.4)';

    debugOverlayList.appendChild(debugOverlayInfo);
    debugOverlayRoot.appendChild(debugOverlayList);
    sceneContainer.appendChild(debugOverlayRoot);
}

function removeDebugOverlay() {
    if (!debugOverlayRoot) {
        return;
    }
    debugOverlayRoot.remove();
    debugOverlayRoot = null;
    debugOverlayList = null;
    debugOverlayInfo = null;
    debugOverlayItems = [];
    debugOverlayDirty = true;
    debugSelectedObject = null;
    removeDebugSelectionHelper();
    resetDebugSelectionMaterials();
}

function refreshDebugOverlayTargets() {
    if (!debugOverlayEnabled || !debugOverlayRoot || !debugOverlayList) {
        return;
    }
    if (!debugOverlayDirty) {
        return;
    }
    debugOverlayDirty = false;

    debugOverlayItems.forEach(item => {
        if (item.labelEl && item.labelEl.parentNode) {
            item.labelEl.parentNode.removeChild(item.labelEl);
        }
    });
    debugOverlayItems = [];
    debugOverlayList.textContent = '';

    const targets = collectDebugTargets();
    debugOverlayInfo = document.createElement('div');
    debugOverlayInfo.style.marginBottom = '8px';
    debugOverlayInfo.style.paddingBottom = '6px';
    debugOverlayInfo.style.borderBottom = '1px solid rgba(102, 255, 170, 0.4)';
    debugOverlayList.appendChild(debugOverlayInfo);

    targets.forEach((target, index) => {
        const labelEl = document.createElement('div');
        labelEl.textContent = target.label;
        labelEl.style.position = 'absolute';
        labelEl.style.color = '#66ffaa';
        labelEl.style.fontFamily = 'monospace';
        labelEl.style.fontSize = '11px';
        labelEl.style.padding = '2px 4px';
        labelEl.style.background = 'rgba(0, 0, 0, 0.45)';
        labelEl.style.border = '1px solid rgba(102, 255, 170, 0.4)';
        labelEl.style.borderRadius = '2px';
        labelEl.style.pointerEvents = 'auto';
        labelEl.style.cursor = 'pointer';
        labelEl.addEventListener('click', event => {
            event.stopPropagation();
            setDebugSelectedObject(target.object);
        });
        debugOverlayRoot.appendChild(labelEl);

        const listItem = document.createElement('div');
        listItem.textContent = `${index + 1}. ${target.label}`;
        debugOverlayList.appendChild(listItem);

        debugOverlayItems.push({ object: target.object, labelEl, listItem });
    });

    updateDebugSelectionDisplay();
}

function updateDebugOverlayPositions() {
    if (!debugOverlayEnabled || !debugOverlayRoot || !camera) {
        return;
    }
    if (debugOverlayDirty) {
        refreshDebugOverlayTargets();
    }

    const width = window.innerWidth;
    const height = window.innerHeight;
    const position = new THREE.Vector3();

    debugOverlayItems.forEach(item => {
        if (!item.object || !item.object.parent) {
            item.labelEl.style.display = 'none';
            return;
        }
        item.object.updateMatrixWorld(true);
        item.object.getWorldPosition(position);
        position.project(camera);

        if (position.z < -1 || position.z > 1) {
            item.labelEl.style.display = 'none';
            return;
        }

        const x = (position.x * 0.5 + 0.5) * width;
        const y = (1 - (position.y * 0.5 + 0.5)) * height;
        item.labelEl.style.display = 'block';
        item.labelEl.style.transform = 'translate(-50%, -50%)';
        item.labelEl.style.left = `${x}px`;
        item.labelEl.style.top = `${y}px`;
    });

    updateDebugSelectionVisuals();
}

function collectDebugTargets() {
    const targets = [];
    if (!scene) {
        return targets;
    }

    scene.traverse(object => {
        if (!object || object === scene) {
            return;
        }
        const isEmitter = isEmitterObject(object);
        if (!isEmitter) {
            return;
        }
        targets.push({
            object,
            label: buildDebugLabel(object)
        });
    });

    return targets;
}

function isEmitterObject(object) {
    if (object.isLight || object.isSprite) {
        return true;
    }
    if (object.material) {
        return hasEmissiveMaterial(object.material);
    }
    return false;
}

function hasEmissiveMaterial(material) {
    if (Array.isArray(material)) {
        return material.some(hasEmissiveMaterial);
    }
    if (!material) {
        return false;
    }
    if (material.emissive && material.emissive.getHex && material.emissive.getHex() !== 0x000000) {
        return true;
    }
    if (material.emissiveIntensity && material.emissiveIntensity > 0.05) {
        return true;
    }
    if (material.blending === THREE.AdditiveBlending) {
        return true;
    }
    return false;
}

function buildDebugLabel(object) {
    const nameHint = object.name || object.userData.label || object.userData.roomId || object.userData.url || '';
    const typeLabel = object.type || (object.isLight ? 'Light' : 'Object');
    const idLabel = typeof object.id === 'number' ? `#${object.id}` : '';
    const lightDetails = object.isLight
        ? ` intensity=${formatNumber(object.intensity)}${object.distance ? ` dist=${formatNumber(object.distance)}` : ''}`
        : '';
    const pos = new THREE.Vector3();
    object.getWorldPosition(pos);
    const posLabel = `pos=(${formatNumber(pos.x)}, ${formatNumber(pos.y)}, ${formatNumber(pos.z)})`;
    const nameLabel = nameHint ? ` "${nameHint}"` : '';
    return `${typeLabel}${idLabel}${nameLabel} ${posLabel}${lightDetails}`;
}

function formatNumber(value) {
    if (value == null || Number.isNaN(value)) {
        return 'n/a';
    }
    return Number(value).toFixed(2);
}

function onDebugPointerDown(event) {
    if (!debugOverlayEnabled || !renderer || !scene || !camera) {
        return;
    }
    if (event.button !== 0) {
        return;
    }
    const rect = renderer.domElement.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    if (x < 0 || y < 0 || x > rect.width || y > rect.height) {
        return;
    }

    if (!raycaster) {
        raycaster = new THREE.Raycaster();
    }
    if (!mouse) {
        mouse = new THREE.Vector2();
    }

    mouse.x = (x / rect.width) * 2 - 1;
    mouse.y = -(y / rect.height) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);
    const intersections = raycaster.intersectObjects(scene.children, true);
    if (!intersections.length) {
        setDebugSelectedObject(null);
        return;
    }

    setDebugSelectedObject(intersections[0].object);
}

function setDebugSelectedObject(object) {
    if (debugSelectedObject === object) {
        return;
    }
    resetDebugSelectionMaterials();
    removeDebugSelectionHelper();
    debugSelectedObject = object;
    if (debugSelectedObject) {
        applyDebugSelectionMaterials(debugSelectedObject);
        updateDebugSelectionHelper();
    }
    updateDebugSelectionDisplay();
}

function updateDebugSelectionDisplay() {
    if (!debugOverlayInfo) {
        return;
    }

    if (!debugSelectedObject) {
        debugOverlayInfo.textContent = `Debug Overlay (${currentRoom}) - click an object to inspect. Toggle ${DEBUG_OVERLAY_HOTKEY}`;
        return;
    }

    const details = buildDebugSelectionDetails(debugSelectedObject);
    debugOverlayInfo.textContent = details;
}

function updateDebugSelectionVisuals() {
    if (!debugOverlayItems.length) {
        return;
    }
    debugOverlayItems.forEach(item => {
        const isSelected = debugSelectedObject && item.object === debugSelectedObject;
        const color = isSelected ? '#ff66cc' : '#66ffaa';
        const border = isSelected ? '1px solid rgba(255, 102, 204, 0.8)' : '1px solid rgba(102, 255, 170, 0.4)';
        item.labelEl.style.color = color;
        item.labelEl.style.border = border;
        if (item.listItem) {
            item.listItem.style.color = color;
        }
    });
}

function updateDebugSelectionHelper() {
    removeDebugSelectionHelper();
    if (!debugSelectedObject || !scene) {
        return;
    }

    debugSelectionHelper = new THREE.BoxHelper(debugSelectedObject, 0xff66cc);
    debugSelectionHelper.material.transparent = true;
    debugSelectionHelper.material.opacity = 0.9;
    debugSelectionHelper.material.depthTest = false;
    scene.add(debugSelectionHelper);
}

function removeDebugSelectionHelper() {
    if (!debugSelectionHelper || !scene) {
        debugSelectionHelper = null;
        return;
    }
    scene.remove(debugSelectionHelper);
    if (debugSelectionHelper.geometry) {
        debugSelectionHelper.geometry.dispose();
    }
    if (debugSelectionHelper.material) {
        debugSelectionHelper.material.dispose();
    }
    debugSelectionHelper = null;
}

function applyDebugSelectionMaterials(object) {
    if (!object) {
        return;
    }
    if (!debugSelectionTexture) {
        debugSelectionTexture = createDebugCheckerTexture();
    }
    if (!debugSelectionMaterial) {
        debugSelectionMaterial = new THREE.MeshBasicMaterial({
            map: debugSelectionTexture,
            color: 0xffffff,
            side: THREE.DoubleSide,
            transparent: true,
            opacity: 0.9
        });
    }
    if (object.isSprite) {
        if (!debugSelectionOriginalMaterial.has(object) && object.material) {
            debugSelectionOriginalMaterial.set(object, object.material);
        }
        object.material = new THREE.SpriteMaterial({
            map: debugSelectionTexture,
            color: 0xffffff,
            transparent: true,
            opacity: 0.9
        });
        return;
    }
    if (object.material) {
        if (!debugSelectionOriginalMaterial.has(object)) {
            debugSelectionOriginalMaterial.set(object, object.material);
        }
        object.material = debugSelectionMaterial;
    }
}

function resetDebugSelectionMaterials() {
    if (!debugSelectionOriginalMaterial.size) {
        return;
    }
    debugSelectionOriginalMaterial.forEach((material, object) => {
        if (object) {
            object.material = material;
        }
    });
    debugSelectionOriginalMaterial.clear();
}

function createDebugCheckerTexture() {
    const size = 64;
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, size, size);
    const block = size / 8;
    ctx.fillStyle = '#ff00ff';
    for (let y = 0; y < 8; y++) {
        for (let x = 0; x < 8; x++) {
            if ((x + y) % 2 === 0) {
                ctx.fillRect(x * block, y * block, block, block);
            }
        }
    }
    const texture = new THREE.CanvasTexture(canvas);
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    texture.repeat.set(2, 2);
    return texture;
}

function buildDebugSelectionDetails(object) {
    const lines = [];
    lines.push(`Debug Overlay (${currentRoom}) - Selected`);
    lines.push(buildDebugLabel(object));

    if (object.isLight) {
        lines.push(`Light color=${formatColor(object.color)} intensity=${formatNumber(object.intensity)} dist=${formatNumber(object.distance)}`);
    }

    if (object.material) {
        const material = Array.isArray(object.material) ? object.material[0] : object.material;
        if (material) {
            lines.push(`Material type=${material.type || 'Material'} color=${formatColor(material.color)}`);
            if (material.emissive) {
                lines.push(`Emissive=${formatColor(material.emissive)} intensity=${formatNumber(material.emissiveIntensity)}`);
            }
            if (material.opacity !== undefined) {
                lines.push(`Opacity=${formatNumber(material.opacity)} transparent=${!!material.transparent}`);
            }
            if (material.blending !== undefined) {
                lines.push(`Blending=${material.blending === THREE.AdditiveBlending ? 'Additive' : material.blending}`);
            }
        }
    }

    const userDataKeys = object.userData ? Object.keys(object.userData) : [];
    if (userDataKeys.length) {
        lines.push(`UserData keys=${userDataKeys.join(', ')}`);
    }

    return lines.join('\n');
}

function formatColor(color) {
    if (!color || !color.getHexString) {
        return 'n/a';
    }
    return `#${color.getHexString()}`;
}

// Handle window resize
function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
    
    // Check if composer exists before calling setSize
    if (composer && typeof composer.setSize === 'function') {
        composer.setSize(window.innerWidth, window.innerHeight);
    }
    
    // Update FXAA resolution if it exists
    if (composer && composer.passes) {
        const fxaaPass = composer.passes.find(pass => pass.material && pass.material.uniforms && pass.material.uniforms.resolution);
        if (fxaaPass) {
            fxaaPass.material.uniforms['resolution'].value.set(
                1 / (window.innerWidth * renderer.getPixelRatio()),
                1 / (window.innerHeight * renderer.getPixelRatio())
            );
        }
    }
}

// Handle mouse movement
function onMouseMove(event) {
    mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
    
    // Check for intersection with nav links
    checkNavLinkIntersection(event);
}

// Handle mouse clicks
function onMouseClick() {
    // Use raycaster to check if we clicked on a nav link or interactive object
    raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(mouse, camera);
    
    // Check for nav links first
    const navLinkIntersects = raycaster.intersectObjects(navLinks);
    if (navLinkIntersects.length > 0) {
        if (debugOverlayEnabled) {
            return;
        }
        const link = navLinkIntersects[0].object;
        if (link.userData.url) {
            // Redirect to the target URL
            window.location.href = link.userData.url;
        }
        return;
    }
    
    // Then check for interactive objects like the terminal screen
    const otherIntersects = raycaster.intersectObjects(scene.children);
    for (let i = 0; i < otherIntersects.length; i++) {
        const object = otherIntersects[i].object;
        if (object.userData.isInteractive && typeof object.userData.activateTerminal === 'function') {
            object.userData.activateTerminal();
            return;
        }
    }
}

// Setup mobile joystick
function setupJoystick() {
    // Create joystick elements dynamically to match how sprint button is created
    joystick = document.createElement('div');
    joystick.id = 'joystick';
    joystick.style.position = 'fixed';
    joystick.style.bottom = '20px';
    joystick.style.left = '20px';
    joystick.style.width = '100px';
    joystick.style.height = '100px';
    joystick.style.backgroundColor = 'rgba(0,0,0,0.7)';
    joystick.style.borderRadius = '50%';
    joystick.style.display = 'block'; // Always visible when setup
    joystick.style.touchAction = 'none';
    joystick.style.zIndex = '1000';
    joystick.style.border = '2px solid rgba(255,255,255,0.3)';
    
    joystickKnob = document.createElement('div');
    joystickKnob.id = 'joystick-knob';
    joystickKnob.style.position = 'absolute';
    joystickKnob.style.left = '50%';
    joystickKnob.style.top = '50%';
    joystickKnob.style.width = '40px';
    joystickKnob.style.height = '40px';
    joystickKnob.style.backgroundColor = 'rgba(255,255,255,0.8)';
    joystickKnob.style.borderRadius = '50%';
    joystickKnob.style.transform = 'translate(-50%, -50%)';
    
    joystick.appendChild(joystickKnob);
    sceneContainer.appendChild(joystick);
    
    let joystickRect;
    let isDragging = false;
    let activeJoystickPointerId = null;
    
    // Make sure the joystick is visible
    joystick.style.display = 'block';
    
    const refreshJoystickRect = () => {
        joystickRect = joystick.getBoundingClientRect();
    };
    joystick.refreshRect = refreshJoystickRect;
    
    const getRelativePosition = (clientX, clientY) => {
        refreshJoystickRect();
        const centerX = joystickRect.left + joystickRect.width / 2;
        const centerY = joystickRect.top + joystickRect.height / 2;
        return {
            x: clientX - centerX,
            y: clientY - centerY
        };
    };
    
    const applyJoystickFromPoint = (clientX, clientY) => {
        const position = getRelativePosition(clientX, clientY);
        const radius = joystickRect.width / 2;
        const distance = Math.sqrt(position.x * position.x + position.y * position.y);
        
        if (distance > radius) {
            position.x = position.x * radius / distance;
            position.y = position.y * radius / distance;
        }
        
        joystickKnob.style.transform = `translate(calc(-50% + ${position.x}px), calc(-50% + ${position.y}px))`;
        joystickDelta.x = position.x / radius;
        joystickDelta.y = position.y / radius;
    };
    
    const findActiveTouch = (touchList) => {
        if (!touchList || activeJoystickPointerId === null || activeJoystickPointerId === 'mouse') {
            return null;
        }
        for (let i = 0; i < touchList.length; i++) {
            if (touchList[i].identifier === activeJoystickPointerId) {
                return touchList[i];
            }
        }
        return null;
    };
    
    const moveJoystickKnob = (event) => {
        if (!isDragging) return;
        
        let point = null;
        if (event.touches) {
            point = findActiveTouch(event.touches);
        } else if (event.changedTouches) {
            point = findActiveTouch(event.changedTouches);
        } else if (activeJoystickPointerId === 'mouse') {
            point = event;
        }
        
        if (!point) return;
        
        applyJoystickFromPoint(point.clientX, point.clientY);
        if (event.cancelable) {
            event.preventDefault();
        }
    };
    
    const startDrag = (event) => {
        if (event.cancelable) {
            event.preventDefault();
        }
        let point;
        if (event.touches && event.changedTouches && event.changedTouches.length) {
            point = event.changedTouches[0];
            activeJoystickPointerId = point.identifier;
        } else if (event.touches && event.touches.length) {
            point = event.touches[0];
            activeJoystickPointerId = point.identifier;
        } else {
            point = event;
            activeJoystickPointerId = 'mouse';
        }
        
        isDragging = true;
        joystickActive = true;
        applyJoystickFromPoint(point.clientX, point.clientY);
    };
    
    const endDrag = (event) => {
        if (!isDragging) return;
        
        if (activeJoystickPointerId !== null && activeJoystickPointerId !== 'mouse') {
            if (!event || !event.changedTouches || !findActiveTouch(event.changedTouches)) {
                return;
            }
        } else if (activeJoystickPointerId === 'mouse' && event.type && event.type.startsWith('touch')) {
            return;
        }
        
        isDragging = false;
        joystickActive = false;
        activeJoystickPointerId = null;
        joystickKnob.style.transform = 'translate(-50%, -50%)';
        joystickDelta.set(0, 0);
    };
    
    // Touch events
    joystick.addEventListener('touchstart', startDrag, { passive: false });
    document.addEventListener('touchmove', moveJoystickKnob, { passive: false });
    document.addEventListener('touchend', endDrag);
    document.addEventListener('touchcancel', endDrag);
    
    // Mouse events for testing on desktop
    joystick.addEventListener('mousedown', startDrag);
    document.addEventListener('mousemove', moveJoystickKnob);
    document.addEventListener('mouseup', endDrag);
}

// Setup sprint button for mobile devices
function setupSprintButton() {
    // Create sprint button element
    const sprintButton = document.createElement('div');
    sprintButton.id = 'sprint-button';
    sprintButton.innerHTML = '<span>SPRINT</span>';
    sprintButton.style.position = 'fixed';
    sprintButton.style.bottom = '20px';
    sprintButton.style.right = '20px';
    sprintButton.style.width = '80px';
    sprintButton.style.height = '80px';
    sprintButton.style.backgroundColor = 'rgba(255, 100, 100, 0.4)';
    sprintButton.style.border = '2px solid rgba(255, 100, 100, 0.6)';
    sprintButton.style.borderRadius = '50%';
    sprintButton.style.display = 'flex';
    sprintButton.style.justifyContent = 'center';
    sprintButton.style.alignItems = 'center';
    sprintButton.style.color = 'white';
    sprintButton.style.fontFamily = 'Arial, sans-serif';
    sprintButton.style.fontSize = '14px';
    sprintButton.style.fontWeight = 'bold';
    sprintButton.style.textShadow = '1px 1px 2px rgba(0, 0, 0, 0.8)';
    sprintButton.style.zIndex = '100';
    sprintButton.style.touchAction = 'none';
    sprintButton.style.userSelect = 'none';
    sceneContainer.appendChild(sprintButton);
    
    // Handle sprint button press events
    const startSprint = (event) => {
        event.preventDefault();
        isSprinting = true;
        sprintButton.style.backgroundColor = 'rgba(255, 100, 100, 0.7)';
    };
    
    const endSprint = () => {
        isSprinting = false;
        sprintButton.style.backgroundColor = 'rgba(255, 100, 100, 0.4)';
    };
    
    // Touch events for mobile
    sprintButton.addEventListener('touchstart', startSprint, { passive: false });
    sprintButton.addEventListener('touchend', endSprint);
    
    // Mouse events for testing on desktop
    sprintButton.addEventListener('mousedown', startSprint);
    sprintButton.addEventListener('mouseup', endSprint);
}

function setupJumpButton() {
    if (jumpButton && jumpButton.isConnected) {
        return;
    }
    
    jumpButton = document.getElementById('jump-button');
    if (jumpButton && jumpButton.isConnected) {
        return;
    }
    
    jumpButton = document.createElement('div');
    jumpButton.id = 'jump-button';
    jumpButton.innerHTML = '<span>JUMP</span>';
    jumpButton.style.position = 'fixed';
    jumpButton.style.bottom = '120px';
    jumpButton.style.right = '20px';
    jumpButton.style.width = '80px';
    jumpButton.style.height = '80px';
    jumpButton.style.backgroundColor = 'rgba(102, 255, 170, 0.4)';
    jumpButton.style.border = '2px solid rgba(102, 255, 170, 0.7)';
    jumpButton.style.borderRadius = '50%';
    jumpButton.style.display = 'flex';
    jumpButton.style.justifyContent = 'center';
    jumpButton.style.alignItems = 'center';
    jumpButton.style.color = '#ffffff';
    jumpButton.style.fontFamily = 'Arial, sans-serif';
    jumpButton.style.fontSize = '14px';
    jumpButton.style.fontWeight = 'bold';
    jumpButton.style.textShadow = '1px 1px 2px rgba(0, 0, 0, 0.7)';
    jumpButton.style.zIndex = '100';
    jumpButton.style.touchAction = 'none';
    jumpButton.style.userSelect = 'none';
    jumpButton.style.transition = 'transform 0.1s ease, background-color 0.1s ease';
    sceneContainer.appendChild(jumpButton);
    
    const pressJump = (event) => {
        event.preventDefault();
        queueJump();
        jumpButton.style.transform = 'scale(0.9)';
        jumpButton.style.backgroundColor = 'rgba(102, 255, 170, 0.7)';
    };
    
    const releaseJump = () => {
        jumpButton.style.transform = 'scale(1)';
        jumpButton.style.backgroundColor = 'rgba(102, 255, 170, 0.4)';
    };
    
    jumpButton.addEventListener('touchstart', pressJump, { passive: false });
    jumpButton.addEventListener('touchend', releaseJump);
    jumpButton.addEventListener('touchcancel', releaseJump);
    jumpButton.addEventListener('mousedown', pressJump);
    jumpButton.addEventListener('mouseup', releaseJump);
    jumpButton.addEventListener('mouseleave', releaseJump);
}

function deviceSupportsTouchControls() {
    return isMobile ||
        ('ontouchstart' in window) ||
        (navigator.maxTouchPoints && navigator.maxTouchPoints > 0) ||
        (navigator.msMaxTouchPoints && navigator.msMaxTouchPoints > 0);
}

function ensureJumpButtonPresence() {
    if (deviceSupportsTouchControls()) {
        setupJumpButton();
    }
}

// Check for intersection with nav links
function checkNavLinkIntersection(event) {
    raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(navLinks);
    
    // Reset cursor and tooltip
    document.body.style.cursor = 'default';
    tooltip.style.display = 'none';
    
    if (intersects.length > 0) {
        const link = intersects[0].object;
        document.body.style.cursor = 'pointer';
        
        // Show tooltip
        if (link.userData.label) {
            tooltip.textContent = link.userData.label;
            tooltip.style.left = (event.clientX + 10) + 'px';
            tooltip.style.top = (event.clientY + 10) + 'px';
            tooltip.style.display = 'block';
        }
    }
}

// Create navigation portals with dynamic links based on user permissions
// FontLoader is actually available, but we'll keep using HTML overlays for now
function createSimpleNavigationPortals() {
    // Store all navigation links that will be created
    const navigationLinks = [];
    
    // Extract navigation data from the actual navbar in the DOM
    const navbar = document.getElementById('navbarToggle');
    if (!navbar) {
        createDefaultNavigationLinks(navigationLinks);
    } else {
        // Get all top-level nav items
        const navItems = navbar.querySelectorAll('.nav-item');
        
        // Process each nav item
        navItems.forEach((navItem, index) => {
            // Check if it's a dropdown or a single link
            const dropdown = navItem.querySelector('.dropdown-toggle');
            const singleLink = navItem.querySelector('.nav-link:not(.dropdown-toggle)');
            
            if (singleLink && !dropdown) {
                // It's a single link, no dropdown
                navigationLinks.push({
                    label: singleLink.textContent.trim(),
                    url: singleLink.getAttribute('href'),
                    color: getColorForNavItem(index),
                    groups: ['all'] // Assume visible to all since it's in the navbar
                });
            } else if (dropdown) {
                // It's a dropdown with multiple links
                const dropdownLinks = navItem.querySelectorAll('.dropdown-item');
                const submenus = [];
                
                dropdownLinks.forEach(link => {
                    // Exclude dividers
                    if (!link.classList.contains('dropdown-divider')) {
                        submenus.push({
                            label: link.textContent.trim(),
                            url: link.getAttribute('href')
                        });
                    }
                });
                
                navigationLinks.push({
                    label: dropdown.textContent.trim(),
                    url: submenus.length > 0 ? submenus[0].url : '#', // Use first submenu as default
                    color: getColorForNavItem(index),
                    groups: ['all'], // Assume visible to all since it's in the navbar
                    submenus: submenus
                });
            }
        });
    }
    
    // If no links were found in the navbar, create default links
    if (navigationLinks.length === 0) {
        createDefaultNavigationLinks(navigationLinks);
    }
    
    // Create the main room
    createMainRoom(navigationLinks);
    
    // Store the main room data
    roomData['main'] = {
        links: navigationLinks,
        parentRoom: null
    };
    
    // Create submenu rooms for each dropdown
    navigationLinks.forEach(link => {
        if (link.submenus && link.submenus.length > 0) {
            const roomId = `room_${link.label.replace(/\s+/g, '_').toLowerCase()}`;
            roomData[roomId] = {
                links: link.submenus,
                parentRoom: 'main',
                parentLink: link.label
            };
        }
    });
    
    // For any Misc. Reports portal, modify its color to match yellow portals
    navLinks.forEach(portal => {
        if (portal.userData.label === "Misc. Reports" && portal.userData.url === "/core/reports") {
            // This special portal setup is now handled directly in createSimplePortal()
            // No need to modify it here anymore
            console.log("Misc. Reports portal already configured during creation");
        }
    });
}

// Create the main navigation room
function createMainRoom(navigationLinks) {
    // Calculate wall dimensions based on number of portals
    const portalWidth = 2; // Width of each portal
    const portalSpacing = 3; // Increased space between portals from 1 to 3
    const totalPortalWidth = navigationLinks.length * portalWidth + (navigationLinks.length - 1) * portalSpacing;
    const wallPadding = 5; // Extra padding on both sides of the wall
    const wallWidth = Math.max(totalPortalWidth + wallPadding * 2, 20); // At least 20 units wide
    const wallHeight = 5; // Increased height for industrial feel
    const roomDepth = 30; // Room depth

    const mainRoomEntry = computeDepthEntryPosition(roomDepth);
    setCurrentRoomEntryPosition(mainRoomEntry, { immediate: currentRoom === 'main' && !roomTransitionInProgress });
    
    // Create metallic wall texture - use a texture that exists
    const wallTexture = loadPersistentTexture(BRICK_TEXTURE_URL, texture => {
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.RepeatWrapping;
    });
    wallTexture.repeat.set(5, 2);
    
    const wallMaterial = new THREE.MeshStandardMaterial({ 
        map: wallTexture,
        roughness: 0.7,
        metalness: 0.6,
        color: 0x555555 // Tint the texture darker
    });
    
    // Create the side walls and ceiling
    createIndustrialWall(-wallWidth/2, wallHeight/2, -10, 0.4, wallHeight, roomDepth, wallMaterial); // Left wall
    createIndustrialWall(wallWidth/2, wallHeight/2, -10, 0.4, wallHeight, roomDepth, wallMaterial); // Right wall
    createIndustrialWall(0, wallHeight, -10, wallWidth, 0.4, roomDepth, wallMaterial); // Ceiling
    
    // Position the first portal
    const startX = -totalPortalWidth / 2 + portalWidth / 2;
    
    // Create back wall sections WITH cutouts for doors
    createWallWithDoorways(navigationLinks, startX, portalWidth, portalSpacing, wallWidth, wallHeight, wallMaterial);
    
    // Add some industrial pipes and details
    addIndustrialDetails(wallWidth, wallHeight, roomDepth);
    
    // Add glow effects beneath the floor for the main room
    addMainRoomGlowEffects();
    
    // Create portals for each accessible link with color coding
    navigationLinks.forEach((link, index) => {
        const x = startX + index * (portalWidth + portalSpacing);
        
        // Determine color - Yellow for room transitions, Blue for direct links
        const portalColor = link.submenus && link.submenus.length > 0 ? 0xffdd22 : 0x33aaff;
        
        // If the link has submenus, create a portal to a submenu room instead of a direct URL
        if (link.submenus && link.submenus.length > 0) {
            const roomId = `room_${link.label.replace(/\s+/g, '_').toLowerCase()}`;
        createSimplePortal(
                x, 2.0, -19.7, // Move portal slightly forward from wall
                link.label, 
                null, // No direct URL
                portalColor, // Yellow for room transitions
                link.groups,
                roomId // Room to transition to
            );
        } else {
            // Regular portal with direct URL
    createSimplePortal(
                x, 2.0, -19.7, // Move portal slightly forward from wall
                link.label, 
                link.url, 
                portalColor, // Blue for direct links
                link.groups
            );
        }
    });
    
    // Create a welcome sign using HTML overlay
    const welcomeSign = document.createElement('div');
    welcomeSign.style.position = 'absolute';
    welcomeSign.style.top = '50px';
    welcomeSign.style.left = '50%';
    welcomeSign.style.transform = 'translateX(-50%)';
    welcomeSign.style.color = '#66FFAA'; // Mako green
    welcomeSign.style.fontFamily = 'Arial, sans-serif';
    welcomeSign.style.fontSize = '24px';
    welcomeSign.style.textShadow = '0 0 10px #33AAFF, 0 0 20px #33AAFF'; // Blue glow
    welcomeSign.style.zIndex = '10';
    welcomeSign.innerHTML = 'Kinpak Navigation 3d';
    welcomeSign.id = 'main-room-welcome';
    sceneContainer.appendChild(welcomeSign);

    ensureJumpButtonPresence();
    markDebugOverlayDirty();
}

// Add glow effects beneath the main floor
function addMainRoomGlowEffects() {
    // Create several glow spots in the main room for dramatic effect
    const mainGlowGeometry = new THREE.PlaneGeometry(3, 3);
    const mainGlowMaterial = new THREE.MeshBasicMaterial({ 
        color: 0x66ffaa, // Mako green
        transparent: true,
        opacity: 0.5,
        side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending
    });
    
    // First glow spot (green, center)
    const glowSpot1 = new THREE.Mesh(mainGlowGeometry, mainGlowMaterial);
    glowSpot1.rotation.x = -Math.PI / 2;
    glowSpot1.position.set(0, -0.1, -10);
    glowSpot1.scale.set(2, 2, 1); // Larger central glow
    scene.add(glowSpot1);
    
    // Add a point light beneath for extra glow
    const glowLight1 = new THREE.PointLight(0x66ffaa, 1.0, 8);
    glowLight1.position.set(0, -0.3, -10);
    scene.add(glowLight1);
    
    // Second glow spot (blue, left)
    const glowSpot2 = new THREE.Mesh(mainGlowGeometry, mainGlowMaterial.clone());
    glowSpot2.rotation.x = -Math.PI / 2;
    glowSpot2.position.set(-8, -0.1, -5);
    glowSpot2.material.color.set(0x33aaff); // Blue glow
    glowSpot2.material.opacity = 0.4;
    scene.add(glowSpot2);
    
    const glowLight2 = new THREE.PointLight(0x33aaff, 0.8, 6);
    glowLight2.position.set(-8, -0.3, -5);
    scene.add(glowLight2);
    
    // Third glow spot (purple, right)
    const glowSpot3 = new THREE.Mesh(mainGlowGeometry, mainGlowMaterial.clone());
    glowSpot3.rotation.x = -Math.PI / 2;
    glowSpot3.position.set(8, -0.1, -5);
    glowSpot3.material.color.set(0xaa33ff); // Purple glow for variety
    glowSpot3.material.opacity = 0.4;
    scene.add(glowSpot3);
    
    const glowLight3 = new THREE.PointLight(0xaa33ff, 0.8, 6);
    glowLight3.position.set(8, -0.3, -5);
    scene.add(glowLight3);
    
    // Fourth glow spot (yellow, far back)
    const glowSpot4 = new THREE.Mesh(mainGlowGeometry, mainGlowMaterial.clone());
    glowSpot4.rotation.x = -Math.PI / 2;
    glowSpot4.position.set(0, -0.1, -18);
    glowSpot4.material.color.set(0xffcc33);
    glowSpot4.material.opacity = 0.3;
    scene.add(glowSpot4);
    
    const glowLight4 = new THREE.PointLight(0xffcc33, 0.25, 4);
    glowLight4.position.set(0, -0.6, -20.5);
    glowLight4.decay = 2;
    scene.add(glowLight4);
}

// Create back wall with doorway cutouts
function createWallWithDoorways(navigationLinks, startX, portalWidth, portalSpacing, wallWidth, wallHeight, wallMaterial) {
    const wallZ = -20;
    const wallDepth = 0.4;
    const doorHeight = 3.2;
    const doorPadding = 0.1;
    const doorWidth = portalWidth + doorPadding * 2;
    
    // Instead of one big wall, create wall segments between doors
    let currentX = -wallWidth / 2;
    
    navigationLinks.forEach((link, index) => {
        const doorCenterX = startX + index * (portalWidth + portalSpacing);
        const doorLeftEdge = doorCenterX - doorWidth / 2;
        
        // Create wall segment to the left of the door if needed
        if (doorLeftEdge > currentX) {
            const segmentWidth = doorLeftEdge - currentX;
            
            // Wall segment before door
            createIndustrialWall(
                currentX + segmentWidth / 2, 
                wallHeight / 2, 
                wallZ, 
                segmentWidth, 
                wallHeight, 
                wallDepth, 
                wallMaterial
            );
        }
        
        // Create door frame (top part above door)
        createIndustrialWall(
            doorCenterX,
            wallHeight - doorHeight / 2,
            wallZ,
            doorWidth,
            wallHeight - doorHeight,
            wallDepth,
            wallMaterial
        );
        
        // Update current X position for next segment
        currentX = doorLeftEdge + doorWidth;
    });
    
    // Create final wall segment after the last door
    if (currentX < wallWidth / 2) {
        const segmentWidth = wallWidth / 2 - currentX;
        
        // Wall segment after last door
        createIndustrialWall(
            currentX + segmentWidth / 2, 
            wallHeight / 2, 
            wallZ, 
            segmentWidth, 
            wallHeight, 
            wallDepth, 
            wallMaterial
        );
    }
}

// Create industrial-looking walls with additional details
function createIndustrialWall(x, y, z, width, height, depth, material) {
    const wallGeometry = new THREE.BoxGeometry(width, height, depth);
    const wall = new THREE.Mesh(wallGeometry, material);
    wall.position.set(x, y, z);
    wall.castShadow = true;
    wall.receiveShadow = true;
    scene.add(wall);
    registerCollider(wall);
    return wall;
}

// Add industrial pipes, machinery and details
function addIndustrialDetails(wallWidth, wallHeight, roomDepth) {
    // Add ceiling pipes
    const pipeGeometry = new THREE.CylinderGeometry(0.2, 0.2, wallWidth * 0.8, 8);
    const pipeMaterial = new THREE.MeshStandardMaterial({ 
        color: 0x888888,
        roughness: 0.7,
        metalness: 0.8
    });
    
    // Horizontal pipes along ceiling
    const ceilingPipe1 = new THREE.Mesh(pipeGeometry, pipeMaterial);
    ceilingPipe1.rotation.z = Math.PI / 2; // Rotate to horizontal
    ceilingPipe1.position.set(0, wallHeight - 0.5, -10);
    scene.add(ceilingPipe1);
    
    // Vertical pipes in corners
    const verticalPipeGeometry = new THREE.CylinderGeometry(0.15, 0.15, wallHeight * 2, 8);
    
    const cornerPipe1 = new THREE.Mesh(verticalPipeGeometry, pipeMaterial);
    cornerPipe1.position.set(-wallWidth/2 + 1, wallHeight/2, -19);
    scene.add(cornerPipe1);
    
    const cornerPipe2 = new THREE.Mesh(verticalPipeGeometry, pipeMaterial);
    cornerPipe2.position.set(wallWidth/2 - 1, wallHeight/2, -19);
    scene.add(cornerPipe2);
    
    // Add some blinking lights
    addBlinkingLight(-wallWidth/4, wallHeight - 0.5, -19, 0xff0000); // Red warning light
    addBlinkingLight(wallWidth/4, wallHeight - 0.5, -19, 0xffaa00); // Amber warning light
    
    // Add some computer console-like geometry
    const consoleGeometry = new THREE.BoxGeometry(1.5, 1.2, 0.8);
    const consoleMaterial = new THREE.MeshStandardMaterial({ 
        color: 0x333333,
        roughness: 0.5,
        metalness: 0.7
    });
    
    const console1 = new THREE.Mesh(consoleGeometry, consoleMaterial);
    console1.position.set(-wallWidth/2 + 2, 0.8, -18);
    console1.rotation.y = Math.PI / 4;
    scene.add(console1);
    
    // Add console screen with glow
    const screenGeometry = new THREE.PlaneGeometry(1, 0.7);
    const screenMaterial = new THREE.MeshStandardMaterial({ 
        color: 0x7700ff,
        emissive: 0x4400ff,
        emissiveIntensity: 0.5
    });
    
    const screen1 = new THREE.Mesh(screenGeometry, screenMaterial);
    screen1.position.set(-wallWidth/2 + 2.01, 1, -17.85);
    screen1.rotation.y = Math.PI / 4;
    scene.add(screen1);
    
    // Add point light near screen for glow effect
    const screenLight = new THREE.PointLight(0x66ffaa, 0.5, 3);
    screenLight.position.set(-wallWidth/2 + 2, 1, -17.8);
    scene.add(screenLight);
}

// Add blinking warning lights
function addBlinkingLight(x, y, z, color) {
    // Create light housing
    const housingGeometry = new THREE.CylinderGeometry(0.15, 0.15, 0.1, 16);
    const housingMaterial = new THREE.MeshStandardMaterial({ 
        color: 0x333333,
        roughness: 0.5,
        metalness: 0.8
    });
    
    const housing = new THREE.Mesh(housingGeometry, housingMaterial);
    housing.position.set(x, y, z);
    housing.rotation.x = Math.PI / 2; // Rotate to point forward
    scene.add(housing);
    
    // Create light bulb with INCREASED emissive intensity to compensate for removed point light
    const bulbGeometry = new THREE.SphereGeometry(0.1, 16, 16);
    const bulbMaterial = new THREE.MeshStandardMaterial({
        color: color,
        emissive: color,
        emissiveIntensity: 1.8 // Increased intensity to compensate for removed light
    });
    
    const bulb = new THREE.Mesh(bulbGeometry, bulbMaterial);
    bulb.position.set(x, y, z + 0.1); // Position slightly in front of housing
    scene.add(bulb);
    
    // Add a small glowing halo (plane) instead of a sprite (avoid camera-facing tilt)
    const spriteMap = loadPersistentTexture(SPRITE_TEXTURE_URL, configureGlowTexture);
    const spriteMaterial = new THREE.MeshBasicMaterial({ 
        map: spriteMap,
        color: color,
        transparent: true,
        opacity: 0.6,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        depthTest: true,
        polygonOffset: true,
        polygonOffsetFactor: -1,
        polygonOffsetUnits: -1
    });
    
    const sprite = new THREE.Mesh(new THREE.PlaneGeometry(0.5, 0.5), spriteMaterial);
    sprite.position.set(x, y, z + 0.12);
    scene.add(sprite);
    
    return { housing, bulb, sprite };
}

// Create a submenu room with its own portals
function createSubmenuRoom(roomId) {
    console.log("🔍 [FLOOR_DEBUG] createSubmenuRoom() - Creating room:", roomId);
    
    // Check if this is the reports room first
    if (roomId === 'room_reports') {
        console.log("🔍 [FLOOR_DEBUG] createSubmenuRoom() - Redirecting to createTerminalRoom for room_reports");
        createTerminalRoom();
        return;
    }

    // Clear existing objects except the character
    clearRoomObjects();
    
    const roomInfo = roomData[roomId];
    if (!roomInfo) {
        console.log("🔍 [FLOOR_DEBUG] createSubmenuRoom() - No room info found for roomId:", roomId);
        return;
    }
    
    // Apply the same lighting as the main room
    setupMainSceneLighting();
    
    const submenuLinks = roomInfo.links;
    
    // Calculate wall dimensions based on number of portals
    const portalWidth = 2; // Width of each portal
    const portalSpacing = 3; // Space between portals
    const totalPortalWidth = submenuLinks.length * portalWidth + (submenuLinks.length - 1) * portalSpacing;
    const wallPadding = 5; // Extra padding on both sides of the wall
    const wallWidth = Math.max(totalPortalWidth + wallPadding * 2, 20); // At least 20 units wide
    const wallHeight = 5; // Increased height for industrial feel
    const roomDepth = 30; // Room depth

    const submenuEntry = computeDepthEntryPosition(roomDepth);
    setCurrentRoomEntryPosition(submenuEntry);
    
    console.log("🔍 [FLOOR_DEBUG] createSubmenuRoom() - Room dimensions:", {
        wallWidth: wallWidth,
        wallHeight: wallHeight,
        roomDepth: roomDepth
    });
    
    // Create metallic wall texture with different color tint for submenu rooms - use a texture that exists
    const wallTexture = loadPersistentTexture(BRICK_TEXTURE_URL, texture => {
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.RepeatWrapping;
    });
    wallTexture.repeat.set(5, 2);
    
    const wallMaterial = new THREE.MeshStandardMaterial({ 
        map: wallTexture,
        roughness: 0.7,
        metalness: 0.6,
        color: 0x445566 // Blueish tint for submenu rooms
    });
    
    // Create the side walls and ceiling
    createIndustrialWall(-wallWidth/2, wallHeight/2, -10, 0.4, wallHeight, roomDepth, wallMaterial); // Left wall
    createIndustrialWall(wallWidth/2, wallHeight/2, -10, 0.4, wallHeight, roomDepth, wallMaterial); // Right wall
    createIndustrialWall(0, wallHeight, -10, wallWidth, 0.4, roomDepth, wallMaterial); // Ceiling
    
    // Position the first portal
    const startX = -totalPortalWidth / 2 + portalWidth / 2;
    
    // Create back wall sections WITH cutouts for doors
    const wallZ = -20;
    createWallWithDoorways(submenuLinks, startX, portalWidth, portalSpacing, wallWidth, wallHeight, wallMaterial);
    
    // Add some industrial details specific to this submenu
    addIndustrialDetails(wallWidth, wallHeight, roomDepth);
    
    // Create floor with different color to distinguish from main room
    console.log("🔍 [FLOOR_DEBUG] createSubmenuRoom() - About to call createSubmenuFloor with wallWidth:", wallWidth);
    createSubmenuFloor(wallWidth);
    
    // After floor creation, check what floors exist
    setTimeout(() => {
        const floors = scene.children.filter(child => 
            child.name === 'mainGround' || 
            child.name === 'submenuFloor' || 
            child.name === 'terminalFloor'
        );
        
        console.log("🔍 [FLOOR_DEBUG] createSubmenuRoom() - After createSubmenuFloor, floors in scene:", 
            floors.map(floor => ({ name: floor.name, position: floor.position }))
        );
    }, 100);
    
    // Create portals for each submenu link - all blue since they are direct links
    submenuLinks.forEach((link, index) => {
        const x = startX + index * (portalWidth + portalSpacing);
        
        createSimplePortal(
            x, 2.0, -19.7, // Move portal slightly forward from wall
            link.label, 
            link.url, 
            0x33aaff, // Blue for direct links
            ['all'] // All submenu items should be accessible
        );
    });
    
    // Create a doorway in the side wall for the "Back" portal
    const backPortalX = -wallWidth/2 + 1.5;
    const backPortalZ = -10;
    const doorHeight = 3.2;
    const doorWidth = 2.2;
    
    // Create door frame (top part above door)
    createIndustrialWall(
        backPortalX,
        wallHeight - doorHeight / 2,
        backPortalZ,
        doorWidth,
        wallHeight - doorHeight,
        0.4,
        wallMaterial
    );
    
    // Create a back portal to return to the main room - yellow for room transition
    createSimplePortal(
        backPortalX, 2.0, backPortalZ - 0.2, // Slightly offset from wall
        "Back", 
        null, 
        0xffdd22, // Yellow for room transition
        ['all'],
        'main' // Transition back to main room
    );
    
    // Create a room title sign using HTML overlay
    const roomTitle = document.createElement('div');
    roomTitle.style.position = 'absolute';
    roomTitle.style.top = '50px';
    roomTitle.style.left = '50%';
    roomTitle.style.transform = 'translateX(-50%)';
    roomTitle.style.color = '#33AAFF'; // Blue
    roomTitle.style.fontFamily = 'Arial, sans-serif';
    roomTitle.style.fontSize = '24px';
    roomTitle.style.textShadow = '0 0 10px #66FFAA, 0 0 20px #66FFAA'; // Mako green glow
    roomTitle.style.zIndex = '10';
    roomTitle.innerHTML = `${roomInfo.parentLink} - Control Terminal`;
    roomTitle.id = 'submenu-room-title';
    sceneContainer.appendChild(roomTitle);
    
    // Reset movement state and align camera with current spawn
    if (character) {
        resetJumpState();
    }
    if (camera && character) {
        camera.position.set(
            character.position.x,
            character.position.y + 2.5,
            character.position.z + 5
        );
        camera.lookAt(character.position);
    }
}

// Create submenu room's floor
function createSubmenuFloor(wallWidth) {
    console.log("🔍 [FLOOR_DEBUG] createSubmenuFloor() - Creating floor for submenu room:", currentRoom, "with wallWidth:", wallWidth);
    
    // First, explicitly remove any mainGround that might be present
    const existingMainGround = scene.getObjectByName('mainGround');
    if (existingMainGround) {
        scene.remove(existingMainGround);
        console.log("🔍 [FLOOR_DEBUG] createSubmenuFloor() - Removed existing mainGround from scene");
    }
    
    // Use the floor grate texture for the entire floor
    const floorTexture = loadPersistentTexture(FLOOR_TEXTURE_URL, texture => {
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.RepeatWrapping;
        texture.minFilter = THREE.NearestFilter;
        texture.magFilter = THREE.NearestFilter;
    });
    
    // IMPORTANT: Calculate proper repetition to maintain original texture resolution
    // Each grate tile should be 2x2 units in the 3D world
    const tileSize = 2;
    
    // DRAMATICALLY increase the depth of the floor - make it much deeper to eliminate void
    const floorDepth = 300; // Massively extended beyond camera view
    const floorWidth = Math.max(wallWidth * 3, 100); // Triple width for extreme coverage
    
    console.log("🔍 [FLOOR_DEBUG] createSubmenuFloor() - Floor dimensions:", {
        depth: floorDepth,
        width: floorWidth,
        tileSize: tileSize,
        repetition: { x: floorWidth/tileSize, y: floorDepth/tileSize }
    });
    
    floorTexture.repeat.set(floorWidth/tileSize, floorDepth/tileSize); // Proper tiling without stretching
    
    const floorGeometry = new THREE.PlaneGeometry(floorWidth, floorDepth);
    const floorMaterial = new THREE.MeshStandardMaterial({ 
        map: floorTexture,
        roughness: 0.7,
        metalness: 0.8,
        color: 0x888888 // Lighter gray to preserve texture details
    });
    const floor = new THREE.Mesh(floorGeometry, floorMaterial);
    floor.rotation.x = -Math.PI / 2;
    floor.position.set(0, 0, -150); // Position dramatically further back
    floor.receiveShadow = true;
    floor.name = 'submenuFloor'; // Give the submenu floor a name
    scene.add(floor);
    registerCollider(floor, { ignoreCollision: true, isFloor: true });
    
    console.log("🔍 [FLOOR_DEBUG] createSubmenuFloor() - Floor created and added to scene:", {
        name: floor.name,
        position: floor.position,
        isInScene: scene.children.includes(floor)
    });
    
    // Add additional glowing elements to fill the expanded floor area
    addFloorGrating(wallWidth);
    
    // Now check all floors in scene after complete setup
    setTimeout(() => {
        const floors = scene.children.filter(child => 
            child.name === 'mainGround' || 
            child.name === 'submenuFloor' || 
            child.name === 'terminalFloor'
        );
        
        console.log("🔍 [FLOOR_DEBUG] createSubmenuFloor() - After setup, floors in scene:", 
            floors.map(floor => ({ name: floor.name, position: floor.position }))
        );
    }, 100);
    
    // Add an extra glow spot further back to illuminate the extended area
    const farGlowGeometry = new THREE.PlaneGeometry(4, 4);
    const farGlowMaterial = new THREE.MeshBasicMaterial({
        color: 0x8866ff, // Purple hue
        transparent: true,
        opacity: 0.35,
        side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending
    });
    
    // Far back glow spot
    const farGlowPlane = new THREE.Mesh(farGlowGeometry, farGlowMaterial);
    farGlowPlane.rotation.x = -Math.PI / 2;
    farGlowPlane.position.set(0, -0.1, -150); // Match new floor position
    scene.add(farGlowPlane);
    
    // Add a point light for the far glow
    const farGrateLight = new THREE.PointLight(0x8866ff, 0.9, 14);
    farGrateLight.position.set(0, -0.3, -150); // Match new floor position
    scene.add(farGrateLight);
    
    // Add an extreme back glow to ensure no void is visible
    const extremeGlowPlane = new THREE.Mesh(farGlowGeometry.clone(), farGlowMaterial.clone());
    extremeGlowPlane.rotation.x = -Math.PI / 2;
    extremeGlowPlane.position.set(0, -0.1, -200); // Position much further back to match new floor depth
    extremeGlowPlane.material.color.set(0x6644aa); // Slightly different purple
    extremeGlowPlane.scale.set(5, 5, 1); // Much larger glow at the back
    scene.add(extremeGlowPlane);
    
    const extremeGrateLight = new THREE.PointLight(0x6644aa, 0.7, 30); // Increased range
    extremeGrateLight.position.set(0, -0.3, -200);
    scene.add(extremeGrateLight);
    
    // Add side glow planes to ensure the void is banished from all angles
    const leftGlowPlane = new THREE.Mesh(farGlowGeometry.clone(), farGlowMaterial.clone());
    leftGlowPlane.rotation.x = -Math.PI / 2;
    leftGlowPlane.position.set(-floorWidth/2 + 5, -0.1, -55);
    leftGlowPlane.material.color.set(0x4455cc);
    leftGlowPlane.scale.set(2, 2, 1);
    scene.add(leftGlowPlane);
    
    const leftGrateLight = new THREE.PointLight(0x4455cc, 0.7, 15);
    leftGrateLight.position.set(-floorWidth/2 + 5, -0.3, -55);
    scene.add(leftGrateLight);
    
    const rightGlowPlane = new THREE.Mesh(farGlowGeometry.clone(), farGlowMaterial.clone());
    rightGlowPlane.rotation.x = -Math.PI / 2;
    rightGlowPlane.position.set(floorWidth/2 - 5, -0.1, -55);
    rightGlowPlane.material.color.set(0x4455cc);
    rightGlowPlane.scale.set(2, 2, 1);
    scene.add(rightGlowPlane);
    
    const rightGrateLight = new THREE.PointLight(0x4455cc, 0.7, 15);
    rightGrateLight.position.set(floorWidth/2 - 5, -0.3, -55);
    scene.add(rightGrateLight);

    ensureJumpButtonPresence();
    markDebugOverlayDirty();
}

// Add glowing elements beneath the floor
function addFloorGrating(wallWidth) {
    // Add a glowing section beneath the floor for effect
    const glowGeometry = new THREE.PlaneGeometry(2.5, 2.5);
    const glowMaterial = new THREE.MeshBasicMaterial({ 
        color: 0x66ffaa, // Mako green
        transparent: true,
        opacity: 0.5,
        side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending // Better glow effect
    });
    
    // First glow spot (green)
    const glowPlane = new THREE.Mesh(glowGeometry, glowMaterial);
    glowPlane.rotation.x = -Math.PI / 2;
    glowPlane.position.set(5, -0.1, -15); // Position below the floor
    scene.add(glowPlane);
    
    // Add a point light beneath for extra glow
    const grateLight = new THREE.PointLight(0x66ffaa, 1.2, 5);
    grateLight.position.set(5, -0.3, -15);
    scene.add(grateLight);
    
    // Second glow spot (blue)
    const glowPlane2 = new THREE.Mesh(glowGeometry, glowMaterial.clone());
    glowPlane2.rotation.x = -Math.PI / 2;
    glowPlane2.position.set(-5, -0.1, -10);
    glowPlane2.material.color.set(0x33aaff); // Blue glow
    glowPlane2.material.opacity = 0.4;
    scene.add(glowPlane2);
    
    const grateLight2 = new THREE.PointLight(0x33aaff, 1.0, 4);
    grateLight2.position.set(-5, -0.3, -10);
    scene.add(grateLight2);
    
    // Third glow spot (yellow/orange)
    const glowPlane3 = new THREE.Mesh(glowGeometry, glowMaterial.clone());
    glowPlane3.rotation.x = -Math.PI / 2;
    glowPlane3.position.set(0, -0.1, -5);
    glowPlane3.material.color.set(0xffcc33); // Yellow/orange glow
    glowPlane3.material.opacity = 0.3;
    glowPlane3.scale.set(3, 3, 1); // Slightly larger glow
    scene.add(glowPlane3);
    
    const grateLight3 = new THREE.PointLight(0xffcc33, 0.8, 6);
    grateLight3.position.set(0, -0.3, -5);
    scene.add(grateLight3);
    
    // Add additional glow spots to cover the expanded floor
    
    // Green glow further back
    const glowPlane4 = new THREE.Mesh(glowGeometry, glowMaterial.clone());
    glowPlane4.rotation.x = -Math.PI / 2;
    glowPlane4.position.set(-8, -0.1, -22);
    glowPlane4.material.color.set(0x66ffaa); // Green glow
    glowPlane4.material.opacity = 0.35;
    glowPlane4.scale.set(2, 2, 1);
    scene.add(glowPlane4);
    
    const grateLight4 = new THREE.PointLight(0x66ffaa, 0.9, 6);
    grateLight4.position.set(-8, -0.3, -22);
    scene.add(grateLight4);
    
    // Blue glow further back
    const glowPlane5 = new THREE.Mesh(glowGeometry, glowMaterial.clone());
    glowPlane5.rotation.x = -Math.PI / 2;
    glowPlane5.position.set(8, -0.1, -22);
    glowPlane5.material.color.set(0x33aaff); // Blue glow
    glowPlane5.material.opacity = 0.3;
    glowPlane5.scale.set(2, 2, 1);
    scene.add(glowPlane5);
    
    const grateLight5 = new THREE.PointLight(0x33aaff, 0.8, 6);
    grateLight5.position.set(8, -0.3, -22);
    scene.add(grateLight5);
    
    // Deep glow spots
    const deepGlowGeometry = new THREE.PlaneGeometry(5, 5);
    
    // Deep green glow
    const deepGlowPlane1 = new THREE.Mesh(deepGlowGeometry, glowMaterial.clone());
    deepGlowPlane1.rotation.x = -Math.PI / 2;
    deepGlowPlane1.position.set(-10, -0.1, -35);
    deepGlowPlane1.material.color.set(0x66ffaa); // Green glow
    deepGlowPlane1.material.opacity = 0.3;
    deepGlowPlane1.scale.set(2, 2, 1);
    scene.add(deepGlowPlane1);
    
    const deepGrateLight1 = new THREE.PointLight(0x66ffaa, 0.7, 8);
    deepGrateLight1.position.set(-10, -0.3, -35);
    scene.add(deepGrateLight1);
    
    // Deep blue glow
    const deepGlowPlane2 = new THREE.Mesh(deepGlowGeometry, glowMaterial.clone());
    deepGlowPlane2.rotation.x = -Math.PI / 2;
    deepGlowPlane2.position.set(10, -0.1, -35);
    deepGlowPlane2.material.color.set(0x33aaff); // Blue glow
    deepGlowPlane2.material.opacity = 0.3;
    deepGlowPlane2.scale.set(2, 2, 1);
    scene.add(deepGlowPlane2);
    
    const deepGrateLight2 = new THREE.PointLight(0x33aaff, 0.7, 8);
    deepGrateLight2.position.set(10, -0.3, -35);
    scene.add(deepGrateLight2);
    
    // Deep purple glow in the center
    const deepGlowPlane3 = new THREE.Mesh(deepGlowGeometry, glowMaterial.clone());
    deepGlowPlane3.rotation.x = -Math.PI / 2;
    deepGlowPlane3.position.set(0, -0.1, -45);
    deepGlowPlane3.material.color.set(0x9966ff); // Purple glow
    deepGlowPlane3.material.opacity = 0.4;
    deepGlowPlane3.scale.set(3, 3, 1);
    scene.add(deepGlowPlane3);
    
    const deepGrateLight3 = new THREE.PointLight(0x9966ff, 0.8, 12);
    deepGrateLight3.position.set(0, -0.3, -45);
    scene.add(deepGrateLight3);

    // Add far back glow spots
    const farGlowPlane1 = new THREE.Mesh(deepGlowGeometry, glowMaterial.clone());
    farGlowPlane1.rotation.x = -Math.PI / 2;
    farGlowPlane1.position.set(-15, -0.1, -90);
    farGlowPlane1.material.color.set(0x33aaff); // Blue glow
    farGlowPlane1.material.opacity = 0.35;
    farGlowPlane1.scale.set(4, 4, 1);
    scene.add(farGlowPlane1);

    const farGrateLight1 = new THREE.PointLight(0x33aaff, 0.7, 15);
    farGrateLight1.position.set(-15, -0.3, -90);
    scene.add(farGrateLight1);

    const farGlowPlane2 = new THREE.Mesh(deepGlowGeometry, glowMaterial.clone());
    farGlowPlane2.rotation.x = -Math.PI / 2;
    farGlowPlane2.position.set(15, -0.1, -90);
    farGlowPlane2.material.color.set(0x66ffaa); // Green glow
    farGlowPlane2.material.opacity = 0.35;
    farGlowPlane2.scale.set(4, 4, 1);
    scene.add(farGlowPlane2);

    const farGrateLight2 = new THREE.PointLight(0x66ffaa, 0.7, 15);
    farGrateLight2.position.set(15, -0.3, -90);
    scene.add(farGrateLight2);
    
    // Add extreme distance glow spots to ensure full floor coverage
    const extremeGlowPlane1 = new THREE.Mesh(deepGlowGeometry, glowMaterial.clone());
    extremeGlowPlane1.rotation.x = -Math.PI / 2;
    extremeGlowPlane1.position.set(0, -0.1, -200);
    extremeGlowPlane1.material.color.set(0x9966ff); // Purple glow
    extremeGlowPlane1.material.opacity = 0.4;
    extremeGlowPlane1.scale.set(8, 8, 1); // Much larger for distant coverage
    scene.add(extremeGlowPlane1);

    const extremeGrateLight1 = new THREE.PointLight(0x9966ff, 0.8, 30); // Increased range
    extremeGrateLight1.position.set(0, -0.3, -200);
    scene.add(extremeGrateLight1);
    
    // Final distant glow spot at the far edge of the floor
    const extremeGlowPlane2 = new THREE.Mesh(deepGlowGeometry, glowMaterial.clone());
    extremeGlowPlane2.rotation.x = -Math.PI / 2;
    extremeGlowPlane2.position.set(0, -0.1, -260);
    extremeGlowPlane2.material.color.set(0x3366aa); // Deep blue glow
    extremeGlowPlane2.material.opacity = 0.3;
    extremeGlowPlane2.scale.set(10, 10, 1); // Extremely large for maximum coverage
    scene.add(extremeGlowPlane2);

    const extremeGrateLight2 = new THREE.PointLight(0x3366aa, 0.6, 40); // Maximum range
    extremeGrateLight2.position.set(0, -0.3, -260);
    scene.add(extremeGrateLight2);
}

// Helper function to create an alpha texture for the grating
function createGrateAlphaTexture() {
    // This function is no longer used since we're displaying the texture directly
    console.log("createGrateAlphaTexture is deprecated");
    return null;
}

// Helper function to draw rounded rectangles
function roundRect(ctx, x, y, width, height, radius) {
    // This function is only used by the deprecated createGrateAlphaTexture function
    console.log("roundRect is deprecated");
}

// Clear room objects except preserved actors and recycle GPU memory
function clearRoomObjects() {
    console.log("🔍 [FLOOR_DEBUG] clearRoomObjects() - Started with currentRoom:", currentRoom);
    
    // First, clear all HTML overlay elements
    const portalLabels = document.querySelectorAll('[id^="portal-label-"]');
    portalLabels.forEach(el => {
        if (el && el.parentNode) {
            el.parentNode.removeChild(el);
        }
    });
    
    const roomElements = document.querySelectorAll('#main-room-welcome, #submenu-room-title, #terminal-interface, #terminal-prompt');
    roomElements.forEach(el => {
        if (el && el.parentNode) {
            el.parentNode.removeChild(el);
        }
    });
    
    // Reset terminal UI references
    if (terminalCursorStylesElement && terminalCursorStylesElement.parentNode) {
        terminalCursorStylesElement.parentNode.removeChild(terminalCursorStylesElement);
    }
    terminalCursorStylesElement = null;
    terminalInterface = null;
    terminalPrompt = null;
    terminalScreenMesh = null;
    
    const existingJumpButton = document.getElementById('jump-button');
    if (existingJumpButton && existingJumpButton.parentNode) {
        existingJumpButton.parentNode.removeChild(existingJumpButton);
    }
    jumpButton = null;
    
    // Clear portal signs array first to avoid stale references
    if (window.portalSigns) {
        window.portalSigns = [];
    }
    
    // Clear navLinks array first to ensure old references are gone
    navLinks = [];
    
    // Clear colliders array
    colliders = [];
    
    // Safely store character before clearing
    const savedCharacter = character;
    const previousBackground = scene ? scene.background : null;
    const previousFog = scene ? scene.fog : null;
    
    if (scene) {
        const preserve = new Set();
        if (savedCharacter) {
            preserve.add(savedCharacter);
            // Preserve the entire avatar hierarchy so its meshes/lights aren't disposed between rooms
            savedCharacter.traverse(child => preserve.add(child));
        }
        disposeSceneResources(scene, preserve);
    }
    
    // Create a new scene to ensure a clean state
    const newScene = new THREE.Scene();
    if (previousBackground) {
        newScene.background = previousBackground;
    }
    if (previousFog) {
        newScene.fog = previousFog;
    }
    
    // Keep the original as backup
    originalScene = newScene;
    
    // Replace the current scene
    scene = newScene;
    
    // Re-add preserved objects
    if (savedCharacter) {
        scene.add(savedCharacter);
    }
    
    // Determine target room to prepare base geometry when needed
    const isGoingToMainRoom = currentRoom === 'main' || currentRoom === 'room_terminal';
    const isGoingToSubmenuRoom = currentRoom.startsWith('room_') && currentRoom !== 'room_terminal';
    
    console.log("🔍 [FLOOR_DEBUG] clearRoomObjects() - Room type:", {
        isGoingToMainRoom,
        isGoingToSubmenuRoom,
        roomId: currentRoom
    });
    
    if (isGoingToMainRoom) {
        console.log("🔍 [FLOOR_DEBUG] clearRoomObjects() - Creating fresh mainGround for main room");
        const floorTexture = loadPersistentTexture('/static/nav3d/models/floor_grate_1.jpg', texture => {
            texture.wrapS = THREE.RepeatWrapping;
            texture.wrapT = THREE.RepeatWrapping;
            texture.minFilter = THREE.NearestFilter;
            texture.magFilter = THREE.NearestFilter;
        });
        
        const tileSize = 2;
        const groundSize = 240; // Match the main ground size from init()
        floorTexture.repeat.set(groundSize / tileSize, groundSize / tileSize);
        
        const groundGeometry = new THREE.PlaneGeometry(groundSize, groundSize);
        const groundMaterial = new THREE.MeshStandardMaterial({ 
            map: floorTexture,
            roughness: 0.7,
            metalness: 0.8,
            color: 0x888888 // Lighter gray to preserve texture details
        });
        const newGround = new THREE.Mesh(groundGeometry, groundMaterial);
        newGround.rotation.x = -Math.PI / 2;
        newGround.position.set(0, 0, -60); // Match position from init()
        newGround.receiveShadow = true;
        newGround.name = 'mainGround';
        scene.add(newGround);
        registerCollider(newGround, { ignoreCollision: true, isFloor: true });
        
        console.log("🔍 [FLOOR_DEBUG] clearRoomObjects() - New mainGround created for main room:", {
            size: groundSize,
            position: newGround.position
        });
    } else if (isGoingToSubmenuRoom) {
        console.log("🔍 [FLOOR_DEBUG] clearRoomObjects() - Skipping floor creation for submenu room:", currentRoom);
    }
    // For submenu rooms, we'll let createSubmenuFloor handle creating the appropriate floor
}

// Check if character is near a portal
function checkPortalProximity() {
    // If transition is in progress, don't check for more portal proximity
    if (roomTransitionInProgress) return;
    
    navLinks.forEach(portal => {
        const distance = character.position.distanceTo(portal.position);
        
        // If character is very close to a portal
        if (distance < 1.5) {
            console.log('Portal proximity detected:', {
                portalLabel: portal.userData.label,
                portalUrl: portal.userData.url,
                portalRoomId: portal.userData.roomId,
                currentRoom: currentRoom
            });
            
            // Check if user has permission
            if (hasPermission(portal.userData.requiredGroups)) {
                // Special case for Reports portal
                if (portal.userData.label === "Misc. Reports" && portal.userData.url === "/core/reports") {
                    console.log('Reports portal detected - initiating terminal room transition');
                    // Set transition flag
                    roomTransitionInProgress = true;
                    
                    // Start vignette transition like other yellow portals
                    portalTransition.startTransition('vignette');
                    
                    // Wait for vignette to reach peak darkness before transitioning
            setTimeout(() => {
                        // Clear current room
            clearRoomObjects();
            
                        // Store room state
                        previousRoom = currentRoom;
                        currentRoom = 'room_terminal';
                        
                        // CRUCIAL: Ensure character model persists through the transition
                        if (!character) {
                            character = new THREE.Group();
                            scene.add(character);
                            resetJumpState();
                            
                            // Attempt to load the beer can model
                            loadBeerCan();
                        } else {
                            resetJumpState();
                        }

                        targetRotation = 0;
                        currentRotation = 0;
                        pendingEntryRotation = 0;
                        pendingApplyRoomEntry = true;

                        // Create terminal room
                        createTerminalRoom();
                        
                        applyRoomEntryPosition();

                        setTimeout(() => {
                            portalTransition.endTransition('vignette');
                            roomTransitionInProgress = false;
                        }, 400);
                    }, 400);
                    return;
                }
                
                if (portal.userData.roomId && portal.userData.roomId !== currentRoom) {
                    // This is a room transition portal
                    console.log('Room transition initiated:', {
                        from: currentRoom,
                        to: portal.userData.roomId
                    });
                    transitionToRoom(portal.userData.roomId);
                } else if (portal.userData.url) {
                    // This is a direct URL portal - start rectangle transition
                    console.log('URL portal activated:', portal.userData.url);
                    roomTransitionInProgress = true;
                    portalTransition.startTransition('rectangle');
                    
                    // Delay the actual navigation to allow transition to play
                    setTimeout(() => {
                        window.location.href = portal.userData.url;
                    }, 600);
                }
            }
        }
    });
}

// Check if user has permission to access a portal
function hasPermission(requiredGroups) {
    // If portal is accessible to all
    if (requiredGroups.includes('all')) {
        return true;
    }
    
    // Check for group membership
    for (const group of requiredGroups) {
        if (userGroups.includes(group)) {
            return true;
        }
    }
    
    return false;
}

// Fetch user permissions from Django
function fetchUserPermissions() {
    const userData = document.getElementById('user-data');
    if (!userData) {
        return;
    }
    
    // Default group for all users
    userGroups = ['all'];
    
    // Check authentication status
    const isAuthenticated = userData.getAttribute('data-is-authenticated') === 'true';
    if (!isAuthenticated) {
        // Not authenticated, only 'all' group available
        createSimpleNavigationPortals(); // Create portals after setting groups
        return; 
    }
    
    // Check admin status
    if (userData.getAttribute('data-is-admin') === 'true') {
        userGroups.push('admin');
    }
    
    // Check other group memberships
    if (userData.getAttribute('data-is-blend-crew') === 'true') {
        userGroups.push('blend_crew');
    }
    
    if (userData.getAttribute('data-is-front-office') === 'true') {
        userGroups.push('front_office');
    }
    
    if (userData.getAttribute('data-is-forklift-operator') === 'true') {
        userGroups.push('forklift_operator');
    }
    
    if (userData.getAttribute('data-is-lab') === 'true') {
        userGroups.push('lab');
    }
    
    // Create the navigation portals AFTER we've fetched permissions
    createSimpleNavigationPortals();
}

// Generate a consistent color based on index
function getColorForNavItem(index) {
    // Array of nice colors for the portals
    const colors = [
        0x00FF00, // Green
        0x0000FF, // Blue
        0xFF00FF, // Magenta
        0xFFAA00, // Orange
        0xAAFF00, // Lime
        0x00FFAA, // Teal
        0xFF0000, // Red
        0xFF8800  // Dark Orange
    ];
    
    return colors[index % colors.length];
}

// Fallback function to create default navigation links if DOM extraction fails
function createDefaultNavigationLinks(navigationLinks) {
    // Parse navbars based on user groups
    // Add base links that all users should have
    navigationLinks.push({
        label: 'Schedule',
        url: '/prodverse/production-schedule',
        color: 0x00FF00,
        groups: ['all']
    });
    
    navigationLinks.push({
        label: 'Item Lookup',
        url: '/core/lookup-item-quantity/',
        color: 0x0000FF,
        groups: ['all'],
        submenus: [
            { label: 'Item Quantity', url: '/core/lookup-item-quantity/' },
            { label: 'Chemical Location', url: '/core/lookup-location/' },
            { label: 'Lot Numbers', url: '/core/lookup-lot-numbers/' },
            { label: 'Spec Sheets', url: '/prodverse/spec-sheet-lookup/' },
            { label: 'Component Shortages', url: '/core/subcomponent-shortages' },
            { label: 'Create Raw Material Label', url: '/core/display-raw-material-label' }
        ]
    });
    
    navigationLinks.push({
        label: 'Feedback',
        url: '/core/feedback/',
        color: 0x00FF00,
        groups: ['all']
    });
    
    // Add blend crew specific links
    if (userGroups.includes('blend_crew') || userGroups.includes('admin')) {
        navigationLinks.push({
            label: 'Blending',
            url: '/core/blend-schedule?blend-area=all',
            color: 0xFF00FF,
            groups: ['blend_crew', 'admin'],
            submenus: [
                { label: 'Component Shortages', url: '/core/subcomponent-shortages' },
                { label: 'Tank Levels', url: '/core/tank-levels' },
                { label: 'XmR Tank Control Limits', url: '/core/xmr-tank-control-limits' },
                { label: 'Lot Numbers', url: '/core/lot-num-records?recordType=blend' },
                { label: 'Blend Shortages', url: '/core/blend-shortages?recordType=blend' },
                { label: 'All Scheduled Blends', url: '/core/blend-schedule?blend-area=all' },
                { label: 'Blend Tote Label', url: '/core/display-blend-tote-label' }
            ]
        });
        
        navigationLinks.push({
            label: 'Count Links',
            url: '/core/display-count-collection-links',
            color: 0xFF00FF,
            groups: ['blend_crew', 'admin']
        });
    }
    
    // Add front office specific links
    if (userGroups.includes('front_office') || userGroups.includes('admin')) {
        navigationLinks.push({
            label: 'Reports',
            url: '/core/reports',
            color: 0xFFAA00,
            groups: ['front_office', 'admin']
        });
    }
    
    // Add lab specific links
    if (userGroups.includes('lab') || userGroups.includes('admin')) {
        navigationLinks.push({
            label: 'QC Data',
            url: '/core/qc-data',
            color: 0xAAFF00,
            groups: ['lab', 'admin']
        });
    }
    
    // Add forklift operator specific links
    if (userGroups.includes('forklift_operator') || userGroups.includes('admin')) {
        navigationLinks.push({
            label: 'Forklift',
            url: '/core/forklift-checklist',
            color: 0x00FFAA,
            groups: ['forklift_operator', 'admin']
        });
    }
    
    // Add admin specific links
    if (userGroups.includes('admin')) {
        navigationLinks.push({
            label: 'Admin',
            url: '/admin',
            color: 0xFF0000,
            groups: ['admin'],
            submenus: [
                { label: 'Django Admin', url: '/admin' },
                { label: 'Missing Audit Groups', url: '/core/display-missing-audit-groups?filterString=all' },
                { label: 'Refresh Status', url: '/core/display-loop-status' },
                { label: 'Forklift Reports', url: '/core/checklist-management/' }
            ]
        });
        
        navigationLinks.push({
            label: 'Inventory',
            url: '/core/items-by-audit-group?recordType=warehouse',
            color: 0xFF8800,
            groups: ['admin'],
            submenus: [
                { label: 'Warehouse Count List', url: '/core/items-by-audit-group?recordType=warehouse' },
                { label: 'View All Warehouse Counts', url: '/core/count-records/?recordType=warehouse' }
            ]
        });
    }
}

// Add atmospheric Mako reactor lights - enhanced brightness and effects
function addReactorLights() {
    // OPTIMIZED: Single strategic Mako point light with increased parameters
    const primaryMakoLight = new THREE.PointLight(0x66ffaa, 1.5, 35);
    primaryMakoLight.position.set(0, 4, -15);
    primaryMakoLight.castShadow = true;
    // Optimize shadow map settings
    primaryMakoLight.shadow.mapSize.width = 512;  // Reduced from default for performance
    primaryMakoLight.shadow.mapSize.height = 512;
    primaryMakoLight.shadow.camera.near = 0.5;
    primaryMakoLight.shadow.camera.far = 40;
    primaryMakoLight.shadow.bias = -0.001;
    scene.add(primaryMakoLight);
    
    // OPTIMIZED: Secondary blue accent light for color variation
    const accentLight = new THREE.PointLight(0x33ccff, 0.8, 25);
    accentLight.position.set(8, 5, -12);
    scene.add(accentLight);
    
    // Add glowing Mako elements using emissive materials instead of lights
    addMakoEmissiveElements();
}

// New function to add glow effects using emissive materials instead of lights
function addMakoEmissiveElements() {
    const glowMap = loadPersistentTexture(SPRITE_TEXTURE_URL, configureGlowTexture);
    
    // Add industrial orange glow for contrast
    const orangeGlowMaterial = new THREE.MeshBasicMaterial({
        map: glowMap,
        color: 0xffaa33,
        transparent: true,
        opacity: 0.3,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        depthTest: true,
        polygonOffset: true,
        polygonOffsetFactor: -1,
        polygonOffsetUnits: -1
    });
    
    // Add a few orange glows to replace the removed industrial light
    const industrialGlow1 = new THREE.Mesh(new THREE.PlaneGeometry(5, 5), orangeGlowMaterial);
    industrialGlow1.position.set(0, 6, -5);
    scene.add(industrialGlow1);
}

// Create a pillar for the sides of the portal
function createPortalPillar(x, y, z, width, height, depth, color = 0x666666) {
    const material = new THREE.MeshPhysicalMaterial({
        color: color,
        roughness: 0.7,
        metalness: 0.3,
        clearcoat: 0.1
    });
    const pillar = new THREE.Mesh(
        new THREE.BoxGeometry(width, height, depth),
        material
    );
    pillar.position.set(x, y, z);
    scene.add(pillar);
    registerCollider(pillar);
    return pillar;
}

// Create pillars on both sides of a portal
function createPortalPillars(x, y, z, doorWidth) {
    const pillarWidth = 0.2;
    const pillarHeight = 3.4; // Slightly taller than door
    const pillarDepth = 0.3;
    
    // Create pillars aligned with door height
    createPortalPillar(
        x - doorWidth/2 - pillarWidth/2, 
        y, // Center at same height as door 
        z,
        pillarWidth, 
        pillarHeight, 
        pillarDepth
    );
    
    createPortalPillar(
        x + doorWidth/2 + pillarWidth/2, 
        y, // Center at same height as door
        z,
        pillarWidth, 
        pillarHeight, 
        pillarDepth
    );
}

// Create a terminal room for reports interface
function createTerminalRoom() {
    // Clear existing objects except the character
    clearRoomObjects();
    
    // Remove any existing main ground to prevent flickering
    const existingMainGround = scene.getObjectByName('mainGround');
    if (existingMainGround) {
        scene.remove(existingMainGround);
        console.log("Removed existing mainGround from terminal room to prevent flickering");
    }
    
    // Apply the same lighting as the main room
    setupMainSceneLighting();
    
    // Room dimensions
    const roomWidth = 15;
    const roomHeight = 5;
    const roomDepth = 15;

    const terminalEntry = computeDepthEntryPosition(roomDepth, { ratio: 0.45 });
    setCurrentRoomEntryPosition(terminalEntry);
    
    // Make sure character is facing forward toward the terminal screen
    if (character) {
        character.rotation.y = 0;
        // Reset character movement tracking variables
        targetRotation = 0;
        currentRotation = 0;
        
        // Set camera to ideal viewing position behind character
        camera.position.set(0, character.position.y + 2.5, -3);
        camera.lookAt(0, character.position.y, -15); // Look toward the terminal at end of room
    }
    
    // Create metallic wall texture with cyberpunk tint
    const wallTexture = loadPersistentTexture(BRICK_TEXTURE_URL, texture => {
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.RepeatWrapping;
    });
    wallTexture.repeat.set(3, 2);
    
    const wallMaterial = new THREE.MeshStandardMaterial({ 
        map: wallTexture,
        roughness: 0.7,
        metalness: 0.8,
        color: 0x223344 // Dark blue-gray for cyberpunk feel
    });
    
    // Create walls and ceiling
    createIndustrialWall(-roomWidth/2, roomHeight/2, -roomDepth/2, 0.4, roomHeight, roomDepth, wallMaterial); // Left wall
    createIndustrialWall(roomWidth/2, roomHeight/2, -roomDepth/2, 0.4, roomHeight, roomDepth, wallMaterial); // Right wall
    createIndustrialWall(0, roomHeight, -roomDepth/2, roomWidth, 0.4, roomDepth, wallMaterial); // Ceiling
    createIndustrialWall(0, roomHeight/2, -roomDepth, roomWidth, roomHeight, 0.4, wallMaterial); // Back wall
    
    // Create matching industrial floor with grate texture
    const floorTexture = loadPersistentTexture(FLOOR_TEXTURE_URL, texture => {
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.RepeatWrapping;
        texture.minFilter = THREE.NearestFilter;
        texture.magFilter = THREE.NearestFilter;
    });
    
    // Extend floor to be larger to prevent void at edges
    const tileSize = 2;
    const extendedRoomDepth = roomDepth * 2; // Double the depth
    const extendedRoomWidth = roomWidth * 1.5; // 50% wider
    
    floorTexture.repeat.set(extendedRoomWidth/tileSize, extendedRoomDepth/tileSize);
    
    const floorGeometry = new THREE.PlaneGeometry(extendedRoomWidth, extendedRoomDepth);
    const floorMaterial = new THREE.MeshStandardMaterial({ 
        map: floorTexture,
        roughness: 0.7,
        metalness: 0.8,
        color: 0x445566 // Darker blue-gray to match walls
    });
    const floor = new THREE.Mesh(floorGeometry, floorMaterial);
    floor.rotation.x = -Math.PI / 2;
    // Position further back to cover more depth
    floor.position.set(0, 0, -roomDepth);
    floor.receiveShadow = true;
    floor.name = 'terminalFloor'; // Give it a distinct name
    scene.add(floor);
    registerCollider(floor, { ignoreCollision: true, isFloor: true });
    
    // Add a subtle blue glow under the floor
    const terminalGlowGeometry = new THREE.PlaneGeometry(3, 3);
    const terminalGlowMaterial = new THREE.MeshBasicMaterial({
        color: 0x3366aa,
        transparent: true,
        opacity: 0.3,
        side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending
    });
    const glowPlane = new THREE.Mesh(terminalGlowGeometry, terminalGlowMaterial);
    glowPlane.rotation.x = -Math.PI / 2;
    glowPlane.position.set(0, -0.1, -roomDepth/2);
    scene.add(glowPlane);
    
    // Add a subtle point light beneath
    const floorGlow = new THREE.PointLight(0x3366aa, 0.8, 5);
    floorGlow.position.set(0, -0.3, -roomDepth/2);
    scene.add(floorGlow);
    
    // Add a deeper glow spot toward the back of the terminal room
    const deepGlowGeometry = new THREE.PlaneGeometry(4, 4);
    const deepGlowMaterial = new THREE.MeshBasicMaterial({
        color: 0x4466cc,
        transparent: true,
        opacity: 0.25,
        side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending
    });
    const deepGlowPlane = new THREE.Mesh(deepGlowGeometry, deepGlowMaterial);
    deepGlowPlane.rotation.x = -Math.PI / 2;
    deepGlowPlane.position.set(0, -0.1, -roomDepth * 1.2);
    scene.add(deepGlowPlane);
    
    // Add a deep point light
    const deepGlow = new THREE.PointLight(0x4466cc, 0.6, 7);
    deepGlow.position.set(0, -0.3, -roomDepth * 1.2);
    scene.add(deepGlow);
    
    // Create terminal desk
    const deskGeometry = new THREE.BoxGeometry(4, 0.1, 2);
    const deskMaterial = new THREE.MeshStandardMaterial({
        color: 0x333333,
        metalness: 0.7,
        roughness: 0.3
    });
    const desk = new THREE.Mesh(deskGeometry, deskMaterial);
    desk.position.set(0, 1.0, -roomDepth + 2);
    scene.add(desk);
    registerCollider(desk, { isPlatform: true });
    
    // Add low-poly keyboard to the desk
    const keyboardWidth = 1.2;
    const keyboardHeight = 0.05;
    const keyboardDepth = 0.4;

    // Main keyboard body
    const keyboardGeometry = new THREE.BoxGeometry(keyboardWidth, keyboardHeight, keyboardDepth);
    const keyboardMaterial = new THREE.MeshStandardMaterial({
        color: 0x222222,
        metalness: 0.8,
        roughness: 0.2
    });
    const keyboard = new THREE.Mesh(keyboardGeometry, keyboardMaterial);
    keyboard.position.set(-0.5, 1.06, -roomDepth + 1.7); // Position on the left side of desk
    scene.add(keyboard);

    // Create keyboard keys with subtle backlight glow
    const keySize = 0.08;
    const keyHeight = 0.02;
    const keySpacing = 0.09;
    const keyRows = 4;
    const keyCols = 12;
    const keyStartX = keyboard.position.x - (keyboardWidth / 2) + (keySize / 2) + 0.04;
    const keyStartZ = keyboard.position.z - (keyboardDepth / 2) + (keySize / 2) + 0.04;

    // Key material with subtle emissive glow
    const keyMaterial = new THREE.MeshStandardMaterial({
        color: 0x333333,
        metalness: 0.5,
        roughness: 0.7,
        emissive: 0x113355, // Subtle blue glow
        emissiveIntensity: 0.4 // Low intensity for subtle effect
    });

    // Create a key grid
    for (let row = 0; row < keyRows; row++) {
        for (let col = 0; col < keyCols; col++) {
            const keyGeometry = new THREE.BoxGeometry(keySize, keyHeight, keySize);
            const key = new THREE.Mesh(keyGeometry, keyMaterial);
            
            // Position each key in the grid
            const x = keyStartX + (col * keySpacing);
            const y = keyboard.position.y + (keyboardHeight / 2) + (keyHeight / 2);
            const z = keyStartZ + (row * keySpacing);
            
            key.position.set(x, y, z);
            scene.add(key);
        }
    }

    // Add a low-poly mouse
    const mouseWidth = 0.15;
    const mouseHeight = 0.05;
    const mouseDepth = 0.25;

    // Mouse body (main part)
    const mouseBodyGeometry = new THREE.BoxGeometry(mouseWidth, mouseHeight, mouseDepth);
    const mouseMaterial = new THREE.MeshStandardMaterial({
        color: 0x222222,
        metalness: 0.7,
        roughness: 0.3
    });
    const mouseBody = new THREE.Mesh(mouseBodyGeometry, mouseMaterial);
    mouseBody.position.set(0.6, 1.06, -roomDepth + 1.7); // Position on the right side of desk
    scene.add(mouseBody);

    // Mouse buttons (left and right)
    const buttonWidth = mouseWidth / 2 - 0.01;
    const buttonHeight = 0.01;
    const buttonDepth = mouseDepth / 2 - 0.01;

    // Left mouse button
    const leftButtonGeometry = new THREE.BoxGeometry(buttonWidth, buttonHeight, buttonDepth);
    const buttonMaterial = new THREE.MeshStandardMaterial({
        color: 0x333333,
        metalness: 0.5,
        roughness: 0.5
    });
    const leftButton = new THREE.Mesh(leftButtonGeometry, buttonMaterial);
    leftButton.position.set(
        mouseBody.position.x - buttonWidth / 2,
        mouseBody.position.y + mouseHeight / 2 + buttonHeight / 2,
        mouseBody.position.z - buttonDepth / 2
    );
    scene.add(leftButton);

    // Right mouse button
    const rightButtonGeometry = new THREE.BoxGeometry(buttonWidth, buttonHeight, buttonDepth);
    const rightButton = new THREE.Mesh(rightButtonGeometry, buttonMaterial);
    rightButton.position.set(
        mouseBody.position.x + buttonWidth / 2,
        mouseBody.position.y + mouseHeight / 2 + buttonHeight / 2,
        mouseBody.position.z - buttonDepth / 2
    );
    scene.add(rightButton);

    // Mouse scroll wheel (with subtle glow)
    const scrollWheelGeometry = new THREE.CylinderGeometry(0.02, 0.02, 0.05, 8);
    const scrollWheelMaterial = new THREE.MeshStandardMaterial({
        color: 0x444444,
        metalness: 0.6,
        roughness: 0.4,
        emissive: 0x113355, // Subtle blue glow like keyboard
        emissiveIntensity: 0.3
    });
    const scrollWheel = new THREE.Mesh(scrollWheelGeometry, scrollWheelMaterial);
    scrollWheel.rotation.x = Math.PI / 2; // Rotate to align with mouse
    scrollWheel.position.set(
        mouseBody.position.x,
        mouseBody.position.y + mouseHeight / 2 + 0.02,
        mouseBody.position.z - mouseDepth / 4
    );
    scene.add(scrollWheel);

    // Subtle illumination from keyboard
    const keyboardGlow = new THREE.PointLight(0x3366ff, 0.2, 0.5);
    keyboardGlow.position.set(
        keyboard.position.x,
        keyboard.position.y + 0.1,
        keyboard.position.z
    );
    scene.add(keyboardGlow);
    
    // Create terminal screen with enhanced brightness
    const screenGeometry = new THREE.PlaneGeometry(3.5, 2);
    const screenMaterial = new THREE.MeshStandardMaterial({
        color: 0x000000,
        emissive: 0x33aaff,  // Brighter blue color
        emissiveIntensity: 1.2,  // Much higher intensity
        side: THREE.DoubleSide  // Render both sides to avoid orientation issues
    });
    const screen = new THREE.Mesh(screenGeometry, screenMaterial);
    screen.position.set(0, 2.0, -roomDepth + 1);
    // Ensure screen rotation is set to default (facing forward)
    screen.rotation.set(0, 0, 0);
    screen.name = 'terminal-screen';
    
    // Make the screen interactable with both keyboard and mouse/touch
    screen.userData.isInteractive = true;
    screen.userData.activateTerminal = () => {
        const screenDistance = character ? character.position.distanceTo(screen.position) : Infinity;
        if (screenDistance < 3) {
            openTerminalInterface();
        }
    };
    
    scene.add(screen);
    terminalScreenMesh = screen;
    
    // Instead of using complex multi-layered glow effects, use a simpler approach
    // Create a self-illuminated plane for the screen glow that entirely surrounds the screen
    const glowGeometry = new THREE.PlaneGeometry(4.0, 2.5); // Larger than the screen
    const glowMaterial = new THREE.MeshBasicMaterial({
        color: 0x33aaff,
        transparent: true,
        opacity: 0.5,
        blending: THREE.AdditiveBlending,
        side: THREE.DoubleSide,
        depthWrite: false // Prevents z-fighting and ensures visibility
    });
    
    // Position the glow slightly behind the screen to ensure it doesn't get cut off
    const screenGlow = new THREE.Mesh(glowGeometry, glowMaterial);
    screenGlow.position.set(
        screen.position.x,
        screen.position.y,
        screen.position.z - 0.01 // Slightly behind the screen
    );
    screenGlow.rotation.copy(screen.rotation);
    scene.add(screenGlow);
    
    // Store reference for animation
    screen.userData.glowSprite = screenGlow;
    screen.userData.terminalActive = false; // Track if terminal is active
    
    // Create back portal
    createSimplePortal(
        0, 1, -1, // Near the entrance
        "Back",
        null,
        0xffdd22, // Yellow for room transition
        ['all'],
        'main' // Return to main room
    );
    
    // Create terminal interface overlay
    if (terminalInterface && terminalInterface.parentNode) {
        terminalInterface.parentNode.removeChild(terminalInterface);
    }
    terminalInterface = document.createElement('div');
    terminalInterface.id = 'terminal-interface';
    terminalInterface.style.display = 'none';
    terminalInterface.style.position = 'fixed';
    terminalInterface.style.top = '50%';
    terminalInterface.style.left = '50%';
    terminalInterface.style.transform = 'translate(-50%, -50%)';
    terminalInterface.style.width = '80%';
    terminalInterface.style.maxWidth = '800px';
    terminalInterface.style.backgroundColor = 'rgba(0, 20, 40, 0.95)';
    terminalInterface.style.border = '2px solid #66ffaa';
    terminalInterface.style.borderRadius = '10px';
    terminalInterface.style.padding = '20px';
    terminalInterface.style.color = '#66ffaa';
    terminalInterface.style.fontFamily = 'monospace';
    terminalInterface.style.zIndex = '1000';
    terminalInterface.style.boxShadow = '0 0 20px rgba(102, 255, 170, 0.3)';
    
    // Create iframe for reports interface
    const reportsFrame = document.createElement('iframe');
    reportsFrame.src = '/core/reports/';
    reportsFrame.style.width = '100%';
    reportsFrame.style.height = '600px';
    reportsFrame.style.border = 'none';
    reportsFrame.style.backgroundColor = 'rgba(0, 20, 40, 0.95)';
    reportsFrame.setAttribute('sandbox', 'allow-same-origin allow-scripts allow-forms');
    
    terminalInterface.appendChild(reportsFrame);
    
    // Add close button
    const closeButton = document.createElement('button');
    closeButton.textContent = 'EXIT TERMINAL';
    closeButton.style.position = 'absolute';
    closeButton.style.top = '10px';
    closeButton.style.right = '10px';
    closeButton.style.backgroundColor = 'rgba(10, 20, 30, 0.8)';
    closeButton.style.color = '#66ffaa';
    closeButton.style.border = '1px solid #66ffaa';
    closeButton.style.borderRadius = '0';
    closeButton.style.clipPath = 'polygon(0 0, 100% 0, 95% 50%, 100% 100%, 0 100%, 5% 50%)';
    closeButton.style.padding = '10px 18px';
    closeButton.style.fontFamily = 'monospace';
    closeButton.style.fontWeight = 'bold';
    closeButton.style.letterSpacing = '1px';
    closeButton.style.textShadow = '0 0 5px #66ffaa';
    closeButton.style.boxShadow = '0 0 10px rgba(102, 255, 170, 0.5)';
    closeButton.style.transition = 'all 0.2s ease';
    closeButton.style.cursor = 'pointer';
    closeButton.style.zIndex = '1001';
    
    closeButton.onclick = () => {
        closeTerminalInterface();
    };
    
    terminalInterface.appendChild(closeButton);
    sceneContainer.appendChild(terminalInterface);
    
    // Add interaction prompt
    if (terminalPrompt && terminalPrompt.parentNode) {
        terminalPrompt.parentNode.removeChild(terminalPrompt);
    }
    terminalPrompt = document.createElement('div');
    terminalPrompt.id = 'terminal-prompt';
    terminalPrompt.style.position = 'fixed';
    terminalPrompt.style.bottom = '20%';
    terminalPrompt.style.left = '50%';
    terminalPrompt.style.transform = 'translateX(-50%)';
    terminalPrompt.style.color = '#66ffaa';
    terminalPrompt.style.fontFamily = 'monospace';
    terminalPrompt.style.fontSize = '18px';
    terminalPrompt.style.textShadow = '0 0 10px rgba(102, 255, 170, 0.5)';
    terminalPrompt.style.display = 'none';
    terminalPrompt.style.pointerEvents = 'none';
    terminalPrompt.innerHTML = 'Press E or click screen to interact';
    sceneContainer.appendChild(terminalPrompt);

    ensureJumpButtonPresence();
    markDebugOverlayDirty();
}

// Handle room transitions
function transitionToRoom(roomId) {
    console.log("🔍 [FLOOR_DEBUG] transitionToRoom() - Starting transition to:", roomId, "from:", currentRoom);
    
    if (roomTransitionInProgress) return;
    roomTransitionInProgress = true;

    const previousCharacterPosition = character ? character.position.clone() : null;
    
    console.log('Beginning room transition:', {
        from: currentRoom,
        to: roomId,
        previousRoom: previousRoom
    });
    
    // Find the portal that triggered this transition
    const transitionPortal = navLinks.find(portal => portal.userData.roomId === roomId);
    // Determine transition type based on portal color
    const transitionType = transitionPortal && transitionPortal.material.color.getHex() === 0xffdd22 ? 'vignette' : 'rectangle';
    const entryPortalTransform = transitionPortal ? {
        position: transitionPortal.position.clone(),
        quaternion: transitionPortal.quaternion.clone()
    } : null;
    let portalForwardHint = null;
    if (entryPortalTransform && previousCharacterPosition) {
        portalForwardHint = entryPortalTransform.position.clone().sub(previousCharacterPosition);
        if (portalForwardHint.lengthSq() <= 0.0001) {
            portalForwardHint = null;
        }
    }
    pendingEntryRotation = entryPortalTransform ? computeEntryFacingRotation(entryPortalTransform, portalForwardHint) : null;
    pendingApplyRoomEntry = true;
    
    // Start the portal transition animation with appropriate type
    portalTransition.startTransition(transitionType);
    
    // After transition animation starts
    setTimeout(() => {
        // Store previous room
        previousRoom = currentRoom;
        currentRoom = roomId;
        
        console.log("🔍 [FLOOR_DEBUG] transitionToRoom() - After animation start, currentRoom set to:", currentRoom);
        
        // Properly clear everything and reset scene
        clearRoomObjects();
        
        console.log("🔍 [FLOOR_DEBUG] transitionToRoom() - After clearRoomObjects, creating new room:", currentRoom);
        
        // Verify character exists in new scene
        if (!character) {
            // If character doesn't exist, create it
            character = new THREE.Group();
            scene.add(character);
            resetJumpState();
            
            // Attempt to load the beer can model
            loadBeerCan();
        } else {
            // Reset jump state and movement tracking before relocating
            resetJumpState();
            direction.set(0, 0, 0);
            moveForward = false;
            moveBackward = false;
            moveLeft = false;
            moveRight = false;
        }

        // Create the new room with a small delay
        setTimeout(() => {
            if (roomId === 'main') {
                console.log("🔍 [FLOOR_DEBUG] transitionToRoom() - Creating main room");
                // Ensure the main room data exists
                if (!roomData['main'] || !roomData['main'].links || !roomData['main'].links.length) {
                    // Try to recover by getting links again
                    const navigationLinks = [];
                    createDefaultNavigationLinks(navigationLinks);
                    roomData['main'] = {
                        links: navigationLinks,
                        parentRoom: null
                    };
                }
                
                // Re-setup lighting for the main scene
                setupMainSceneLighting();
                
                // Recreate main room
                createMainRoom(roomData['main'].links);
            } else {
                console.log("🔍 [FLOOR_DEBUG] transitionToRoom() - Creating submenu room:", roomId);
                // Create submenu room
                createSubmenuRoom(roomId);
            }
            
            applyRoomEntryPosition();

            // Complete the transition
            portalTransition.endTransition(transitionType);
            
            // Reset transition flag after animation completes
            setTimeout(() => {
                roomTransitionInProgress = false;
                console.log("🔍 [FLOOR_DEBUG] transitionToRoom() - Transition complete to:", currentRoom);
                
                // Check what floors exist in the scene now
                const floors = scene.children.filter(child => 
                    child.name === 'mainGround' || 
                    child.name === 'submenuFloor' || 
                    child.name === 'terminalFloor'
                );
                
                console.log("🔍 [FLOOR_DEBUG] transitionToRoom() - Current floors in scene:", 
                    floors.map(floor => ({ name: floor.name, position: floor.position }))
                );
                
            }, 800);
        }, 100);
    }, 400); // Shortened from 800 to match the timing used by the Misc. Reports portal
}

// Create a simple portal (door) with enhanced glow effects
function createSimplePortal(x, y, z, label, url, color, requiredGroups, roomId) {
    const doorWidth = 2.2; // Width with padding from createWallWithDoorways
    const doorHeight = 3.2; // Must match the door opening height
    const portalCenterY = (typeof y === 'number') ? y : doorHeight / 2 + 0.4;
    
    // Special case for Misc. Reports portal (handled by shared vortex styling now)
    const isMiscReports = (label === "Misc. Reports" && url === "/core/reports");
    
    const portalGeometry = new THREE.BoxGeometry(doorWidth, doorHeight, 0.1);
    const portalMaterial = new THREE.MeshStandardMaterial({
        color: color,
        transparent: true,
        opacity: 0.8,
        emissive: color,
        emissiveIntensity: 1.2,
        metalness: 0.2,
        roughness: 0.3
    });

    const portalTextures = createPortalVortexTextures(label, color);
    portalMaterial.map = portalTextures.vortexTexture;
    portalMaterial.emissiveMap = portalTextures.vortexTexture;
    portalMaterial.emissive = new THREE.Color(color);
    portalMaterial.transparent = true;
    portalMaterial.opacity = 0.85;
    portalMaterial.needsUpdate = true;
    
    const portal = new THREE.Mesh(portalGeometry, portalMaterial);
    portal.position.set(x, portalCenterY, z);
    portal.userData = {
        isPortal: true,
        label: label,
        url: url,
        requiredGroups: requiredGroups,
        roomId: roomId || null // Store room ID for transition
    };
    
    if (isMiscReports) {
        portal.userData.isSpecialPortal = true;
    }
    
    scene.add(portal);
    navLinks.push(portal);
    
    // Add a glow effect aligned to the wall (planes avoid camera-facing tilt)
    const spriteMap = loadPersistentTexture(SPRITE_TEXTURE_URL, configureGlowTexture);
    const spriteMaterial = new THREE.MeshBasicMaterial({ 
        map: spriteMap,
        color: color,
        transparent: true,
        opacity: 0.6,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        depthTest: true,
        polygonOffset: true,
        polygonOffsetFactor: -1,
        polygonOffsetUnits: -1
    });
    const glowSprite = new THREE.Mesh(new THREE.PlaneGeometry(2.6, doorHeight + 0.4), spriteMaterial);
    glowSprite.position.set(x, portalCenterY, z - 0.05); // Match portal position
    
    // Tag sprite as special if for Misc. Reports
    if (isMiscReports) {
        glowSprite.userData.isSpecialPortalSprite = true;
    }
    
    scene.add(glowSprite);
    
    // Add subtle edge glow with a second, larger plane for depth
    const edgeGlowMaterial = spriteMaterial.clone();
    edgeGlowMaterial.opacity = 0.3;
    const edgeGlowSprite = new THREE.Mesh(new THREE.PlaneGeometry(3.2, 4), edgeGlowMaterial);
    edgeGlowSprite.position.set(x, portalCenterY + 1.5, z - 0.1); // Match portal position
    
    // Tag edge sprite as special if for Misc. Reports
    if (isMiscReports) {
        edgeGlowSprite.userData.isSpecialPortalSprite = true;
    }
    
    scene.add(edgeGlowSprite);

    const rimMaterial = new THREE.MeshBasicMaterial({
        map: portalTextures.rimTexture,
        transparent: true,
        opacity: 0.9,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        depthTest: true,
        polygonOffset: true,
        polygonOffsetFactor: -1,
        polygonOffsetUnits: -1
    });
    const rimMesh = new THREE.Mesh(new THREE.PlaneGeometry(doorWidth + 0.6, doorHeight + 0.8), rimMaterial);
    rimMesh.position.set(x, portalCenterY, z + 0.06);
    scene.add(rimMesh);

    portal.userData.portalVortex = {
        vortexTexture: portalTextures.vortexTexture,
        rimTexture: portalTextures.rimTexture,
        vortexSpeed: 0.15,
        rimSpeed: 0.08,
        rimMesh: rimMesh
    };
    
    // Create a physical sign for the portal (instead of HTML)
    createPortalSign(portal, label, color);
    
    return portal;
}

// Create a physical 3D sign for the portal with enhanced lighting
function createPortalSign(portal, label, color) {
    // Create sign backing
    const signWidth = 1.8; // Slightly smaller than portal width (2)
    const signHeight = 0.7;
    const signDepth = 0.05;
    
    // Calculate position (top of door)
    const portalPos = portal.position;
    const doorHeight = portal.geometry && portal.geometry.parameters && portal.geometry.parameters.height
        ? portal.geometry.parameters.height
        : 5;
    // Position the sign at the top of the door with a small gap
    const signY = portalPos.y + doorHeight / 2 + signHeight / 2 + 0.1;
    
    // Create sign backing with emissive edge for glow effect
    const signGeometry = new THREE.BoxGeometry(signWidth, signHeight, signDepth);
    const signMaterial = new THREE.MeshStandardMaterial({
        color: 0x111111, // Dark background for sign
        metalness: 0.3,
        roughness: 0.7,
        emissive: 0x222222,
        emissiveIntensity: 0.6 // Increased glow to compensate for removed light
    });
    
    const sign = new THREE.Mesh(signGeometry, signMaterial);
    // Position the sign directly on the portal
    sign.position.set(portalPos.x, signY, portalPos.z + 0.08); // Slightly in front of portal
    scene.add(sign);
    
    // Use a plane so the glow stays aligned to the wall (sprites always face the camera)
    const spriteMap = loadPersistentTexture(SPRITE_TEXTURE_URL, configureGlowTexture);
    const glowMaterial = new THREE.MeshBasicMaterial({
        map: spriteMap,
        color: color,
        transparent: true,
        opacity: 0.4,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        depthTest: true,
        polygonOffset: true,
        polygonOffsetFactor: -1,
        polygonOffsetUnits: -1
    });

    const signGlow = new THREE.Mesh(new THREE.PlaneGeometry(2, 0.8), glowMaterial);
    signGlow.position.set(portalPos.x, signY, portalPos.z + 0.15);
    scene.add(signGlow);
    
    // Create text for the sign using HTML overlay with fixed position
    const labelElement = document.createElement('div');
    const labelId = `portal-label-${label.replace(/\s+/g, '-').toLowerCase()}-${Date.now().toString(36)}`;
    labelElement.id = labelId;
    labelElement.textContent = label;
    labelElement.style.position = 'absolute';
    labelElement.style.color = '#ffffff';
    labelElement.style.backgroundColor = 'transparent';
    labelElement.style.padding = '5px';
    labelElement.style.fontFamily = 'Arial, sans-serif';
    labelElement.style.fontSize = '14px';
    labelElement.style.fontWeight = 'bold';
    labelElement.style.textAlign = 'center';
    labelElement.style.pointerEvents = 'none';
    labelElement.style.zIndex = '5';
    labelElement.style.width = '180px'; // Fixed width
    labelElement.style.transform = 'translate(-50%, -50%)'; // Center text
    
    // Set color based on portal color - enhanced glow effect
    const colorObj = new THREE.Color(color);
    const r = Math.floor(colorObj.r * 255);
    const g = Math.floor(colorObj.g * 255);
    const b = Math.floor(colorObj.b * 255);
    labelElement.style.textShadow = `0 0 5px rgb(${r}, ${g}, ${b}), 0 0 10px rgb(${r}, ${g}, ${b}), 0 0 15px rgb(${r}, ${g}, ${b})`; // Added third layer for more intense glow
    
    sceneContainer.appendChild(labelElement);
    
    // Store reference to DOM element and its ID
    sign.userData.labelElement = labelElement;
    sign.userData.labelId = labelId;
    sign.userData.portalRef = portal;
    portal.userData.signRef = sign;
    
    // Add sign to array for position updates
    if (!window.portalSigns) window.portalSigns = [];
    window.portalSigns.push(sign);
    
    return sign;
}

// Create a room
function createRoom(x, y, z, width, height, depth, color) {
    const wallGeometry = new THREE.BoxGeometry(width, height, depth);
    const wallMaterial = new THREE.MeshStandardMaterial({ color: color });
    const wall = new THREE.Mesh(wallGeometry, wallMaterial);
    wall.position.set(x, y, z);
    wall.castShadow = true;
    wall.receiveShadow = true;
    
    scene.add(wall);
    registerCollider(wall);
}

function updateVerticalMovement(delta) {
    if (!character || !velocity) return;

    jumpBufferTimer = Math.max(0, jumpBufferTimer - delta);
    const groundHeight = getGroundHeightAt(character.position.x, character.position.z);
    const targetY = groundHeight + CHARACTER_BASE_HEIGHT;

    if (isGrounded) {
        coyoteTimer = COYOTE_TIME;
    } else {
        coyoteTimer = Math.max(0, coyoteTimer - delta);
    }

    const wantsJump = jumpBufferTimer > 0;

    velocity.y -= GRAVITY * delta;
    character.position.y += velocity.y * delta;

    if (character.position.y <= targetY + GROUND_SNAP_EPSILON) {
        if (character.position.y < targetY) {
            character.position.y = targetY;
        }
        if (velocity.y < 0) {
            velocity.y = 0;
        }
        if (!isGrounded) {
            isGrounded = true;
            canJump = true;
        }
    } else if (isGrounded) {
        isGrounded = false;
        canJump = false;
    }

    if (wantsJump && (isGrounded || coyoteTimer > 0)) {
        velocity.y = JUMP_SPEED;
        character.position.y = targetY + 0.02;
        isGrounded = false;
        canJump = false;
        coyoteTimer = 0;
        jumpBufferTimer = 0;
    }
}

// Add global variables for rotation control - enhanced with adaptive turn speed
let currentRotation = 0;
let targetRotation = 0;
const baseRotationSpeed = 4.0; // Base rotation speed (lower = slower)
const maxRotationSpeed = 7.0;  // Maximum rotation speed for large turns
const minAngleForSpeedBoost = 1.0; // Radians (~57 degrees) where speed boost starts

// Animation loop
function animate() {
    requestAnimationFrame(animate);
    
    const delta = clock.getDelta();
    
    // Update any animations from the GLTF model
    if (mixer) {
        mixer.update(delta);
    }
    
    // Update character position
    const speed = isSprinting ? SPEED_SPRINT : SPEED_NORMAL;
    
    // Reversed direction.z to fix forward/backward movement
    direction.z = Number(moveBackward) - Number(moveForward);
    direction.x = Number(moveRight) - Number(moveLeft);
    
    // Don't normalize if no movement (avoids NaN)
    if (direction.x !== 0 || direction.z !== 0) {
        direction.normalize();
    }
    
    // If using joystick (mobile), also fix joystick direction
    if (joystickActive) {
        direction.z = joystickDelta.y;
        direction.x = joystickDelta.x;
    }
    
    // Apply movement with collision handling
    if (moveForward || moveBackward || moveLeft || moveRight || joystickActive) {
        const currentX = character.position.x;
        const currentZ = character.position.z;
        
        let nextX = currentX;
        let nextZ = currentZ;
        
        const attemptedX = currentX + direction.x * speed * delta;
        if (!wouldCollide(attemptedX, currentZ)) {
            nextX = attemptedX;
        }
        
        const attemptedZ = currentZ + direction.z * speed * delta;
        if (!wouldCollide(nextX, attemptedZ)) {
            nextZ = attemptedZ;
        }
        
        character.position.x = nextX;
        character.position.z = nextZ;
        
        // Face character in movement direction if we actually moved
        if (direction.x !== 0 || direction.z !== 0) {
            // Calculate the target rotation based on movement direction
            targetRotation = Math.atan2(direction.x, direction.z);
        }
    } else {
        // When no movement keys are pressed, stop all rotation
        // This ensures rotation stops immediately when keys are released
        targetRotation = currentRotation;
    }
    
    if (currentRotation !== targetRotation) {
        // Calculate the shortest angle distance
        let angleDiff = targetRotation - currentRotation;
        
        // Ensure we rotate the shortest way
        if (angleDiff > Math.PI) angleDiff -= Math.PI * 2;
        if (angleDiff < -Math.PI) angleDiff += Math.PI * 2;
        
        // Calculate adaptive turn speed based on angle magnitude
        const angleMagnitude = Math.abs(angleDiff);
        let adaptiveSpeed = baseRotationSpeed;
        
        // For larger turns, gradually increase the rotation speed
        if (angleMagnitude > minAngleForSpeedBoost) {
            // Scale speed between base and max speed based on angle size
            const speedFactor = Math.min(1.0, (angleMagnitude - minAngleForSpeedBoost) / (Math.PI - minAngleForSpeedBoost));
            adaptiveSpeed = baseRotationSpeed + (maxRotationSpeed - baseRotationSpeed) * speedFactor;
        }
        
        // Apply smooth interpolation based on delta time and adaptive speed
        if (Math.abs(angleDiff) > 0.01) {
            currentRotation += angleDiff * Math.min(1.0, adaptiveSpeed * delta);
            
            // Normalize the angle to stay within -PI to PI
            if (currentRotation > Math.PI) currentRotation -= Math.PI * 2;
            if (currentRotation < -Math.PI) currentRotation += Math.PI * 2;
        } else {
            // Close enough, snap to target to avoid tiny perpetual rotations
            currentRotation = targetRotation;
        }
        
        // Apply the interpolated rotation
        character.rotation.y = currentRotation;
    }
    
    updateVerticalMovement(delta);
    
    // Camera follows character height
    camera.position.x = character.position.x;
    camera.position.z = character.position.z + 5;
    camera.position.y = character.position.y + 2.5;
    camera.lookAt(character.position);
    
    // Update 2D labels for portals
    updatePortalLabels();
    
    // Check for portal proximity
    checkPortalProximity();

    // Update portal vortex animations
    navLinks.forEach(portal => {
        const vortex = portal.userData.portalVortex;
        if (!vortex) {
            return;
        }

        vortex.vortexTexture.rotation += delta * vortex.vortexSpeed;
        vortex.rimTexture.rotation -= delta * vortex.rimSpeed;
    });
    
    // Check for terminal screen proximity and handle glow animation
    const screen = terminalScreenMesh && terminalScreenMesh.parent ? terminalScreenMesh : null;
    const prompt = terminalPrompt;
    if (screen && prompt) {
        const screenDistance = character.position.distanceTo(screen.position);
        
        // Update prompt display
        if (screenDistance < 3 && !screen.userData.terminalActive) {
            prompt.style.display = 'block';
            
            // Only animate the glow when terminal is not active
            if (screen.userData.glowSprite && !screen.userData.terminalActive) {
                // Use a pulsing animation for the glow
                const glowOpacity = 0.3 + Math.sin(Date.now() * 0.005) * 0.2; // Pulsing between 0.1 and 0.5
                screen.userData.glowSprite.material.opacity = glowOpacity;
                
                // Change the screen's emissive intensity as well for a more pronounced effect
                if (screen.material && screen.material.emissiveIntensity) {
                    screen.material.emissiveIntensity = 0.8 + Math.sin(Date.now() * 0.005) * 0.4; // Pulsing between 0.4 and 1.2
                    screen.material.needsUpdate = true;
                }
            }
        } else {
            prompt.style.display = 'none';
            
            // If terminal is active, set fixed glow values (no animation)
            if (screen.userData.glowSprite) {
                if (screen.userData.terminalActive) {
                    // Fixed bright glow when terminal is active
                    screen.userData.glowSprite.material.opacity = 0.7;
                    
                    if (screen.material && screen.material.emissiveIntensity) {
                        screen.material.emissiveIntensity = 1.2; // Fixed bright value
                        screen.material.needsUpdate = true;
                    }
                } else if (screenDistance >= 3) {
                    // Turn off glow effect when not in proximity and terminal not active
                    screen.userData.glowSprite.material.opacity = 0.1;
                    
                    // Reset screen emissive intensity
                    if (screen.material && screen.material.emissiveIntensity) {
                        screen.material.emissiveIntensity = 0.5;
                        screen.material.needsUpdate = true;
                    }
                }
            }
        }
    } else if (prompt) {
        prompt.style.display = 'none';
    }
    
    // Update special portal animations (legacy Misc. Reports effect)
    scene.traverse(object => {
        if (object.userData.isSpecialPortal && !object.userData.portalVortex) {
            // Update animation time
            object.userData.portalAnimation.time += delta * object.userData.portalAnimation.speed;
            
            // Create swirling color effect using noise texture offset and color interpolation
            const time = object.userData.portalAnimation.time;
            
            // Offset noise texture for flowing effect
            if (object.material && object.material.map) {
                object.material.map.offset.x = Math.sin(time * 0.2) * 0.2;
                object.material.map.offset.y = Math.cos(time * 0.3) * 0.2;
                object.material.emissiveMap.offset.x = object.material.map.offset.x;
                object.material.emissiveMap.offset.y = object.material.map.offset.y;
            }
            
            // Interpolate between yellow and blue
            const ratio = (Math.sin(time) + 1) * 0.5; // 0 to 1 value
            object.userData.portalAnimation.currentColor.copy(object.userData.portalAnimation.baseColor1)
                .lerp(object.userData.portalAnimation.baseColor2, ratio);
            
            // Apply color to portal
            if (object.material) {
                object.material.emissive.copy(object.userData.portalAnimation.currentColor);
                object.material.needsUpdate = true;
            }
            
            // Update associated sprites with same color
            scene.traverse(sprite => {
                if (sprite.userData.isSpecialPortalSprite) {
                    sprite.material.color.copy(object.userData.portalAnimation.currentColor);
                }
            });
        }
    });

    updateDebugOverlayPositions();
    
    // Direct rendering without post-processing for better performance
    if (renderer && scene && camera) {
        if (debugSelectionHelper) {
            debugSelectionHelper.update();
        }
        renderer.render(scene, camera);
    }
}

// Update portal label positions in 2D - modified to handle sign labels with fixed positions
function updatePortalLabels() {
    if (!window.portalSigns) return;
    
    window.portalSigns.forEach(sign => {
        if (sign.userData.labelElement && sign.userData.portalRef) {
            // Get the sign's position
            const position = new THREE.Vector3();
            position.copy(sign.position);
            
            // Project to screen space
            position.project(camera);
            
            // Convert to CSS coordinates
            const x = (position.x * 0.5 + 0.5) * window.innerWidth;
            const y = (1 - (position.y * 0.5 + 0.5)) * window.innerHeight;
            
            // Update label position
            sign.userData.labelElement.style.left = x + 'px';
            sign.userData.labelElement.style.top = y + 'px';
            
            // Hide label if portal is behind camera
            const isBehindCamera = position.z > 1;
            sign.userData.labelElement.style.display = isBehindCamera ? 'none' : 'block';
        }
    });
}

// Handler for successful model load
function handleSuccessfulLoad(gltf) {
    console.log('BeerCan model loaded successfully', gltf);
    
    // Add the model to our character group
    const model = gltf.scene;
    
    // Scale the model appropriately (this value should be 0.1, 0.1, .01 don't change it don't touch it don't even think about it)
    model.scale.set(0.1, 0.1, 0.1);
    
    // Ensure model casts shadows and enhance visibility with targeted lighting
    model.traverse((object) => {
        if (object.isMesh) {
            object.castShadow = true;
            object.receiveShadow = true;
            
            // Subtle enhancement to material properties - preserve texture
            if (object.material) {
                // Use a very subtle emissive glow that won't wash out textures
                object.material.emissive = new THREE.Color(0x111111); // Very subtle warm glow
                object.material.emissiveIntensity = 0.2; // Low intensity to preserve texture
                
                // Subtle material enhancements that won't overpower texture
                if (object.material.metalness !== undefined) {
                    // For Standard material - preserve reflectivity without washing out
                    object.material.metalness = 0.6; // Less metallic to preserve texture
                    object.material.roughness = 0.4; // More roughness to show texture detail
                } else {
                    // For Phong material fallback
                    object.material.shininess = 30; // Lower shininess preserves texture
                    object.material.specular = new THREE.Color(0x333333); // Subtle specular
                }
                
                // Make sure the material updates properly
                object.material.needsUpdate = true;
            }
        }
    });
    
    // Create a softer rim light for better visibility without washing out texture
    const canLight = new THREE.PointLight(0xffffff, 0.7, 1);
    canLight.position.set(0.3, 0.7, 0.5); // Position for rim lighting effect
    character.add(canLight); // Add to character group so it moves with the can
    
    // Add a second, more subtle light from below for dimension
    const fillLight = new THREE.PointLight(0x6699cc, 0.3, 1);
    fillLight.position.set(-0.3, 0.2, -0.3); // Position for fill lighting
    character.add(fillLight);
    
    // Center the model based on its bounding box
    const box = new THREE.Box3().setFromObject(model);
    const center = box.getCenter(new THREE.Vector3());
    model.position.x = -center.x;
    model.position.z = -center.z;
    
    // Adjust the Y position to ensure model sits on the ground
    const height = box.max.y - box.min.y;
    model.position.y = -box.min.y - 0.9;
    
    // Add model to character group
    character.add(model);
    
    // Check for animations
    if (gltf.animations && gltf.animations.length) {
        mixer = new THREE.AnimationMixer(model);
        gltf.animations.forEach((clip) => {
            mixer.clipAction(clip).play();
        });
    }
}

// Handler for load errors
function handleLoadError(error) {
    console.error('Error parsing BeerCan model:', error);
    createFallbackCube();
}

// Helper function to monitor floor changes in the scene
function monitorFloorChanges() {
    console.log("🔍 [FLOOR_DEBUG] Starting floor monitoring");
    
    // Store references to the original scene.add and scene.remove methods
    const originalSceneAdd = scene.add;
    const originalSceneRemove = scene.remove;
    
    // Override scene.add to detect when floors are added
    scene.add = function(object) {
        // Call the original method
        const result = originalSceneAdd.call(this, object);
        
        // Check if the added object is a floor
        if (object.name === 'mainGround' || object.name === 'submenuFloor' || object.name === 'terminalFloor') {
            console.log(`🔍 [FLOOR_DEBUG] FLOOR ADDED: ${object.name}`, {
                position: object.position,
                dimensions: object.geometry ? {
                    width: object.geometry.parameters.width,
                    height: object.geometry.parameters.height
                } : 'unknown',
                addedBy: new Error().stack
            });
        }
        
        return result;
    };
    
    // Override scene.remove to detect when floors are removed
    scene.remove = function(object) {
        // Check if the removed object is a floor
        if (object && (object.name === 'mainGround' || object.name === 'submenuFloor' || object.name === 'terminalFloor')) {
            console.log(`🔍 [FLOOR_DEBUG] FLOOR REMOVED: ${object.name}`, {
                position: object.position,
                removedBy: new Error().stack
            });
        }
        
        // Call the original method
        return originalSceneRemove.call(this, object);
    };
    
    console.log("🔍 [FLOOR_DEBUG] Floor monitoring initialized");
}

// Call this function early in the init process to start monitoring
const originalInit = init;
init = function() {
    const result = originalInit.apply(this, arguments);
    monitorFloorChanges();
    return result;
};
