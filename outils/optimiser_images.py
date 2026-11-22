#!/usr/bin/env python3
"""Allège les images du site : conversion PNG/JPEG -> WebP et réduction des
images démesurées (largeur max 2400 px). Les références dans les pages HTML
et les CSS sont mises à jour.

Les images citées en adresse absolue (aperçus de partage og:image, logo
JSON-LD) gardent leur format d'origine : certains réseaux sociaux lisent mal
le WebP.

Usage : python3 outils/optimiser_images.py [dossier_site]
"""
import os
import re
import sys

from PIL import Image

SITE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "site")
SITE_URL = "https://www.bicycompost.fr"
MAX_W = 2400
MIN_BYTES = 40_000      # en dessous, le gain ne vaut pas la peine
QUALITY = 82

texts = {}
for root, _, files in os.walk(SITE):
    for f in files:
        if f.endswith((".html", ".css")):
            p = os.path.join(root, f)
            with open(p, encoding="utf-8") as fh:
                texts[p] = fh.read()

before = after = 0
converted = 0
for root, _, files in os.walk(os.path.join(SITE, "assets")):
    for f in files:
        p = os.path.join(root, f)
        ext = f.rsplit(".", 1)[-1].lower() if "." in f else ""
        if ext not in ("png", "jpg", "jpeg", "webp"):
            continue
        size = os.path.getsize(p)
        if size < MIN_BYTES:
            continue
        try:
            im = Image.open(p)
            if getattr(im, "is_animated", False):
                continue
            im.load()
        except Exception as e:  # noqa: BLE001
            print("  ! illisible :", p, e)
            continue
        if im.width > MAX_W:
            im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA" if "A" in im.getbands() or "transparency" in im.info else "RGB")
        web = "/" + os.path.relpath(p, SITE).replace(os.sep, "/")
        if ext == "webp" and os.path.exists(p.rsplit(".", 1)[0] + ".png") or ext == "webp" and im.width <= MAX_W and size < 400_000:
            continue
        if ext == "webp":
            tmp = p + ".tmp"
            im.save(tmp, "WEBP", quality=QUALITY, method=6)
            if os.path.getsize(tmp) < size * 0.9:
                os.replace(tmp, p)
            else:
                os.remove(tmp)
            before += size
            after += os.path.getsize(p)
            continue
        new_p = p.rsplit(".", 1)[0] + ".webp"
        if os.path.exists(new_p):
            continue  # déjà converti (original gardé pour les aperçus de partage)
        im.save(new_p, "WEBP", quality=QUALITY, method=6)
        new_size = os.path.getsize(new_p)
        if new_size > size * 0.9:
            os.remove(new_p)
            continue
        new_web = "/" + os.path.relpath(new_p, SITE).replace(os.sep, "/")
        # remplace les chemins relatifs au site, pas les adresses absolues
        pat = re.compile(r"(?<!" + re.escape(SITE_URL) + r")" + re.escape(web) + r"(?![\w.-])")
        still_absolute = False
        for tp, t in texts.items():
            if web in t:
                texts[tp] = pat.sub(new_web, t)
                if SITE_URL + web in texts[tp]:
                    still_absolute = True
        before += size
        after += new_size
        converted += 1
        if still_absolute:
            after += size
        else:
            os.remove(p)

for tp, t in texts.items():
    with open(tp, "w", encoding="utf-8") as fh:
        fh.write(t)

print(f"{converted} images converties en WebP")
print(f"images traitées : {before / 1e6:.1f} Mo -> {after / 1e6:.1f} Mo")

# Polices : OTF -> WOFF2 (3 fois plus léger, même rendu)
try:
    from fontTools.ttLib import TTFont
except ImportError:
    TTFont = None
    print("fontTools absent : polices non converties (pip install fonttools brotli)")
if TTFont:
    css_files = [p for p in texts if p.endswith(".css")]
    for root, _, files in os.walk(os.path.join(SITE, "assets")):
        for f in files:
            if not f.lower().endswith((".otf", ".ttf")):
                continue
            p = os.path.join(root, f)
            web = "/" + os.path.relpath(p, SITE).replace(os.sep, "/")
            new_p = p.rsplit(".", 1)[0] + ".woff2"
            font = TTFont(p)
            font.flavor = "woff2"
            font.save(new_p)
            new_web = "/" + os.path.relpath(new_p, SITE).replace(os.sep, "/")
            fmt = re.compile(re.escape(web) + r'(["\']?\))\s*format\(["\'](?:opentype|truetype)["\']\)')
            for cp in css_files:
                with open(cp, encoding="utf-8") as fh:
                    css = fh.read()
                css2 = fmt.sub(new_web + r'\1 format("woff2")', css)
                if css2 != css:
                    with open(cp, "w", encoding="utf-8") as fh:
                        fh.write(css2)
            print(f"police {f}: {os.path.getsize(p) // 1000} ko -> {os.path.getsize(new_p) // 1000} ko")
            os.remove(p)
