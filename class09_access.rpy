# -*- coding: utf-8 -*-
# =============================================================
# Class of '09 - Complete Non-Visual Accessibility Mod
# 100% Accessible: Main Menu, In-Game Dialogue, Branching Choices,
# Full Settings/Preferences (Volume Percentages & Display Toggles),
# Save/Load Slots with Timestamps, and About/Credits Screens.
# Exclusively routes through NVDA (no dual voices, no lag).
# =============================================================

init -999 python:
    import sys
    import os
    import time
    import ctypes
    import re

    class ScreenReaderManager(object):
        def __init__(self):
            self.nvda = None
            self.tolk = None
            self.sapi = None
            self.active_driver = None
            self.read_dialogue = True
            self.last_spoken_text = u""
            self.last_spoken_time = 0.0
            self.last_who = u""
            self.last_what = u""
            self.current_choices = []
            self.current_say_id = 0
            self.spoken_say_id = -1
            self.pause_depth = 0
            self.last_line_auto_advance = False
            self.menu_index = 0
            self.menu_labels = [u"New Game", u"Continue and Load Game", u"Options", u"About", u"Exit Game"]
            self.shown_announced = set()
            self.init_speech()

        def init_speech(self):
            game_dir = renpy.config.gamedir
            is_64 = (sys.maxsize > 2**32)

            # 1. STRICT PRIORITY: Check NVDA
            nvda_dll = "nvdaControllerClient64.dll" if is_64 else "nvdaControllerClient32.dll"
            search_paths = [
                os.path.join(game_dir, nvda_dll),
                os.path.join(game_dir, "nvdaControllerClient.dll"),
                os.path.join(os.path.dirname(game_dir), nvda_dll),
                nvda_dll
            ]

            for p in search_paths:
                if os.path.exists(p):
                    try:
                        dll = ctypes.cdll.LoadLibrary(p)
                        # NVDA may still be starting up when the game
                        # launches. Retry briefly before falling back to
                        # Tolk / SAPI so we never end up with a second
                        # TTS voice while NVDA is actually running.
                        nvda_running = False
                        for _attempt in range(5):
                            try:
                                if dll.nvdaController_testIfRunning() == 0:
                                    nvda_running = True
                                    break
                            except Exception:
                                break
                            time.sleep(0.2)
                        if nvda_running:
                            self.nvda = dll
                            self.nvda.nvdaController_speakText.argtypes = [ctypes.c_wchar_p]
                            self.nvda.nvdaController_speakText.restype = ctypes.c_long
                            self.active_driver = "NVDA"
                            return
                    except Exception:
                        pass

            # 2. Tolk Fallback (for JAWS / SuperNova)
            tolk_dll = "Tolk64.dll" if is_64 else "Tolk32.dll"
            tolk_paths = [
                os.path.join(game_dir, tolk_dll),
                os.path.join(game_dir, "Tolk.dll"),
                os.path.join(os.path.dirname(game_dir), tolk_dll),
                tolk_dll
            ]
            for p in tolk_paths:
                if os.path.exists(p):
                    try:
                        dll = ctypes.cdll.LoadLibrary(p)
                        dll.Tolk_Load()
                        if dll.Tolk_IsLoaded() and dll.Tolk_HasSpeech():
                            self.tolk = dll
                            self.tolk.Tolk_Output.argtypes = [ctypes.c_wchar_p, ctypes.c_bool]
                            self.active_driver = "TOLK"
                            return
                    except Exception:
                        pass

            # 3. SAPI Fallback
            try:
                import win32com.client
                self.sapi = win32com.client.Dispatch("SAPI.SpVoice")
                self.active_driver = "SAPI"
            except Exception:
                self.sapi = None

        def clean_text(self, text):
            if not text:
                return u""
            if isinstance(text, str):
                try:
                    text = text.decode('utf-8', 'ignore')
                except Exception:
                    try:
                        text = unicode(text)
                    except Exception:
                        pass
            elif not isinstance(text, unicode):
                text = unicode(text)
            text = re.sub(r'{[^}]*}', '', text)
            return text.strip()

        def speak(self, text, interrupt=True, force=False, debounce=True):
            clean = self.clean_text(text)
            if not clean:
                return

            # Debounce identical sequential speech so menu / choice / hover
            # announcements that fire several times in a row can never flood
            # the NVDA buffer. Dialogue lines bypass the debounce and rely on
            # the line-id guard instead, so two identical consecutive lines
            # both still get read. `force` bypasses the debounce for
            # intentional repeats (H, C, menu announcements, status toggles).
            now = time.time()
            if (not force) and debounce and clean == self.last_spoken_text and (now - self.last_spoken_time) < 0.5:
                return
            self.last_spoken_text = clean
            self.last_spoken_time = now

            if self.active_driver == "NVDA" and self.nvda:
                try:
                    if interrupt:
                        self.nvda.nvdaController_cancelSpeech()
                    self.nvda.nvdaController_speakText(clean)
                    return
                except Exception:
                    self.nvda = None
                    self.active_driver = None

            elif self.active_driver == "TOLK" and self.tolk:
                try:
                    self.tolk.Tolk_Output(clean, bool(interrupt))
                    return
                except Exception:
                    self.tolk = None
                    self.active_driver = None

            elif self.active_driver == "SAPI" and self.sapi:
                try:
                    flags = 1 if interrupt else 0
                    self.sapi.Speak(clean, flags)
                    return
                except Exception:
                    self.sapi = None
                    self.active_driver = None

        def begin_pause(self):
            self.pause_depth = 1
            self.stop_speech()

        def resume_from_pause(self):
            if self.pause_depth:
                self.pause_depth = 0
            if not self.pause_depth and self.read_dialogue:
                self.repeat_last_dialogue()

        def stop_speech(self):
            self.last_spoken_text = u""
            self.last_spoken_time = 0.0
            try:
                if self.active_driver == "NVDA" and self.nvda:
                    self.nvda.nvdaController_cancelSpeech()
                elif self.active_driver == "TOLK" and self.tolk:
                    self.tolk.Tolk_Silence()
                elif self.active_driver == "SAPI" and self.sapi:
                    self.sapi.Speak(u"", 3)
            except Exception:
                pass

        def on_say_advance(self):
            # Never advance the line counter for lines that are only being
            # predicted, or while the game is skipping -- otherwise the
            # duplicate-suppression guard below gets out of sync.
            if not self.pause_depth and not renpy.predicting() and not renpy.config.skipping:
                self.current_say_id += 1

        def on_dialogue(self, who, what, interrupt=True):
            if renpy.predicting():
                return
            if not self.read_dialogue:
                return
            if self.pause_depth:
                return
            # While skipping (Tab / Ctrl+Tab / auto-skip) the lines flash by
            # without any user interaction. Reading each one with an
            # interrupt would produce the "reads everything at high speed"
            # stutter, so stay silent and let the player read normally.
            if renpy.config.skipping:
                return

            clean_who = self.clean_text(who) if who else u""
            clean_what = self.clean_text(what) if what else u""

            # Ignore empty filler lines (e.g. "window auto" placeholders)
            # without touching the repeat-last-dialogue buffer.
            if not clean_what:
                return

            if self.spoken_say_id == self.current_say_id and clean_who == self.last_who and clean_what == self.last_what:
                return

            # Class of '09 writes every line with {p=X}{nw}, which makes the
            # game auto-advance when the timed pause elapses (it is voice
            # acted, so the pause matches the actor's line). When the PREVIOUS
            # line could auto-advance, the current line may have appeared
            # without a click -- queue it instead of cancelling NVDA
            # mid-sentence. Otherwise the reader is constantly cut off and it
            # sounds like the game is "reading very fast / skipping
            # everything".
            if self.last_line_auto_advance:
                interrupt = False
            self.last_line_auto_advance = u"{nw}" in (what or u"")

            self.spoken_say_id = self.current_say_id
            self.last_who = clean_who
            self.last_what = clean_what
            self.current_choices = []

            if clean_who:
                msg = u"%s: %s" % (clean_who, clean_what)
            else:
                msg = clean_what

            # `interrupt` is False for lines the game shows without waiting
            # for input (rapid-fire / cinematic narration). Those must be
            # queued instead of cancelling whatever is currently being read,
            # otherwise every line cuts off the previous one and the game
            # sounds like it is "skipping everything".
            self.speak(msg, interrupt=interrupt, debounce=False)

        def on_choices_shown(self, items):
            if renpy.predicting():
                return
            if self.pause_depth:
                return
            if renpy.config.skipping:
                return
            self.current_choices = [self.clean_text(item.caption) for item in items]
            options_text = u", ".join([u"Choice %d: %s" % (i + 1, c) for i, c in enumerate(self.current_choices)])
            self.speak(options_text, interrupt=False)

        def repeat_last_dialogue(self):
            # Never run during Ren'Py's screen prediction, which executes
            # keymap actions as part of predicting a screen.
            if renpy.predicting():
                return
            if self.last_what or self.last_who:
                msg = (u"%s: %s" % (self.last_who, self.last_what)) if self.last_who else self.last_what
                self.speak(msg, interrupt=True, force=True)
            else:
                self.speak(u"No dialogue to repeat.", interrupt=True, force=True)

        def repeat_choices(self):
            if renpy.predicting():
                return
            if self.current_choices:
                options_text = u", ".join([u"Choice %d: %s" % (i + 1, c) for i, c in enumerate(self.current_choices)])
                self.speak(options_text, interrupt=True, force=True)
            else:
                self.speak(u"No choices on screen.", interrupt=True, force=True)

        def toggle_dialogue_speech(self):
            if renpy.predicting():
                return
            self.read_dialogue = not self.read_dialogue
            status = u"Dialogue reading enabled." if self.read_dialogue else u"Dialogue reading muted."
            self.speak(status, interrupt=True, force=True)

        def get_volume_percent(self, mixer):
            try:
                vol = _preferences.get_volume(mixer)
                return int(round(vol * 100))
            except Exception:
                return 100

        def adjust_volume(self, mixer, delta):
            try:
                vol = _preferences.get_volume(mixer)
                new_vol = max(0.0, min(1.0, vol + delta))
                _preferences.set_volume(mixer, new_vol)
                name = u"Scene Volume" if mixer == "music" else u"UI Volume"
                self.speak(u"%s: %d percent" % (name, int(round(new_vol * 100))), interrupt=True)
            except Exception:
                pass

        def get_display_status(self, mode):
            is_full = getattr(_preferences, 'fullscreen', False)
            if mode == "fullscreen":
                return u"Display: Fullscreen, Selected" if is_full else u"Display: Fullscreen"
            else:
                return u"Display: Window, Selected" if not is_full else u"Display: Window"

        # ---------------------------------------------------------
        # MAIN MENU NAVIGATION
        #
        # The five menu buttons are full-screen images stacked on top of
        # each other, so Ren'Py's focus system can never move between them
        # with the arrow keys (nothing is focused, nothing is spoken).
        # Navigation is driven by an explicit selection index instead.
        # ---------------------------------------------------------
        def nav_set(self, index):
            self.menu_index = index

        def nav_move(self, delta):
            self.menu_index = (self.menu_index + delta) % len(self.menu_labels)
            self.speak(self.menu_labels[self.menu_index], interrupt=True, force=True)

        def nav_reset(self):
            self.menu_index = 0
            self.speak(u"Main Menu. 1: New Game. 2: Continue and Load Game. 3: Options. 4: About. 5: Exit Game. Use the arrow keys or the number keys.", interrupt=False, force=True)

        def nav_activate(self):
            index = self.menu_index
            self.speak(self.menu_labels[index], interrupt=True, force=True)
            if index == 0:
                renpy.run(Start())
            elif index == 1:
                renpy.run(ShowMenu("load"))
            elif index == 2:
                renpy.run(ShowMenu("preferences"))
            elif index == 3:
                renpy.run(ShowMenu("about"))
            else:
                renpy.run(Quit(confirm=not main_menu))

        # -----------------------------------------------------------------
        # SCREEN WATCHDOG
        #
        # Ren'Py only fires a screen's `on "show"` action for screens shown
        # through `call screen` or a non-transient `show_screen`. The menus
        # opened by the engine's standard game-menu path (the pause menu,
        # Options, Save/Load, About...) are shown transiently, so their
        # on-show announcements never run and the game would be silent when
        # they appear. This watchdog runs on a short periodic tick and
        # announces each such screen the moment it appears (and again each
        # time it is reopened).
        # -----------------------------------------------------------------
        def screen_watch(self):
            try:
                present = set()
                for n in (u"pause_menu", u"pause", u"game_menu", u"save", u"load",
                          u"preferences", u"about", u"actors", u"artists"):
                    try:
                        if renpy.get_screen(n):
                            present.add(n)
                    except Exception:
                        pass

                newly = present - self.shown_announced
                for n in sorted(newly):
                    if n in (u"pause_menu", u"pause", u"game_menu"):
                        self.begin_pause()
                        self.speak(u"Pause Menu. 1: Resume. 2: Save Game. 3: Load Game. 4: Options. 5: Main Menu. 6: Quit Game. Press Escape to resume.", False, True)
                    elif n == u"save":
                        self.speak(u"Save Menu. Select a slot, or press Escape to return.", False, True)
                    elif n == u"load":
                        self.speak(u"Load Menu. Select a slot, or press Escape to return.", False, True)
                    elif n == u"preferences":
                        self.speak(u"Options Menu. Display Mode and Volume Controls. Press Escape to return.", False, True)
                    elif n == u"about":
                        self.speak(u"About. This video game is entirely based on real events, encounters, and personalities. Any content viewed as offensive is a reflection of American culture and not endorsed by Class of 09 or its staff.", False, True)
                    elif n == u"actors":
                        self.speak(u"Voice Acting Cast. Nicole played by Kayli Mills. Jecka played by Elsie Lovelock. Emily played by Kira Buckland. Kelly played by Megan Shipman. Jeffrey played by Joshua Waters. Coach Colby played by Frank Todaro. Kylar played by Martin Billany. Principal Lynn played by Karen Strassman.", False, True)
                    elif n == u"artists":
                        self.speak(u"Art and Design. Character sprites, CG backgrounds, and user interface designed by SBN3 and contributing artists.", False, True)

                self.shown_announced = present
            except Exception:
                pass

    sr = ScreenReaderManager()

    # -------------------------------------------------------------
    # Ren'Py self-voicing / SAPI lockdown.
    #
    # Ren'Py's built-in self-voicing reads *every* screen and dialogue
    # line through Windows SAPI ("wscript say.vbs") whenever it is
    # enabled (V / Shift+V / saved preference). Running it at the same
    # time as this mod produces two voices speaking at once and makes
    # the game read everything at high speed. When we have our own
    # driver (NVDA / Tolk / SAPI) we disable Ren'Py's TTS completely
    # and keep it disabled.
    # -------------------------------------------------------------
    try:
        import renpy.display.tts as rtts
    except Exception:
        rtts = None

    _last_watch = [0.0]
    def tts_lockdown():
        # Screen watchdog: announce transiently-shown menus shortly after
        # they appear (their `on "show"` actions never fire).
        try:
            if time.time() - _last_watch[0] >= 0.4:
                _last_watch[0] = time.time()
                sr.screen_watch()
        except Exception:
            pass

        if not sr.active_driver:
            return
        try:
            if rtts is not None:
                rtts.default_tts_function = None
            config.tts_function = None
            renpy.game.preferences.self_voicing = False
        except Exception:
            pass

    tts_lockdown()

    # Disable the built-in self-voicing hotkeys (V, Shift+V, C, Shift+C)
    # and remove the bindings that collide with this mod's own hotkeys
    # (H = repeat dialogue, C = repeat choices, D = toggle dialogue TTS).
    if sr.active_driver:
        try:
            km = config.underlay[0].keymap
            km.pop("self_voicing", None)
            km.pop("clipboard_voicing", None)
            km.pop("debug_voicing", None)
            km["hide_windows"] = [k for k in km.get("hide_windows", []) if k not in ("h", "H")]
            km["developer"] = [k for k in km.get("developer", []) if k != "shift_K_d"]
            config.keymap["self_voicing"] = []
            config.keymap["clipboard_voicing"] = []
            config.keymap["debug_voicing"] = []
            config.keymap["hide_windows"] = [k for k in config.keymap.get("hide_windows", []) if k not in ("h", "H")]
            config.keymap["developer"] = [k for k in config.keymap.get("developer", []) if k != "shift_K_d"]
        except Exception:
            pass

        # Watchdog: re-assert the lockdown on every periodic tick so a
        # toggle from a game screen or a restored preference can never
        # resurrect Ren'Py's second voice mid-game.
        try:
            config.periodic_callbacks.append(tts_lockdown)
        except Exception:
            pass

