#!/usr/bin/env python3
"""Aperçu local : python3 outils/apercu.py  puis ouvrir http://localhost:8000
Sert le dossier site/ avec les mêmes adresses que le site en ligne (/blog -> blog.html)."""
import http.server, os, functools
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site")
class H(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        path = self.path.split("?")[0].split("#")[0].rstrip("/")
        local = self.translate_path(path)
        if path and not os.path.isfile(local) and os.path.exists(local + ".html"):
            self.path = path + ".html"
        elif path and not os.path.exists(local):
            self.path = "/404.html"
            f = super().send_head()
            return f
        return super().send_head()
port = int(os.environ.get("PORT", 8000))
print(f"Aperçu sur http://localhost:{port}")
http.server.ThreadingHTTPServer(("", port), functools.partial(H, directory=ROOT)).serve_forever()
