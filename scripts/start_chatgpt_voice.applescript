-- Start ChatGPT voice mode by pressing the user's ChatGPT shortcut (Control-Option-Command-V).
-- Run from a Shortcuts "Run AppleScript" action so Siri can trigger it by name.
-- Needs Accessibility permission for the app that sends the keystroke (Shortcuts / Siri).
tell application "ChatGPT" to activate
delay 0.7
tell application "System Events" to keystroke "v" using {control down, option down, command down}
