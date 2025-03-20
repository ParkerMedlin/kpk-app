# PowerShell script to download Three.js modules
# Created by the Grand Vizier of Digital Machinations

# Base URLs
$threeJsBase = "https://raw.githubusercontent.com/mrdoob/three.js/dev"
$modulesDir = "modules"

# Ensure modules directory exists
if (-not (Test-Path $modulesDir)) {
    New-Item -ItemType Directory -Path $modulesDir
    Write-Host "Created modules directory"
}

# Define file mappings - source URL to destination file
$filesToDownload = @(
    # Core Three.js
    @{
        Url = "$threeJsBase/build/three.module.js"
        Destination = "$modulesDir/three.module.js"
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

# Download each file
foreach ($file in $filesToDownload) {
    Write-Host "Downloading $($file.Url) to $($file.Destination)..."
    try {
        Invoke-WebRequest -Uri $file.Url -OutFile $file.Destination
        Write-Host "  SUCCESS: Downloaded $($file.Destination)" -ForegroundColor Green
    } catch {
        Write-Host "  ERROR: Failed to download $($file.Destination)" -ForegroundColor Red
        Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Fix module imports in downloaded files
Write-Host "`nFixing module imports..." -ForegroundColor Cyan

# Get all JS files in the modules directory
$jsFiles = Get-ChildItem -Path $modulesDir -Filter "*.js"

foreach ($file in $jsFiles) {
    Write-Host "Processing $($file.Name)..."
    
    $content = Get-Content -Path $file.FullName -Raw
    
    # Replace various import paths with relative paths
    $content = $content -replace "from '../../../build/three.module.js'", "from './three.module.js'"
    $content = $content -replace "from '../../build/three.module.js'", "from './three.module.js'"
    $content = $content -replace "from '../build/three.module.js'", "from './three.module.js'"
    
    # Fix imports for shaders, etc.
    $content = $content -replace "from '../shaders/", "from './"
    $content = $content -replace "from '../postprocessing/", "from './"
    $content = $content -replace "from '../controls/", "from './"
    $content = $content -replace "from '../loaders/", "from './"
    $content = $content -replace "from '../geometries/", "from './"
    $content = $content -replace "from '../utils/", "from './"
    $content = $content -replace "from '../math/", "from './"
    
    # Write the modified content back to the file
    Set-Content -Path $file.FullName -Value $content
    
    Write-Host "  Updated imports in $($file.Name)" -ForegroundColor Green
}

Write-Host "`nAll files downloaded and imports fixed!" -ForegroundColor Green
Write-Host "Remember to run 'python manage.py collectstatic' to update your static files.`n" 