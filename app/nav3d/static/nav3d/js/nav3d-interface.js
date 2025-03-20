// The 3D Navigation Portal for KPK-App

// Since dynamic imports aren't working reliably with Django's static file system,
// we'll use the pre-bundled Three.js that's already loaded

// Global variables for Three.js components we need
let scene, camera, renderer, clock, mixer;
let character, controls;
let colliders = [];
let navLinks = [];
let raycaster;
let mouse;
let isMobile = window.matchMedia("(max-width: 768px)").matches;
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
const joystick = document.getElementById('joystick');
const joystickKnob = document.getElementById('joystick-knob');

// User permissions based on groups (will be populated from Django)
let userGroups = [];

// Create global variables for post-processing
let composer;

// Initialize the scene when the document is ready
document.addEventListener("DOMContentLoaded", function() {
    if (window.THREE) {
        console.log("Using global THREE object:", window.THREE.REVISION);
        
        // Initialize the scene
        initWithThree(window.THREE);
    } else {
        console.error("THREE.js not found! Please include it as a global script in interface.html");
        document.getElementById('loading-text').textContent = 
            "Error: THREE.js not found. Please check browser console for details.";
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
    console.log("Initializing 3D scene...");
    
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
    renderer.outputEncoding = THREE.sRGBEncoding;
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
    
    // Setup joystick for mobile
    if (isMobile) {
        setupJoystick();
        setupSprintButton();
    }
    
    // Setup simple renderer for now (no post-processing)
    composer = {
        render: function() {
            renderer.render(scene, camera);
        },
        setSize: function(width, height) {
            // Just a stub for compatibility
        }
    };
    
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
    console.log("Setting up keyboard controls...");
    document.addEventListener('keydown', onKeyDown, false);
    document.addEventListener('keyup', onKeyUp, false);
    
    // Debug - print a message when any key is pressed
    document.addEventListener('keydown', function(event) {
        console.log("Key pressed:", event.code);
    });
}

// Handle keyboard input (keydown)
function onKeyDown(event) {
    console.log("onKeyDown triggered:", event.code);
    switch (event.code) {
        case 'ArrowUp':
        case 'KeyW':
            console.log("moveForward set to true");
            moveForward = true;
            break;
            
        case 'ArrowDown':
        case 'KeyS':
            console.log("moveBackward set to true");
            moveBackward = true;
            break;
            
        case 'ArrowLeft':
        case 'KeyA':
            console.log("moveLeft set to true");
            moveLeft = true;
            break;
            
        case 'ArrowRight':
        case 'KeyD':
            console.log("moveRight set to true");
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
            console.log("isSprinting set to true");
            isSprinting = true;
            break;
    }
}

// Handle keyboard input (keyup)
function onKeyUp(event) {
    console.log("onKeyUp triggered:", event.code);
    switch (event.code) {
        case 'ArrowUp':
        case 'KeyW':
            console.log("moveForward set to false");
            moveForward = false;
            break;
            
        case 'ArrowDown':
        case 'KeyS':
            console.log("moveBackward set to false");
            moveBackward = false;
            break;
            
        case 'ArrowLeft':
        case 'KeyA':
            console.log("moveLeft set to false");
            moveLeft = false;
            break;
            
        case 'ArrowRight':
        case 'KeyD':
            console.log("moveRight set to false");
            moveRight = false;
            break;
            
        case 'ShiftLeft':
        case 'ShiftRight':
            console.log("isSprinting set to false");
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
    let joystickRect;
    let isDragging = false;
    
    const getJoystickPosition = (event) => {
        if (!joystickRect) {
            joystickRect = joystick.getBoundingClientRect();
        }
        
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
        
        joystickKnob.style.transform = `translate(${position.x}px, ${position.y}px)`;
        
        // Calculate movement direction
        joystickDelta.x = position.x / radius;
        joystickDelta.y = position.y / radius;
    };
    
    const startDrag = (event) => {
        event.preventDefault();
        isDragging = true;
        joystickRect = joystick.getBoundingClientRect();
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
    console.log("Creating dynamic navigation portals from existing navbar...");
    
    // Log the user groups to confirm they've been fetched before creating portals
    console.log(`Current user groups when creating portals:`, userGroups);
    
    // Store all navigation links that will be created
    const navigationLinks = [];
    
    // Extract navigation data from the actual navbar in the DOM
    const navbar = document.getElementById('navbarToggle');
    if (!navbar) {
        console.error("Navbar element (#navbarToggle) not found! Falling back to default links.");
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
        
        console.log(`Extracted ${navigationLinks.length} navigation links from DOM navbar`);
    }
    
    // If no links were found in the navbar, create default links
    if (navigationLinks.length === 0) {
        console.warn("No navigation links found in navbar, using defaults");
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
        
        // Add decoration/arch around the portal
        decoratePortal(x, 0, -19.7, 0, link.label);
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
    
    // Create light bulb
    const bulbGeometry = new THREE.SphereGeometry(0.1, 16, 16);
    const bulbMaterial = new THREE.MeshStandardMaterial({
        color: 0xff9500,
        emissive: 0xff9500,
        emissiveIntensity: 1.0
    });
    
    const bulb = new THREE.Mesh(bulbGeometry, bulbMaterial);
    bulb.position.set(x, y, z + 0.1); // Position slightly in front of housing
    scene.add(bulb);
    
    // Add point light
    const warningLight = new THREE.PointLight(color, 0.8, 3);
    warningLight.position.set(x, y, z + 0.15);
    scene.add(warningLight);
    
    // Set up blinking
    let isOn = true;
    setInterval(() => {
        isOn = !isOn;
        bulbMaterial.opacity = isOn ? 1 : 0.1;
        warningLight.intensity = isOn ? 0.8 : 0;
    }, 1000 + Math.random() * 500); // Random blink timing
    
    return { housing, bulb, light: warningLight };
}

// Create a submenu room with its own portals
function createSubmenuRoom(roomId) {
    // Clear existing objects except the character
    clearRoomObjects();
    
    const roomInfo = roomData[roomId];
    if (!roomInfo) {
        console.error(`Room data not found for ${roomId}`);
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
        
        // Add decoration/arch around the portal
        decoratePortal(x, 0, -19.7, 0, link.label);
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
    decoratePortal(backPortalX, 0, backPortalZ - 0.2, Math.PI / 2, "Back");
    
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
    
    console.log("Created submenu floor");
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
    console.log("Clearing room objects");
    
    // First, clear all HTML overlay elements
    const portalLabels = document.querySelectorAll('[id^="portal-label-"]');
    portalLabels.forEach(el => {
        if (el && el.parentNode) {
            console.log(`Removing portal label: ${el.id}`);
            el.parentNode.removeChild(el);
        }
    });
    
    const roomElements = document.querySelectorAll('#main-room-welcome, #submenu-room-title');
    roomElements.forEach(el => {
        if (el && el.parentNode) {
            console.log(`Removing room element: ${el.id}`);
            el.parentNode.removeChild(el);
        }
    });
    
    // Clear portal signs array first to avoid stale references
    if (window.portalSigns) {
        console.log(`Clearing ${window.portalSigns.length} portal signs`);
        window.portalSigns = [];
    }
    
    // Clear navLinks array first to ensure old references are gone
    console.log(`Clearing ${navLinks.length} nav links`);
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
    
    console.log(`Found ${objectsToRemove.length} objects to remove`);
    
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
    
    console.log("Room clearing complete");
}

// Handle room transitions
function transitionToRoom(roomId) {
    if (roomTransitionInProgress) return;
    roomTransitionInProgress = true;
    
    console.log(`Transitioning from ${currentRoom} to ${roomId}`);
    
    // Create a fade overlay
    const fadeOverlay = document.createElement('div');
    fadeOverlay.style.position = 'fixed';
    fadeOverlay.style.top = '0';
    fadeOverlay.style.left = '0';
    fadeOverlay.style.width = '100%';
    fadeOverlay.style.height = '100%';
    fadeOverlay.style.backgroundColor = '#000';
    fadeOverlay.style.opacity = '0';
    fadeOverlay.style.transition = 'opacity 0.5s';
    fadeOverlay.style.zIndex = '1000';
    document.body.appendChild(fadeOverlay);
    
    // Fade out
    setTimeout(() => {
        fadeOverlay.style.opacity = '1';
    }, 10);
    
    // After fade out completes
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
                console.error("Main room data is missing or invalid!", roomData);
                // Try to recover by getting links again
                const navigationLinks = [];
                createDefaultNavigationLinks(navigationLinks);
                roomData['main'] = {
                    links: navigationLinks,
                    parentRoom: null
                };
            }
            
            console.log("Recreating main room with links:", roomData['main'].links.length);
            
            // Properly clear everything first
            clearRoomObjects();
            
            // Add a small delay to ensure everything is cleared before rebuilding
            setTimeout(() => {
                // Recreate main room
                createMainRoom(roomData['main'].links);
                console.log(`Main room recreation complete, created ${navLinks.length} portals`);
                
                // Update camera position to look at character
                if (camera && character) {
                    camera.position.set(character.position.x, character.position.y + 2.5, character.position.z + 5);
                    camera.lookAt(character.position);
                }
                
                // Complete the transition
                completeTransition();
            }, 100);
        } else {
            // Create submenu room
            console.log(`Creating submenu room: ${roomId}`);
            clearRoomObjects();
            
            // Add a small delay to ensure everything is cleared before rebuilding
            setTimeout(() => {
                createSubmenuRoom(roomId);
                console.log(`Submenu room creation complete, created ${navLinks.length} portals`);
                
                // Update camera position to look at character
                if (camera && character) {
                    camera.position.set(character.position.x, character.position.y + 2.5, character.position.z + 5);
                    camera.lookAt(character.position);
                }
                
                // Complete the transition
                completeTransition();
            }, 100);
        }
        
        function completeTransition() {
            // Fade in
            setTimeout(() => {
                fadeOverlay.style.opacity = '0';
                
                // Remove overlay after fade completes
                setTimeout(() => {
                    if (fadeOverlay.parentNode) {
                        fadeOverlay.parentNode.removeChild(fadeOverlay);
                    }
                    roomTransitionInProgress = false;
                    console.log(`Transition to ${roomId} complete with ${navLinks.length} portals and ${window.portalSigns ? window.portalSigns.length : 0} signs`);
                }, 500);
            }, 100);
        }
    }, 500);
}

// Create a simple portal (door) with enhanced glow effects
function createSimplePortal(x, y, z, label, url, color, requiredGroups, roomId) {
    // Door dimensions - ensure consistent sizing
    const doorWidth = 2;
    const doorHeight = 3;
    
    const portalGeometry = new THREE.BoxGeometry(doorWidth, doorHeight, 0.1);
    const portalMaterial = new THREE.MeshStandardMaterial({ 
        color: color,
        transparent: true,
        opacity: 0.8,
        emissive: color,
        emissiveIntensity: 0.5, // Increased from 0.3 for brighter glow
        metalness: 0.2,
        roughness: 0.3
    });
    
    const portal = new THREE.Mesh(portalGeometry, portalMaterial);
    portal.position.set(x, y, z);
    portal.userData = {
        isPortal: true,
        label: label,
        url: url,
        requiredGroups: requiredGroups,
        roomId: roomId || null // Store room ID for transition
    };
    
    scene.add(portal);
    navLinks.push(portal);
    
    // Add a point light at the portal for enhanced glow effect
    const portalLight = new THREE.PointLight(color, 0.8, 5); // Add light source at each portal
    portalLight.position.set(x, y, z - 0.2);
    scene.add(portalLight);
    
    // Create a physical sign for the portal (instead of HTML)
    createPortalSign(portal, label, color);
}

// Implement the decoratePortal function with enhanced lighting
function decoratePortal(x, y, z, rotationY, label) {
    // --- DOOR ARCH --- 
    const archMaterial = new THREE.MeshPhysicalMaterial({
        color: 0x808080,
        roughness: 0.7,
        metalness: 0.2,
        clearcoat: 0.1
    });

    // Door dimensions
    const doorWidth = 2;
    const doorHeight = 3;
    
    // Archway parameters - adjust for proper door size
    const archSegments = 8;
    const archRadius = doorWidth / 2; // Half the door width
    const archThickness = 0.2;  // Thickness of each arch piece
    const archDepth = 0.3;      // Depth of each arch piece
    
    // Calculate top of the door as the starting point for the arch
    const doorTop = doorHeight / 2; // Position relative to door center
    
    // Create arch container to group segments
    const archContainer = new THREE.Group();

    for (let i = 0; i <= archSegments; i++) {
        // Calculate position on a half-circle (0 to π)
        const angle = (Math.PI / archSegments) * i;
        
        // Position each segment along the semi-circle
        const segX = Math.sin(angle) * archRadius;
        const segY = Math.cos(angle) * archRadius;
        
        const archPiece = new THREE.Mesh(
            new THREE.BoxGeometry(archThickness, archThickness, archDepth),
            archMaterial
        );
        
        // Position based on orientation (forward or side-facing)
        if (rotationY === 0 || rotationY === Math.PI) {
            // Forward/backward facing portal
            archPiece.position.set(segX, doorTop + segY, 0);
        } else {
            // Side-facing portal
            archPiece.position.set(0, doorTop + segY, segX);
        }
        
        archContainer.add(archPiece);
    }

    // Add the entire arch group to the scene with proper position
    archContainer.position.set(x, y, z);
    archContainer.rotation.y = rotationY;
    scene.add(archContainer);
    
    // Add enhanced light near the top of the arch for dramatic effect
    const archLight = new THREE.PointLight(0xffffff, 0.8, 5); // Increased from 0.5 to 0.8 for brightness
    archLight.position.set(x, y + doorTop + archRadius * 0.8, z - 0.2);
    scene.add(archLight);
    
    // Optionally, create small pillars on each side of the door for a more complete look
    createPortalPillar(x - doorWidth/2 - archThickness/2, y, z, archThickness, doorHeight, archDepth, archMaterial);
    createPortalPillar(x + doorWidth/2 + archThickness/2, y, z, archThickness, doorHeight, archDepth, archMaterial);
}

// Create a physical 3D sign for the portal with enhanced lighting
function createPortalSign(portal, label, color) {
    // Create sign backing
    const signWidth = 1.8; // Slightly smaller than portal width (2)
    const signHeight = 0.6;
    const signDepth = 0.05;
    
    // Calculate position (top third of door)
    const portalPos = portal.position.clone();
    const signY = portalPos.y + 0.9; // Position at top third of door height (door is 3 units tall)
    
    // Create sign backing
    const signGeometry = new THREE.BoxGeometry(signWidth, signHeight, signDepth);
    const signMaterial = new THREE.MeshStandardMaterial({
        color: 0x111111, // Dark background for sign
        metalness: 0.3,
        roughness: 0.7,
        emissive: 0x111111,
        emissiveIntensity: 0.2 // Slight glow for the sign itself
    });
    
    const sign = new THREE.Mesh(signGeometry, signMaterial);
    sign.position.set(portalPos.x, signY, portalPos.z - 0.08); // Slightly in front of portal
    scene.add(sign);
    
    // Add a glow around the sign
    const signLightColor = new THREE.Color(color);
    const signLight = new THREE.PointLight(signLightColor, 0.5, 3);
    signLight.position.set(portalPos.x, signY, portalPos.z - 0.3);
    scene.add(signLight);
    
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

// Animation loop - add debugging prints for movement
function animate() {
    requestAnimationFrame(animate);
    
    const delta = clock.getDelta();
    
    // Update character position
    const speed = isSprinting ? SPEED_SPRINT : SPEED_NORMAL; // Use sprinting speed when active
    
    // Reversed direction.z to fix forward/backward movement
    direction.z = Number(moveBackward) - Number(moveForward);
    direction.x = Number(moveRight) - Number(moveLeft);
    
    // Add debug logging for movement variables
    if (moveForward || moveBackward || moveLeft || moveRight) {
        console.log("Movement state:", { 
            moveForward, 
            moveBackward, 
            moveLeft, 
            moveRight,
            directionX: direction.x,
            directionZ: direction.z
        });
    }
    
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
        
        console.log("Character moved to:", character.position);
    }
    
    // Camera follows character height
    camera.position.y = character.position.y + 2.5;
    camera.lookAt(character.position);
    
    // Update 2D labels for portals
    updatePortalLabels();
    
    // Check for portal proximity
    checkPortalProximity();
    
    // Safely call composer.render if it exists
    if (composer && typeof composer.render === 'function') {
        composer.render();
    } else {
        // Fallback if composer is not properly initialized
        if (renderer && scene && camera) {
    renderer.render(scene, camera);
        }
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
                    console.log(`Portal proximity triggered for ${portal.userData.label} to room ${portal.userData.roomId}`);
                    transitionToRoom(portal.userData.roomId);
                } else if (portal.userData.url) {
                    // This is a direct URL portal
                window.location.href = portal.userData.url;
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
        console.error('User data element not found');
        return;
    }
    
    // Default group for all users
    userGroups = ['all'];
    
    // Check authentication status
    const isAuthenticated = userData.getAttribute('data-is-authenticated') === 'true';
    if (!isAuthenticated) {
        // Not authenticated, only 'all' group available
        console.log('User is not authenticated, using default group "all"');
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
    
    console.log('User groups:', userGroups);
    
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
    // Add blue-green point lights around the area for a Mako feel - increased intensity
    const makoLight1 = new THREE.PointLight(0x66ffaa, 1.2, 20); // Increased intensity from 0.8 to 1.2 and range from 15 to 20
    makoLight1.position.set(-8, 3, -15);
    scene.add(makoLight1);
    
    const makoLight2 = new THREE.PointLight(0x33ccff, 1.0, 25); // Increased intensity from 0.6 to 1.0 and range from 20 to 25
    makoLight2.position.set(8, 4, -18);
    scene.add(makoLight2);
    
    // Add dim yellow-orange industrial lights - increased brightness
    const industrialLight1 = new THREE.PointLight(0xffaa33, 0.8, 15); // Increased intensity from 0.5 to 0.8 and range from 10 to 15
    industrialLight1.position.set(0, 5, -5);
    scene.add(industrialLight1);
    
    // Add additional spotlights to highlight key areas
    // Spotlight for the central area
    const centralSpotlight = new THREE.SpotLight(0x4488ff, 1.0, 30, Math.PI / 6, 0.5, 1);
    centralSpotlight.position.set(0, 10, -10);
    centralSpotlight.target.position.set(0, 0, -15);
    scene.add(centralSpotlight);
    scene.add(centralSpotlight.target);
    
    // Add pulsing light effect for dramatic ambiance
    const pulsingLight = new THREE.PointLight(0x66ffaa, 1.5, 20);
    pulsingLight.position.set(0, 2, -25);
    scene.add(pulsingLight);
    
    // Enhanced flicker and pulse effects for more dynamic lighting
    let time = 0;
    setInterval(() => {
        time += 0.1;
        // Flicker effect for first light
        makoLight1.intensity = 1.0 + Math.sin(time * 5) * 0.2;
        
        // Pulse effect for central mako energy
        pulsingLight.intensity = 1.2 + Math.sin(time) * 0.5;
    }, 100);
}

// Create a pillar for the sides of the portal
function createPortalPillar(x, y, z, width, height, depth, material) {
    const pillar = new THREE.Mesh(
        new THREE.BoxGeometry(width, height, depth),
        material
    );
    pillar.position.set(x, y, z);
    scene.add(pillar);
}

// Add a TextureLoader for centralized texture management with error handling
const textureLoader = new THREE.TextureLoader();
textureLoader.crossOrigin = 'anonymous';

// Add a loading manager to handle errors
const loadingManager = new THREE.LoadingManager();
loadingManager.onError = function(url) {
    console.error('Error loading texture:', url);
    // Load a fallback texture if the requested one fails
    return textureLoader.load('https://cdn.jsdelivr.net/gh/mrdoob/three.js@r152/examples/textures/crate.gif');
};

// Update the textureLoader to use the loading manager
textureLoader.manager = loadingManager; 