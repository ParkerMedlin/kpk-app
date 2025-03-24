// The 3D Navigation Portal for KPK-App

// Since dynamic imports aren't working reliably with Django's static file system,
// we'll use the pre-bundled Three.js that's already loaded

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

// DOM elements
const loadingScreen = document.getElementById('loading-screen');
const sceneContainer = document.getElementById('scene-container');
const tooltip = document.getElementById('tooltip');
let joystick; // Will be created dynamically
let joystickKnob; // Will be created dynamically

// User permissions based on groups (will be populated from Django)
let userGroups = [];

// Create global variables for post-processing
let composer;

// Setup fullscreen button handler
document.addEventListener("DOMContentLoaded", function() {
    // Perform mobile detection again to ensure it works in all browsers
    isMobile = window.matchMedia("(max-width: 1024px)").matches || 
        (('ontouchstart' in window) || (navigator.maxTouchPoints > 0) || (navigator.msMaxTouchPoints > 0));
    
    const fullscreenButton = document.getElementById('fullscreenButton');
    if (fullscreenButton) {
        fullscreenButton.addEventListener('click', toggleFullscreen);
        
        // Add double-click handler to set return-on-exit attribute
        fullscreenButton.addEventListener('dblclick', function() {
            if (this.hasAttribute('data-return-on-exit')) {
                this.removeAttribute('data-return-on-exit');
                // Show brief feedback
                const originalBackground = this.style.backgroundColor;
                this.style.backgroundColor = 'rgba(0, 150, 0, 0.7)';
                setTimeout(() => {
                    this.style.backgroundColor = originalBackground;
                }, 300);
            } else {
                this.setAttribute('data-return-on-exit', 'true');
                // Show brief feedback
                const originalBackground = this.style.backgroundColor;
                this.style.backgroundColor = 'rgba(150, 0, 0, 0.7)';
                setTimeout(() => {
                    this.style.backgroundColor = originalBackground;
                }, 300);
            }
        });
    }
    
    if (window.THREE) {
        // Initialize the scene
        initWithThree(window.THREE);
    } else {
        document.getElementById('loading-text').textContent = 
            "Error: THREE.js not found. Please check browser console for details.";
    }
});

// Toggle fullscreen mode
function toggleFullscreen() {
    const container = document.getElementById('scene-container');
    
    if (!document.fullscreenElement) {
        // Enter fullscreen
        if (container.requestFullscreen) {
            container.requestFullscreen();
        } else if (container.mozRequestFullScreen) { // Firefox
            container.mozRequestFullScreen();
        } else if (container.webkitRequestFullscreen) { // Chrome, Safari and Opera
            container.webkitRequestFullscreen();
        } else if (container.msRequestFullscreen) { // IE/Edge
            container.msRequestFullscreen();
        }
        
        // Update icon to show exit fullscreen
        updateFullscreenButtonIcon(true);
        
        // Ensure the joystick remains visible in fullscreen mode if on mobile device
        if (isMobile) {
            setTimeout(() => {
                const joystickElement = document.getElementById('joystick');
                if (joystickElement) {
                    joystickElement.style.display = 'block';
                    joystickElement.style.zIndex = '9999'; // Ensure it's above other elements
                }
            }, 300); // Short delay to ensure it happens after fullscreen transition
        }
    } else {
        // Exit fullscreen
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.mozCancelFullScreen) {
            document.mozCancelFullScreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen();
        }
        
        // Update icon to show enter fullscreen
        updateFullscreenButtonIcon(false);
    }
}

// Update fullscreen button icon based on state
function updateFullscreenButtonIcon(isFullscreen) {
    const fullscreenButton = document.getElementById('fullscreenButton');
    if (!fullscreenButton) return;
    
    if (isFullscreen) {
        // Show exit fullscreen icon
        fullscreenButton.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                <path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z"/>
            </svg>
        `;
    } else {
        // Show enter fullscreen icon
        fullscreenButton.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
            </svg>
        `;
    }
}

