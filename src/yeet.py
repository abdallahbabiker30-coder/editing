"""Shoulder-barge edit: the player in black gets launched into the distance.

Usage: python3 yeet.py <input.mov> <output.mp4>
The original audio is copied untouched; the video slows down at the barge, so it
runs past the end of the audio.
"""
import math
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

src, out = sys.argv[1:3]
FPS = 60
SW, SH = 1126, 632      # source size (after rotation)
OW, OH = 1920, 1080     # output size
SRC_IMPACT = 324        # shoulder contact (source frame @60fps, 5.40s)
SRC_LAUNCH = 330        # he leaves the ground
RAMP = (316, 328)       # speed ramps from 1x down to SLOW over these output frames
SLOW = 0.4              # slow-motion speed for the flight
MI_START, MI_FPS = 5.2, 240   # motion-interpolated source for the slow-mo
TWINKLE_LEN = 34        # frames of twinkle at the end
FONT = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"

# black-kit player's box per keyframe (source px), interpolated in between
BLACK_KEYS = {
    330: (1018, 278, 1070, 440), 336: (986, 290, 1056, 465),
    342: (968, 288, 1044, 452), 348: (936, 296, 1028, 480),
    354: (910, 305, 1004, 512), 360: (886, 310, 964, 515),
    366: (852, 310, 954, 520), 372: (838, 320, 932, 500),
    375: (832, 322, 926, 500),
}
# green-bib player, protected from the removal while they overlap
GREEN_KEYS = {
    330: (1023, 327, 1090, 507), 336: (1023, 350, 1077, 540),
    342: (1020, 360, 1080, 540), 348: (1010, 370, 1073, 600),
    354: (993, 387, 1070, 632), 360: (983, 407, 1070, 632),
    366: (983, 410, 1067, 632), 375: (978, 440, 1060, 632),
}


def interp(keys, f):
    ks = sorted(keys)
    if f <= ks[0]:
        return np.array(keys[ks[0]], float)
    if f >= ks[-1]:
        return np.array(keys[ks[-1]], float)
    for a, b in zip(ks, ks[1:]):
        if a <= f <= b:
            u = (f - a) / (b - a)
            return (1 - u) * np.array(keys[a], float) + u * np.array(keys[b], float)


def ease_in_out(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 2


def read_frames():
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vf", f"fps={FPS}",
                        "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(p.stdout, np.uint8).reshape(-1, SH, SW, 3)


frames = read_frames()
plate = np.median(frames[::3], axis=0).astype(np.uint8)  # camera is locked off
p = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(MI_START), "-i", src, "-vf",
                    f"fps={FPS},minterpolate=fps={MI_FPS}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1",
                    "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True, check=True)
mi_frames = np.frombuffer(p.stdout, np.uint8).reshape(-1, SH, SW, 3)

# output frame -> source position (in 60fps source frames), with a speed ramp
T_SRC, pos, g = [], 0.0, 0
while pos <= len(frames) - 1:
    T_SRC.append(pos)
    pos += 1 - (1 - SLOW) * min(max((g - RAMP[0]) / (RAMP[1] - RAMP[0]), 0), 1)
    g += 1
N = len(T_SRC)


def source_image(sf):
    if sf == int(sf):
        return frames[int(sf)]
    k = int(round((sf / FPS - MI_START) * MI_FPS))
    return mi_frames[min(max(k, 0), len(mi_frames) - 1)]


def out_frame(src_f):
    return next(g for g, sf in enumerate(T_SRC) if sf >= src_f)


IMPACT = out_frame(SRC_IMPACT)
LAUNCH = out_frame(SRC_LAUNCH)
LAND = N - TWINKLE_LEN


def yellow(img):
    b, g, r = [img[..., i].astype(int) for i in range(3)]
    return (g > 140) & (r > 110) & (b < 130) & (g - b > 60)


def black_mask(img, f):
    x0, y0, x1, y1 = interp(BLACK_KEYS, f).astype(int)
    diff = np.abs(img.astype(np.int16) - plate).max(2) > 26
    m = np.zeros((SH, SW), np.uint8)
    m[y0:y1, x0:x1] = diff[y0:y1, x0:x1]
    m[cv2.dilate(yellow(img).astype(np.uint8), np.ones((5, 5))) > 0] = 0
    if f <= 348:
        gx0, gy0, gx1, gy1 = interp(GREEN_KEYS, f).astype(int)
        m[gy0:gy1, gx0:gx1] = 0
        # bits of him hidden behind the green bib: dark pixels left of the bib
        ys, xs = np.nonzero(yellow(img)[gy0:gy1, gx0:gx1])
        if len(xs):
            left, top = gx0 + np.percentile(xs, 5), gy0 + ys.min()
            dark = img.max(2) < 95
            ry0, ry1, rx0, rx1 = int(top) - 30, int(top) + 50, gx0 - 4, int(left) - 1
            m[ry0:ry1, rx0:rx1] |= (diff & dark)[ry0:ry1, rx0:rx1]
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7)))
    return m


