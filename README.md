# Hook edit

`output/hook_edit.mp4`: 1080x1920, 30fps, H.264, SDR (tone-mapped from the iPhone HLG source). The original audio is kept so a soundtrack can be added in another app.

Re-render: `python3 src/render.py <IMG_6729.mov> <strava_overlay.png> output/hook_edit.mp4`
Timing values (`HIT`, `PUNCH`, `LOOP_DRAW`, `STAGGER`, `DIM`) are at the top of the script.

# Barge edit

`output/yeet_edit.mp4`: 1920x1080, 60fps, H.264, 7.5s. The original 6.2s audio is copied untouched.
At the shoulder barge (5.40s) the video ramps into 0.4x slow motion (motion-interpolated) and the player in black is lifted out of the shot and launched slowly into the far side of the pitch, ending in a twinkle. Because of the slow-mo, the video runs about 1.3s past the end of the audio.

Re-render: `pip install opencv-python-headless` then `python3 src/yeet.py <ScreenRecording.mov> output/yeet_edit.mp4`
