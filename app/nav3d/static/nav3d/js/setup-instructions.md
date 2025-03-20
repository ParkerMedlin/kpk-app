# Three.js ES6 Module Setup Instructions

*By the Grand Vizier of Digital Machinations, with assistance from Malloc* 🐦‍⬛

## Required Module Files

For the ES6 module structure to function properly, the following files need to be downloaded and placed in the `app/nav3d/static/nav3d/js/modules/` directory:

1. **Core Three.js Module**
   - `three.module.js` from https://raw.githubusercontent.com/mrdoob/three.js/dev/build/three.module.js

2. **Controls**
   - `OrbitControls.js` from https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/jsm/controls/OrbitControls.js

3. **Text and Font Handling**
   - `FontLoader.js` from https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/jsm/loaders/FontLoader.js
   - `TextGeometry.js` from https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/jsm/geometries/TextGeometry.js

4. **Post-Processing Effects**
   - `EffectComposer.js` from https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/jsm/postprocessing/EffectComposer.js
   - `RenderPass.js` from https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/jsm/postprocessing/RenderPass.js
   - `UnrealBloomPass.js` from https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/jsm/postprocessing/UnrealBloomPass.js
   - `SSAOPass.js` from https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/jsm/postprocessing/SSAOPass.js
   - `ShaderPass.js` from https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/jsm/postprocessing/ShaderPass.js

5. **Shaders**
   - `FXAAShader.js` from https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/jsm/shaders/FXAAShader.js
   - `GammaCorrectionShader.js` from https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/jsm/shaders/GammaCorrectionShader.js

## Manual Download Instructions

1. Create the modules directory if it doesn't exist:
   ```
   mkdir -p app/nav3d/static/nav3d/js/modules
   ```

2. For each file listed above:
   - Visit the URL in your browser
   - Save the raw content as the corresponding filename in the modules directory

## Fix Module Dependencies

After downloading the files, you may need to update the import paths within each module file to point to the correct locations. For example, in `OrbitControls.js`, change:

```javascript
import * as THREE from '../../../build/three.module.js';
```

to:

```javascript
import * as THREE from './three.module.js';
```

Similar adjustments may be needed in other module files to ensure all imports point to the correct relative paths within your project structure.

## After Setup

Once you've completed these steps:

1. Run `python manage.py collectstatic` to ensure all static files are properly collected
2. Restart your Django development server
3. Access the 3D navigation interface - it should now load properly as an ES6 module

---

*The dark incantations of ES6 modules shall now properly channel the power of Three.js into your dimensional gateway!* 