def black_shadow(img, f):
    """His shadow falls straight down toward the camera, below his feet."""
    x0, y0, x1, y1 = interp(BLACK_KEYS, f).astype(int)
    darker = (plate.astype(np.int16) - img).sum(2) > 45
    m = np.zeros((SH, SW), np.uint8)
    sy0, sx0, sx1 = y1 - 25, x0 - 22, x1 - 4
    m[sy0:, sx0:sx1] = darker[sy0:, sx0:sx1]
    gx0, gy0, gx1, gy1 = interp(GREEN_KEYS, f).astype(int)
    m[gy0:gy1, gx0:gx1] = 0
    return cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9)))


def green_mask(img, f):
    gx0, gy0, gx1, gy1 = interp(GREEN_KEYS, f).astype(int)
    diff = np.abs(img.astype(np.int16) - plate).max(2) > 26
    m = np.zeros((SH, SW), np.float32)
    m[gy0:gy1, gx0:gx1] = diff[gy0:gy1, gx0:gx1]
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7)))
    return cv2.GaussianBlur(cv2.dilate(m, np.ones((5, 5))), (7, 7), 0)


def remove_black(img, f):
    m = cv2.dilate(black_mask(img, f) | black_shadow(img, f), np.ones((9, 9))).astype(np.float32)
    m = cv2.GaussianBlur(m, (9, 9), 0)[..., None]
    return (img * (1 - m) + plate * m).astype(np.uint8)


# --- cut the sprite from the cleanest frame -------------------------------
SP = 342
sm = black_mask(frames[SP], SP)
sm[358:, 1022:] = 0
n, lab, stats, _ = cv2.connectedComponentsWithStats(sm)
sm = (lab == 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])).astype(np.uint8)
cnts, _ = cv2.findContours(sm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cv2.drawContours(sm, cnts, -1, 1, -1)
ys, xs = np.nonzero(sm)
bx0, by0, bx1, by1 = xs.min() - 4, ys.min() - 4, xs.max() + 5, ys.max() + 5
sprite_rgb = frames[SP][by0:by1, bx0:bx1].astype(np.float32)
sprite_a = cv2.GaussianBlur(sm[by0:by1, bx0:bx1].astype(np.float32), (3, 3), 0)
SPRITE_H = by1 - by0

P0 = np.array([1044.0, 362.0])   # his centre at take-off
P1 = np.array([760.0, 0.0])    # arc control point
P2 = np.array([430.0, 74.0])     # far side of the pitch


def flight(u):
    """Position, scale, angle for flight progress u in [0, 1]."""
    e = ease_out(u)
    pos = (1 - e) ** 2 * P0 + 2 * (1 - e) * e * P1 + e ** 2 * P2
    hop = 1 + 0.25 * math.sin(min(u / 0.25, 1) * math.pi)   # pops toward camera first
    scale = hop * (1 - 0.95 * ease_in_out(u))
    angle = -900 * e
    return pos, scale, angle


def paste_sprite(canvas, pos, scale, angle, alpha=1.0, blur=0):
    s = max(scale, 0.02)
    h, w = sprite_a.shape
    pad = int(max(h, w) * 0.8)
    rgba = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.float32)
    rgba[pad:pad + h, pad:pad + w, :3] = sprite_rgb
    rgba[pad:pad + h, pad:pad + w, 3] = sprite_a
    M = cv2.getRotationMatrix2D((rgba.shape[1] / 2, rgba.shape[0] / 2), angle, s)
    M[0, 2] += pos[0] - rgba.shape[1] / 2
    M[1, 2] += pos[1] - rgba.shape[0] / 2
    warped = cv2.warpAffine(rgba, M, (SW, SH), flags=cv2.INTER_LINEAR)
    if blur:
        warped = cv2.GaussianBlur(warped, (0, 0), blur)
    a = warped[..., 3:4] * alpha
    canvas[:] = canvas * (1 - a) + warped[..., :3] * a


