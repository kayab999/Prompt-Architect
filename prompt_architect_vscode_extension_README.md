# Prompt Architect VS Code Extension Setup

This document provides instructions on how to set up and run the VS Code extension for Prompt Architect.

## Setup Instructions

1.  **Install Node.js and npm:** Ensure you have Node.js (which includes npm) installed on your system.
2.  **Install VS Code Extension Generator (optional, for reference):**
    Open your terminal and run:
    ```bash
    npm install -g yo generator-code
    ```
    You can use this to create a basic extension structure as a reference if you want to expand the provided files.
3.  **Copy the provided files:**
    *   Copy the `package.json` and `extension.js` files into a new directory, for example, `~/prompt_architect_vscode_extension`.
4.  **Open in VS Code:** Open this new directory in VS Code.
5.  **Install dependencies:** In the VS Code terminal (Ctrl+` or View > Terminal), navigate to the extension directory and run:
    ```bash
    npm install
    ```
6.  **Run the extension:**
    *   Press `F5` to open a new Extension Development Host window. This new window will have your extension enabled.

## Important Notes:

*   The Prompt Architect backend (FastAPI sidecar) must be running. The application now uses **dynamic port allocation**. The extension will automatically discover the backend's port.
*   The `refinerModel` and `targetModel` are currently hardcoded in `extension.js`. You can modify these directly in the `extension.js` file or enhance the extension to make them configurable via VS Code settings.
