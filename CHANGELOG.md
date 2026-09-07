# Class of '09 Access — Changelog

Newest first. Version 1.0.0 is the current initial release.

Class of '09 Access is developed for *Class of '09* and *Class of '09: The Re-Up* on Windows (64-bit and 32-bit), running on Ren'Py 7.5.0 with Python 2.7.

## Unreleased — Accessibility Reliability Fixes

- Fixed the pause menu so it captures keyboard input and prevents dialogue or choice interactions from leaking through while paused.
- Stopped narration cleanly during pause and re-read the current dialogue when resuming instead of skipping ahead to the next choice.
- Fixed duplicate dialogue announcements caused by overlapping speech callbacks.
- Cleared stale choice data when new dialogue begins and made pause state reliable across Save, Load, and Options screens.

---

## 1.0.0 — Initial Release: Complete Screen Reader Bridge

The first complete release bringing full non-visual accessibility to *Class of '09* and *The Re-Up*.

### Core Features:
- **Direct NVDA Controller Client Hook**:
  - Implemented real-time communication with NVDA via `nvdaControllerClient64.dll` and `nvdaControllerClient32.dll`.
  - Speech is dispatched instantaneously through native `ctypes` bindings without subprocess overhead or latency.
  - Added seamless fallback chain to **Tolk** (for JAWS and SuperNova users), **Windows SAPI5**, and Ren'Py internal speech.

- **Accessible Branching Decisions & Choices**:
  - Replaced the stock `choice` screen with an accessible container.
  - When the game reaches a choice branch, the mod announces the total count and reads the options aloud.
  - Up and Down arrow keys smoothly navigate between choices with full spoken feedback (e.g. *"Choice 1 of 2: [Text]"*).
  - Pressing **`C`** re-reads all available choices on screen at any time.
  - Removed intrusive earcon chimes so dialogue and speech remain clean and natural.

- **Real-Time Dialogue & Narration**:
  - Hooked into `screen say(who, what)` to capture active character names and dialogue.
  - Automatically speaks speaker tags and spoken lines on display.
  - Rapid line progression cleanly interrupts previous speech so there is no backlog or speech queue delay.
  - Pressing **`H`** repeats the last spoken dialogue and speaker name.
  - Pressing **`D`** toggles dialogue TTS on/off (allowing players to switch between full spoken text or purely listening to the original voice actors).

- **Main Menu Graphical Buttons Replaced**:
  - Replaced the silent 1920x1080 transparent image buttons on `screen navigation()` with fully accessible buttons with `alt` and `hovered` hooks.
  - Spoken options for New Game, Continue (Load Game), Options, About, and Exit Game.
  - Added direct numeric key navigation (`1` through `5`) on the main menu for effortless launching.

- **Spoken Save & Load File Slots**:
  - Rebuilt `pause_file_slots` to inspect save slot timestamps via `renpy.slot_mtime()`.
  - Announces slot numbers alongside exact save date and time (or announces `"Empty"` if no save exists).
  - Spoken page navigation for Auto Saves, Quick Saves, and numbered save pages.

- **Pause Menu & Preferences**:
  - Fully navigable Pause menu accessible via `Escape`.
  - Accessible Preferences screen for switching between Windowed and Fullscreen modes, with spoken volume slider adjustments using Left and Right arrow keys.
