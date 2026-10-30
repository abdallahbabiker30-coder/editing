#!/usr/bin/env python3
"""Before/after reel renderer (1080x1920, TikTok + Instagram Reels).

Usage:
    python3 ba_reel.py config.json            # full render
    python3 ba_reel.py config.json --preview  # contact sheet of key frames only, no video

Everything is driven by the JSON config: assets (photos, with optional face
anchors so before and after line up), a list of timed segments (still, clip,
wipe, slider, split, flash, card) and text overlays. See PLAYBOOK.md for the
recommended structures and example_config.json for a working example.
"""
import json
import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H = 1080, 1920
SS = 1.5  # supersampling of the asset canvases, so push-ins stay sharp
CW, CH = int(W * SS), int(H * SS)

# Text positions (centre y). The bottom ~400 px and right ~140 px are covered by
# the TikTok / Reels UI, so nothing important goes there.
POS = {"top": 300, "upper": 520, "center": 960, "lower": 1300, "bottom": 1450}
SAFE_W = 900

ARABIC = range(0x0600, 0x06FF + 1)


def ease(t, kind="inout"):
    t = min(max(t, 0.0), 1.0)
    if kind == "out":
        return 1 - (1 - t) ** 3
    if kind == "in":
        return t ** 3
    if kind == "linear":
        return t
    return 3 * t * t - 2 * t * t * t if kind == "smooth" else (4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2)


def hex2rgb(h, a=255):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


# ---------------------------------------------------------------- assets

def similarity(src_pts, dst_pts):
    """2-point similarity transform (scale, rotation, translation) src -> dst as a 2x3 matrix."""
    (x1, y1), (x2, y2) = src_pts
    (u1, v1), (u2, v2) = dst_pts
    sv = complex(x2 - x1, y2 - y1)
    dv = complex(u2 - u1, v2 - v1)
    r = dv / sv
    t = complex(u1, v1) - r * complex(x1, y1)
    return np.array([[r.real, -r.imag, t.real], [r.imag, r.real, t.imag]])


def warp(img, M):
    """Render img through forward matrix M onto a CWxCH canvas."""
    A = np.vstack([M, [0, 0, 1]])
    inv = np.linalg.inv(A)
    coeffs = (inv[0, 0], inv[0, 1], inv[0, 2], inv[1, 0], inv[1, 1], inv[1, 2])
    return img.transform((CW, CH), Image.AFFINE, coeffs, resample=Image.BICUBIC, fillcolor=(235, 233, 228))


def grade(img, g):
    if not g:
        return img
    a = np.asarray(img).astype(np.float32) / 255.0
    a = a * g.get("exposure", 1.0)
    c = g.get("contrast", 1.0)
    a = (a - 0.5) * c + 0.5
    s = g.get("saturation", 1.0)
    lum = (a * [0.299, 0.587, 0.114]).sum(axis=2, keepdims=True)
    a = lum + (a - lum) * s
    w = g.get("warmth", 0.0)
    a[..., 0] += w * 0.03
    a[..., 2] -= w * 0.03
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def load_assets(cfg, base):
    """Each asset becomes a CWxCH canvas. An asset with `align_to` is warped so
    its two anchor points land exactly where the reference asset's anchors land."""
    specs = cfg["assets"]
    out, mats = {}, {}
    order = sorted(specs, key=lambda k: 1 if "align_to" in specs[k] else 0)
    for name in order:
        s = specs[name]
        img = ImageOps.exif_transpose(Image.open(os.path.join(base, s["src"]))).convert("RGB")
        if "align_to" in s:
            ref = specs[s["align_to"]]
            Mref = mats[s["align_to"]]
            dst = [tuple(Mref @ np.array([p[0], p[1], 1.0])) for p in ref["anchors"]]
            M = similarity(s["anchors"], dst)
        else:
            # Frame by focus point (source px) placed at frame_pos (fraction of frame) at `scale`
            # (output px per source px, before supersampling). Default: cover-fit, centred.
            iw, ih = img.size
            scale = s.get("scale", max(W / iw, H / ih)) * SS
            fx, fy = s.get("focus", [iw / 2, ih / 2])
            px, py = s.get("frame_pos", [0.5, 0.5])
            M = np.array([[scale, 0, px * CW - fx * scale], [0, scale, py * CH - fy * scale]])
        mats[name] = M
        out[name] = grade(warp(img, M), {**cfg.get("grade", {}), **s.get("grade", {})})
    return out


