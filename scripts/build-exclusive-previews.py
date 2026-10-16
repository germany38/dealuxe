"""Render a protected preview (low-res, blurred body, watermarked) of each exclusive PDF's first page.

Usage: python scripts/build-exclusive-previews.py exclusive-files exclusive/previews [slug ...]
Needs: pip install pymupdf pillow
"""
import sys, os, io, pymupdf
from PIL import Image, ImageFilter, ImageDraw, ImageFont
src, out = sys.argv[1], sys.argv[2]
only = sys.argv[3:] or None
os.makedirs(out, exist_ok=True)
W = 360
try: font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
except Exception: font = ImageFont.load_default()
files = sorted(f for f in os.listdir(src) if f.endswith(".pdf"))
for f in files:
    slug = f[:-4]
    if only and slug not in only: continue
    doc = pymupdf.open(os.path.join(src, f)); pg = doc[0]
    z = W / pg.rect.width
    pix = pg.get_pixmap(matrix=pymupdf.Matrix(z, z), alpha=False)
    im = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    w, h = im.size
    cut = int(h * 0.2)  # header band stays recognisable, the body is frosted
    body = im.crop((0, cut, w, h)).resize((w // 4, (h - cut) // 4)).resize((w, h - cut), Image.BILINEAR).filter(ImageFilter.GaussianBlur(3))
    im.paste(body, (0, cut))
    # diagonal tiled watermark baked into the pixels
    mark = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(mark)
    for y in range(0, h * 2, 90):
        for x in range(-((y // 90) % 2) * 160, w * 2, 320):
            d.text((x, y), "DEALUX PREVIEW", font=font, fill=(122, 90, 18, 55))
    mark = mark.rotate(30, resample=Image.BICUBIC).crop((w // 2, h // 2, w // 2 + w, h // 2 + h))
    im = Image.alpha_composite(im.convert("RGBA"), mark).convert("RGB")
    im.save(os.path.join(out, slug + ".webp"), "WEBP", quality=55, method=6)
