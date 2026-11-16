"""Build a printable PDF of the CV from _config.yml.

The site content lives in _config.yml, so this script reads the same data
and lays it out as a clean A4 PDF. Re-run it after editing _config.yml so
the download on the site stays in step with the page.

Usage (from the repo root):
    python -m pip install fpdf2 pyyaml
    python tools/build_cv.py
"""

import re
import sys
from pathlib import Path

import yaml
from fpdf import FPDF

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "_config.yml"
OUTPUT = ROOT / "Felix-Saville-CV.pdf"

FONT_DIR = Path("C:/Windows/Fonts")
FONTS = {"": "segoeui.ttf", "B": "segoeuib.ttf"}

BLUE = (43, 108, 176)
DARK = (31, 41, 51)
GREY = (82, 96, 109)
RULE = (217, 226, 236)

MARGIN = 16


def clean(text):
    """Strip HTML tags and markdown links, and tidy whitespace."""
    text = re.sub(r"<a\b[^>]*>.*?</a>", "", text or "", flags=re.S)
    text = re.sub(r"\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def paragraphs(text):
    return [line.strip() for line in clean(text).splitlines() if line.strip()]


class CV(FPDF):
    def __init__(self):
        super().__init__(format="A4")
        self.set_margins(MARGIN, MARGIN, MARGIN)
        self.set_auto_page_break(True, margin=MARGIN)
        self.unicode_fonts = all((FONT_DIR / f).exists() for f in FONTS.values())
        if self.unicode_fonts:
            for style, file in FONTS.items():
                self.add_font("Body", style, str(FONT_DIR / file))
            self.family = "Body"
        else:
            self.family = "Helvetica"

    def text_safe(self, text):
        if self.unicode_fonts:
            return text
        swaps = {"\u2013": "-", "\u2014": "-", "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"'}
        for old, new in swaps.items():
            text = text.replace(old, new)
        return text.encode("latin-1", "replace").decode("latin-1")

    def font(self, style="", size=10, color=DARK):
        self.set_font(self.family, style, size)
        self.set_text_color(*color)

    def footer(self):
        self.set_y(-10)
        self.font("", 8, GREY)
        self.cell(0, 4, self.text_safe(f"{self.cv_name}  |  Page {self.page_no()}"), align="C")

    def heading(self, title):
        # Keep a heading on the same page as at least the start of its first entry.
        if self.get_y() > self.h - MARGIN - 50:
            self.add_page()
        self.ln(3)
        self.font("B", 10.5, BLUE)
        self.cell(0, 6, title.upper(), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*RULE)
        self.set_line_width(0.3)
        self.line(MARGIN, self.get_y(), self.w - MARGIN, self.get_y())
        self.ln(2.5)

    def body(self, text):
        self.font("", 9.5, DARK)
        self.multi_cell(0, 4.6, self.text_safe(text), align="L", new_x="LMARGIN", new_y="NEXT")
        self.ln(1.2)

    def entry(self, title, sub, date, description):
        # Keep an entry's heading with at least a couple of lines of text.
        if self.get_y() > self.h - MARGIN - 22:
            self.add_page()
        width = self.w - 2 * MARGIN
        date = self.text_safe(str(date or ""))
        self.font("", 9, GREY)
        date_w = self.get_string_width(date) + 2
        y = self.get_y()
        self.font("B", 10.5, DARK)
        title_txt = self.text_safe(title)
        self.cell(self.get_string_width(title_txt) + 1, 5.5, title_txt)
        if sub:
            self.font("", 9.5, GREY)
            self.cell(width - date_w - self.get_string_width(title_txt) - 1, 5.5, self.text_safe(f"  \u00b7  {sub}" if self.unicode_fonts else f"  -  {sub}"))
        self.set_xy(MARGIN + width - date_w, y)
        self.font("", 9, GREY)
        self.cell(date_w, 5.5, date, align="R", new_x="LMARGIN", new_y="NEXT")
        self.ln(0.5)
        for para in paragraphs(description):
            self.body(para)
        self.ln(1.5)


def build(cfg):
    pdf = CV()
    pdf.cv_name = cfg.get("name", "CV")
    pdf.set_title(f"{pdf.cv_name} - CV")
    pdf.set_author(pdf.cv_name)
    pdf.add_page()

    # Header
    pdf.font("B", 22, DARK)
    pdf.cell(0, 10, pdf.text_safe(pdf.cv_name), new_x="LMARGIN", new_y="NEXT")
    pdf.font("", 12, BLUE)
    pdf.cell(0, 6, pdf.text_safe(cfg.get("title", "")), new_x="LMARGIN", new_y="NEXT")
    contact = [cfg.get("email", ""), cfg.get("website", "").replace("https://", "").rstrip("/")]
    if cfg.get("linkedin_username"):
        contact.append(f"linkedin.com/in/{cfg['linkedin_username']}")
    if cfg.get("github_username"):
        contact.append(f"github.com/{cfg['github_username']}")
    pdf.ln(1)
    pdf.font("", 9, GREY)
    pdf.cell(0, 5, pdf.text_safe("   |   ".join(c for c in contact if c)), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_draw_color(*BLUE)
    pdf.set_line_width(0.7)
    pdf.line(MARGIN, pdf.get_y(), pdf.w - MARGIN, pdf.get_y())
    pdf.ln(3)

    sections = {s["title"]: s["content"] for s in cfg.get("content", [])}

    pdf.heading("About")
    for para in paragraphs(cfg.get("about_content", "")):
        pdf.body(para)

    if "Experience" in sections:
        pdf.heading("Experience")
        for item in sections["Experience"]:
            pdf.entry(item["title"], item.get("sub_title"), item.get("caption"), item.get("description"))

    if "Projects" in sections:
        pdf.heading("Projects")
        # Newest first reads better on paper.
        for item in reversed(sections["Projects"]):
            pdf.entry(item["title"], None, item.get("quote"), item.get("description"))

    if "Education" in sections:
        pdf.heading("Education")
        for item in sections["Education"]:
            pdf.entry(item["title"], item.get("sub_title"), item.get("caption"), item.get("description"))

    return pdf


def main():
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    pdf = build(cfg)
    pdf.output(str(OUTPUT))
    if not OUTPUT.exists() or OUTPUT.stat().st_size == 0:
        sys.exit("PDF was not created.")
    print(f"Wrote {OUTPUT.name}: {pdf.page_no()} pages, {OUTPUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
