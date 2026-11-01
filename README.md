# Hook edit

`output/hook_edit.mp4`: 1080x1920, 30fps, H.264, SDR (tone-mapped from the iPhone HLG source). The original audio is kept so a soundtrack can be added in another app.

Re-render: `python3 src/render.py <IMG_6729.mov> <strava_overlay.png> output/hook_edit.mp4`
Timing values (`HIT`, `PUNCH`, `LOOP_DRAW`, `STAGGER`, `DIM`) are at the top of the script.

# LinkedIn profile photo

`output/linkedin_profile_{gray,blue,blur}.jpg`: 1080x1080 head-and-shoulders crops of the black-polo photo. The person is cut out with rembg (`birefnet-portrait`) and placed on a studio gradient (gray or blue) or on the original background blurred. The tones are lifted slightly because the source is a night photo.

Re-render: crop the source and save the mask as `crop.png` / `mask_birefnet-portrait.png`, then run `python3 src/linkedin_profile.py`.
