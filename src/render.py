"""Render the hook edit: Strava stats overlay revealed on the dap.

Usage: python3 render.py <input.mov> <overlay.png> <output.mp4>
"""
import subprocess
import sys

import numpy as np
from PIL import Image, ImageFilter

W, H, FPS = 1080, 1920, 30
HIT = 7.0          # dap impact (seconds)
PUNCH = 0.40       # zoom punch duration
LOOP_DRAW = 0.55   # orange loop draw-on duration
STAGGER = 0.07     # delay between text lines
LINE_IN = 0.28     # each text line's animation length
DIM = 0.70         # video brightness under the stats

src, overlay_path, out = sys.argv[1:4]


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_out_back(x, s=1.6):
    x = min(max(x, 0.0), 1.0)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


# --- split the overlay into an orange loop layer and a white text layer ---
ov = np.asarray(Image.open(overlay_path).convert("RGBA")).astype(np.float32) / 255
alpha = ov[..., 3]
whiteness = np.clip((ov[..., 1] - 0.35) / 0.55, 0, 1)
text_a = alpha * whiteness
loop_a = alpha * (1 - whiteness)
# close the holes the text punched in the loop so it reads as a solid stroke
loop_img = Image.fromarray((loop_a * 255).astype(np.uint8))
loop_img = loop_img.filter(ImageFilter.MaxFilter(17)).filter(ImageFilter.MinFilter(17))
loop_a = np.maximum(loop_a, np.asarray(loop_img).astype(np.float32) / 255)
ORANGE = np.array([252, 82, 0], np.float32) / 255

ys, xs = np.nonzero(loop_a > 0.5)
cy, cx = ys.mean(), xs.mean()
yy, xx = np.mgrid[0:H, 0:W]
# angle measured clockwise from the top of the loop, 0..1
loop_angle = ((np.arctan2(xx - cx, -(yy - cy)) / (2 * np.pi)) + 1) % 1

# text shadow for legibility over the bright sky
shadow_a = np.asarray(
    Image.fromarray((text_a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(10))
).astype(np.float32) / 255 * 0.85

# group text into lines by horizontal projection
rows = text_a.max(axis=1) > 0.2
lines, start = [], None
for y, on in enumerate(rows):
    if on and start is None:
        start = y
    elif not on and start is not None:
        lines.append((start, y))
        start = None
# pair each label with its value ("Distance" / "5.01 km"); the logo stays alone
merged = [lines[0]] + [(lines[i][0], lines[min(i + 1, len(lines) - 1)][1])
                       for i in range(1, len(lines), 2)]
lines = [(max(a - 12, 0), min(b + 12, H)) for a, b in merged]


def text_layer(t):
    """Return (alpha, shadow_alpha) for the text at time t, lines staggered."""
    ta = np.zeros((H, W), np.float32)
    sa = np.zeros((H, W), np.float32)
    for i, (a, b) in enumerate(lines):
        p = (t - HIT - i * STAGGER) / LINE_IN
        if p <= 0:
            continue
        fade = ease_out(p * 1.6)
        rise = int(round((1 - ease_out_back(p)) * 40))
        band_t, band_s = text_a[a:b], shadow_a[a:b]
        na, nb = a + rise, min(b + rise, H)
        ta[na:nb] = np.maximum(ta[na:nb], band_t[: nb - na] * fade)
        sa[na:nb] = np.maximum(sa[na:nb], band_s[: nb - na] * fade)
    return ta, sa


def grade(f):
    # gentle contrast + saturation lift
    lum = f.mean(axis=2, keepdims=True)
    f = lum + (f - lum) * 1.15
    f = (f - 0.5) * 1.08 + 0.5
    return np.clip(f, 0, 1)


def vignette():
    nx = (xx - W / 2) / (W / 2)
    ny = (yy - H / 2) / (H / 2)
    return np.clip(1 - 0.35 * (nx ** 2 + ny ** 2) ** 1.2, 0, 1)[..., None].astype(np.float32)


VIG = vignette()

dec = subprocess.Popen(
    ["ffmpeg", "-v", "error", "-i", src, "-vf",
     "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
     "zscale=t=bt709:m=bt709:r=tv,format=rgb24",
     "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
    stdout=subprocess.PIPE)
enc = subprocess.Popen(
    ["ffmpeg", "-v", "error", "-y",
     "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
     "-i", src, "-map", "0:v", "-map", "1:a?",
     "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
     "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
     "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", out],
    stdin=subprocess.PIPE)

n = 0
while True:
    buf = dec.stdout.read(W * H * 3)
    if len(buf) < W * H * 3:
        break
    t = n / FPS
    frame = np.frombuffer(buf, np.uint8).reshape(H, W, 3)

    # zoom punch on the dap
    p = (t - HIT) / PUNCH
    if 0 <= p < 1:
        z = 1 + 0.09 * (1 - ease_out(p))
        cw, ch = int(W / z), int(H / z)
        x0, y0 = (W - cw) // 2, (H - ch) // 2
        frame = np.asarray(Image.fromarray(frame).crop((x0, y0, x0 + cw, y0 + ch))
                           .resize((W, H), Image.LANCZOS))

    f = grade(frame.astype(np.float32) / 255)
    f *= 0.8 + 0.2 * VIG

    if t >= HIT:
        dt = t - HIT
        f *= 1 - (1 - DIM) * ease_out(dt / 0.25)
        # quick flash on impact
        flash = 0.45 * max(0.0, 1 - dt / 0.12)
        f = f + (1 - f) * flash

        # orange loop draws on clockwise
        prog = ease_out(dt / LOOP_DRAW)
        la = loop_a * np.clip((prog * 1.02 - loop_angle) / 0.02, 0, 1)
        f = f * (1 - la[..., None]) + ORANGE * la[..., None]

        ta, sa = text_layer(t)
        f = f * (1 - sa[..., None])
        f = f * (1 - ta[..., None]) + ta[..., None]

    enc.stdin.write((np.clip(f, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
    n += 1

enc.stdin.close()
enc.wait()
dec.wait()
print(f"rendered {n} frames, {len(lines)} text lines")
