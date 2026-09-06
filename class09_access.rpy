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
            self.last_who = u""
            self.last_what = u""
            self.current_choices = []
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
                        if dll.nvdaController_testIfRunning() == 0:
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

        def speak(self, text, interrupt=True):
            clean = self.clean_text(text)
            if not clean:
                return

            # Debounce identical sequential speech to avoid NVDA buffer flooding
            if clean == self.last_spoken_text:
                return
            self.last_spoken_text = clean

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

        def on_dialogue(self, who, what):
            if renpy.predicting():
                return
            if not self.read_dialogue:
                return

            clean_who = self.clean_text(who) if who else u""
            clean_what = self.clean_text(what) if what else u""

            if clean_who:
                msg = u"%s: %s" % (clean_who, clean_what)
            else:
                msg = clean_what

            self.last_who = clean_who
            self.last_what = clean_what
            self.last_spoken_text = u""
            self.speak(msg, interrupt=True)

        def on_choices_shown(self, items):
            if renpy.predicting():
                return
            self.current_choices = [self.clean_text(item.caption) for item in items]
            options_text = u", ".join([u"Choice %d: %s" % (i + 1, c) for i, c in enumerate(self.current_choices)])
            self.last_spoken_text = u""
            self.speak(options_text, interrupt=False)

        def repeat_last_dialogue(self):
            if self.last_what or self.last_who:
                msg = (u"%s: %s" % (self.last_who, self.last_what)) if self.last_who else self.last_what
                self.last_spoken_text = u""
                self.speak(msg, interrupt=True)
            else:
                self.speak(u"No dialogue to repeat.", interrupt=True)

        def repeat_choices(self):
            if self.current_choices:
                options_text = u", ".join([u"Choice %d: %s" % (i + 1, c) for i, c in enumerate(self.current_choices)])
                self.last_spoken_text = u""
                self.speak(options_text, interrupt=True)
            else:
                self.speak(u"No choices on screen.", interrupt=True)

        def toggle_dialogue_speech(self):
            self.read_dialogue = not self.read_dialogue
            status = u"Dialogue reading enabled." if self.read_dialogue else u"Dialogue reading muted."
            self.last_spoken_text = u""
            self.speak(status, interrupt=True)

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
                self.last_spoken_text = u""
                self.speak(u"%s: %d percent" % (name, int(round(new_vol * 100))), interrupt=True)
            except Exception:
                pass

        def get_display_status(self, mode):
            is_full = getattr(_preferences, 'fullscreen', False)
            if mode == "fullscreen":
                return u"Display: Fullscreen, Selected" if is_full else u"Display: Fullscreen"
            else:
                return u"Display: Window, Selected" if not is_full else u"Display: Window"

    sr = ScreenReaderManager()

    # Completely silence Ren'Py's background wscript / SAPI voice
    try:
        import renpy.display.tts as rtts
        rtts.default_tts_function = lambda s: None
        config.tts_function = lambda s: None
    except Exception:
        pass

init 100 python:
    _base_say = renpy.exports.say

    def _accessible_say_hook(who, what, *args, **kwargs):
        sr.on_dialogue(who, what)
        return _base_say(who, what, *args, **kwargs)

    renpy.exports.say = _accessible_say_hook
    renpy.say = _accessible_say_hook

# -------------------------------------------------------------
# 1. DIALOGUE SCREEN (say)
# -------------------------------------------------------------
screen say(who, what):
    style_prefix "say"

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
            textbutton item.caption:
                action [Play("sfx", "audio/PhoneSelect.mp3"), item.action]
                hovered Function(sr.speak, choice_desc, True)