// Listen for fullscreen change events
document.addEventListener('fullscreenchange', function() {
    updateFullscreenButtonIcon(!!document.fullscreenElement);
    
    // Ensure joystick is still visible in fullscreen mode if on a touch device
    if (document.fullscreenElement && isMobile) {
        // Make sure joystick is visible when in fullscreen mode
        const joystickElement = document.getElementById('joystick');
        if (joystickElement) {
            joystickElement.style.display = 'block';
            // Also ensure joystick is in a visible position
            joystickElement.style.bottom = '20px';
            joystickElement.style.left = '20px';
            joystickElement.style.zIndex = '9999'; // Higher z-index to ensure visibility
            // Force update of joystick position after fullscreen transition
            setTimeout(() => {
                if (joystick) {
                    joystickRect = joystick.getBoundingClientRect();
                }
            }, 300); // Wait for fullscreen transition to complete
        }
    }
    
    // If exiting fullscreen and the button has a data attribute to return to normal, do so
    if (!document.fullscreenElement && fullscreenButton.hasAttribute('data-return-on-exit')) {
        window.location.href = '/';
    }
});

document.addEventListener('webkitfullscreenchange', function() {
    updateFullscreenButtonIcon(!!document.fullscreenElement);
    
    // Also handle joystick visibility for webkit browsers
    if (document.webkitFullscreenElement && isMobile) {
        const joystickElement = document.getElementById('joystick');
        if (joystickElement) {
            joystickElement.style.display = 'block';
            joystickElement.style.bottom = '20px';
            joystickElement.style.left = '20px';
            joystickElement.style.zIndex = '9999';
        }
    }
});

document.addEventListener('mozfullscreenchange', function() {
    updateFullscreenButtonIcon(!!document.mozFullScreenElement);
    
    // Also handle joystick visibility for firefox
    if (document.mozFullScreenElement && isMobile) {
        const joystickElement = document.getElementById('joystick');
        if (joystickElement) {
            joystickElement.style.display = 'block';
            joystickElement.style.bottom = '20px';
            joystickElement.style.left = '20px';
            joystickElement.style.zIndex = '9999';
        }
    }
});

document.addEventListener('MSFullscreenChange', function() {
    updateFullscreenButtonIcon(!!document.msFullscreenElement);
    
    // Also handle joystick visibility for IE/Edge
    if (document.msFullscreenElement && isMobile) {
        const joystickElement = document.getElementById('joystick');
        if (joystickElement) {
            joystickElement.style.display = 'block';
            joystickElement.style.bottom = '20px';
            joystickElement.style.left = '20px';
            joystickElement.style.zIndex = '9999';
        }
    }
});

// Initialize with globally available THREE
function initWithThree(THREE) {
    // Create raycaster and mouse objects
    raycaster = new THREE.Raycaster();
    mouse = new THREE.Vector2();
    velocity = new THREE.Vector3();
    direction = new THREE.Vector3();
    joystickDelta = new THREE.Vector2();
    
    // Create scene
    init(THREE);
}

