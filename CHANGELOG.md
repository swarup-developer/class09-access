# Class of '09 Access — Changelog

Newest first. Version 1.0.1 is the current release; 1.0.0 was the initial release.

Class of '09 Access is developed for *Class of '09* and *Class of '09: The Re-Up* on Windows (64-bit and 32-bit), running on Ren'Py 7.5.0 with Python 2.7.

## 1.0.1 — Menu Announcement & Confirm-Dialog Fixes (Current Release)

- **Fixed the silent Pause / Options / Save / Load / About menus.** Ren'Py only runs a screen's `on "show"` action when the screen is shown through `call screen` or a non-transient `show_screen`; every menu the engine opens through its standard game-menu path (ESC pause menu, Options, Save, Load, About) is shown *transiently*, so those announcements never fired and the menus opened in complete silence even though their buttons worked. A screen watchdog now polls once per tick and announces each menu aloud the moment it appears (and again each time it is reopened), so pressing `Escape` during dialogue now speaks "Pause Menu. 1: Resume. 2: Save Game. 3: Load Game. 4: Options. 5: Main Menu. 6: Quit Game…" and the Save/Load slot lists, Options, and About screens introduce themselves. Verified live in-game: pause opened mid-scene announces and captures input (`pause_depth`), choices announce in full when they appear, and dialogue keeps reading in order.
- **Confirmed choice menus announce end-to-end in the real game** ("Choice 1: …, Choice 2: …" spoken on show, per-option speech on focus/hover) at two separate decision points in a live New Game run.
- **Fixed the confirmation dialog's dead arrow keys.** The dialog announced "Press Left Arrow for Yes, Right Arrow for No" but no key was actually bound, so a keyboard user could not answer. `Left` now activates Yes, `Right` activates No (both with spoken feedback), `Escape` cancels, and `Enter`/`Space` are intentionally inert so an accidental press can never confirm a destructive action.

---

### Also included in 1.0.1 — Dual-Voice & Fast-Reading Fixes

- **Eliminated the second voice:** Ren'Py's built-in self-voicing (SAPI "wscript") could run alongside NVDA whenever it was toggled on with `V`/`Shift+V` or restored from a saved preference, producing two voices and making the game read at high speed. It is now hard-disabled at launch and re-disabled on every frame (watchdog), the `V`/`Shift+V`/`C` self-voicing hotkeys are removed, and the saved `self_voicing` preference is forced off whenever a mod driver (NVDA / Tolk / SAPI) is active.
- **Fixed "reads everything very fast / skips everything after New Game":** Class of '09 writes every line with `{p=X}{nw}`, which makes the game auto-advance dialogue timed to the voice acting. Each auto-advanced line used to cancel NVDA's current reading mid-sentence, so the reader was constantly cut off. Lines that follow an auto-advanceable line are now queued instead of interrupting, so NVDA finishes every line in order; lines the player advances with a click still read instantly. Dialogue is also no longer spoken while the game is skipping (Tab / Ctrl+Tab), and rapid-fire `interact=False` narration lines are queued instead of cancelling each other.
- **Fixed the repeat hotkeys:** `H`, `C`, and `Shift+D` collided with Ren'Py's own `hide_windows`, `clipboard_voicing`, and `developer` bindings in the global keymap, and Python 2.7's dict ordering decided which one won. The conflicting bindings are now removed, so `H` always repeats the last line, `C` always repeats the choices, and `D` always toggles dialogue speech.
- **Fixed the silent main menu:** no button is focused when the game first launches (and the five full-screen menu buttons overlap, so arrow keys can never move focus between them), so nothing was ever spoken until a key was pressed. The main menu now announces all options aloud the moment it appears, and **arrow keys drive a spoken selection index** (each option is announced as you move), with **Enter / Space** (and `1`–`5`) activating the selected option. Mouse hover and click still work. This also fixes "NVDA does not read" at launch after the self-voicing removal.
- **Fixed the choice announcement race:** the first choice button grabbing focus no longer cancels the "Decision point…" announcement before it is spoken.
- **No more stray speech from screen prediction:** the `H` / `C` / `D` hotkeys no longer fire (e.g. speak "No choices on screen.") when Ren'Py predicts screens.
- **More reliable NVDA detection:** the mod retries `nvdaController_testIfRunning()` for up to a second at launch, so it never silently falls back to SAPI while NVDA is still starting up.
- **Added a time-based debounce** so a single line picked up by several hooks can never flood the NVDA speech queue, while intentional repeats (`H`, `C`, menu announcements) still always speak.
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
