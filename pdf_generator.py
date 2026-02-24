"""
HEM Product Catalogue v3 — PDF & Excel Generator
==================================================
PDF engine priority:
  1. wkhtmltopdf (pdfkit)  — Windows local, if binary found
  2. WeasyPrint             — Streamlit Cloud (Linux), pure-Python, no binary needed

Excel uses xlsxwriter for professional formatting.

PDF THEME: 100% Plain White — NO dark backgrounds, NO gold, NO tinted colours.
  Every background   : #ffffff  (pure white, !important everywhere)
  Body / heading text: #222222  (dark charcoal, readable)
  Brand accent       : #c8102e  (HEM Crimson Red — borders & badges ONLY)
  Supporting grey    : #333333 / #555555 / #888888
  Dividers / borders : #dddddd / #e0e0e0 / #eeeeee  (light grey)
  Table header bg    : #f5f5f5  (near-white)
  Image placeholder  : #f8f8f8  (near-white)
"""

import os
import io
import gc
import platform
import subprocess
import logging

import pandas as pd
import streamlit as st

from config import BASE_DIR, LOGO_PATH, STORY_IMG_1_PATH, COVER_IMAGE_URL, JOURNEY_IMAGE_URL
from cloudinary_client import get_image_as_base64_str
from data_loader import create_safe_id

logger = logging.getLogger(__name__)

# ── Optional WeasyPrint import (available on Streamlit Cloud) ─────────────
HAS_WEASYPRINT = False
try:
    from weasyprint import HTML as WP_HTML
    HAS_WEASYPRINT = True
    logger.info("WeasyPrint available ✓")
except Exception as e:
    logger.info(f"WeasyPrint not available ({e}) — will use pdfkit if possible.")

# ── pdfkit / wkhtmltopdf configuration ───────────────────────────────────
import pdfkit
PDFKIT_CONFIG = None
try:
    if platform.system() == "Windows":
        candidates = [
            r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
            r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe",
            os.path.join(BASE_DIR, "bin", "wkhtmltopdf.exe"),
        ]
        for p in candidates:
            if os.path.exists(p):
                PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf=p)
                logger.info(f"wkhtmltopdf found: {p}")
                break
    else:
        try:
            wp_path = subprocess.check_output(["which", "wkhtmltopdf"]).decode().strip()
            PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf=wp_path)
        except Exception:
            if os.path.exists("/usr/bin/wkhtmltopdf"):
                PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf="/usr/bin/wkhtmltopdf")
except Exception as e:
    logger.warning(f"pdfkit config error: {e}")
    PDFKIT_CONFIG = None


