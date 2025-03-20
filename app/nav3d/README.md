# 3D Navigation Interface for KPK-App

This app provides an immersive 3D interface for navigating the KPK-App using Three.js. 
It presents the standard navbar as a 3D environment where users can navigate between pages
by walking their character to different portals.

## Features

- Interactive 3D environment with a third-person camera view
- User-controlled character that can move through the environment
- Navigation portals representing menu items and links
- Permission-based access to portals based on user group membership
- Mobile compatibility with touch joystick controls
- Responsive design for both desktop and mobile devices

## Technical Details

- Built with Three.js for 3D rendering
- Fully integrated with Django's authentication and permission system
- Mobile-friendly with touch controls
- Uses FontLoader and TextGeometry for 3D text rendering

## How to Use

1. Navigate to `/nav3d/` to access the 3D interface
2. Use WASD or arrow keys to move your character
3. On mobile, use the on-screen joystick
4. Walk through portals to navigate to different pages
5. Use the "Return to Normal View" button to go back to the standard interface

## Development

To extend the 3D interface:

1. Modify `createNavigationPortals()` in `nav3d-interface.js` to add new portals or environments
2. Adjust portal permissions using the `requiredGroups` parameter
3. Create additional rooms or hallways with the `createRoom()` function 