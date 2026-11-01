import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
crop = Image.open("crop.png").convert("RGB")
mask = Image.open("mask_birefnet-portrait.png").convert("L")
box = (105, 110, 595, 600)  # square, head & shoulders
fg = crop.crop(box); m = mask.crop(box)
S = 1080
fg = fg.resize((S, S), Image.LANCZOS)
m = m.resize((S, S), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.2))
# gentle tone lift for a night photo
fg = ImageEnhance.Brightness(fg).enhance(1.10)
fg = ImageEnhance.Contrast(fg).enhance(1.05)
fg = fg.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
def bg(c_center, c_edge):
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    d = np.sqrt((xx - S*0.5)**2 + (yy - S*0.35)**2) / (S*0.8)
    d = np.clip(d, 0, 1)[..., None]
    a = np.array(c_center, np.float32); b = np.array(c_edge, np.float32)
    return Image.fromarray((a*(1-d) + b*d).astype(np.uint8))
for name, cc, ce in [("gray", (205,208,212), (130,135,142)),
                     ("blue", (120,150,185), (35,55,85))]:
    out = Image.composite(fg, bg(cc, ce), m)
    out.save(f"/home/user/editing/output/linkedin_profile_{name}.jpg", quality=95)
# blurred original background version
blur = crop.crop(box).resize((S,S), Image.LANCZOS).filter(ImageFilter.GaussianBlur(18))
blur = ImageEnhance.Brightness(blur).enhance(0.8)
Image.composite(fg, blur, m).save("/home/user/editing/output/linkedin_profile_blur.jpg", quality=95)
