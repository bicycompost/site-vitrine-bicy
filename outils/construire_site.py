#!/usr/bin/env python3
"""Transforme une copie wget du site Webflow en site statique autonome.

Usage : python3 outils/construire_site.py <dossier_miroir> <dossier_sortie>

- Les pages de www.bicycompost.fr deviennent <sortie>/<chemin>.html
  (les liens internes restent « propres » : /blog, /a-propos/valeurs, ...).
- Les fichiers hébergés chez Webflow (images, CSS, JS, polices) sont
  rapatriés dans <sortie>/assets/ avec des noms sans espaces ni accents.
- Les attributs « integrity » sont retirés (les fichiers CSS sont réécrits).
"""
import html
import os
import posixpath
import re
import shutil
import sys
import unicodedata
import urllib.parse
import urllib.request

SITE_HOST = "www.bicycompost.fr"
SITE_URL = "https://" + SITE_HOST
ASSET_HOSTS = {
    "cdn.prod.website-files.com": "assets/medias",
    "assets-global.website-files.com": "assets/medias",
    "uploads-ssl.webflow.com": "assets/medias",
    "d3e54v103j8qbb.cloudfront.net": "assets/webflow",
    "ajax.googleapis.com": "assets/vendor",
}

MIRROR, OUT = sys.argv[1], sys.argv[2]
copied = {}      # chemin miroir -> chemin de sortie (relatif à OUT)
missing = set()


def slug(name):
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name)
    return re.sub(r"-{2,}", "-", name).strip("-") or "fichier"


def download(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f)
        return True
    except Exception as e:  # noqa: BLE001
        print("  ! téléchargement impossible :", url, e)
        return False


def asset_out(mirror_rel):
    """Chemin de sortie d'un fichier du miroir (hors pages)."""
    host, _, rest = mirror_rel.partition("/")
    base = ASSET_HOSTS[host]
    parts = [slug(p) for p in rest.split("/")]
    return base + "/" + "/".join(parts)


def mirror_path_for_url(url, base_dir):
    """Retourne (chemin relatif dans le miroir, fragment) ou None si externe."""
    raw = html.unescape(url).strip()
    if not raw or raw.startswith(("data:", "mailto:", "tel:", "javascript:", "#")):
        return None
    frag = ""
    if "#" in raw:
        raw, frag = raw.split("#", 1)
        frag = "#" + frag
    p = urllib.parse.urlsplit(raw)
    if p.scheme in ("http", "https") or raw.startswith("//"):
        host = p.netloc.lower()
        if host == "bicycompost.fr":
            host = SITE_HOST
        if host != SITE_HOST and host not in ASSET_HOSTS:
            return None
        path = urllib.parse.unquote(p.path) or "/"
        rel = host + path
        if host == SITE_HOST:
            rel = rel.rstrip("/")
            if rel == SITE_HOST:
                rel = SITE_HOST + "/index"
            if not rel.endswith(".html") and "." not in posixpath.basename(rel):
                rel += ".html"
        elif not os.path.exists(os.path.join(MIRROR, rel)):
            # fichier Webflow non récupéré par wget (og:image, jquery?site=...)
            if not download(urllib.parse.urlunsplit((p.scheme or "https", p.netloc, p.path, "", "")),
                            os.path.join(MIRROR, rel)):
                return None
        return rel, frag
    if p.scheme:
        return None
    path = urllib.parse.unquote(p.path)
    if not path:
        return None
    rel = posixpath.normpath(posixpath.join(base_dir, path))
    return rel, frag


def new_url(mirror_rel, frag, absolute=False):
    if mirror_rel.startswith(SITE_HOST + "/"):
        page = mirror_rel[len(SITE_HOST) + 1:]
        if page.endswith(".html"):
            page = page[:-5]
            url = "/" if page == "index" else "/" + page
            return (SITE_URL + url if absolute else url) + frag
        out = page  # fichier à la racine (pdf, etc.)
    else:
        if mirror_rel.split("/", 1)[0] not in ASSET_HOSTS:
            return None
        out = asset_out(mirror_rel)
    src = os.path.join(MIRROR, mirror_rel)
    if not os.path.isfile(src):
        missing.add(mirror_rel)
        return None
    copied[mirror_rel] = out
    return (SITE_URL if absolute else "") + "/" + urllib.parse.quote(out) + frag


