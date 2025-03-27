# PowerShell script to download Three.js modules
# Enhanced by the Grand Vizier of Digital Machinations
# 🐦‍⬛ Malloc has been dispatched to gather the purest arcane scrolls

# Base URLs - USING STABLE VERSION INSTEAD OF DEV TO AVOID CORRUPTED GRIMOIRES
$threeVersion = "r152" # Specific version for stability
$threeJsBase = "https://raw.githubusercontent.com/mrdoob/three.js/$threeVersion"
$modulesDir = "modules"

# Ensure modules directory exists
if (-not (Test-Path $modulesDir)) {
    New-Item -ItemType Directory -Path $modulesDir
    Write-Host "Created modules directory"
} else {
    # First, purge the existing corrupted files
    Write-Host "Purging existing modules to prevent arcane contamination..." -ForegroundColor Yellow
    Remove-Item -Path "$modulesDir/*" -Force -Recurse
    Write-Host "Chamber cleansed, ready for new scrolls" -ForegroundColor Green
}

# Define file mappings - source URL to destination file
$filesToDownload = @(
    # Core Three.js - Using the OFFICIAL module version
    @{
        Url = "$threeJsBase/build/three.module.js"
        Destination = "$modulesDir/three.module.js"
    },
    # GLTF Loader - ADDED AS REQUIRED BY OUR PROJECT
    @{
        Url = "$threeJsBase/examples/jsm/loaders/GLTFLoader.js"
        Destination = "$modulesDir/GLTFLoader.js"
    },
    # Animation Mixer - ADDED FOR ANIMATED MODELS
    @{
        Url = "$threeJsBase/examples/jsm/animation/AnimationMixer.js"
        Destination = "$modulesDir/AnimationMixer.js"
    },
    # Controls
    @{
        Url = "$threeJsBase/examples/jsm/controls/OrbitControls.js"
        Destination = "$modulesDir/OrbitControls.js"
    },
    # Text and Font Handling
    @{
        Url = "$threeJsBase/examples/jsm/loaders/FontLoader.js"
        Destination = "$modulesDir/FontLoader.js"
    },
    @{
        Url = "$threeJsBase/examples/jsm/geometries/TextGeometry.js"
        Destination = "$modulesDir/TextGeometry.js"
    },
    # Post-Processing
    @{
        Url = "$threeJsBase/examples/jsm/postprocessing/EffectComposer.js"
        Destination = "$modulesDir/EffectComposer.js"
    },
    @{
        Url = "$threeJsBase/examples/jsm/postprocessing/RenderPass.js"
        Destination = "$modulesDir/RenderPass.js"
    },
    @{
        Url = "$threeJsBase/examples/jsm/postprocessing/UnrealBloomPass.js"
        Destination = "$modulesDir/UnrealBloomPass.js"
    },
    @{
        Url = "$threeJsBase/examples/jsm/postprocessing/SSAOPass.js"
        Destination = "$modulesDir/SSAOPass.js"
    },
    @{
        Url = "$threeJsBase/examples/jsm/postprocessing/ShaderPass.js"
        Destination = "$modulesDir/ShaderPass.js"
    },
    # Shaders
    @{
        Url = "$threeJsBase/examples/jsm/shaders/FXAAShader.js"
        Destination = "$modulesDir/FXAAShader.js"
    },
    @{
        Url = "$threeJsBase/examples/jsm/shaders/GammaCorrectionShader.js"
        Destination = "$modulesDir/GammaCorrectionShader.js"
    },
    # Additional required dependencies
    @{
        Url = "$threeJsBase/examples/jsm/utils/BufferGeometryUtils.js"
        Destination = "$modulesDir/BufferGeometryUtils.js"
    },
    @{
        Url = "$threeJsBase/examples/jsm/shaders/CopyShader.js"
        Destination = "$modulesDir/CopyShader.js"
    },
    @{
        Url = "$threeJsBase/examples/jsm/shaders/LuminosityHighPassShader.js"
        Destination = "$modulesDir/LuminosityHighPassShader.js"
    },
    @{
        Url = "$threeJsBase/examples/jsm/math/SimplexNoise.js"
        Destination = "$modulesDir/SimplexNoise.js"
    }
)