init 100 python:
    _base_say = renpy.exports.say

    def _accessible_say_hook(who, what, *args, **kwargs):
        sr.on_say_advance()
        # Determine whether this line waits for player input. Lines shown
        # without waiting (interact=False) are queued, not interrupting.
        interact = kwargs.get("interact", True)
        if args:
            interact = args[0]
        sr.on_dialogue(who, what, interrupt=bool(interact))
        return _base_say(who, what, *args, **kwargs)

    renpy.exports.say = _accessible_say_hook
    renpy.say = _accessible_say_hook

    try:
        _base_show_display_say = renpy.character.show_display_say
        def _accessible_show_display_say(who, what, *args, **kwargs):
            sr.on_dialogue(who, what)
            return _base_show_display_say(who, what, *args, **kwargs)
        renpy.character.show_display_say = _accessible_show_display_say
    except Exception:
        pass


# -------------------------------------------------------------
# 1. DIALOGUE SCREEN (say)
# -------------------------------------------------------------
screen say(who, what):
    style_prefix "say"

    $ sr.on_dialogue(who, what)

    window:
        id "window"

        if who is not None:
            window:
                id "namebox"
                style "namebox"
                text who id "who"

        text what id "what"

    if not renpy.variant("small"):
        add SideImage() xalign 0.0 yalign 1.0