def rewrite_one(url, base_dir, absolute=False):
    r = mirror_path_for_url(url, base_dir)
    if not r:
        return url
    nu = new_url(r[0], r[1], absolute)
    return html.escape(nu, quote=True) if nu else url


ATTR_RE = re.compile(r'(\s(?:src|href|data-src|poster|action|content))="([^"]*)"')
SRCSET_RE = re.compile(r'(\s(?:srcset|data-srcset))="([^"]*)"')
CSS_URL_RE = re.compile(r'url\((["\']?)([^)"\']+)\1\)')
JSON_URL_RE = re.compile(r'https?://(?:cdn\.prod\.website-files\.com|assets-global\.website-files\.com|uploads-ssl\.webflow\.com)/[^"\'\s<>\\]+')


def rewrite_html(text, base_dir):
    def attr(m):
        name, val = m.group(1), m.group(2)
        if name.strip() == "content" and not val.startswith(("http", "../", "/")):
            return m.group(0)
        if name.strip() == "content":
            return name + '="' + rewrite_one(val, base_dir, absolute=True) + '"'
        return name + '="' + rewrite_one(val, base_dir) + '"'

    def srcset(m):
        items = []
        for item in m.group(2).split(","):
            bits = item.strip().split()
            if bits:
                bits[0] = rewrite_one(bits[0], base_dir)
                items.append(" ".join(bits))
        return m.group(1) + '="' + ", ".join(items) + '"'

    text = re.sub(r'\sintegrity="[^"]*"', "", text)
    text = re.sub(r'<link href="https://cdn\.prod\.website-files\.com" rel="preconnect"[^>]*>', "", text)
    text = ATTR_RE.sub(attr, text)
    text = SRCSET_RE.sub(srcset, text)
    text = CSS_URL_RE.sub(lambda m: "url(" + m.group(1) + rewrite_one(m.group(2), base_dir) + m.group(1) + ")", text)
    # URLs restantes (JSON-LD, scripts inline)
    text = JSON_URL_RE.sub(lambda m: rewrite_one(m.group(0), base_dir, absolute=True), text)
    return text


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    site_dir = os.path.join(MIRROR, SITE_HOST)
    pages = []
    for root, _, files in os.walk(site_dir):
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, MIRROR).replace(os.sep, "/")
            if f.endswith(".html"):
                pages.append(rel)
            else:
                copied[rel] = rel[len(SITE_HOST) + 1:]
    for rel in sorted(pages):
        with open(os.path.join(MIRROR, rel), encoding="utf-8") as fh:
            text = fh.read()
        text = rewrite_html(text, posixpath.dirname(rel))
        dest = os.path.join(OUT, rel[len(SITE_HOST) + 1:])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(text)
    # Copie des fichiers référencés ; les CSS sont réécrits (url(...)).
    done = set()
    while len(done) < len(copied):
        for rel, out in list(copied.items()):
            if rel in done:
                continue
            done.add(rel)
            src, dest = os.path.join(MIRROR, rel), os.path.join(OUT, out)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if rel.endswith(".css"):
                with open(src, encoding="utf-8") as fh:
                    css = fh.read()
                css = CSS_URL_RE.sub(lambda m: "url(" + m.group(1) + rewrite_one(m.group(2), posixpath.dirname(rel)) + m.group(1) + ")", css)
                with open(dest, "w", encoding="utf-8") as fh:
                    fh.write(css)
            else:
                shutil.copyfile(src, dest)
    print(f"{len(pages)} pages, {len(copied) - len(pages)} fichiers copiés")
    for m in sorted(missing):
        print("  ! introuvable dans le miroir :", m)


main()