def view(canvas, zoom=1.0, center=(0.5, 0.5)):
    """Crop a CWxCH canvas around a normalised centre at a zoom factor, return WxH."""
    cw, ch = CW / zoom, CH / zoom
    cx = min(max(center[0] * CW, cw / 2), CW - cw / 2)
    cy = min(max(center[1] * CH, ch / 2), CH - ch / 2)
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    return canvas.resize((W, H), Image.LANCZOS if zoom < 1.2 else Image.BICUBIC, box=box)


def lerp(a, b, t):
    if isinstance(a, (list, tuple)):
        return [lerp(x, y, t) for x, y in zip(a, b)]
    return a + (b - a) * t


def cam(seg, t):
    """Camera move over a segment: zoom [z0,z1] and center [[x0,y0],[x1,y1]] (or single values)."""
    k = ease(t, seg.get("ease", "inout"))
    z = seg.get("zoom", 1.0)
    z = lerp(z[0], z[1], k) if isinstance(z, list) else z
    c = seg.get("center", [0.5, 0.5])
    c = lerp(c[0], c[1], k) if isinstance(c[0], list) else c
    return z, c


# ---------------------------------------------------------------- text

class Fonts:
    def __init__(self, cfg, base):
        self.latin = self._resolve(cfg.get("font"), base, [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "NimbusSansNarrow-Bold.otf"),
            "/mnt/project-files/reels/fonts/NimbusSansNarrow-Bold.otf",
        ])
        self.arabic = self._resolve(cfg.get("font_ar"), base, ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"])
        self.cache = {}

    @staticmethod
    def _resolve(p, base, fallbacks):
        for c in ([os.path.join(base, p)] if p else []) + fallbacks:
            if c and os.path.exists(c):
                return c
        raise SystemExit("font not found: %s" % p)

    def get(self, size, text):
        ar = any(ord(ch) in ARABIC for ch in text)
        key = (size, ar)
        if key not in self.cache:
            self.cache[key] = ImageFont.truetype(self.arabic if ar else self.latin, size,
                                                 layout_engine=ImageFont.Layout.RAQM)
        return self.cache[key], ar


def wrap(draw, text, font, maxw, ar):
    kw = {"direction": "rtl"} if ar else {}
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            test = (cur + " " + word).strip()
            if draw.textlength(test, font=font, **kw) <= maxw or not cur:
                cur = test
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def draw_text(frame, item, fonts, local_t, style_defaults):
    """item: {text, pos|y, size, style: box|outline|label|plain, color, bg, start, end, anim}"""
    st = {**style_defaults, **item}
    text = st["text"]
    size = st.get("size", 82)
    font, ar = fonts.get(size, text)
    kw = {"direction": "rtl", "language": "ar"} if ar else {}
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    lines = wrap(d, text, font, st.get("max_width", SAFE_W), ar)
    asc, desc = font.getmetrics()
    lh = int((asc + desc) * st.get("line_height", 1.08))
    y0 = st.get("y", POS.get(st.get("pos", "top"), 300))
    total = lh * len(lines)
    y = y0 - total / 2
    style = st.get("style", "box")
    color = hex2rgb(st.get("color", "#000000" if style == "box" else "#FFFFFF"))
    bg = hex2rgb(st.get("bg", "#FFFFFF" if style == "box" else "#111111"),
                 int(255 * st.get("bg_alpha", 1.0 if style == "box" else 0.82)))
    x_center = st.get("x", W / 2)
    for line in lines:
        tw = d.textlength(line, font=font, **kw)
        x = x_center - tw / 2
        if style in ("box", "label"):
            padx, pady = (size * 0.32, size * 0.12) if style == "box" else (size * 0.45, size * 0.18)
            d.rounded_rectangle([x - padx, y - pady + size * 0.06, x + tw + padx, y + lh - pady * 0.2],
                                radius=int(size * (0.18 if style == "box" else 0.5)), fill=bg)
            d.text((x, y), line, font=font, fill=color, **kw)
        elif style == "outline":
            d.text((x, y), line, font=font, fill=color, stroke_width=max(4, size // 11),
                   stroke_fill=hex2rgb(st.get("stroke", "#000000")), **kw)
        else:
            d.text((x, y), line, font=font, fill=color, **kw)
        y += lh
    # entrance animation
    anim = st.get("anim", "pop")
    if anim == "pop" and local_t < 0.18:
        k = ease(local_t / 0.18, "out")
        s = 0.82 + 0.18 * k + 0.06 * math.sin(k * math.pi)
        bbox = layer.getbbox()
        if bbox:
            cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
            layer = layer.transform((W, H), Image.AFFINE, (1 / s, 0, cx - cx / s, 0, 1 / s, cy - cy / s),
                                    resample=Image.BICUBIC)
            a = layer.getchannel("A").point(lambda v: int(v * min(1, k * 1.6)))
            layer.putalpha(a)
    elif anim == "fade" and local_t < 0.25:
        a = layer.getchannel("A").point(lambda v: int(v * local_t / 0.25))
        layer.putalpha(a)
    frame.alpha_composite(layer)


# ---------------------------------------------------------------- segments

def seg_frames(seg, assets, clips, fps):
    n = max(1, round(seg["dur"] * fps))
    typ = seg["type"]
    for i in range(n):
        t = i / max(1, n - 1)
        if typ == "still":
            z, c = cam(seg, t)
            yield view(assets[seg["asset"]], z, c)
        elif typ == "clip":
            frames = clips[id(seg)]
            yield frames[min(i, len(frames) - 1)]
        elif typ in ("wipe", "slider"):
            z, c = cam(seg, t)
            a, b = view(assets[seg["from"]], z, c), view(assets[seg["to"]], z, c)
            if typ == "wipe":
                hold = seg.get("hold", 0.25)  # fraction of the segment spent holding at each end
                p = ease((t - hold) / max(1e-6, 1 - 2 * hold), seg.get("wipe_ease", "inout"))
            else:
                p = 0.5 - 0.5 * math.cos(t * math.pi * 2 * seg.get("sweeps", 1))
                p = 0.08 + 0.84 * p
            yield wipe(a, b, p, seg.get("direction", "lr"), seg.get("line", True))
        elif typ == "split":
            yield split(seg, assets)
        elif typ == "flash":
            period = max(1, round(seg.get("every", 0.25) * fps))
            name = seg["assets"][(i // period) % len(seg["assets"])]
            z, c = cam(seg, t)
            yield view(assets[name], z, c)
        elif typ == "card":
            img = Image.new("RGB", (W, H), seg.get("bg", "#000000"))
            if seg.get("logo"):
                logo = Image.open(seg["logo_path"]).convert("RGBA")
                logo.thumbnail((seg.get("logo_width", 520), 520))
                img.paste(logo, ((W - logo.width) // 2, seg.get("logo_y", 640) - logo.height // 2), logo)
            if seg.get("asset"):
                z, c = cam(seg, t)
                v = view(assets[seg["asset"]], z, c).filter(ImageFilter.GaussianBlur(seg.get("blur", 24)))
                img = Image.blend(v, Image.new("RGB", (W, H), "black"), seg.get("dim", 0.45))
            yield img
        else:
            raise SystemExit("unknown segment type " + typ)


def wipe(a, b, p, direction, line):
    """Reveal b over a. p=0 shows all a, p=1 all b."""
    out = a.copy()
    if direction in ("lr", "rl"):
        x = int(W * p) if direction == "lr" else int(W * (1 - p))
        box = (0, 0, x, H) if direction == "lr" else (x, 0, W, H)
        edge = [(x - 3, 0), (x + 3, H)]
    else:
        y = int(H * p) if direction == "tb" else int(H * (1 - p))
        box = (0, 0, W, y) if direction == "tb" else (0, y, W, H)
        edge = [(0, y - 3), (W, y + 3)]
    if box[2] > box[0] and box[3] > box[1]:
        out.paste(b.crop(box), box[:2])
    if line and 0.005 < p < 0.995:
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.rectangle(edge, fill=(255, 255, 255, 255))
        glow = Image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(9)), glow)
        out = Image.alpha_composite(out.convert("RGBA"), glow).convert("RGB")
    return out


def split(seg, assets):
    """Two assets side by side ("side") or stacked ("stack"); each panel crops around its own centre."""
    img = Image.new("RGB", (W, H), "white")
    names = seg["assets"]
    zooms = seg.get("zooms", [1.0, 1.0])
    centers = seg.get("centers", [[0.5, 0.5], [0.5, 0.5]])
    gap = seg.get("gap", 6)
    if seg.get("layout", "stack") == "stack":
        ph = (H - gap) // 2
        for k, name in enumerate(names):
            v = view(assets[name], zooms[k], centers[k])
            # panel aspect is 1080x957: take the middle band of the view
            top = int((H - ph) / 2)
            img.paste(v.crop((0, top, W, top + ph)), (0, k * (ph + gap)))
    else:
        pw = (W - gap) // 2
        for k, name in enumerate(names):
            v = view(assets[name], zooms[k], centers[k])
            left = int((W - pw) / 2)
            img.paste(v.crop((left, 0, left + pw, H)), (k * (pw + gap), 0))
    return img


def load_clip(seg, base, fps):
    """Decode a video segment to WxH frames with ffmpeg (auto-rotates, tone-maps nothing: SDR only)."""
    speed = seg.get("speed", 1.0)
    n = max(1, round(seg["dur"] * fps))
    fx = seg.get("focus_x", 0.5)
    vf = (f"setpts=PTS/{speed},fps={fps},scale=-2:{H}:flags=lanczos,"
          f"crop={W}:{H}:(iw-{W})*{fx}:0,format=rgb24")
    if seg.get("zoom", 1.0) != 1.0:
        z = seg["zoom"]
        vf = vf.replace(f"scale=-2:{H}", f"scale=-2:{int(H * z)}").replace(
            f"crop={W}:{H}:(iw-{W})*{fx}:0", f"crop={W}:{H}:(iw-{W})*{fx}:(ih-{H})*{seg.get('focus_y', 0.5)}")
    cmd = ["ffmpeg", "-v", "error", "-ss", str(seg.get("start", 0)), "-i", os.path.join(base, seg["src"]),
           "-t", str(seg["dur"] * speed + 0.5), "-vf", vf, "-frames:v", str(n), "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, check=True, stdout=subprocess.PIPE).stdout
    fr = [Image.frombuffer("RGB", (W, H), raw[i * W * H * 3:(i + 1) * W * H * 3]) for i in range(len(raw) // (W * H * 3))]
    if not fr:
        raise SystemExit("could not decode clip " + seg["src"])
    return fr


# ---------------------------------------------------------------- sound design

SR = 48000


def sfx_track(events, total):
    """Synthesised, royalty-free sound design: whoosh on wipes, sub hit on reveals, tick on flashes."""
    out = np.zeros(int(total * SR) + SR)
    rng = np.random.default_rng(7)
    for kind, at, dur, gain in events:
        i0 = int(at * SR)
        if kind == "whoosh":
            n = int(dur * SR)
            noise = rng.standard_normal(n)
            # sweep a one-pole low-pass from dark to bright and back
            cut = np.sin(np.linspace(0, np.pi, n)) ** 1.5
            y = np.zeros(n)
            acc = 0.0
            for k in range(n):
                a = 0.02 + 0.5 * cut[k]
                acc += a * (noise[k] - acc)
                y[k] = acc
            env = np.sin(np.linspace(0, np.pi, n)) ** 2
            s = y * env * 0.9
        elif kind == "hit":
            n = int(0.7 * SR)
            tt = np.arange(n) / SR
            f = 55 + 90 * np.exp(-tt * 18)
            s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 5.5)
            s += 0.25 * rng.standard_normal(n) * np.exp(-tt * 60)
        elif kind == "tick":
            n = int(0.06 * SR)
            tt = np.arange(n) / SR
            s = (np.sin(2 * np.pi * 2400 * tt) * 0.5 + rng.standard_normal(n) * 0.3) * np.exp(-tt * 90)
        else:
            continue
        s = s / (np.abs(s).max() + 1e-9) * gain
        end = min(len(out), i0 + len(s))
        out[i0:end] += s[:end - i0]
    return out[: int(total * SR)]


def write_wav(path, mono):
    pcm = (np.clip(mono, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- main

def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cfg_path = sys.argv[1]
    preview = "--preview" in sys.argv
    cfg = json.load(open(cfg_path))
    base = os.path.abspath(cfg.get("media_dir", os.path.dirname(os.path.abspath(cfg_path))))
    fps = cfg.get("fps", 30)
    out_path = cfg["output"] if os.path.isabs(cfg["output"]) else os.path.join(os.path.dirname(os.path.abspath(cfg_path)), cfg["output"])
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    print("loading assets…")
    assets = load_assets(cfg, base)
    fonts = Fonts(cfg, base)
    segs = cfg["segments"]
    clips = {id(s): load_clip(s, base, fps) for s in segs if s["type"] == "clip"}
    style_defaults = cfg.get("text_style", {})

    # timeline + sound events
    t = 0.0
    events = []
    for s in segs:
        s["_t0"] = t
        if s["type"] == "wipe":
            hold = s.get("hold", 0.25)
            events.append(("whoosh", t + s["dur"] * hold - 0.05, s["dur"] * (1 - 2 * hold) + 0.15, 0.55))
        if s.get("hit"):
            events.append(("hit", t, 0, 0.8))
        if s["type"] == "flash":
            every = s.get("every", 0.25)
            for k in range(int(s["dur"] / every)):
                events.append(("tick", t + k * every, 0, 0.35))
        t += s["dur"]
    total = t
    overlays = cfg.get("overlays", [])  # global text with absolute start/end times

    if preview:
        thumbs = []
        for s in segs:
            fr = list(seg_frames({**s, "dur": max(s["dur"], 3 / fps)}, assets, clips, fps))
            for k in (0.0, 0.5, 1.0):
                f = fr[min(int(k * (len(fr) - 1)), len(fr) - 1)].convert("RGBA")
                lt = s["_t0"] + k * s["dur"]
                for item in s.get("text", []):
                    if item.get("start", 0) <= k * s["dur"] * 0.999 < item.get("end", 1e9):
                        draw_text(f, item, fonts, 1.0, style_defaults)
                for item in overlays:
                    if item["start"] <= lt <= item["end"]:
                        draw_text(f, item, fonts, 1.0, style_defaults)
                thumbs.append(f.convert("RGB").resize((270, 480)))
        cols = 9
        sheet = Image.new("RGB", (270 * cols, 480 * math.ceil(len(thumbs) / cols)), "white")
        for i, th in enumerate(thumbs):
            sheet.paste(th, ((i % cols) * 270, (i // cols) * 480))
        p = os.path.splitext(out_path)[0] + "_preview.jpg"
        sheet.save(p, quality=85)
        print("preview:", p)
        return

    tmp_v = out_path + ".video.mp4"
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                            "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709",
                            "-colorspace", "bt709", tmp_v], stdin=subprocess.PIPE)
    nframes = 0
    for s in segs:
        for i, f in enumerate(seg_frames(s, assets, clips, fps)):
            lt = i / fps
            gt = s["_t0"] + lt
            f = f.convert("RGBA")
            for item in s.get("text", []):
                if item.get("start", 0) <= lt < item.get("end", 1e9):
                    draw_text(f, item, fonts, lt - item.get("start", 0), style_defaults)
            for item in overlays:
                if item["start"] <= gt < item["end"]:
                    draw_text(f, item, fonts, gt - item["start"], style_defaults)
            enc.stdin.write(f.convert("RGB").tobytes())
            nframes += 1
        print(f"  {s['type']:<6} {s['dur']:.2f}s done ({nframes} frames)")
    enc.stdin.close()
    enc.wait()

    # audio: sound design + optional music
    sfx_wav = out_path + ".sfx.wav"
    write_wav(sfx_wav, sfx_track(events, total) if cfg.get("sfx", True) else np.zeros(int(total * SR)))
    variants = [(out_path, cfg.get("music"))]
    if cfg.get("music") and cfg.get("also_no_music", True):
        variants.append((os.path.splitext(out_path)[0] + "-no-music.mp4", None))
    for path, music in variants:
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", tmp_v, "-i", sfx_wav]
        if music:
            mp = music if os.path.isabs(music) else os.path.join(base, music)
            cmd += ["-ss", str(cfg.get("music_start", 0)), "-i", mp]
            fc = (f"[2:a]volume={cfg.get('music_volume', 0.8)},afade=t=out:st={total - 0.8}:d=0.8[m];"
                  f"[1:a]volume={cfg.get('sfx_volume', 1.0)}[s];[m][s]amix=inputs=2:normalize=0,"
                  f"loudnorm=I=-14:TP=-1.5:LRA=11[a]")
        else:
            fc = f"[1:a]volume={cfg.get('sfx_volume', 1.0)},alimiter=limit=0.7:level=disabled[a]"
        cmd += ["-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-ar", "48000", "-t", f"{total:.3f}", "-movflags", "+faststart", path]
        subprocess.run(cmd, check=True)
        print("wrote", path)
    os.remove(tmp_v)
    os.remove(sfx_wav)


if __name__ == "__main__":
    main()