# -------------------------------------------------------------
# 2. CHOICE SCREEN
# -------------------------------------------------------------
screen choice(items):
    style_prefix "choice"
    image Image("gui/choice_window.png")

    on "show" action Function(sr.on_choices_shown, items)

    vbox:
        for i, item in enumerate(items):
            $ choice_desc = u"Choice %d: %s" % (i + 1, sr.clean_text(item.caption))
            # The first button grabs focus the moment the menu appears and
            # would otherwise cancel the "Decision point..." announcement
            # before it is spoken. Queue it instead of interrupting.
            $ choice_interrupt = (i > 0)
            textbutton item.caption:
                action [Play("sfx", "audio/PhoneSelect.mp3"), item.action]
                hovered Function(sr.speak, choice_desc, choice_interrupt)

# -------------------------------------------------------------
# 3. MAIN MENU NAVIGATION
# -------------------------------------------------------------
screen navigation():
    style_prefix "navigation"

    # Announce the whole menu when it appears (nothing is focused at launch,
    # so without this the game would be completely silent). Arrow keys and
    # number keys drive the selection index with spoken feedback; Enter and
    # Space activate the selected option. Mouse hover still speaks and
    # clicks still activate, through the same index.
    on "show" action Function(sr.nav_reset)

    key "K_DOWN" action Function(sr.nav_move, 1)
    key "K_UP" action Function(sr.nav_move, -1)
    key "K_RETURN" action Function(sr.nav_activate)
    key "K_SPACE" action Function(sr.nav_activate)
    key "K_KP_ENTER" action Function(sr.nav_activate)

    key "1" action [Function(sr.nav_set, 0), Function(sr.nav_activate)]
    key "2" action [Function(sr.nav_set, 1), Function(sr.nav_activate)]
    key "3" action [Function(sr.nav_set, 2), Function(sr.nav_activate)]
    key "4" action [Function(sr.nav_set, 3), Function(sr.nav_activate)]
    key "5" action [Function(sr.nav_set, 4), Function(sr.nav_activate)]

    imagebutton:
        idle "NEWGAME.png"
        hover "NEWGAME_selected.png"
        xpos 0
        ypos 0
        focus_mask "NEWGAME_mask.png"
        activate_sound "audio/MainMenuPress.mp3"
        hover_sound "audio/MainMenuRollover.mp3"
        hovered [Function(sr.nav_set, 0), Function(sr.speak, u"New Game", False)]
        action Function(sr.nav_activate)

    imagebutton:
        idle "CONTINUE.png"
        hover "CONTINUE_selected.png"
        xpos 0
        ypos 0
        focus_mask "CONTINUE_mask.png"
        activate_sound "audio/MainMenuPress.mp3"
        hover_sound "audio/MainMenuRollover.mp3"
        hovered [Function(sr.nav_set, 1), Function(sr.speak, u"Continue and Load Game", False)]
        action Function(sr.nav_activate)

    imagebutton:
        idle "OPTIONS.png"
        hover "OPTIONS_selected.png"
        xpos 0
        ypos 0
        focus_mask "OPTIONS_mask.png"
        activate_sound "audio/MainMenuPress.mp3"
        hover_sound "audio/MainMenuRollover.mp3"
        hovered [Function(sr.nav_set, 2), Function(sr.speak, u"Options", False)]
        action Function(sr.nav_activate)

    imagebutton:
        idle "ABOUT.png"
        hover "ABOUT_selected.png"
        xpos 0
        ypos 0
        focus_mask "ABOUT_mask.png"
        activate_sound "audio/MainMenuPress.mp3"
        hover_sound "audio/MainMenuRollover.mp3"
        hovered [Function(sr.nav_set, 3), Function(sr.speak, u"About", False)]
        action Function(sr.nav_activate)

    imagebutton:
        idle "EXIT.png"
        hover "EXIT_selected.png"
        xpos 0
        ypos 0
        focus_mask "EXIT_mask.png"
        activate_sound "audio/MainMenuPress.mp3"
        hover_sound "audio/MainMenuRollover.mp3"
        hovered [Function(sr.nav_set, 4), Function(sr.speak, u"Exit Game", False)]
        action Function(sr.nav_activate)