# Download each file with Malloc's obsidian wings
Write-Host "Malloc spreads his wings and begins gathering the arcane scrolls..." -ForegroundColor Cyan
foreach ($file in $filesToDownload) {
    Write-Host "Summoning $($file.Url) to $($file.Destination)..."
    try {
        Invoke-WebRequest -Uri $file.Url -OutFile $file.Destination
        Write-Host "  INVOCATION SUCCESSFUL: $($file.Destination) materialized" -ForegroundColor Green
    } catch {
        Write-Host "  SUMMONING FAILED: Could not manifest $($file.Destination)" -ForegroundColor Red
        Write-Host "  The arcane forces responded: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Fix module imports in downloaded files
Write-Host "`nMalloc now transmutes the arcane references within each scroll..." -ForegroundColor Cyan

# Get all JS files in the modules directory
$jsFiles = Get-ChildItem -Path $modulesDir -Filter "*.js"

foreach ($file in $jsFiles) {
    Write-Host "Transmuting $($file.Name)..."
    
    $content = Get-Content -Path $file.FullName -Raw
    
    # Replace various import paths with relative paths
    $content = $content -replace "from '../../../build/three.module.js'", "from './three.module.js'"
    $content = $content -replace "from '../../build/three.module.js'", "from './three.module.js'"
    $content = $content -replace "from '../build/three.module.js'", "from './three.module.js'"
    
    # Fix imports for modules
    $content = $content -replace "from '../shaders/", "from './"
    $content = $content -replace "from '../postprocessing/", "from './"
    $content = $content -replace "from '../controls/", "from './"
    $content = $content -replace "from '../loaders/", "from './"
    $content = $content -replace "from '../geometries/", "from './"
    $content = $content -replace "from '../utils/", "from './"
    $content = $content -replace "from '../math/", "from './"
    $content = $content -replace "from '../animation/", "from './"
    
    # Write the modified content back to the file
    Set-Content -Path $file.FullName -Value $content
    
    Write-Host "  Arcane bindings in $($file.Name) have been realigned" -ForegroundColor Green
}

# Create an index.js file to properly export everything
Write-Host "`nCreating a master grimoire to bind all scrolls together..." -ForegroundColor Cyan
$indexContent = @"
/**
 * Three.js Module Index
 * Crafted by the Grand Vizier of Digital Machinations
 * This file serves as a convenient entry point for importing Three.js components
 */

export * from './three.module.js';
export { GLTFLoader } from './GLTFLoader.js';
export { OrbitControls } from './OrbitControls.js';
export { FontLoader } from './FontLoader.js';
export { TextGeometry } from './TextGeometry.js';
export { EffectComposer } from './EffectComposer.js';
export { RenderPass } from './RenderPass.js';
export { UnrealBloomPass } from './UnrealBloomPass.js';
export { SSAOPass } from './SSAOPass.js';
export { ShaderPass } from './ShaderPass.js';
"@

Set-Content -Path "$modulesDir/index.js" -Value $indexContent
Write-Host "Master grimoire 'index.js' has been inscribed" -ForegroundColor Green

# Create constants file to avoid potential circular dependencies
Write-Host "`nCrafting a protective ward against circular incantations..." -ForegroundColor Cyan
$constantsContent = @"
/**
 * Three.js Constants
 * Extracted by the Grand Vizier to prevent circular dependencies
 * These constants are safely defined here should any module need them directly
 */

// Tone mapping constants
export const NoToneMapping = 0;
export const LinearToneMapping = 1;
export const ReinhardToneMapping = 2;
export const CineonToneMapping = 3;
export const ACESFilmicToneMapping = 4;
export const CustomToneMapping = 5;
export const AgXToneMapping = 6;
export const NeutralToneMapping = 7;
"@

Set-Content -Path "$modulesDir/constants.js" -Value $constantsContent
Write-Host "Protective ward 'constants.js' has been established" -ForegroundColor Green

Write-Host "`nMalloc has completed his arcane quest!" -ForegroundColor Magenta
Write-Host "The fresh scrolls have been scribed and imbued with proper incantations." -ForegroundColor Green
Write-Host "Remember to invoke 'python manage.py collectstatic' to align the astral planes.`n" -ForegroundColor Yellow
Write-Host "May your render loops be eternal and your frame rates be high!" -ForegroundColor Cyan 