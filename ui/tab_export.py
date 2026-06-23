"""
HEM Product Catalogue v3 — Tab 3: Export
PDF catalogue + Excel order sheet generation with case-size selection.
"""
import re
import logging

import pandas as pd
import streamlit as st

from config import BASE_DIR, LOGO_PATH, CASE_SIZE_PATH, CATALOGUE_COVER_URLS, COVER_IMAGE_URL, CASE_SIZE_CATALOGUE_MAP
from imagekit_client import get_image_as_base64_str
from pdf_generator import generate_pdf_html, generate_excel_file, render_pdf
from ui.components import section_header, gold_divider, empty_state

logger = logging.getLogger(__name__)

COLS = ["Catalogue", "Category", "Case Size Qty Per Carton",
        "Gross Wt. Kg", "Net Wt. Kg", "Length Cm", "Breadth Cm", "Height Cm", "CBM"]


def _norm(s: str) -> str:
    """Normalize for matching: strip whitespace, remove non-ASCII, lowercase."""
    return re.sub(r'\s+', ' ', s.encode("ascii", errors="ignore").decode().strip().lower())


def _load_case_size() -> pd.DataFrame:
    """
    Parse the multi-section Case Size Excel into a single clean DataFrame.

    File structure (repeats for each catalogue):
        <Catalogue title row>   col[0] = catalogue name, col[2] blank
        <Header row>            col[0] = "Category"
        <Data rows>             col[0] = category, col[2] = case size qty

    Returns a DataFrame with columns in COLS.
    Only rows with a valid Category AND Case Size Qty are included.
    """
    try:
        raw = pd.read_excel(CASE_SIZE_PATH, header=None, dtype=str)
    except Exception as e:
        logger.error(f"Cannot read Case Size Excel: {e}")
        return pd.DataFrame(columns=COLS)

    rows = []
    current_catalogue = ""

    for _, row in raw.iterrows():
        col0 = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        col2 = str(row.iloc[2]).strip() if len(row) > 2 and pd.notna(row.iloc[2]) else ""

        if not col0:
            continue

        norm0 = _norm(col0)

        # Catalogue title row → set current section
        if norm0 in CASE_SIZE_CATALOGUE_MAP:
            current_catalogue = CASE_SIZE_CATALOGUE_MAP[norm0]
            continue

        # Header row
        if norm0 == "category":
            continue

        # Skip rows with no Case Size Qty (incomplete / spacer rows)
        if not col2 or col2.lower() == "nan":
            continue

        # Clean category: strip whitespace + non-ASCII (\xa0 etc.)
        clean_cat = col0.encode("ascii", errors="ignore").decode().strip()
        if not clean_cat:
            continue

        def _val(idx):
            v = str(row.iloc[idx]).strip() if len(row) > idx and pd.notna(row.iloc[idx]) else ""
            return "" if v.lower() == "nan" else v

        rows.append({
            "Catalogue":                current_catalogue,
            "Category":                 clean_cat,
            "Case Size Qty Per Carton": col2,
            "Gross Wt. Kg":             _val(3),
            "Net Wt. Kg":               _val(4),
            "Length Cm":                _val(5),
            "Breadth Cm":               _val(6),
            "Height Cm":                _val(7),
            "CBM":                      _val(8),
        })

    return pd.DataFrame(rows, columns=COLS) if rows else pd.DataFrame(columns=COLS)