# -------------------------------------------------------------
# 4. IN-GAME QUICK MENU
# -------------------------------------------------------------
screen quick_menu():
    zorder 100

    if quick_menu:
        imagebutton:
            idle "gui/pausebutton.png"
            hover "gui/pausebutton.png"
            action ShowMenu("pause")
            hovered Function(sr.speak, u"Pause", True)
            xalign 0.92
            yalign .89

        imagebutton:
            idle "gui/backbutton.png"
            hover "gui/backbutton.png"
            action Rollback()
            hovered Function(sr.speak, u"Back", True)
            xalign 0.92
            yalign 0.98

# -------------------------------------------------------------
# 5. ACCESSIBLE PAUSE MENU HUB
# -------------------------------------------------------------
screen game_pause_menu():
    tag menu
    modal True
    add "gui/nvl.png"

    frame:
        xalign 0.5
        yalign 0.5
        background "#000000cc"
        padding (50, 35)

        vbox:
            spacing 15
            xalign 0.5

            label _("PAUSE MENU"):
                xalign 0.5

            textbutton _("1. Resume"):
                action [Function(sr.resume_from_pause), Return()]
                hovered Function(sr.speak, u"1: Resume Game", True)
                xalign 0.5

            textbutton _("2. Save Game"):
                action ShowMenu("save")
                hovered Function(sr.speak, u"2: Save Game", True)
                xalign 0.5

            textbutton _("3. Load Game"):
                action ShowMenu("load")
                hovered Function(sr.speak, u"3: Load Game", True)
                xalign 0.5

            textbutton _("4. Options"):
                action ShowMenu("preferences")
                hovered Function(sr.speak, u"4: Options and Settings", True)
                xalign 0.5

            textbutton _("5. Main Menu"):
                action MainMenu()
                hovered Function(sr.speak, u"5: Return to Main Menu", True)
                xalign 0.5

            textbutton _("6. Quit Game"):
                action Quit(confirm=True)
                hovered Function(sr.speak, u"6: Quit Game", True)
                xalign 0.5

    key "game_menu" action [Function(sr.resume_from_pause), Return()]
    key "1" action [Function(sr.resume_from_pause), Return()]
    key "2" action ShowMenu("save")
    key "3" action ShowMenu("load")
    key "4" action ShowMenu("preferences")
    key "5" action MainMenu()
    key "6" action Quit(confirm=True)

