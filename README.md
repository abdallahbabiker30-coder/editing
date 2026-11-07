# Hook edit

`output/hook_edit.mp4`: 1080x1920, 30fps, H.264, SDR (tone-mapped from the iPhone HLG source). The original audio is kept so a soundtrack can be added in another app.

Re-render: `python3 src/render.py <IMG_6729.mov> <strava_overlay.png> output/hook_edit.mp4`
Timing values (`HIT`, `PUNCH`, `LOOP_DRAW`, `STAGGER`, `DIM`) are at the top of the script.

# Barge edit

`output/yeet_edit.mp4`: 1920x1080, 60fps, H.264. The original audio is copied untouched.
At the shoulder barge (5.40s) the player in black is lifted out of the shot and launched into the far side of the pitch, ending in a twinkle.

Re-render: `pip install opencv-python-headless` then `python3 src/yeet.py <ScreenRecording.mov> output/yeet_edit.mp4`