# ═════════════════════════════════════════════════════════════════════════
# STORY PAGE HTML
# ═════════════════════════════════════════════════════════════════════════
def generate_story_html(story_img_b64: str) -> str:
    """Build the 'Our Journey' page — plain white, no dark colours."""
    text1 = (
        "HEM Corporation is amongst top global leaders in the manufacturing and export "
        "of perfumed agarbattis. For over three decades we have been distributing "
        "high-quality masala sticks, agarbattis, dhoops, and cones to customers in "
        "more than 70 countries. HEM has been awarded as the 'Top Exporters' brand "
        "for incense sticks by the Export Promotion Council for Handicraft (EPCH) "
        "for three consecutive years (2008–2011)."
    )
    text2 = (
        "From a brand founded by three brothers in 1983, HEM Fragrances has come a "
        "long way. HEM started as a simple incense store offering masala agarbatti, "
        "thuribles, and dhoops. With time, HEM expanded to meet the global demand for "
        "aromatherapy, meditation aids, and premium fragrance products. Today HEM "
        "serves over 70 countries and is the most preferred incense brand worldwide."
    )
    img_tag = (
        f'<img src="data:image/jpeg;base64,{story_img_b64}" '
        f'style="max-width:100% !important;height:auto !important;'
        f'border:1px solid #dddddd !important;border-radius:4px !important;" />'
        if story_img_b64
        else (
            '<div style="padding:40px !important;border:1px dashed #cccccc !important;'
            'color:#999999 !important;text-align:center !important;'
            'background:#ffffff !important;">Image not found</div>'
        )
    )
    return f"""
    <div style="page-break-after:always !important;padding:25px 50px !important;
                font-family:Arial,sans-serif !important;
                background:#ffffff !important;color:#222222 !important;
                margin:0 !important;">
      <h1 style="text-align:center !important;color:#c8102e !important;
                 font-size:26pt !important;margin-bottom:12px !important;
                 letter-spacing:2px !important;text-transform:uppercase !important;
                 background:#ffffff !important;">Our Journey</h1>
      <div style="height:1px !important;background:#dddddd !important;
                  margin-bottom:22px !important;"></div>
      <p style="font-size:11pt !important;line-height:1.8 !important;
                margin-bottom:18px !important;text-align:justify !important;
                color:#333333 !important;background:#ffffff !important;">{text1}</p>
      <div style="overflow:auto !important;margin-bottom:20px !important;
                  background:#ffffff !important;">
        <div style="float:left !important;width:50% !important;
                    padding-right:20px !important;font-size:11pt !important;
                    line-height:1.8 !important;text-align:justify !important;
                    color:#333333 !important;background:#ffffff !important;">{text2}</div>
        <div style="float:right !important;width:46% !important;
                    text-align:center !important;
                    background:#ffffff !important;">{img_tag}</div>
      </div>
      <div style="clear:both !important;"></div>
      <div style="height:1px !important;background:#dddddd !important;
                  margin-top:22px !important;margin-bottom:14px !important;"></div>
      <h2 style="text-align:center !important;font-size:11pt !important;
                 color:#c8102e !important;margin-top:0 !important;
                 letter-spacing:3px !important;font-weight:600 !important;
                 background:#ffffff !important;">
        INNOVATION · CREATIVITY · SUSTAINABILITY
      </h2>
    </div>
    """