screen pause():
    tag menu
    use game_pause_menu

screen pause_menu():
    tag menu
    use game_pause_menu

screen game_menu(title="", scroll=None):
    tag menu
    use game_pause_menu

init python:
    _game_menu_screen = "pause"

# -------------------------------------------------------------
# 6. PAUSE SAVE & LOAD FILE SLOTS
# -------------------------------------------------------------
init python:
    def get_slot_description(slot, title):
        time_str = renpy.slot_mtime(slot)
        if time_str:
            import time
            readable_time = time.strftime("%B %d, %Y at %I:%M %p", time.localtime(time_str))
            return u"Slot %d: Saved on %s." % (slot, readable_time)
        else:
            return u"Slot %d: Empty." % (slot)

screen save():
    tag menu
    use pause_file_slots(_("Save"))

screen load():
    tag menu
    use pause_file_slots(_("Load"))

screen pause_file_slots(title):
    default page_name_value = FilePageNameInputValue(pattern=_("Page {}"), auto=_("Auto saves"), quick=_("Quick saves"))

    add "gui/nvl.png"

    fixed:
        order_reverse True

        button:
            style "page_label"
            key_events True
            xalign 0.5
            yalign 0.0
            action page_name_value.Toggle()
            hovered Function(sr.speak, u"Page %s" % FilePageName(), True)

            input:
                style "page_label_text"
                value page_name_value

        grid gui.file_slot_cols gui.file_slot_rows:
            style_prefix "slot"
            xalign 0.5
            yalign 0.2
            spacing gui.slot_spacing

            for i in range(gui.file_slot_cols * gui.file_slot_rows):
                $ slot = i + 1
                $ slot_desc = get_slot_description(slot, title)

                button:
                    action [Function(sr.speak, u"%s Slot %d" % (title, slot)), FileAction(slot)]
                    hovered Function(sr.speak, slot_desc, True)

                    has vbox
                    add FileScreenshot(slot) xalign 0.5
                    text FileTime(slot, format=_("{#file_time}%A, %B %d %Y, %H:%M"), empty=_("empty slot")):
                        style "slot_time_text"
                    text FileSaveName(slot):
                        style "slot_name_text"

                    key "save_delete" action [Function(sr.speak, u"Deleted slot %d" % slot), FileDelete(slot)]

        hbox:
            style_prefix "page"
            xalign 0.5
            yalign 0.75
            spacing gui.page_spacing

            imagebutton:
                idle "gui/arrowleft.png"
                hover "gui/arrowleft.png"
                action FilePagePrevious()
                hovered Function(sr.speak, u"Previous Page", True)

            if config.has_autosave:
                textbutton _("{#auto_page}A"):
                    action FilePage("auto")
                    hovered Function(sr.speak, u"Auto Saves", True)

            if config.has_quicksave:
                textbutton _("{#quick_page}Q"):
                    action FilePage("quick")
                    hovered Function(sr.speak, u"Quick Saves", True)

            for page in range(1, 10):
                textbutton "[page]":
                    action FilePage(page)
                    hovered Function(sr.speak, u"Page %d" % page, True)

            imagebutton:
                idle "gui/arrowright.png"
                hover "gui/arrowright.png"
                action FilePageNext()
                hovered Function(sr.speak, u"Next Page", True)

        textbutton _("Return"):
            xalign 0.5
            yalign 0.90
            action Return()
            hovered Function(sr.speak, u"Return", True)

    key "game_menu" action Return()

