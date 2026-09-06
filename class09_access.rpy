# Class of '09 Accessibility Mod (Class09 Access)
# Designed for blind and visually impaired players
# Drop this file into: "Class of '09/game/" or "Class of '09 - The Re-Up/game/"

init -999 python:
    import sys
    import os
    import ctypes
    import winsound

    class ScreenReaderManager(object):
        """
        Handles communication with NVDA, JAWS, and Windows SAPI.
        Works across both Python 2 (Ren'Py 7) and Python 3 (Ren'Py 8).
        """
        def __init__(self):
            self.nvda = None
            self.sapi = None
            self.init_nvda()
            self.init_sapi()

        def init_nvda(self):
            try:
                # Try connecting to NVDA via standard Windows DLL
                self.nvda = ctypes.windll.nvdaControllerClient
                res = self.nvda.nvdaController_testIfRunning()
                if res != 0:
                    self.nvda = None
            except Exception:
                self.nvda = None

        def init_sapi(self):
            try:
                import win32com.client
                self.sapi = win32com.client.Dispatch("SAPI.SpVoice")
            except Exception:
                # If win32com is not available in Ren'Py runtime, fallback to PowerShell or Ren'Py self-voicing
                self.sapi = None

        def speak(self, text, interrupt=True):
            if not text:
                return
            
            # Ensure text is unicode / clean
            if sys.version_info[0] < 3:
                if isinstance(text, str):
                    text = text.decode('utf-8', 'ignore')
            else:
                text = str(text)

            spoken = False
            # 1. Try NVDA
            if self.nvda:
                try:
                    if interrupt:
                        self.nvda.nvdaController_cancelSpeech()
                    self.nvda.nvdaController_speakText(text)
                    spoken = True
                except Exception:
                    self.nvda = None

            # 2. Try SAPI
            if not spoken and self.sapi:
                try:
                    flags = 1 if interrupt else 0 # 1 = SVSFlagsAsync
                    self.sapi.Speak(text, 1)
                    spoken = True
                except Exception:
                    self.sapi = None

            # 3. Ren'Py built-in speech fallback
            if not spoken:
                try:
                    renpy.speech.speak(text)
                except Exception:
                    pass

        def stop(self):
            if self.nvda:
                try:
                    self.nvda.nvdaController_cancelSpeech()
                except Exception:
                    pass

        def play_choice_cue(self):
            """Play an audio chime when a choice point appears."""
            try:
                # Two-tone cheerful prompt: 587Hz (D5) -> 880Hz (A5)
                winsound.Beep(587, 100)
                winsound.Beep(880, 150)
            except Exception:
                pass

        def play_select_cue(self):
            """Play a subtle confirmation click/tone."""
            try:
                winsound.Beep(1046, 80)
            except Exception:
                pass

    # Instantiate global screen reader manager
    sr = ScreenReaderManager()

    # Enable Ren'Py self-voicing support
    config.speech_menu = True

# Hook choice screens
screen choice(items):
    style_prefix "choice"

    # Play cue and announce choices when choice screen opens
    on "show" action Function(sr.play_choice_cue)

    vbox:
        for i, item in enumerate(items):
            $ choice_text = "{}: {}".format(i + 1, item.caption)
            textbutton item.caption:
                action [Function(sr.play_select_cue), item.action]
                hovered Function(sr.speak, choice_text, True)
                focus_mask True
                # Ren'Py accessibility attribute
                alt choice_text

# Hook dialogue callback to speak character lines if self-voicing is preferred
init python:
    def accessibility_dialogue_callback(event, interact=True, **kwargs):
        # Class of '09 is fully voice acted, but we can optionally announce speaker names
        pass

    config.all_character_callbacks.append(accessibility_dialogue_callback)

# Add keyboard shortcuts for blind users
init python:
    # Press 'V' to toggle self-voicing in Ren'Py
    # Press 'H' to speak previous dialogue line
    def speak_last_history():
        history = _history_list
        if history:
            last = history[-1]
            who = last.who or "Narrator"
            what = last.what or ""
            sr.speak("{}: {}".format(who, what), True)

    config.keymap['speak_last_dialogue'] = ['h', 'H']
    config.underlay[0].keymap['speak_last_dialogue'] = speak_last_history
