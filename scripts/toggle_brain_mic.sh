#!/bin/sh
# Turn Brain's microphone off or on. Bound to Control-Option-Command-B in Shortcuts.
# brain_voice.py watches this file; the sound here proves the key press worked.
FLAG="$HOME/Library/Application Support/Brain/mic_off"
if ! pgrep -qf "scripts/brain_voice.py"; then
    say "Brain is not running."
elif [ -e "$FLAG" ]; then
    rm -f "$FLAG"
    afplay /System/Library/Sounds/Glass.aiff &
else
    mkdir -p "$(dirname "$FLAG")"
    touch "$FLAG"
    afplay /System/Library/Sounds/Purr.aiff &
fi