# -------------------------------------------------------------
# 7. COMPLETE SETTINGS / PREFERENCES (Fully Accessible to NVDA)
# -------------------------------------------------------------
screen preferences():
    tag menu
    add "gui/nvl.png"

    frame:
        xalign 0.5
        yalign 0.5
        background "#000000cc"
        padding (50, 35)

        vbox:
            spacing 12
            xalign 0.5

            label _("DISPLAY MODE"):
                xalign 0.5

            hbox:
                spacing 30
                xalign 0.5
                textbutton _("Window"):
                    action [Function(sr.speak, u"Window mode selected", True), Preference("display", "window")]
                    hovered Function(sr.speak, sr.get_display_status("window"), True)
                textbutton _("Fullscreen"):
                    action [Function(sr.speak, u"Fullscreen mode selected", True), Preference("display", "fullscreen")]
                    hovered Function(sr.speak, sr.get_display_status("fullscreen"), True)

            null height 10

            # SCENE / MUSIC VOLUME
            label _("SCENE VOLUME"):
                xalign 0.5

            hbox:
                spacing 15
                xalign 0.5
                textbutton _("Decrease Scene Volume (-10%)"):
                    action Function(sr.adjust_volume, "music", -0.10)
                    hovered Function(sr.speak, u"Decrease Scene Volume. Currently %d percent." % sr.get_volume_percent("music"), True)
                
                textbutton _("Scene Volume: %d%%" % sr.get_volume_percent("music")):
                    action Function(sr.adjust_volume, "music", 0.10)
                    hovered Function(sr.speak, u"Scene Volume: %d percent." % sr.get_volume_percent("music"), True)

                textbutton _("Increase Scene Volume (+10%)"):
                    action Function(sr.adjust_volume, "music", 0.10)
                    hovered Function(sr.speak, u"Increase Scene Volume. Currently %d percent." % sr.get_volume_percent("music"), True)

            null height 10

            # UI / SOUND VOLUME
            label _("UI VOLUME"):
                xalign 0.5

            hbox:
                spacing 15
                xalign 0.5
                textbutton _("Decrease UI Volume (-10%)"):
                    action Function(sr.adjust_volume, "sfx", -0.10)
                    hovered Function(sr.speak, u"Decrease UI Volume. Currently %d percent." % sr.get_volume_percent("sfx"), True)

                textbutton _("UI Volume: %d%%" % sr.get_volume_percent("sfx")):
                    action Function(sr.adjust_volume, "sfx", 0.10)
                    hovered Function(sr.speak, u"UI Volume: %d percent." % sr.get_volume_percent("sfx"), True)

                textbutton _("Increase UI Volume (+10%)"):
                    action Function(sr.adjust_volume, "sfx", 0.10)
                    hovered Function(sr.speak, u"Increase UI Volume. Currently %d percent." % sr.get_volume_percent("sfx"), True)

            null height 15

            textbutton _("Return"):
                action Return()
                hovered Function(sr.speak, u"Return to previous menu", True)
                xalign 0.5

    key "game_menu" action Return()

