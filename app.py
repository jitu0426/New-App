"""
HEM Product Catalogue v3 — Main Entry Point
============================================
Run with:  streamlit run app.py

Architecture:
  app.py              → bootstraps services, layout, tabs
  config.py           → all paths & constants
  styles.py           → full luxury dark-gold CSS
  imagekit_client.py  → ImageKit.io (images, uploads)
  database.py         → JSON DB (cart, overrides, custom products)
  data_loader.py      → Excel + ImageKit.io image pipeline
  cart.py             → cart add / remove / clear helpers
  pdf_generator.py    → PDF (WeasyPrint/pdfkit) + Excel export
  ui/sidebar.py       → sidebar: templates, sync, info
  ui/tab_filter.py    → Tab 1: browse & filter products
  ui/tab_review.py    → Tab 2: review & edit cart
  ui/tab_export.py    → Tab 3: generate PDF / Excel
  ui/tab_add_product.py → Tab 4: add custom products
  ui/components.py    → shared UI helpers
"""
import time
import logging

import streamlit as st

# ── Logging (configure first so all modules inherit it) ───────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)s │ %(levelname)s │ %(message)s",
)
logger = logging.getLogger(__name__)

# ── Page config — MUST be first Streamlit call ────────────────────────────
from config import NO_SELECTION_PLACEHOLDER, APP_TITLE, APP_ICON
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Remaining imports ─────────────────────────────────────────────────────
from styles import APP_CSS
from imagekit_client import init_imagekit
from database import load_cart_from_db, migrate_old_custom_items
from data_loader import load_data_cached

# ── Inject CSS ────────────────────────────────────────────────────────────
st.markdown(APP_CSS, unsafe_allow_html=True)

# ── Initialize ImageKit.io ────────────────────────────────────────────────
init_imagekit()

# ── Session-state defaults (survive reruns within one browser session) ────
_defaults = {
    "cart":                         None,           # filled from DB below
    "gen_pdf_bytes":                None,
    "gen_excel_bytes":              None,
    "selected_catalogue_dropdown":  NO_SELECTION_PLACEHOLDER,
    "selected_categories_multi":    [],
    "selected_subcategories_multi": [],
    "item_search_query":            "",
    "master_pid_map":               {},
    "data_timestamp":               time.time(),
}
for key, val in _defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# Load persisted cart from JSON DB on first run only
if st.session_state.cart is None:
    st.session_state.cart = load_cart_from_db()

# ── One-time migration from legacy custom_products.json ──────────────────
migrate_old_custom_items()

# ── Load product data (cached; bust cache by updating data_timestamp) ─────
products_df = load_data_cached(st.session_state.data_timestamp)

# Rebuild fast ProductID → row lookup map
# drop_duplicates keeps the last occurrence (same behaviour as the old iterrows loop)
st.session_state.master_pid_map = (
    products_df.drop_duplicates(subset="ProductID", keep="last")
    .set_index("ProductID")
    .to_dict("index")
)

# ── Sidebar ───────────────────────────────────────────────────────────────
from ui.sidebar import render_sidebar
render_sidebar()

# ── Main title banner ─────────────────────────────────────────────────────
st.markdown(
    """
    <div class="main-title">
        <span class="title-brand">HEM Product Catalogue</span>
        <span class="title-sub">Premium Incense &amp; Fragrance Collection — Export Edition</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Tab navigation ────────────────────────────────────────────────────────
cart_count = len(st.session_state.cart)
cart_label = f"✏️ Review & Edit ({cart_count})" if cart_count else "✏️ Review & Edit"

tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 Filter Products",
    cart_label,
    "📄 Export",
    "➕ Add Product",
])

# ── Render tabs ───────────────────────────────────────────────────────────
from ui.tab_filter      import render_filter_tab
from ui.tab_review      import render_review_tab
from ui.tab_export      import render_export_tab
from ui.tab_add_product import render_add_product_tab

with tab1:
    render_filter_tab(products_df)

with tab2:
    render_review_tab()

with tab3:
    render_export_tab(products_df)

with tab4:
    render_add_product_tab(products_df)