# ═════════════════════════════════════════════════════════════════════════
# TABLE OF CONTENTS HTML
# ═════════════════════════════════════════════════════════════════════════
def generate_table_of_contents_html(df_sorted: pd.DataFrame) -> str:
    """Generate Table of Contents — pure white cards, HEM red labels."""
    css = """
    <style>
      * { box-sizing:border-box !important; }
      body,html { background:#ffffff !important; color:#222222 !important; margin:0 !important; padding:0 !important; }
      .toc-page { background:#ffffff !important; padding:20px !important; }
      .toc-title { text-align:center !important; font-family:Georgia,serif !important;
                   font-size:28pt !important; color:#c8102e !important;
                   margin:10px 0 6px !important; text-transform:uppercase !important;
                   letter-spacing:2px !important; background:#ffffff !important; }
      .toc-divider { height:1px !important; background:#dddddd !important;
                     margin:0 auto 20px !important; width:70% !important; }
      .toc-cat-header { background:#ffffff !important; color:#222222 !important;
                        font-family:Arial,sans-serif !important; font-size:13pt !important;
                        padding:8px 14px !important; margin:0 0 12px !important;
                        border-left:3px solid #c8102e !important;
                        border-bottom:1px solid #eeeeee !important;
                        border-right:none !important; border-top:none !important;
                        page-break-inside:avoid !important; }
      .idx-grid { display:block !important; width:100% !important; font-size:0 !important; }
      .idx-card { display:inline-block !important; width:30% !important; margin:1.5% !important;
                  height:195px !important; background:#ffffff !important;
                  border-radius:6px !important; text-decoration:none !important;
                  overflow:hidden !important; border:1px solid #e0e0e0 !important;
                  page-break-inside:avoid !important; vertical-align:top !important; }
      .idx-img { width:100% !important; height:155px !important;
                 background-repeat:no-repeat !important; background-position:center !important;
                 background-size:contain !important; background-color:#f8f8f8 !important; }
      .idx-label { height:40px !important; background:#c8102e !important;
                   color:#ffffff !important; font-family:Arial,sans-serif !important;
                   font-size:8.5pt !important; font-weight:700 !important;
                   display:block !important; line-height:40px !important;
                   text-align:center !important; text-transform:uppercase !important;
                   letter-spacing:0.8px !important; white-space:nowrap !important;
                   overflow:hidden !important; text-overflow:ellipsis !important;
                   padding:0 10px !important; }
      .clearfix::after { content:"" !important; clear:both !important; display:table !important; }
    </style>
    <div id="main-index" class="toc-page"
         style="page-break-after:always !important;padding:20px !important;
                background:#ffffff !important;">
      <h1 class="toc-title">Table of Contents</h1>
      <div class="toc-divider"></div>
    """
    catalogues = df_sorted["Catalogue"].unique()
    first = True
    for cat_name in catalogues:
        pb = "" if first else 'style="page-break-before:always !important;padding-top:20px !important;background:#ffffff !important;"'
        css += f'<div {pb}>'
        css += f'<h3 class="toc-cat-header">{cat_name}</h3>'
        css += '<div class="idx-grid clearfix">'
        cat_df = df_sorted[df_sorted["Catalogue"] == cat_name]
        for category in cat_df["Category"].unique():
            grp = cat_df[cat_df["Category"] == category]
            rep_img = ""
            for _, row in grp.iterrows():
                s = str(row.get("ImageB64", ""))
                if len(s) > 100:
                    rep_img = s
                    break
            bg = (
                f"background-image:url('data:image/png;base64,{rep_img}') !important;"
                if rep_img
                else "background-color:#f8f8f8 !important;"
            )
            safe_id = create_safe_id(category)
            css += f"""
            <a href="#category-{safe_id}" class="idx-card">
              <div class="idx-img" style="{bg}"></div>
              <div class="idx-label">{category}</div>
            </a>"""
        css += "</div><div style='clear:both !important;'></div></div>"
        first = False
    css += "</div>"
    return css


# ═════════════════════════════════════════════════════════════════════════
# FULL PDF HTML BUILDER
# ═════════════════════════════════════════════════════════════════════════
def generate_pdf_html(df_sorted: pd.DataFrame, customer_name: str,
                      logo_b64: str, case_selection_map: dict) -> str:
    """Assemble complete HTML — Cover → Story → TOC → Product pages. Plain white only."""

    def load_img(fname, specific=None, resize=False, max_size=(500, 500)):
        paths = []
        if specific:
            paths.append(specific)
        paths += [
            os.path.join(BASE_DIR, "assets", fname),
            os.path.join(BASE_DIR, fname),
        ]
        for p in paths:
            if os.path.exists(p):
                return get_image_as_base64_str(p, resize=resize, max_size=max_size)
        return ""

    # Load images
    cover_b64     = get_image_as_base64_str(COVER_IMAGE_URL) or load_img("cover page.png")
    story_b64     = get_image_as_base64_str(JOURNEY_IMAGE_URL, max_size=(600, 600)) or \
                    load_img("image-journey.png", specific=STORY_IMG_1_PATH,
                             resize=True, max_size=(600, 600))
    watermark_b64 = load_img("watermark.png")

    # ── NUCLEAR WHITE CSS — every rule uses !important ────────────────────
    global_css = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
/* ── RESET — force white on absolutely everything ── */
*, *::before, *::after {{
  box-sizing: border-box !important;
  background-color: #ffffff !important;
  color: #222222 !important;
}}
@page {{ size:A4; margin:0; }}

html, body {{
  margin:0 !important; padding:0 !important; width:100% !important;
  background:#ffffff !important; color:#222222 !important;
}}

/* ── Watermark (near-invisible) ── */
#wm {{
  position:fixed !important; top:0 !important; left:0 !important;
  width:100% !important; height:100% !important; z-index:-1 !important;
  background-image:url('data:image/png;base64,{watermark_b64}') !important;
  background-repeat:repeat !important; background-size:cover !important;
  opacity:0.03 !important;
  background-color:transparent !important;
}}