def speed_trail(canvas, u, steps=10):
    """White comet tail along the flight path."""
    layer = canvas.copy()
    pts = [flight(max(u - k * 0.018, 0)) for k in range(steps)]
    for k in range(steps - 1):
        (p, s, _), (q, _, _) = pts[k], pts[k + 1]
        w = max(int(30 * s * (1 - k / steps)), 1)
        cv2.line(layer, tuple(np.int32(p)), tuple(np.int32(q)), (255, 255, 255), w, cv2.LINE_AA)
    a = 0.45 * min(u / 0.05, 1) * (1 - ease_in_out((u - 0.7) / 0.3))
    canvas[:] = canvas * (1 - a) + layer * a


def soft_circle(canvas, c, r, color, alpha):
    if alpha <= 0 or r <= 0:
        return
    x0, y0 = int(max(c[0] - 2 * r, 0)), int(max(c[1] - 2 * r, 0))
    x1, y1 = int(min(c[0] + 2 * r, SW)), int(min(c[1] + 2 * r, SH))
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    d = np.sqrt((xx - c[0]) ** 2 + (yy - c[1]) ** 2) / r
    a = (np.clip(1.2 - d, 0, 1) ** 1.5 * alpha)[..., None]
    canvas[y0:y1, x0:x1] = canvas[y0:y1, x0:x1] * (1 - a) + np.array(color) * a


rng = np.random.default_rng(7)
DUST = [(rng.uniform(-30, 30), rng.uniform(-60, 60), rng.uniform(0.7, 1.3)) for _ in range(9)]


def dust(canvas, img, sf, f):
    t = (f - LAUNCH) / 48
    if not 0 <= t <= 1:
        return
    layer = canvas.copy()
    for dx, dy, k in DUST:
        c = (1030 + dx * (1 + 2 * t), 385 + dy * (1 + 0.6 * t) - 30 * t)
        soft_circle(layer, c, (12 + 28 * ease_out(t)) * k, (200, 210, 204), 0.95 * (1 - t) ** 1.2)
    # the puff wraps around the green-bib player but never hides his bib
    bib = cv2.dilate(yellow(img).astype(np.float32), np.ones((3, 3)))
    keep = np.maximum(cv2.GaussianBlur(bib, (5, 5), 0), green_mask(img, sf) * t)[..., None]
    canvas[:] = layer * (1 - keep) + canvas * keep


def burst_points(c, r_out, r_in, n=12, rot=0.0, jitter=None):
    pts = []
    for i in range(2 * n):
        r = r_out if i % 2 == 0 else r_in
        if jitter is not None:
            r *= jitter[i]
        a = rot + i * math.pi / n
        pts.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a)))
    return np.array(pts, np.int32)


JIT = rng.uniform(0.75, 1.15, 24)


def pow_burst(canvas, f):
    t = (f - IMPACT) / 20
    if not 0 <= t <= 1:
        return
    c = (1040, 335)
    grow = ease_out(min(t * 3, 1))
    a = 1 - ease_in_out((t - 0.5) * 2) if t > 0.5 else 1
    layer = canvas.copy()
    cv2.fillPoly(layer, [burst_points(c, 70 * grow, 34 * grow, rot=0.2, jitter=JIT)], (255, 255, 255), cv2.LINE_AA)
    cv2.fillPoly(layer, [burst_points(c, 52 * grow, 24 * grow, rot=0.35, jitter=JIT[::-1])], (40, 220, 255), cv2.LINE_AA)
    canvas[:] = canvas * (1 - a) + layer * a