// Create and configure the scene
function init(THREE) {
    // Create scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x000000); // Dark background for industrial feel
    
    // Create atmospheric fog effect - reduced density for better visibility
    scene.fog = new THREE.FogExp2(0x0a2933, 0.025); // Reduced from 0.035 to 0.025
    
    // Create clock for animations
    clock = new THREE.Clock();
    
    // Create camera
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(0, 1.6, 5); // Eye level for character
    
    // Create renderer
    renderer = new THREE.WebGLRenderer({ 
        antialias: true,
        powerPreference: "high-performance"
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2)); // Limit pixel ratio for performance
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap; // Better shadow quality
    // Update deprecated properties with modern equivalents
    renderer.outputColorSpace = THREE.SRGBColorSpace; // Modern replacement for outputEncoding
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    sceneContainer.appendChild(renderer.domElement);
    
    // Enhanced Lighting for industrial Mako feel - INCREASED BRIGHTNESS
    // Ambient light increased for better overall illumination
    const ambientLight = new THREE.AmbientLight(0x3a4a6a, 0.6); // Changed color to blueish and increased intensity from 0.3 to 0.6
    scene.add(ambientLight);
    
    // Main directional light with bluish tint - increased intensity
    const directionalLight = new THREE.DirectionalLight(0x6680cc, 0.7); // Changed color to more vibrant blue and increased from 0.4 to 0.7
    directionalLight.position.set(10, 10, 10);
    directionalLight.castShadow = true;
    directionalLight.shadow.mapSize.width = 2048;
    directionalLight.shadow.mapSize.height = 2048;
    scene.add(directionalLight);
    
    // Add enhanced atmospheric reactor lights
    addReactorLights();
    
    // Create industrial flooring
    const floorTexture = new THREE.TextureLoader().load('https://cdn.jsdelivr.net/gh/mrdoob/three.js@r152/examples/textures/hardwood2_diffuse.jpg');
    floorTexture.wrapS = THREE.RepeatWrapping;
    floorTexture.wrapT = THREE.RepeatWrapping;
    floorTexture.repeat.set(5, 5);
    
    const groundGeometry = new THREE.PlaneGeometry(100, 100);
    const groundMaterial = new THREE.MeshStandardMaterial({ 
        map: floorTexture,
        roughness: 0.8,
        metalness: 0.2,
        color: 0x666666 // Tint the texture darker
    });
    const ground = new THREE.Mesh(groundGeometry, groundMaterial);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    ground.name = 'mainGround'; // Give it a name to find it later
    scene.add(ground);
    
    // Create a simple character (cube placeholder)
    // In a full implementation, you would load a character model here
    const characterGeometry = new THREE.BoxGeometry(0.5, 1.8, 0.5);
    const characterMaterial = new THREE.MeshStandardMaterial({ color: 0xff0000 });
    character = new THREE.Mesh(characterGeometry, characterMaterial);
    character.position.set(0, 0.9, 0);
    character.castShadow = true;
    scene.add(character);
    
    // Position camera slightly behind character
    camera.position.set(0, 2.5, 5);
    
    // Create controls
    setupControls();
    
    // Add event listeners
    window.addEventListener('resize', onWindowResize, false);
    window.addEventListener('mousemove', onMouseMove, false);
    window.addEventListener('click', onMouseClick, false);
    
    // Setup joystick for mobile and tablets
    if (isMobile) {
        setupJoystick();
        setupSprintButton();
    } else {
        // Also setup touch controls for touch-capable devices that might not be detected as mobile
        if ('ontouchstart' in window || navigator.maxTouchPoints > 0 || navigator.msMaxTouchPoints > 0) {
            setupJoystick();
            setupSprintButton();
        }
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

// Setup character controls
function setupControls() {
    document.addEventListener('keydown', onKeyDown, false);
    document.addEventListener('keyup', onKeyUp, false);
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
            if (canJump) {
                velocity.y = 10;
                canJump = false;
            }
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
        case 'ArrowUp':
        case 'KeyW':
            moveForward = false;
            break;
            
        case 'ArrowDown':
        case 'KeyS':
            moveBackward = false;
            break;
            
        case 'ArrowLeft':
        case 'KeyA':
            moveLeft = false;
            break;
            
        case 'ArrowRight':
        case 'KeyD':
            moveRight = false;
            break;
            
        case 'ShiftLeft':
        case 'ShiftRight':
            isSprinting = false;
            break;
    }
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
    // Use raycaster to check if we clicked on a nav link
    raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(navLinks);
    
    if (intersects.length > 0) {
        const link = intersects[0].object;
        if (link.userData.url) {
            // Redirect to the target URL
            window.location.href = link.userData.url;
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
    
    // Make sure the joystick is visible
    joystick.style.display = 'block';
    
    const getJoystickPosition = (event) => {
        // Always get fresh position of joystick container
            joystickRect = joystick.getBoundingClientRect();
        
        let clientX, clientY;
        
        if (event.touches) {
            clientX = event.touches[0].clientX;
            clientY = event.touches[0].clientY;
        } else {
            clientX = event.clientX;
            clientY = event.clientY;
        }
        
        const centerX = joystickRect.left + joystickRect.width / 2;
        const centerY = joystickRect.top + joystickRect.height / 2;
        
        return {
            x: clientX - centerX,
            y: clientY - centerY
        };
    };
    
    const moveJoystickKnob = (event) => {
        if (!isDragging) return;
        
        const position = getJoystickPosition(event);
        const radius = joystickRect.width / 2;
        const distance = Math.sqrt(position.x * position.x + position.y * position.y);
        
        if (distance > radius) {
            position.x = position.x * radius / distance;
            position.y = position.y * radius / distance;
        }
        
        joystickKnob.style.transform = `translate(calc(-50% + ${position.x}px), calc(-50% + ${position.y}px))`;
        
        // Calculate movement direction
        joystickDelta.x = position.x / radius;
        joystickDelta.y = position.y / radius;
    };
    
    const startDrag = (event) => {
        event.preventDefault();
        isDragging = true;
        joystickActive = true;
        moveJoystickKnob(event);
    };
    
    const endDrag = () => {
        isDragging = false;
        joystickActive = false;
        joystickKnob.style.transform = 'translate(0, 0)';
        joystickDelta.set(0, 0);
    };
    
    // Touch events
    joystick.addEventListener('touchstart', startDrag, { passive: false });
    document.addEventListener('touchmove', moveJoystickKnob, { passive: false });
    document.addEventListener('touchend', endDrag);
    
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
    
    // Create metallic wall texture - use a texture that exists
    const wallTexture = new THREE.TextureLoader().load('https://cdn.jsdelivr.net/gh/mrdoob/three.js@r152/examples/textures/brick_diffuse.jpg');
    wallTexture.wrapS = THREE.RepeatWrapping;
    wallTexture.wrapT = THREE.RepeatWrapping;
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
    
    // Create portals for each accessible link with color coding
    navigationLinks.forEach((link, index) => {
        const x = startX + index * (portalWidth + portalSpacing);
        
        // Determine color - Yellow for room transitions, Blue for direct links
        const portalColor = link.submenus && link.submenus.length > 0 ? 0xffdd22 : 0x33aaff;
        
        // If the link has submenus, create a portal to a submenu room instead of a direct URL
        if (link.submenus && link.submenus.length > 0) {
            const roomId = `room_${link.label.replace(/\s+/g, '_').toLowerCase()}`;
    createSimplePortal(
                x, 1, -19.7, // Move portal slightly forward from wall
                link.label, 
                null, // No direct URL
                portalColor, // Yellow for room transitions
                link.groups,
                roomId // Room to transition to
            );
        } else {
            // Regular portal with direct URL
    createSimplePortal(
                x, 1, -19.7, // Move portal slightly forward from wall
                link.label, 
                link.url, 
                portalColor, // Blue for direct links
                link.groups
            );
        }
        
        // Add simple pillars on each side of the portal without arches
        createPortalPillars(x, 1, -19.7, portalWidth);
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
}

// Create back wall with doorway cutouts
function createWallWithDoorways(navigationLinks, startX, portalWidth, portalSpacing, wallWidth, wallHeight, wallMaterial) {
    const wallZ = -20;
    const wallDepth = 0.4;
    const doorHeight = 3;
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
    colliders.push(wall);
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
    
    // Add a small glowing halo (sprite) instead of an actual light
    const spriteMap = new THREE.TextureLoader().load('https://cdn.jsdelivr.net/gh/mrdoob/three.js@r152/examples/textures/sprites/circle.png');
    const spriteMaterial = new THREE.SpriteMaterial({ 
        map: spriteMap,
        color: color,
        transparent: true,
        opacity: 0.6,
        blending: THREE.AdditiveBlending
    });
    
    const sprite = new THREE.Sprite(spriteMaterial);
    sprite.scale.set(0.5, 0.5, 1);
    sprite.position.set(x, y, z + 0.12);
    scene.add(sprite);
    
    return { housing, bulb, sprite };
}

// Create a submenu room with its own portals
function createSubmenuRoom(roomId) {
    // Clear existing objects except the character
    clearRoomObjects();
    
    const roomInfo = roomData[roomId];
    if (!roomInfo) {
        return;
    }
    
    const submenuLinks = roomInfo.links;
    
    // Calculate wall dimensions based on number of portals
    const portalWidth = 2; // Width of each portal
    const portalSpacing = 3; // Space between portals
    const totalPortalWidth = submenuLinks.length * portalWidth + (submenuLinks.length - 1) * portalSpacing;
    const wallPadding = 5; // Extra padding on both sides of the wall
    const wallWidth = Math.max(totalPortalWidth + wallPadding * 2, 20); // At least 20 units wide
    const wallHeight = 5; // Increased height for industrial feel
    const roomDepth = 30; // Room depth
    
    // Create metallic wall texture with different color tint for submenu rooms - use a texture that exists
    const wallTexture = new THREE.TextureLoader().load('https://cdn.jsdelivr.net/gh/mrdoob/three.js@r152/examples/textures/brick_diffuse.jpg');
    wallTexture.wrapS = THREE.RepeatWrapping;
    wallTexture.wrapT = THREE.RepeatWrapping;
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
    createSubmenuFloor(wallWidth);
    
    // Create portals for each submenu link - all blue since they are direct links
    submenuLinks.forEach((link, index) => {
        const x = startX + index * (portalWidth + portalSpacing);
        
        createSimplePortal(
            x, 1, -19.7, // Move portal slightly forward from wall
            link.label, 
            link.url, 
            0x33aaff, // Blue for direct links
            ['all'] // All submenu items should be accessible
        );
        
        // Add pillars on each side of the portal
        createPortalPillars(x, 1, -19.7, portalWidth);
    });
    
    // Create a doorway in the side wall for the "Back" portal
    const backPortalX = -wallWidth/2 + 1.5;
    const backPortalZ = -10;
    const doorHeight = 3;
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
        backPortalX, 1, backPortalZ - 0.2, // Slightly offset from wall
        "Back", 
        null, 
        0xffdd22, // Yellow for room transition
        ['all'],
        'main' // Transition back to main room
    );
    // Add pillars on each side of the back portal
    createPortalPillars(backPortalX, 1, backPortalZ - 0.2, portalWidth);
    
    // Add more atmospheric lighting specific to this room
    const submenuLight = new THREE.PointLight(0x66ffaa, 0.8, 15);
    submenuLight.position.set(0, 4, -10);
    scene.add(submenuLight);
    
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
    
    // Reset character position
    if (character) {
        character.position.set(0, 0.9, 0);
        camera.position.set(0, 2.5, 5);
    }
}

// Create submenu room's floor
function createSubmenuFloor(wallWidth) {
    // Use a texture that exists
    const floorTexture = new THREE.TextureLoader().load('https://cdn.jsdelivr.net/gh/mrdoob/three.js@r152/examples/textures/hardwood2_diffuse.jpg');
    floorTexture.wrapS = THREE.RepeatWrapping;
    floorTexture.wrapT = THREE.RepeatWrapping;
    floorTexture.repeat.set(8, 4);
    
    const floorGeometry = new THREE.PlaneGeometry(wallWidth, 20);
    const floorMaterial = new THREE.MeshStandardMaterial({ 
        map: floorTexture,
        roughness: 0.6,
        metalness: 0.8,
        color: 0x334455 // Dark blue-gray metallic
    });
    const floor = new THREE.Mesh(floorGeometry, floorMaterial);
    floor.rotation.x = -Math.PI / 2;
    floor.position.set(0, -0.01, -10); // Slightly below ground level
    floor.receiveShadow = true;
    floor.name = 'submenuFloor'; // Give the submenu floor a name
    scene.add(floor);
    colliders.push(floor);
    
    // Add some grating/grid sections to the floor
    addFloorGrating(wallWidth);
}

// Add metal grating sections to the floor
function addFloorGrating(wallWidth) {
    // Create a few sections of grating/grid on the floor
    const grateGeometry = new THREE.PlaneGeometry(3, 3);
    const grateMaterial = new THREE.MeshStandardMaterial({ 
        color: 0x222222,
        roughness: 0.5,
        metalness: 0.9,
        transparent: true,
        opacity: 0.9
    });
    
    // Add grid texture or wireframe effect
    grateMaterial.wireframe = true;
    
    // Add a few grate sections
    for (let i = 0; i < 3; i++) {
        const grate = new THREE.Mesh(grateGeometry, grateMaterial);
        grate.rotation.x = -Math.PI / 2;
        
        // Position grates at different spots on the floor
        const offsetX = (i - 1) * 5;
        grate.position.set(offsetX, 0.01, -15 + i * 2); // Slightly above the floor
        
        scene.add(grate);
    }
    
    // Add a glowing section beneath one of the grates for effect
    const glowGeometry = new THREE.PlaneGeometry(2.5, 2.5);
    const glowMaterial = new THREE.MeshStandardMaterial({ 
        color: 0x66ffaa, // Mako green
        transparent: true,
        opacity: 0.5
    });
    
    const glowPlane = new THREE.Mesh(glowGeometry, glowMaterial);
    glowPlane.rotation.x = -Math.PI / 2;
    glowPlane.position.set(5, -0.05, -15); // Below the grate
    scene.add(glowPlane);
    
    // Add a point light beneath for extra glow
    const grateLight = new THREE.PointLight(0x66ffaa, 0.8, 5);
    grateLight.position.set(5, -0.3, -15);
    scene.add(grateLight);
}

// Clear room objects except character and ground
function clearRoomObjects() {
    // First, clear all HTML overlay elements
    const portalLabels = document.querySelectorAll('[id^="portal-label-"]');
    portalLabels.forEach(el => {
        if (el && el.parentNode) {
            el.parentNode.removeChild(el);
        }
    });
    
    const roomElements = document.querySelectorAll('#main-room-welcome, #submenu-room-title');
    roomElements.forEach(el => {
        if (el && el.parentNode) {
            el.parentNode.removeChild(el);
        }
    });
    
    // Clear portal signs array first to avoid stale references
    if (window.portalSigns) {
        window.portalSigns = [];
    }
    
    // Clear navLinks array first to ensure old references are gone
    navLinks = [];
    
    // Clear colliders array
    colliders = [];
    
    // Remove all existing walls, portals, etc.
    const objectsToRemove = [];
    
    scene.traverse(object => {
        // Skip the character
        if (object === character) return;
        
        // Skip the main ground plane
        if (object.name === 'mainGround') return;
        
        // Skip lights (except for portal lights)
        if (object.isLight) {
            // Only remove point lights that might be part of portals
            if (object.isPointLight) {
                objectsToRemove.push(object);
            }
            return;
        }
        
        // Skip camera
        if (object.isCamera) return;
        
        // Mark for removal if it's a mesh, group, or other visible object
        if (object.isMesh || object.isGroup || object.isObject3D) {
            if (object !== scene) {
                objectsToRemove.push(object);
            }
        }
    });
    
    // Remove all objects
    objectsToRemove.forEach(object => {
        if (object.parent) {
            object.parent.remove(object);
            
            // If this is a portal or sign, also clear any HTML references
            if (object.userData && object.userData.labelElement) {
                const labelEl = object.userData.labelElement;
                if (labelEl && labelEl.parentNode) {
                    labelEl.parentNode.removeChild(labelEl);
                }
            }
        }
    });
}

// Handle room transitions
function transitionToRoom(roomId) {
    if (roomTransitionInProgress) return;
    roomTransitionInProgress = true;
    
    // Find the portal that triggered this transition
    const transitionPortal = navLinks.find(portal => portal.userData.roomId === roomId);
    // Determine transition type based on portal color
    const transitionType = transitionPortal && transitionPortal.material.color.getHex() === 0xffdd22 ? 'vignette' : 'rectangle';
    
    // Start the portal transition animation with appropriate type
    portalTransition.startTransition(transitionType);
    
    // After transition animation completes
    setTimeout(() => {
        // Store previous room
        previousRoom = currentRoom;
        currentRoom = roomId;
        
        // Reset character position to avoid being in walls or colliders
        if (character) {
            character.position.set(0, 0.9, 0);
            // Reset direction to avoid moving after transition
            direction.set(0, 0, 0);
            moveForward = false;
            moveBackward = false;
            moveLeft = false;
            moveRight = false;
        }
        
        // Create the new room
        if (roomId === 'main') {
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
            
            // Properly clear everything first
            clearRoomObjects();
            
            // Add a small delay to ensure everything is cleared before rebuilding
            setTimeout(() => {
                // Recreate main room
                createMainRoom(roomData['main'].links);
                
                // Update camera position to look at character
                if (camera && character) {
                    camera.position.set(character.position.x, character.position.y + 2.5, character.position.z + 5);
                    camera.lookAt(character.position);
                }
                
                // Complete the transition
                completeTransition(transitionType);
            }, 100);
        } else {
            // Create submenu room
            clearRoomObjects();
            
            // Add a small delay to ensure everything is cleared before rebuilding
            setTimeout(() => {
                createSubmenuRoom(roomId);
                
                // Update camera position to look at character
                if (camera && character) {
                    camera.position.set(character.position.x, character.position.y + 2.5, character.position.z + 5);
                    camera.lookAt(character.position);
                }
                
                // Complete the transition
                completeTransition(transitionType);
            }, 100);
        }
        
        function completeTransition(type) {
            // End the portal transition animation with appropriate type
            portalTransition.endTransition(type);
            
            // Reset transition flag after animation completes
            setTimeout(() => {
                roomTransitionInProgress = false;
            }, 800);
        }
    }, 800);
}

// Create a simple portal (door) with enhanced glow effects
function createSimplePortal(x, y, z, label, url, color, requiredGroups, roomId) {
    const doorWidth = 2.2; // Width with padding from createWallWithDoorways
    const doorHeight = 5.0; // Must match the door opening height
    
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
    
    const portal = new THREE.Mesh(portalGeometry, portalMaterial);
    portal.position.set(x, 0, z);
    portal.userData = {
        isPortal: true,
        label: label,
        url: url,
        requiredGroups: requiredGroups,
        roomId: roomId || null // Store room ID for transition
    };
    
    scene.add(portal);
    navLinks.push(portal);
    
    // OPTIMIZED: Add a sprite glow effect instead of a point light (much cheaper)
    const spriteMap = new THREE.TextureLoader().load('https://cdn.jsdelivr.net/gh/mrdoob/three.js@r152/examples/textures/sprites/circle.png');
    const spriteMaterial = new THREE.SpriteMaterial({ 
        map: spriteMap,
        color: color,
        transparent: true,
        opacity: 0.6,
        blending: THREE.AdditiveBlending
    });
    const glowSprite = new THREE.Sprite(spriteMaterial);
    glowSprite.scale.set(2.6, (doorHeight + 0.4), 1); // Slightly larger than the portal
    glowSprite.position.set(x, 0, z - 0.05); // Match portal position
    scene.add(glowSprite);
    
    // Add subtle edge glow with a second, larger sprite for depth
    const edgeGlowSprite = new THREE.Sprite(spriteMaterial);
    edgeGlowSprite.scale.set(3.2, 4, 1);
    edgeGlowSprite.position.set(x, 1.5, z - 0.1); // Match portal position
    edgeGlowSprite.material.opacity = 0.3;
    scene.add(edgeGlowSprite);
    
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
    const doorHeight = 3;
    // Position the sign at the top of the door with a small gap
    const signY =  doorHeight - (signHeight / 2) - 0.5;
    
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
    
    // OPTIMIZED: Use a sprite for the sign glow instead of a point light
    const spriteMap = new THREE.TextureLoader().load('https://cdn.jsdelivr.net/gh/mrdoob/three.js@r152/examples/textures/sprites/circle.png');
    const spriteMaterial = new THREE.SpriteMaterial({ 
        map: spriteMap,
        color: color,
        transparent: true,
        opacity: 0.4,
        blending: THREE.AdditiveBlending
    });
    
    const signGlow = new THREE.Sprite(spriteMaterial);
    signGlow.scale.set(2, 0.8, 1);
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
    colliders.push(wall);
}

// Animation loop
function animate() {
    requestAnimationFrame(animate);
    
    const delta = clock.getDelta();
    
    // Update character position
    const speed = isSprinting ? SPEED_SPRINT : SPEED_NORMAL; // Use sprinting speed when active
    
    // Reversed direction.z to fix forward/backward movement
    direction.z = Number(moveBackward) - Number(moveForward);
    direction.x = Number(moveRight) - Number(moveLeft);
    
    // Don't normalize if no movement (avoids NaN)
    if (direction.x !== 0 || direction.z !== 0) {
    direction.normalize(); // Normalize for consistent movement in all directions
    }
    
    // If using joystick (mobile), also fix joystick direction
    if (joystickActive) {
        direction.z = joystickDelta.y; // Reversed this value from -joystickDelta.y
        direction.x = joystickDelta.x;
    }
    
    // Apply movement with simplified collision detection
    if (moveForward || moveBackward || moveLeft || moveRight || joystickActive) {
        // Calculate proposed new position
        const proposedX = character.position.x + direction.x * speed * delta;
        const proposedZ = character.position.z + direction.z * speed * delta;
        
        // TEMPORARILY DISABLE ALL COLLISION DETECTION FOR DEBUGGING
        // Just apply movement directly without collision checks
        character.position.x = proposedX;
        character.position.z = proposedZ;
        
        // Face character in movement direction if we actually moved
        if (direction.x !== 0 || direction.z !== 0) {
            character.rotation.y = Math.atan2(direction.x, direction.z);
        }
        
        // Move camera to follow character
        camera.position.x = character.position.x;
        camera.position.z = character.position.z + 5; // Position camera behind character
    }
    
    // Camera follows character height
    camera.position.y = character.position.y + 2.5;
    camera.lookAt(character.position);
    
    // Update 2D labels for portals
    updatePortalLabels();
    
    // Check for portal proximity
    checkPortalProximity();
    
    // Direct rendering without post-processing for better performance
    if (renderer && scene && camera) {
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

// Check if character is near a portal
function checkPortalProximity() {
    // If transition is in progress, don't check for more portal proximity
    if (roomTransitionInProgress) return;
    
    navLinks.forEach(portal => {
        const distance = character.position.distanceTo(portal.position);
        
        // If character is very close to a portal
        if (distance < 1.5) {
            // Check if user has permission
            if (hasPermission(portal.userData.requiredGroups)) {
                if (portal.userData.roomId && portal.userData.roomId !== currentRoom) {
                    // This is a room transition portal
                    transitionToRoom(portal.userData.roomId);
                } else if (portal.userData.url) {
                    // This is a direct URL portal - start rectangle transition
                    roomTransitionInProgress = true;
                    portalTransition.startTransition('rectangle');
                    
                    // Delay the actual navigation to allow transition to play
                    setTimeout(() => {
                        window.location.href = portal.userData.url;
                    }, 600); // Slightly shorter than the full transition time to ensure smooth transition
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
            { label: 'Component Shortages', url: '/core/component-shortages' },
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
    // Create central Mako pool glow
    const poolGeometry = new THREE.CircleGeometry(3, 24);
    const poolMaterial = new THREE.MeshStandardMaterial({
        color: 0x66ffaa,
        emissive: 0x66ffaa,
        emissiveIntensity: 0.8,
        transparent: true,
        opacity: 0.7,
        side: THREE.DoubleSide
    });
    
    const makoPool = new THREE.Mesh(poolGeometry, poolMaterial);
    makoPool.rotation.x = -Math.PI / 2; // Lay flat
    makoPool.position.set(0, 0.01, -20); // Slightly above floor
    scene.add(makoPool);
    
    // Add glow sprite above pool
    const glowMap = new THREE.TextureLoader().load('https://cdn.jsdelivr.net/gh/mrdoob/three.js@r152/examples/textures/sprites/circle.png');
    const glowMaterial = new THREE.SpriteMaterial({
        map: glowMap,
        color: 0x66ffaa,
        transparent: true,
        opacity: 0.4,
        blending: THREE.AdditiveBlending
    });
    
    const poolGlow = new THREE.Sprite(glowMaterial);
    poolGlow.scale.set(6, 6, 1);
    poolGlow.position.set(0, 0.5, -20);
    scene.add(poolGlow);
    
    // Add industrial orange glow for contrast (using sprites instead of lights)
    const orangeGlowMaterial = new THREE.SpriteMaterial({
        map: glowMap,
        color: 0xffaa33,
        transparent: true,
        opacity: 0.3,
        blending: THREE.AdditiveBlending
    });
    
    // Add a few orange glows to replace the removed industrial light
    const industrialGlow1 = new THREE.Sprite(orangeGlowMaterial);
    industrialGlow1.scale.set(5, 5, 1);
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

// Add a TextureLoader for centralized texture management with error handling
const textureLoader = new THREE.TextureLoader();
textureLoader.crossOrigin = 'anonymous';

// Add a loading manager to handle errors
const loadingManager = new THREE.LoadingManager();
loadingManager.onError = function(url) {
    // Load a fallback texture if the requested one fails
    return textureLoader.load('https://cdn.jsdelivr.net/gh/mrdoob/three.js@r152/examples/textures/crate.gif');
};

// Update the textureLoader to use the loading manager
textureLoader.manager = loadingManager; 