/* ── Cover page ── */
.cover-page {{
  width:210mm !important; height:297mm !important;
  display:block !important; position:relative !important;
  margin:0 !important; padding:0 !important; overflow:hidden !important;
  page-break-after:always !important;
  background:#ffffff !important;
}}
.cover-page img {{
  width:100% !important; height:100% !important; object-fit:cover !important;
}}

/* ── Catalogue content wrapper ── */
.cat-content {{
  padding:8mm 10mm 50px !important; position:relative !important;
  z-index:1 !important; background:#ffffff !important;
}}

/* ── Catalogue name heading (e.g. "HEM Incense") ── */
.cat-heading {{
  background:#ffffff !important; color:#c8102e !important;
  font-size:15pt !important; padding:8px 14px !important;
  margin-bottom:6px !important; font-weight:bold !important;
  font-family:Arial,sans-serif !important;
  border-left:4px solid #c8102e !important;
  border-bottom:1px solid #eeeeee !important;
  border-top:none !important; border-right:none !important;
  page-break-inside:avoid !important; clear:both !important;
}}

/* ── Category heading (e.g. "Flora Range") ── */
.category-heading {{
  color:#222222 !important; font-size:12pt !important;
  padding:7px 0 5px !important; border-bottom:1px solid #dddddd !important;
  border-top:none !important; border-left:none !important; border-right:none !important;
  margin-top:6mm !important; clear:both !important;
  font-family:Georgia,serif !important;
  page-break-inside:avoid !important; width:100% !important;
  background:#ffffff !important;
}}

/* ── Subcategory header strip ── */
.subcat-hdr {{
  color:#555555 !important; font-size:9.5pt !important;
  font-weight:bold !important; margin:8px 0 4px !important;
  clear:both !important; font-family:Arial,sans-serif !important;
  border-left:2px solid #c8102e !important; padding:3px 8px !important;
  border-top:none !important; border-right:none !important; border-bottom:none !important;
  page-break-inside:avoid !important; width:100% !important;
  background:#ffffff !important;
}}

/* ── Case-size table ── */
.cs-table {{
  width:100% !important; border-collapse:collapse !important;
  font-size:8.5pt !important; margin-bottom:10px !important;
  clear:both !important; background:#ffffff !important;
}}
.cs-table th {{
  border:1px solid #dddddd !important; background:#f5f5f5 !important;
  padding:4px !important; text-align:center !important;
  font-weight:bold !important; color:#333333 !important;
}}
.cs-table td {{
  border:1px solid #e8e8e8 !important; padding:4px !important;
  text-align:center !important; color:#555555 !important;
  background:#ffffff !important;
}}

/* ── Product card block ── */
.cat-block {{
  display:block !important; font-size:0 !important;
  clear:both !important; page-break-inside:auto !important;
  margin-bottom:18px !important; width:100% !important;
  page-break-before:always !important;
  background:#ffffff !important;
}}
h1.cat-heading + .cat-block {{
  page-break-before:avoid !important;
}}

/* ── Individual product card ── */
.prod-card {{
  display:inline-block !important; width:23% !important;
  margin:8px 1% !important; vertical-align:top !important;
  font-size:12pt !important; padding:0 !important;
  background:#ffffff !important;
  border:1px solid #e0e0e0 !important; border-radius:4px !important;
  text-align:center !important; position:relative !important;
  overflow:hidden !important; height:178px !important;
  page-break-inside:avoid !important;
}}

/* ── Product image area ── */
.card-img {{
  width:100% !important; height:112px !important; position:relative !important;
  background-color:#f8f8f8 !important; background:#f8f8f8 !important;
  border-bottom:1px solid #eeeeee !important; overflow:hidden !important;
}}
.card-img img {{
  position:absolute !important; top:0 !important; bottom:0 !important;
  left:0 !important; right:0 !important; margin:auto !important;
  max-width:95% !important; max-height:95% !important;
  width:auto !important; height:auto !important; display:block !important;
}}

