# Class of '09 Access

<div align="center">

![Accessibility: Screen Reader Supported](https://img.shields.io/badge/Accessibility-Screen%20Reader%20Ready-success?style=for-the-badge&logo=accessibility)
![Game: Class of '09](https://img.shields.io/badge/Game-Class%20of%20'09-pink?style=for-the-badge)
![Engine: Ren'Py](https://img.shields.io/badge/Engine-Ren'Py-yellow?style=for-the-badge&logo=python)
![Voice Acting: 100% Fully Voiced](https://img.shields.io/badge/Voice%20Acting-100%25%20Fully%20Voiced-purple?style=for-the-badge)

### The Complete Screen Reader Accessibility Mod for *Class of '09* & *Class of '09: The Re-Up*
*Audio choice chimes, spoken branching decisions, NVDA / SAPI screen reader integration, and dialogue history replay.*

</div>

---

## 🎮 Why Class of '09?

* **100% Full Professional Voice Acting:** Every character (Nicole, Jecka, Emily, Kelly, Jeffrey, etc.) and every line of dialogue is completely voiced by real actors!
* **Ultra-Low PC Specs:** Runs smoothly on integrated graphics (Intel HD), 2 GB RAM, and any low-end or older laptop.
* **Pure Audio Drama Experience:** Because the voice acting carries the entire story, this mod bridges the remaining visual gaps (decision points, menus, and choice navigation).

---

## ✨ Features

1. **Audio Choice Earcon**: Automatically plays a two-tone chime (`D5 -> A5`) whenever a branching choice appears on screen, alerting the player that input is required.
2. **Instant Screen Reader Speech**:
   * Bridges directly with **NVDA** via `nvdaControllerClient`.
   * Automatically falls back to **Windows SAPI5** or Ren'Py speech engine.
3. **Spoken Choice Navigation**:
   * As you press the **Up / Down Arrow** keys to navigate decisions, your screen reader announces the choice number and option text.
4. **Action Confirmation Tone**:
   * Plays a subtle confirmation click/tone when pressing `Enter` or `Space` to confirm a decision.
5. **Dialogue History Shortcut (`H`)**:
   * Press **`H`** at any time to read out who spoke last and what was said.

---

## 🚀 Installation

1. Download or copy `class09_access.rpy`.
2. Locate your game installation directory:
   * **Class of '09**: `Steam/steamapps/common/Class of '09/game/`
   * **Class of '09 - The Re-Up**: `Steam/steamapps/common/Class of '09 - The Re-Up/game/`
3. Paste `class09_access.rpy` into the `game/` folder.
4. Launch the game! Ren'Py will automatically detect and compile the mod.

---

## ⌨️ Controls

| Key | Action |
| :--- | :--- |
| **Up / Down Arrows** | Navigate through choice options (spoken by screen reader) |
| **Enter / Space** | Confirm choice selection / Advance dialogue |
| **H** | Speak the last dialogue line and character name |
| **Shift + V** | Toggle Ren'Py self-voicing TTS mode |
| **Escape** | Open / Close pause menu |