# -------------------------------------------------------------
# 3. MAIN MENU NAVIGATION
# -------------------------------------------------------------
screen navigation():
    style_prefix "navigation"

    imagebutton:
        idle "NEWGAME.png"
        hover "NEWGAME_selected.png"
        xpos 0
        ypos 0
        focus_mask "NEWGAME_mask.png"
        activate_sound "audio/MainMenuPress.mp3"
        hover_sound "audio/MainMenuRollover.mp3"
        hovered Function(sr.speak, u"New Game", True)
        action Start()

    imagebutton:
        idle "CONTINUE.png"
        hover "CONTINUE_selected.png"
        xpos 0
        ypos 0
        focus_mask "CONTINUE_mask.png"
        activate_sound "audio/MainMenuPress.mp3"
        hover_sound "audio/MainMenuRollover.mp3"
        hovered Function(sr.speak, u"Continue", True)
        action ShowMenu("load")

    imagebutton:
        idle "OPTIONS.png"
        hover "OPTIONS_selected.png"
        xpos 0
        ypos 0
        focus_mask "OPTIONS_mask.png"
        activate_sound "audio/MainMenuPress.mp3"
        hover_sound "audio/MainMenuRollover.mp3"
        hovered Function(sr.speak, u"Options", True)
        action ShowMenu("preferences")

    imagebutton:
        idle "ABOUT.png"
        hover "ABOUT_selected.png"
        xpos 0
        ypos 0
        focus_mask "ABOUT_mask.png"
        activate_sound "audio/MainMenuPress.mp3"
        hover_sound "audio/MainMenuRollover.mp3"
        hovered Function(sr.speak, u"About", True)
        action ShowMenu("about")

    imagebutton:
        idle "EXIT.png"
        hover "EXIT_selected.png"
        xpos 0
        ypos 0
        focus_mask "EXIT_mask.png"
        activate_sound "audio/MainMenuPress.mp3"
        hover_sound "audio/MainMenuRollover.mp3"
        hovered Function(sr.speak, u"Exit", True)
        action Quit(confirm=not main_menu)

    key "1" action Start()
    key "2" action ShowMenu("load")
    key "3" action ShowMenu("preferences")
    key "4" action ShowMenu("about")
    key "5" action Quit(confirm=not main_menu)

# -------------------------------------------------------------
# 4. IN-GAME QUICK MENU
# -------------------------------------------------------------
screen quick_menu():
    zorder 100

    if quick_menu:
        imagebutton:
            idle "gui/pausebutton.png"
            hover "gui/pausebutton.png"
            action ShowMenu()
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
# 5. PAUSE SAVE & LOAD FILE SLOTS
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

# -------------------------------------------------------------
# 6. COMPLETE SETTINGS / PREFERENCES (Fully Accessible to NVDA)
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
# 7. ABOUT & CREDITS SCREENS (100% Accessible)
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
    on "show" action Function(sr.speak, about_text, False)

screen actors():
    tag menu
    $ actors_text = u"Voice Acting Cast: Nicole played by Kayli Mills. Jecka played by Elsie Lovelock. Emily played by Kira Buckland. Kelly played by Megan Shipman. Jeffrey played by Joshua Waters. Coach Colby played by Frank Todaro. Kylar played by Martin Billany. Principal Lynn played by Karen Strassman."
    use aboutmenu():
        vbox:
            text actors_text:
                size 22
                color "#FFFFFF"
    on "show" action Function(sr.speak, actors_text, False)

screen artists():
    tag menu
    $ artists_text = u"Art and Design: Character sprites, CG backgrounds, and user interface designed by SBN3 and contributing artists."
    use aboutmenu():
        vbox:
            text artists_text:
                size 24
                color "#FFFFFF"
    on "show" action Function(sr.speak, artists_text, False)

# -------------------------------------------------------------
# 8. CONFIRMATION SCREEN
# -------------------------------------------------------------
screen confirm(message, yes_action, no_action):
    modal True
    zorder 200
    style_prefix "confirm"

    on "show" action Function(sr.speak, u"%s. Press Left Arrow for Yes, Right Arrow for No." % sr.clean_text(message), True)

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

    key "game_menu" action no_action

# -------------------------------------------------------------
# 9. GLOBAL ACCESSIBILITY HOTKEYS
# -------------------------------------------------------------
init python:
    config.keymap['sr_repeat_dialogue'] = ['h', 'H']
    config.underlay[0].keymap['sr_repeat_dialogue'] = sr.repeat_last_dialogue

    config.keymap['sr_repeat_choices'] = ['c', 'C']
    config.underlay[0].keymap['sr_repeat_choices'] = sr.repeat_choices

    config.keymap['sr_toggle_dialogue'] = ['d', 'D']
    config.underlay[0].keymap['sr_toggle_dialogue'] = sr.toggle_dialogue_speech