/* ── Product info area ── */
.card-info {{
  height:62px !important; display:block !important;
  padding:5px !important; background:#ffffff !important;
}}
.card-name {{
  font-family:Georgia,serif !important; color:#222222 !important;
  line-height:1.2 !important; font-weight:bold !important;
  margin:0 !important; padding-top:4px !important; display:block !important;
  background:#ffffff !important;
}}

/* ── NEW badge ── */
.new-badge {{
  position:absolute !important; top:0 !important; right:0 !important;
  background:#c8102e !important; color:#ffffff !important;
  font-size:7px !important; font-weight:bold !important;
  padding:2px 7px !important; border-radius:0 0 0 4px !important;
  z-index:10 !important; letter-spacing:0.5px !important;
}}

/* ── INDEX link ── */
.idx-link {{
  float:right !important; font-size:9px !important;
  color:#888888 !important; text-decoration:none !important;
  font-weight:normal !important; font-family:Arial,sans-serif !important;
  margin-top:4px !important; background:transparent !important;
}}

.clearfix::after {{ content:"" !important; clear:both !important; display:table !important; }}
</style>
</head>
<body style="margin:0 !important;padding:0 !important;background:#ffffff !important;color:#222222 !important;">
<div id="wm"></div>
<div class="cover-page">
  <img src="data:image/png;base64,{cover_b64}" alt="Cover" />
