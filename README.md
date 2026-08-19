# MMOS (Massive Multiplayer Operating System)

A custom, Arch-based Linux operating system that turns the desktop into a contextual multiplayer space. Users can see and interact with the pixel-art cursors of other players in real-time, but only if they are actively using the same application or website.

## Table of Contents
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation and Building](#installation-and-building)
- [Usage](#usage)
- [Configuration](#configuration)
- [Contributing](#contributing)
- [License](#license)

## Features
*   **Contextual Multiplayer:** Cursors are only shared with users in the same active window class (e.g., both users looking at the terminal).
*   **Custom Pixel Art:** Built-in GTK graphical installer allows users to draw their own 16x16 cursor on boot.
*   **Alternative Input:** Choose between standard mouse controls or a virtual WASD keyboard-driven mouse.
*   **Privacy Controls:** Toggle visibility between "All", "Friends Only", or "Offline".
*   **Wayland Native:** Built on top of Hyprland, utilizing hardware-accelerated Cairo graphics for the transparent UI overlay.

## Architecture
This project is split into three main components:
1.  **The OS Base (`arch-profile/`):** A custom Arch Linux ISO configuration using `archiso`. Pre-configured with Hyprland and necessary Python GTK dependencies.
2.  **The Client Daemon (`client-daemon/`):** A Python script running in the background. It polls local coordinates using `hyprctl`, hashes the active window class, and renders other players using a pass-through layer shell.
3.  **The Backend Server:** A PocketBase instance handling real-time WebSockets/SSE to sync X/Y coordinates and context hashes globally.

## Prerequisites
If you are building the ISO locally instead of using GitHub Actions, you will need:
*   Docker (or Podman)
*   QEMU (for local testing)
*   Git

## Installation and Building

### Automated Build (Recommended)
This repository uses GitHub Actions to automatically compile the `.iso` file.
1. Navigate to the **Actions** tab in this repository.
2. Select the **Build MMOS Arch ISO** workflow.
3. Once the build finishes, download the `MMOS-Bootable-ISO` artifact.

### Manual Local Build
To build the OS locally using Docker:
```bash
# 1. Build the Docker image environment
sudo docker build -t mmos-builder .

# 2. Compile the ISO using the arch-profile
sudo docker run --rm --privileged -v $(pwd):/mmos-build mmos-builder
