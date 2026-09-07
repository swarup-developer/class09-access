# Class of '09 Access

<div align="center">

![Accessibility: Screen Reader Ready](https://img.shields.io/badge/Accessibility-Screen%20Reader%20Ready-success?style=for-the-badge&logo=accessibility)
![Game: Class of '09](https://img.shields.io/badge/Game-Class%20of%20'09-pink?style=for-the-badge)
![Game: The Re-Up](https://img.shields.io/badge/Game-The%20Re--Up-purple?style=for-the-badge)
![Engine: Ren'Py](https://img.shields.io/badge/Engine-Ren'Py%207-yellow?style=for-the-badge&logo=python)
![NVDA Supported](https://img.shields.io/badge/Screen%20Reader-NVDA%20%7C%20JAWS%20%7C%20SAPI5-blue?style=for-the-badge)

### Complete Screen Reader Accessibility Mod for *Class of '09* and *Class of '09: The Re-Up*
*Spoken branching choices, live dialogue announcements, full keyboard navigation, accessible save/load slots, and zero visual barriers.*

---

</div>

## ⚠️ Content Warning
*Class of '09* is a dark comedy visual novel featuring mature themes, strong profanity, drug/alcohol references, and crude humor. Recommended for mature audiences only.

---

## 📢 Community Notice

Welcome to **Class of '09 Access**! 

*Class of '09* is one of the most entertaining narrative visual novels because it features **100% full professional voice acting** for every single character and dialogue line. However, out of the box, blind and visually impaired players encounter serious roadblocks: the main menu buttons are unlabeled graphical images, branching decision points give no spoken feedback on what you are selecting, and the save/load slots are completely silent.

This mod bridges every single visual gap directly to your screen reader:
- Hooks natively into **NVDA** via `nvdaControllerClient`, with seamless fallback to **Tolk** (JAWS / SuperNova) and **Windows SAPI5**.
- Automatically speaks choice menus as you move with your arrow keys.
- Reads character names and dialogue lines in real-time as they appear on screen.
- Allows full keyboard navigation for the main menu, pause menu, save slots, and settings.
- Runs smoothly on literally any PC, laptop, or budget machine.

---

## ✨ Features

### 1. Spoken Branching Decisions
* When the game stops at a choice point, the mod announces:  
  `"Decision point. 2 choices available. 1: HUMOR THE SCHOOL TOUR, 2: DECLINE AND GO STRAIGHT TO CLASS"`
* Press **Up / Down Arrow** to move between choices. Your screen reader speaks each option cleanly (e.g. *"Choice 1 of 2: HUMOR THE SCHOOL TOUR"*).
* Press **`C`** at any time to re-hear all available choices on screen.

### 2. Live Dialogue & Narration
* Even though the game is fully voice acted, NVDA automatically speaks who is talking and what they are saying:  
  `"Nicole: God they are never funny. Its like the girls just laugh to avoid sexual assault."`
* Advancing dialogue with `Space` or `Enter` immediately cuts off the previous line and speaks the new line instantly.
* **Press `H`**: Repeats the last dialogue line and character name.
* **Press `D`**: Toggle dialogue speech on/off if you only want to hear the game's voice actors without screen reader overlap.

### 3. Accessible Main Menu & Navigation
* The game's original main menu uses graphical image buttons with no text tags. This mod replaces them with fully accessible controls.
* **The moment the game opens, the whole menu is announced aloud** ("Main Menu. 1: New Game. 2: Continue and Load Game…") — nothing is silently focused at launch, so the mod speaks instead of waiting for a keypress.
* Arrow keys speak each option as you move between them:
  * **New Game**
  * **Continue (Load Game)**
  * **Options (Preferences)**
  * **About**
  * **Exit Game**
* **Enter / Space** activates the option you are on; **Quick Number Shortcuts:** Press `1` for New Game, `2` for Continue, `3` for Options, `4` for About, `5` for Exit.
* Mouse users still hear each button on hover and select with a click.

### 4. Spoken Save & Load Slots
* When opening the Save or Load menu (`Escape`), every slot is announced with its real save time and date:  
  `"Save Slot 1: Saved on September 7, 2026 at 12:05 AM"` or `"Save Slot 2: Empty"`
* Page controls announce page numbers (`Page 1`, `Auto Saves`, `Quick Saves`, `Previous Page`, `Next Page`).

### 5. Preferences & Settings
* Easily toggle **Window** or **Fullscreen** mode.
* Navigate and adjust Scene Volume and UI Sound Volume sliders using Left/Right arrows.

---

## ⌨️ Controls & Keyboard Shortcuts

| Key | Function |
| :--- | :--- |
| **Up / Down Arrows** | Move between choice options and menu buttons |
| **Left / Right Arrows** | Adjust volume sliders / switch options |
| **Enter / Space** | Confirm choice / Select button / Advance dialogue |
| **H** | Repeat the last spoken dialogue line |
| **C** | Repeat the current decision options on screen |
| **D** | Toggle screen reader dialogue reading (voices only vs voice + TTS) |
| **1 to 5** | Quick shortcuts on the Main Menu |
| **Escape** | Open / Close Pause Menu |

> **Note:** Ren'Py's built-in self-voicing (the `V` / `Shift+V` keys) is
> permanently disabled while this mod is active. Running Ren'Py's SAPI
> voice at the same time as NVDA produces two voices speaking at once
> and makes the game read everything at high speed, so the mod keeps
> Ren'Py's TTS switched off and routes all speech through a single
> driver. All dialogue, menus, choices, and save slots are already
> spoken by this mod, so nothing is lost.

---

## 🚀 Installation Guide

### For *Class of '09*:
1. Locate your game installation directory:
   * **Steam Default:** `C:\Program Files (x86)\Steam\steamapps\common\Class of '09\`
   * **Custom / DRM-Free:** Wherever `Class_Of_09.exe` is located (e.g. `D:\game\Class of 09\`).
2. Open the **`game\`** subfolder inside the game directory.
3. Copy the following files from this repository into that **`game\`** folder:
   * `class09_access.rpy` (you can also name it `zz_class09_access.rpy`)
   * `nvdaControllerClient64.dll` & `nvdaControllerClient32.dll` (from the `lib/` folder)
   * `Tolk64.dll` & `Tolk32.dll` (from the `lib/` folder)
4. Launch `Class_Of_09.exe`. You will immediately hear NVDA announce the Main Menu!

### For *Class of '09: The Re-Up*:
* Follow the exact same steps above, placing the files into `Class of '09 - The Re-Up/game/`.

---

## 🛠️ Technical Details

* **Engine:** Ren'Py 7.5.0 (Python 2.7 runtime, 64-bit AMD64 / 32-bit i686).
* **Architecture:** Injects early via `init -999 python:` using `ctypes` bindings to direct controller client DLLs.
* **Compatibility:** Tested on Windows 10 & Windows 11 with NVDA 2024.x / 2025.x / 2026.x, JAWS, and Microsoft SAPI5.

---

## 🤝 Community & Feedback

Built with passion for accessible gaming. If you encounter any bugs, silent buttons, or have suggestions for new accessibility features, please open an issue or share your feedback on AudioGames.net!