def render_export_tab(products_df: pd.DataFrame) -> None:
    """Render Tab 3 — Export Catalogue."""
    section_header("Export Catalogue", icon="📄")

    if not st.session_state.cart:
        empty_state("📄", "Cart is empty. Add products in <strong>Filter Products</strong> first.")
        return

    # ── 1. Case size selection per category ───────────────────────────────
    st.markdown(
        '<div style="font-size:13px;color:#6b4040;margin-bottom:12px;">'
        '◆ Select the carton/case size for each product category in your cart.'
        '</div>',
        unsafe_allow_html=True,
    )

    # Unique (catalogue, category) pairs from cart
    cart_items = sorted(
        {(item.get("Catalogue", ""), item["Category"]) for item in st.session_state.cart}
    )

    case_df = _load_case_size()
    selection_map: dict = {}

    if case_df.empty:
        st.error("Could not load Case Size data. Check that 'Case Size.xlsx' exists in the app folder.")
    else:
        # Build lookup: (norm_catalogue, norm_category) → list of row dicts
        case_lookup: dict[tuple, list] = {}
        for _, row in case_df.iterrows():
            key = (_norm(row["Catalogue"]), _norm(row["Category"]))
            case_lookup.setdefault(key, []).append(row.to_dict())

        cols_per_row = 2
        chunks = [cart_items[i:i+cols_per_row] for i in range(0, len(cart_items), cols_per_row)]

        for chunk in chunks:
            cols = st.columns(len(chunk))
            for col, (catalogue, cat) in zip(cols, chunk):
                with col:
                    options = case_lookup.get((_norm(catalogue), _norm(cat)), [])

                    if not options:
                        st.warning(f"⚠️ No case sizes found for **{cat}**")
                        continue

                    # Build labels: "24 Doz  (CBM: 0.060)"
                    labels = []
                    for opt in options:
                        qty = str(opt.get("Case Size Qty Per Carton", "")).strip()
                        cbm = str(opt.get("CBM", "")).strip()
                        if cbm:
                            try:
                                cbm = f"{float(cbm):.3f}"
                            except ValueError:
                                pass
                            labels.append(f"{qty}  (CBM: {cbm})")
                        else:
                            labels.append(qty)

                    chosen_label = st.selectbox(
                        f"📦 **{cat}**",
                        labels,
                        key=f"case_{catalogue}_{cat}",
                    )
                    selection_map[cat] = options[labels.index(chosen_label)]

    gold_divider()

    # ── 2. Client name ────────────────────────────────────────────────────
    client_name = st.text_input(
        "👤 Client Name",
        value="Valued Client",
        key="export_client_name",
    )

    # ── 3. Generate button ────────────────────────────────────────────────
    if st.button(
        "🚀 Generate Catalogue & Order Sheet",
        use_container_width=True,
        type="primary",
    ):
        _generate_files(products_df, client_name, selection_map)

    gold_divider()

    # ── 4. Download buttons ───────────────────────────────────────────────
    if st.session_state.gen_pdf_bytes or st.session_state.gen_excel_bytes:
        st.markdown(
            '<div style="font-size:13px;color:#c8102e;margin-bottom:10px;'
            'letter-spacing:1px;text-transform:uppercase;">◆ Ready to Download</div>',
            unsafe_allow_html=True,
        )
        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            if st.session_state.gen_pdf_bytes:
                safe_name = client_name.replace(" ", "_")
                st.download_button(
                    "⬇️ Download PDF Catalogue",
                    data=st.session_state.gen_pdf_bytes,
                    file_name=f"{safe_name}_catalogue.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
        with dl_col2:
            if st.session_state.gen_excel_bytes:
                safe_name = client_name.replace(" ", "_")
                st.download_button(
                    "⬇️ Download Excel Order Sheet",
                    data=st.session_state.gen_excel_bytes,
                    file_name=f"{safe_name}_order.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )


def _generate_files(products_df, client_name, selection_map):
    """Internal helper: build and store PDF + Excel in session state."""
    cart_data   = st.session_state.cart
    schema_cols = [
        "Catalogue", "Category", "Subcategory", "ItemName",
        "Fragrance", "SKU Code", "ImageB64", "Packaging", "IsNew",
    ]
    df = pd.DataFrame(cart_data)
    for col in schema_cols:
        if col not in df.columns:
            df[col] = ""

    sort_cols = [c for c in ["Catalogue", "Category", "ItemName"] if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols, key=lambda s: s.str.lower())

    df["SerialNo"] = range(1, len(df) + 1)

    cart_catalogues = set(df["Catalogue"].dropna().unique()) if "Catalogue" in df.columns else set()
    if len(cart_catalogues) == 1:
        single_catalogue = cart_catalogues.pop()
        cover_url = CATALOGUE_COVER_URLS.get(single_catalogue, "") or COVER_IMAGE_URL
    else:
        cover_url = COVER_IMAGE_URL

    progress = st.progress(0, text="Starting…")

    progress.progress(20, text="Building Excel order sheet…")
    try:
        st.session_state.gen_excel_bytes = generate_excel_file(df, client_name, selection_map)
    except Exception as e:
        st.error(f"Excel generation failed: {e}")
        st.session_state.gen_excel_bytes = None

    progress.progress(50, text="Rendering PDF (this may take 30–60 seconds)…")
    try:
        logo_b64 = get_image_as_base64_str(LOGO_PATH, resize=True, max_size=(200, 100))
        html     = generate_pdf_html(df, client_name, logo_b64, selection_map, cover_url=cover_url)
        progress.progress(80, text="Finalising PDF…")
        pdf_bytes, engine_or_err = render_pdf(html)
        if pdf_bytes:
            st.session_state.gen_pdf_bytes = pdf_bytes
            progress.progress(100, text="Done!")
            st.toast(f"✅ PDF ready ({engine_or_err})", icon="🎉")
        else:
            st.session_state.gen_pdf_bytes = None
            progress.empty()
            st.error(f"PDF generation failed:\n\n{engine_or_err}")
    except Exception as e:
        logger.error(f"PDF exception: {e}")
        st.session_state.gen_pdf_bytes = None
        progress.empty()
        st.error(f"PDF error: {e}")