screen pause_prefs():
    tag menu
    use preferences

# -------------------------------------------------------------
# 8. ABOUT & CREDITS SCREENS (100% Accessible)
# -------------------------------------------------------------
screen aboutmenu():
    tag menu
    add "gui/nvl.png"

    frame:
        xalign 0.5
        yalign 0.5
        background "#000000cc"
        padding (45, 30)

        vbox:
            spacing 15
            xalign 0.5

            hbox:
                spacing 25
                xalign 0.5
                textbutton _("About"):
                    action ShowMenu("about")
                    hovered Function(sr.speak, u"About Tab. Game premise and description.", True)
                textbutton _("Actors"):
                    action ShowMenu("actors")
                    hovered Function(sr.speak, u"Actors Tab. Voice actor credits.", True)
                textbutton _("Artists"):
                    action ShowMenu("artists")
                    hovered Function(sr.speak, u"Artists Tab. Visual artist credits.", True)

            null height 15

            viewport:
                xsize 700
                ysize 300
                scrollbars "vertical"
                mousewheel True
                draggable True
                vbox:
                    xalign 0.5
                    transclude

            null height 10

            textbutton _("Return"):
                action Return()
                hovered Function(sr.speak, u"Return to Main Menu", True)
                xalign 0.5

    key "game_menu" action Return()