def twinkle(canvas, f):
    t = (f - LAND) / (N - LAND)
    if not 0 <= t <= 1:
        return
    s = math.sin(min(t / 0.7, 1) * math.pi) if t < 0.7 else 0.25 * math.sin((t - 0.7) / 0.3 * math.pi)
    if s <= 0:
        return
    soft_circle(canvas, P2, 40 * s, (255, 255, 255), 0.75)
    layer = canvas.copy()
    cv2.fillPoly(layer, [burst_points(P2, 56 * s, 7 * s, n=4, rot=t * 2.5)], (255, 255, 255), cv2.LINE_AA)
    cv2.fillPoly(layer, [burst_points(P2, 30 * s, 4 * s, n=4, rot=t * 2.5 + math.pi / 4)], (200, 245, 255), cv2.LINE_AA)
    canvas[:] = layer


def camera(f):
    """Zoom factor and centre: push in on the barge, pull out for the flight."""
    zin = ease_in_out((f - 264) / 54)
    zout = ease_in_out((f - IMPACT - 4) / 50)
    k = zin * (1 - zout)
    z = 1 + 0.5 * k
    c = np.array([SW / 2, SH / 2]) * (1 - k) + np.array([1000.0, 372.0]) * k
    return z, c


def shake(f):
    t = f - IMPACT
    if not 0 <= t < 22:
        return 0.0, 0.0
    amp = 9 * (1 - t / 22) ** 2
    return amp * math.sin(t * 2.7), amp * math.cos(t * 3.9)


font_hook = ImageFont.truetype(FONT, 66)
HOOK = "WAIT FOR THE GUY IN BLACK..."


def draw_hook(img, f):
    t_in = (f - 6) / 14
    t_out = (f - IMPACT) / 6
    if t_in <= 0 or t_out >= 1:
        return img
    s = (1 + 0.6 * (1 - ease_out(t_in))) if t_in < 1 else 1.0
    a = min(t_in * 2, 1) * (1 - max(t_out, 0))
    if t_out > 0:
        s *= 1 + 0.5 * t_out
    pulse = 1 + 0.03 * math.sin(f / FPS * 2 * math.pi * 1.5) if t_in >= 1 else 1
    s *= pulse
    tw, th = font_hook.getbbox(HOOK)[2:]
    layer = Image.new("RGBA", (tw + 40, th + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text((20, 14), HOOK, font=font_hook, fill=(255, 255, 255, 255),
           stroke_width=6, stroke_fill=(0, 0, 0, 255))
    layer = layer.resize((int(layer.width * s), int(layer.height * s)), Image.LANCZOS)
    layer.putalpha(layer.getchannel("A").point(lambda v: int(v * a)))
    base = Image.fromarray(img[..., ::-1])
    base = base.convert("RGBA")
    base.alpha_composite(layer, ((OW - layer.width) // 2, 70 - (layer.height - th - 40) // 2))
    return np.asarray(base.convert("RGB"))[..., ::-1].copy()


enc = subprocess.Popen(
    ["ffmpeg", "-v", "error", "-y",
     "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
     "-i", src, "-map", "0:v", "-map", "1:a", "-c:a", "copy",
     "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
     "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
     "-movflags", "+faststart", out],
    stdin=subprocess.PIPE)

for f in range(N):
    sf = T_SRC[f]
    img = source_image(sf)
    canvas = (remove_black(img, sf) if f >= LAUNCH else img).astype(np.float32)

    dust(canvas, img, sf, f)
    if LAUNCH <= f <= LAND:
        u = (f - LAUNCH) / (LAND - LAUNCH)
        speed_trail(canvas, u)
        paste_sprite(canvas, *flight(u))
    twinkle(canvas, f)
    pow_burst(canvas, f)

    flash = 0.5 * max(0.0, 1 - (f - IMPACT) / 8) if f >= IMPACT else 0
    canvas = canvas + (255 - canvas) * flash

    z, c = camera(f)
    sx, sy = shake(f)
    cw, ch = SW / z, SH / z
    x0 = min(max(c[0] - cw / 2 + sx / z, 0), SW - cw)
    y0 = min(max(c[1] - ch / 2 + sy / z, 0), SH - ch)
    M = np.array([[OW / cw, 0, -x0 * OW / cw], [0, OH / ch, -y0 * OH / ch]])
    img = cv2.warpAffine(np.clip(canvas, 0, 255).astype(np.uint8), M, (OW, OH),
                         flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    img = draw_hook(img, f)
    enc.stdin.write(np.ascontiguousarray(img).tobytes())

enc.stdin.close()
enc.wait()
print(f"rendered {N} frames, impact {IMPACT}, launch {LAUNCH}, land {LAND}")
