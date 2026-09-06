# -*- coding: utf-8 -*-
# Class of '09 Complete Non-Visual Accessibility Mod
# Strictly isolates NVDA to prevent dual speech (no Windows SAPI overlap)
# Hooks dialogue, choices, menus, save slots, and settings seamlessly.

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
            self.last_spoken = u""
            self.last_who = u""
            self.last_what = u""
            self.current_choices = []
            self.init_speech()

        def init_speech(self):
            game_dir = renpy.config.gamedir
            is_64 = (sys.maxsize > 2**32)

            # 1. STRICT PRIORITY: Try NVDA first
            nvda_dll = "nvdaControllerClient64.dll" if is_64 else "nvdaControllerClient32.dll"
            search_paths = [
                os.path.join(game_dir, nvda_dll),
                os.path.join(game_dir, "nvdaControllerClient.dll"),
                os.path.join(os.path.dirname(game_dir), nvda_dll),
                os.path.join(os.path.dirname(game_dir), "nvdaControllerClient.dll"),
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
                            # If NVDA is running, do NOT load Tolk or SAPI to prevent double voice!
                            return
                    except Exception:
                        pass

            # 2. Tolk Fallback (Only if NVDA is not active, for JAWS / SuperNova)
            tolk_dll = "Tolk64.dll" if is_64 else "Tolk32.dll"
            tolk_paths = [
                os.path.join(game_dir, tolk_dll),
                os.path.join(game_dir, "Tolk.dll"),
                os.path.join(os.path.dirname(game_dir), tolk_dll),
                os.path.join(os.path.dirname(game_dir), "Tolk.dll"),
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

            # 3. SAPI Fallback (Only if neither NVDA nor JAWS is running)
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
            
            # Strip Ren'Py style tags like {b}, {i}, {color=...}, {fast}, etc.
            text = re.sub(r'{[^}]*}', '', text)
            return text.strip()

        def speak(self, text, interrupt=True):
            clean = self.clean_text(text)
            if not clean:
                return

            # Exclusively use active driver to prevent dual speech
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

        def stop(self):
            if self.active_driver == "NVDA" and self.nvda:
                try:
                    self.nvda.nvdaController_cancelSpeech()
                except Exception:
                    pass
            elif self.active_driver == "TOLK" and self.tolk:
                try:
                    self.tolk.Tolk_Silence()
                except Exception:
                    pass

        def on_dialogue(self, who, what):
            """Called whenever dialogue is shown or executed."""
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

            if msg == self.last_spoken:
                return

            self.last_spoken = msg
            self.last_who = clean_who
            self.last_what = clean_what
            self.speak(msg, interrupt=True)

        def on_choices_shown(self, items):
            """Announces choice options without any beep chime."""
            if renpy.predicting():
                return
            self.current_choices = [self.clean_text(item.caption) for item in items]
            options_text = u", ".join([u"%d: %s" % (i + 1, c) for i, c in enumerate(self.current_choices)])
            announcement = u"Decision point. %d choices available. %s" % (len(items), options_text)
            self.speak(announcement, interrupt=False)

        def repeat_last_dialogue(self):
            if self.last_what or self.last_who:
                if self.last_who:
                    msg = u"%s: %s" % (self.last_who, self.last_what)
                else:
                    msg = self.last_what
                self.speak(msg, interrupt=True)
            else:
                self.speak(u"No dialogue to repeat.", interrupt=True)

        def repeat_choices(self):
            if self.current_choices:
                options_text = u", ".join([u"Choice %d: %s" % (i + 1, c) for i, c in enumerate(self.current_choices)])
                self.speak(options_text, interrupt=True)
            else:
                self.speak(u"No choices on screen.", interrupt=True)

        def toggle_dialogue_speech(self):
            self.read_dialogue = not self.read_dialogue
            status = u"Dialogue screen reader speech enabled." if self.read_dialogue else u"Dialogue screen reader speech muted. Voice acting only."
            self.speak(status, interrupt=True)

    sr = ScreenReaderManager()

    # Silence Ren'Py built-in SAPI speech so only NVDA speaks
    try:
        import renpy.speech
        renpy.speech.speak = lambda *a, **kw: None
    except Exception:
        pass

# Hook into Ren'Py's exports.say so EVERY single dialogue line is captured immediately
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

    # Also hook directly into screen say display
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
            $ choice_desc = u"Choice %d of %d: %s" % (i + 1, len(items), sr.clean_text(item.caption))
            textbutton item.caption:
                action [Play("sfx", "audio/PhoneSelect.mp3"), item.action]
                hovered Function(sr.speak, choice_desc, True)

# -------------------------------------------------------------
# 3. MAIN MENU NAVIGATION
# -------------------------------------------------------------
screen navigation():
    style_prefix "navigation"

    on "show" action Function(sr.speak, u"Main Menu. 1: New Game. 2: Continue. 3: Options. 4: About. 5: Exit. Use arrow keys or number keys.", False)

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
        hovered Function(sr.speak, u"Continue. Load saved game.", True)
        action ShowMenu("load")

    imagebutton:
        idle "OPTIONS.png"
        hover "OPTIONS_selected.png"
        xpos 0
        ypos 0
        focus_mask "OPTIONS_mask.png"
        activate_sound "audio/MainMenuPress.mp3"
        hover_sound "audio/MainMenuRollover.mp3"
        hovered Function(sr.speak, u"Options and Preferences.", True)
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
        hovered Function(sr.speak, u"Exit Game", True)
        action Quit(confirm=not main_menu)

    key "1" action Start()
    key "2" action ShowMenu("load")
    key "3" action ShowMenu("preferences")
    key "4" action ShowMenu("about")
    key "5" action Quit(confirm=not main_menu)

# -------------------------------------------------------------
# 4. IN-GAME QUICK MENU (Pause & Rollback)
# -------------------------------------------------------------
screen quick_menu():
    zorder 100

    if quick_menu:
        imagebutton:
            idle "gui/pausebutton.png"
            hover "gui/pausebutton.png"
            action ShowMenu()
            hovered Function(sr.speak, u"Pause Menu. Press Escape or click to open.", True)
            xalign 0.92
            yalign .89

        imagebutton:
            idle "gui/backbutton.png"
            hover "gui/backbutton.png"
            action Rollback()
            hovered Function(sr.speak, u"Back. Rollback to previous line.", True)
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
            return u"%s Slot %d: Saved on %s." % (title, slot, readable_time)
        else:
            return u"%s Slot %d: Empty." % (title, slot)

screen pause_file_slots(title):
    default page_name_value = FilePageNameInputValue(pattern=_("Page {}"), auto=_("Auto saves"), quick=_("Quick saves"))

    on "show" action Function(sr.speak, u"%s menu. Select a slot to save or load, or Return to resume." % title, False)

    add "gui/nvl.png"

    fixed:
        order_reverse True

        button:
            style "page_label"
            key_events True
            xalign 0.5
            yalign 0.0
            action page_name_value.Toggle()
            hovered Function(sr.speak, u"Page selection. Current page: %s" % FilePageName(), True)

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
                    action FileAction(slot)
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
                    hovered Function(sr.speak, u"Auto Saves Page", True)

            if config.has_quicksave:
                textbutton _("{#quick_page}Q"):
                    action FilePage("quick")
                    hovered Function(sr.speak, u"Quick Saves Page", True)

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
            hovered Function(sr.speak, u"Return to Game", True)

# -------------------------------------------------------------
# 6. PAUSE PREFERENCES / SETTINGS
# -------------------------------------------------------------
screen pause_prefs():
    tag menu
    add "gui/nvl.png"
    style_prefix "alt_menu"

    on "show" action Function(sr.speak, u"Preferences Menu. Window or Fullscreen, Scene Volume, UI Volume, Return.", False)

    vbox:
        xalign 0.5
        yalign 0.5

        hbox:
            box_wrap True
            if renpy.variant("pc") or renpy.variant("web"):
                vbox:
                    style_prefix "radio"
                    label _("Display")
                    textbutton _("Window"):
                        action [Function(sr.speak, u"Window mode selected", True), Preference("display", "window")]
                        hovered Function(sr.speak, u"Display: Window", True)
                    textbutton _("Fullscreen"):
                        action [Function(sr.speak, u"Fullscreen mode selected", True), Preference("display", "fullscreen")]
                        hovered Function(sr.speak, u"Display: Fullscreen", True)

        null height (4 * gui.pref_spacing)

        vbox:
            style_prefix "slider"
            box_wrap True

            vbox:
                if config.has_sound:
                    label _("Scene Volume")
                    vbox:
                        bar value Preference("music volume") hovered Function(sr.speak, u"Scene Volume Slider. Use Left and Right arrow keys to adjust.", True)

                    label _("UI Volume")
                    vbox:
                        bar value Preference("sound volume") hovered Function(sr.speak, u"UI Sound Volume Slider. Use Left and Right arrow keys to adjust.", True)

                    textbutton _("Return"):
                        action Return()
                        hovered Function(sr.speak, u"Return to Game", True)

# -------------------------------------------------------------
# 7. CONFIRMATION SCREEN
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
# 8. GLOBAL ACCESSIBILITY HOTKEYS
# -------------------------------------------------------------
init python:
    def action_repeat_dialogue():
        sr.repeat_last_dialogue()

    def action_repeat_choices():
        sr.repeat_choices()

    def action_toggle_dialogue():
        sr.toggle_dialogue_speech()

    # Bind H to repeat dialogue
    config.keymap['sr_repeat_dialogue'] = ['h', 'H']
    config.underlay[0].keymap['sr_repeat_dialogue'] = action_repeat_dialogue

    # Bind C to repeat choices
    config.keymap['sr_repeat_choices'] = ['c', 'C']
    config.underlay[0].keymap['sr_repeat_choices'] = action_repeat_choices

    # Bind D to toggle dialogue TTS
    config.keymap['sr_toggle_dialogue'] = ['d', 'D']
    config.underlay[0].keymap['sr_toggle_dialogue'] = action_toggle_dialogue
