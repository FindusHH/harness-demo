#!/usr/bin/env python3
"""Erzeugt aus der Schulungs-Markdown-Datei ein PDF (A4 hoch).

Aufruf (die venv mit weasyprint/markdown liegt unter ../Data Science Curriculum/.venv):

    DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib \
        "../Data Science Curriculum/.venv/bin/python" build_pdf.py

Mermaid-Diagramme werden mit dem Mermaid-CLI (npx @mermaid-js/mermaid-cli) zu SVG
gerendert und als Grafik eingebettet.
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# macOS: Homebrew-Bibliotheken (Pango/GObject fuer WeasyPrint) auffindbar machen.
if sys.platform == "darwin":
    _brew_lib = "/opt/homebrew/lib"
    _dyld = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
    if os.path.isdir(_brew_lib) and _brew_lib not in _dyld.split(":"):
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = f"{_brew_lib}:{_dyld}" if _dyld else _brew_lib
        os.execv(sys.executable, [sys.executable] + sys.argv)

import markdown
from weasyprint import HTML

BASE_DIR = Path(__file__).parent
SOURCE = BASE_DIR / "Agent-Harnessing-Schulung.md"
OUTPUT = BASE_DIR / "Agent-Harnessing-Schulung.pdf"
ASSETS_DIR = BASE_DIR / "_mermaid_assets"

MD_EXTENSIONS = ["tables", "fenced_code", "sane_lists", "toc", "md_in_html"]

MERMAID_BLOCK = re.compile(r"```mermaid\s*\n(.*?)\n```", re.DOTALL)


def render_mermaid_to_svg(code: str, index: int) -> Path:
    """Rendert einen Mermaid-Quelltext zu PNG und gibt den Dateipfad zurueck.

    PNG statt SVG, weil WeasyPrint die HTML-basierten Textlabels in Mermaid-SVGs
    (foreignObject) nicht rendert und die Diagramme sonst ohne Text erscheinen.
    """
    ASSETS_DIR.mkdir(exist_ok=True)
    out_png = ASSETS_DIR / f"diagram_{index:02d}.png"
    with tempfile.NamedTemporaryFile("w", suffix=".mmd", delete=False, encoding="utf-8") as tmp:
        tmp.write(code)
        tmp_path = Path(tmp.name)
    try:
        subprocess.run(
            ["npx", "-y", "@mermaid-js/mermaid-cli", "-i", str(tmp_path),
             "-o", str(out_png), "-b", "white", "-w", "1600", "-s", "2"],
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        tmp_path.unlink(missing_ok=True)
    return out_png


def replace_mermaid_blocks(text: str) -> str:
    """Ersetzt alle Mermaid-Bloecke durch eingebettete SVG-Grafiken."""
    counter = {"i": 0}

    def _sub(match: re.Match) -> str:
        counter["i"] += 1
        code = match.group(1)
        svg = render_mermaid_to_svg(code, counter["i"])
        rel = svg.relative_to(BASE_DIR)
        print(f"  Mermaid-Diagramm {counter['i']} -> {rel}")
        return f'<p class="mermaid-figure"><img class="mermaid-img" src="{rel}" alt="Diagramm {counter["i"]}"></p>'

    return MERMAID_BLOCK.sub(_sub, text)


CSS = """
@page {
    size: A4 portrait;
    margin: 2cm 1.8cm 2cm 1.8cm;
    @bottom-right { content: "Seite " counter(page) " / " counter(pages); font-size: 8pt; color: #888; }
}
* { box-sizing: border-box; }
body { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; color: #1f2430; font-size: 10.5pt; line-height: 1.5; }

h1 { font-size: 22pt; color: #1f3a5f; margin: 0 0 0.5em 0; }
h2 { font-size: 16pt; color: #1f3a5f; margin: 1.1em 0 0.5em 0; padding-bottom: 0.2em; border-bottom: 2pt solid #e8a33d; page-break-after: avoid; }
h3 { font-size: 13pt; color: #1f3a5f; margin: 0.9em 0 0.3em 0; page-break-after: avoid; }

p, li { font-size: 10.5pt; }
ul, ol { margin: 0.3em 0 0.7em 0; padding-left: 1.3em; }
li { margin-bottom: 0.2em; }
strong { color: #14243a; }

a { color: #1f3a5f; text-decoration: none; word-break: break-all; }

hr { border: none; border-top: 1pt solid #d5dae2; margin: 1.2em 0; }

blockquote {
    margin: 0.6em 0; padding: 0.5em 0.9em;
    background: #f3f6fb; border-left: 3pt solid #1f3a5f; color: #33415c;
}

table { border-collapse: collapse; width: 100%; margin: 0.6em 0; font-size: 9pt; page-break-inside: avoid; }
th, td { border: 0.75pt solid #c9d1dc; padding: 4pt 6pt; text-align: left; vertical-align: top; }
th { background: #1f3a5f; color: #fff; }
tr:nth-child(even) td { background: #f5f7fb; }

code { font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace; font-size: 8.6pt; background: #eef1f6; padding: 1pt 3pt; border-radius: 3px; color: #b8003a; }
pre { background: #f6f8fa; border: 0.75pt solid #d5dae2; border-radius: 5px; padding: 8pt 10pt; overflow-x: auto; page-break-inside: avoid; margin: 0.5em 0; }
pre code { background: none; color: #24292e; padding: 0; font-size: 8.6pt; }

/* Gerenderte Mermaid-Diagramme als Grafik. */
.mermaid-figure { text-align: center; margin: 0.8em 0; page-break-inside: avoid; }
.mermaid-img { max-width: 100%; height: auto; }
"""


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Quelldatei nicht gefunden: {SOURCE}")

    text = SOURCE.read_text(encoding="utf-8")
    text = replace_mermaid_blocks(text)
    html_body = markdown.markdown(text, extensions=MD_EXTENSIONS)
    html_doc = (
        f"<!DOCTYPE html><html lang='de'><head><meta charset='utf-8'>"
        f"<style>{CSS}</style></head><body>{html_body}</body></html>"
    )
    HTML(string=html_doc, base_url=str(BASE_DIR)).write_pdf(str(OUTPUT))
    print(f"PDF erstellt: {OUTPUT}")


if __name__ == "__main__":
    main()