</div>
"""

    html_parts = [global_css]

    # Story page
    html_parts.append(generate_story_html(story_b64))
    # Table of Contents
    html_parts.append(generate_table_of_contents_html(df_sorted))
    # Open catalogue content wrapper
    html_parts.append('<div class="cat-content clearfix">')

    def fuzzy_get(row_data, keys):
        for k in keys:
            for dk in row_data:
                if k.lower() in dk.lower():
                    return str(row_data[dk])
        return "-"

    cur_catalogue = cur_category = cur_subcategory = None
    is_first = True
    cat_open = False

    for index, row in df_sorted.iterrows():
        # ── New catalogue section ─────────────────────────────────────────
        if row["Catalogue"] != cur_catalogue:
            if cat_open:
                html_parts.append("</div>")
                cat_open = False
            cur_catalogue = row["Catalogue"]
            cur_category = cur_subcategory = None
            pb = 'style="page-break-before:always !important;"' if not is_first else ""
            html_parts.append(
                f'<div style="clear:both !important;"></div>'
                f'<h1 class="cat-heading" {pb}>{cur_catalogue}</h1>'
            )
            is_first = False

        # ── New category section ──────────────────────────────────────────
        if row["Category"] != cur_category:
            if cat_open:
                html_parts.append("</div>")
            cur_category = row["Category"]
            cur_subcategory = None
            safe_id = create_safe_id(cur_category)
            row_data = case_selection_map.get(cur_category, {})

            html_parts.append('<div class="cat-block clearfix">')
            cat_open = True

            html_parts.append(
                f'<h2 class="category-heading" id="category-{safe_id}">'
                f'<a href="#main-index" class="idx-link">INDEX ↑</a>'
                f'{cur_category}</h2>'
            )

            # Case size table
            if row_data:
                desc = row_data.get("Description", "")
                if desc:
                    html_parts.append(
                        f'<p style="color:#555555 !important;font-size:9.5pt !important;'
                        f'font-style:italic !important;margin:4px 0 !important;'
                        f'background:#ffffff !important;">'
                        f'<strong style="color:#333333 !important;background:#ffffff !important;">'
                        f'Case Size:</strong> {desc}</p>'
                    )
                packing = fuzzy_get(row_data, ["Packing", "Master Ctn"])
                gross   = fuzzy_get(row_data, ["Gross Wt", "Gross Weight"])
                net     = fuzzy_get(row_data, ["Net Wt", "Net Weight"])
                length  = fuzzy_get(row_data, ["Length"])
                breadth = fuzzy_get(row_data, ["Breadth", "Width"])
                height  = fuzzy_get(row_data, ["Height"])
                cbm     = fuzzy_get(row_data, ["CBM"])
                html_parts.append(
                    f'<table class="cs-table"><tr>'
                    f'<th>Packing/Ctn</th><th>Gross Wt (Kg)</th><th>Net Wt (Kg)</th>'
                    f'<th>L (Cm)</th><th>B (Cm)</th><th>H (Cm)</th><th>CBM</th></tr>'
                    f'<tr><td>{packing}</td><td>{gross}</td><td>{net}</td>'
                    f'<td>{length}</td><td>{breadth}</td><td>{height}</td><td>{cbm}</td></tr>'
                    f'</table>'
                )

        # ── Subcategory header ────────────────────────────────────────────
        sub = str(row.get("Subcategory", "")).strip()
        if sub and sub.upper() != "N/A" and sub.lower() != "nan":
            if sub != cur_subcategory:
                cur_subcategory = sub
                html_parts.append(f'<div class="subcat-hdr">{sub}</div>')

        # ── Product card ──────────────────────────────────────────────────
        img_b64 = row.get("ImageB64", "")
        if str(img_b64).startswith("http"):
            img_b64 = get_image_as_base64_str(img_b64)
        mime = "image/png" if img_b64 and "png" in str(img_b64)[:30].lower() else "image/jpeg"
        img_html = (
            f'<img src="data:{mime};base64,{img_b64}" alt="img" />'
            if img_b64
            else (
                '<div style="padding-top:35px !important;color:#bbbbbb !important;'
                'font-size:9px !important;background:#f8f8f8 !important;">NO IMAGE</div>'
            )
        )
        new_badge = (
            '<div class="new-badge">NEW</div>'
            if row.get("IsNew") == 1 else ""
        )
        name = str(row.get("ItemName", "N/A"))
        fs = "9pt" if len(name) < 30 else ("8pt" if len(name) < 50 else "7pt")

        html_parts.append(f"""
        <div class="prod-card">
          {new_badge}
          <div class="card-img">{img_html}</div>
          <div class="card-info">
            <div class="card-name" style="font-size:{fs} !important;">
              <span style="color:#888888 !important;margin-right:2px !important;
                           background:#ffffff !important;">{index+1}.</span>{name}
            </div>
          </div>
        </div>""")

    if cat_open:
        html_parts.append("</div>")
    html_parts.append(
        '<div style="clear:both !important;"></div>'
        '</div>'
        '</body></html>'
    )
    return "".join(html_parts)


# ═════════════════════════════════════════════════════════════════════════
# EXCEL ORDER SHEET
# ═════════════════════════════════════════════════════════════════════════
def generate_excel_file(df_sorted: pd.DataFrame, customer_name: str,
                        case_selection_map: dict) -> bytes:
    """Generate a formatted Excel order sheet with CBM calculator."""
    output = io.BytesIO()
    rows = []
    for idx, row in df_sorted.iterrows():
        cat = row["Category"]
        suffix, cbm = "", 0.0
        if cat in case_selection_map:
            cd = case_selection_map[cat]
            for k, v in cd.items():
                if "suffix" in k.lower():
                    suffix = str(v).strip()
                if "cbm" in k.lower():
                    try:
                        cbm = round(float(v), 3)
                    except Exception:
                        cbm = 0.0
            if suffix == "nan":
                suffix = ""
        full_name = str(row["ItemName"]).strip()
        if suffix:
            full_name = f"{full_name} {suffix}"
        rows.append({
            "Ref No":                     idx + 1,
            "Category":                   cat,
            "Product Name + Carton Name": full_name,
            "Carton CBM":                 cbm,
            "Order Qty (Cartons)":        0,
            "Total CBM":                  0,
        })

    df_xl = pd.DataFrame(rows)
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_xl.to_excel(writer, index=False, sheet_name="Order Sheet", startrow=7)
        wb = writer.book
        ws = writer.sheets["Order Sheet"]

        # ── Formats (white + HEM red headers) ────────────────────────────
        hdr_fmt   = wb.add_format({"bold": True, "bg_color": "#c8102e",
                                    "font_color": "#ffffff", "border": 1})
        input_fmt = wb.add_format({"bg_color": "#FFFCB7", "border": 1, "locked": False})
        lock_fmt  = wb.add_format({"border": 1, "locked": True, "num_format": "0.000"})
        cnt_fmt   = wb.add_format({"num_format": "0.00", "bold": True, "border": 1})
        title_fmt = wb.add_format({"bold": True, "font_size": 14, "font_color": "#c8102e"})

        ws.protect()
        ws.freeze_panes(8, 0)

        ws.write("B1", f"Order Sheet — {customer_name}", title_fmt)
        ws.write("B2", "Total CBM:")
        ws.write_formula("C2", f"=SUM(F9:F{len(df_xl)+9})",
                         wb.add_format({"num_format": "0.000"}))

        ws.write("B3", "CONTAINER TYPE", hdr_fmt)
        ws.write("C3", "ESTIMATED CONTAINERS", hdr_fmt)
        ws.write("B4", "20 FT  (30 CBM)",  wb.add_format({"border": 1}))
        ws.write("B5", "40 FT  (60 CBM)",  wb.add_format({"border": 1}))
        ws.write("B6", "40 FT HC (70 CBM)", wb.add_format({"border": 1}))
        ws.write_formula("C4", "=$C$2/30", cnt_fmt)
        ws.write_formula("C5", "=$C$2/60", cnt_fmt)
        ws.write_formula("C6", "=$C$2/70", cnt_fmt)

        for ci, col in enumerate(df_xl.columns):
            ws.write(7, ci, col, hdr_fmt)

        ws.set_column("A:A", 8)
        ws.set_column("B:B", 25)
        ws.set_column("C:C", 52)
        ws.set_column("D:F", 16)

        for i in range(len(df_xl)):
            ri = i + 9
            ws.write(ri - 1, 4, 0, input_fmt)
            ws.write_formula(ri - 1, 5, f"=D{ri}*E{ri}", lock_fmt)

    return output.getvalue()


# ═════════════════════════════════════════════════════════════════════════
# RENDER PDF — engine selection
# ═════════════════════════════════════════════════════════════════════════
def render_pdf(html_string: str):
    """
    Convert HTML → PDF bytes.
    Returns (pdf_bytes, engine_name) on success
         or (None, error_message) on failure.
    """
    try:
        if PDFKIT_CONFIG:
            options = {
                "page-size":                "A4",
                "margin-top":               "0mm",
                "margin-right":             "0mm",
                "margin-bottom":            "0mm",
                "margin-left":              "0mm",
                "encoding":                 "UTF-8",
                "no-outline":               None,
                "enable-local-file-access": None,
                "disable-smart-shrinking":  None,
                "print-media-type":         None,
                "background":               None,
            }
            pdf = pdfkit.from_string(
                html_string, False,
                configuration=PDFKIT_CONFIG,
                options=options,
            )
            gc.collect()
            return pdf, "wkhtmltopdf"

        elif HAS_WEASYPRINT:
            pdf = WP_HTML(string=html_string, base_url=BASE_DIR).write_pdf()
            gc.collect()
            return pdf, "WeasyPrint"

        else:
            return None, (
                "No PDF engine found!\n"
                "• On Streamlit Cloud: add 'weasyprint' to requirements.txt and redeploy.\n"
                "• Locally on Windows: install wkhtmltopdf from https://wkhtmltopdf.org"
            )

    except Exception as exc:
        logger.error(f"PDF render error: {exc}")
        return None, str(exc)