screen about():
    tag menu
    $ about_text = u"This video game is entirely based on real events, encounters, and personalities. Any content viewed as offensive is a reflection of American culture and not endorsed by Class of '09 or its staff."
    use aboutmenu():
        vbox:
            text about_text:
                size 24
                color "#FFFFFF"
screen actors():
    tag menu
    $ actors_text = u"Voice Acting Cast: Nicole played by Kayli Mills. Jecka played by Elsie Lovelock. Emily played by Kira Buckland. Kelly played by Megan Shipman. Jeffrey played by Joshua Waters. Coach Colby played by Frank Todaro. Kylar played by Martin Billany. Principal Lynn played by Karen Strassman."
    use aboutmenu():
        vbox:
            text actors_text:
                size 22
                color "#FFFFFF"
screen artists():
    tag menu
    $ artists_text = u"Art and Design: Character sprites, CG backgrounds, and user interface designed by SBN3 and contributing artists."
    use aboutmenu():
        vbox:
            text artists_text:
                size 24
                color "#FFFFFF"
# -------------------------------------------------------------
# 9. CONFIRMATION SCREEN
# -------------------------------------------------------------
screen confirm(message, yes_action, no_action):
    modal True
    zorder 200
    style_prefix "confirm"

    on "show" action Function(sr.speak, u"%s. Press Left Arrow for Yes, Right Arrow for No, or Escape to cancel." % sr.clean_text(message), True, True)

    add "gui/overlay/confirm.png"

    frame:
        vbox:
            xalign .5
            yalign .5
            spacing 45

            label _(message):
                style "confirm_prompt"
                xalign 0.5

            hbox:
                xalign 0.5
                spacing 150

                textbutton _("Yes"):
                    action yes_action
                    hovered Function(sr.speak, u"Yes", True)
                textbutton _("No"):
                    action no_action
                    hovered Function(sr.speak, u"No", True)

    # The announcement promises arrow keys work; make them real so a
    # keyboard user can answer the prompt. Return is intentionally inert so
    # an accidental Enter can never confirm a destructive action.
    key "K_LEFT" action [Function(sr.speak, u"Yes", True, True), yes_action]
    key "K_RIGHT" action [Function(sr.speak, u"No", True, True), no_action]
    key "K_RETURN" action no_action
    key "K_SPACE" action no_action
    key "game_menu" action no_action

# -------------------------------------------------------------
# 10. GLOBAL ACCESSIBILITY HOTKEYS
# -------------------------------------------------------------
init python:
    config.keymap['sr_repeat_dialogue'] = ['h', 'H']
    config.underlay[0].keymap['sr_repeat_dialogue'] = sr.repeat_last_dialogue

    config.keymap['sr_repeat_choices'] = ['c', 'C']
    config.underlay[0].keymap['sr_repeat_choices'] = sr.repeat_choices

    config.keymap['sr_toggle_dialogue'] = ['d', 'D']
    config.underlay[0].keymap['sr_toggle_dialogue'] = sr.toggle_dialogue_speech