"""
HEM Product Catalogue v3 — Sidebar
Renders: logo, template save/load/delete, data sync, database info.
"""
import time
import streamlit as st

from database import (
    load_saved_templates, save_template_to_disk, delete_template,
    load_products_db,
)
from cart import clear_cart
from imagekit_client import fetch_all_imagekit_resources


def render_sidebar() -> None:
    """Render the full left sidebar."""
    with st.sidebar:
        # ── Logo / branding ───────────────────────────────────────────────
        st.markdown(
            """
            <div style="text-align:center;padding:20px 0 12px;">
                <div style="font-size:38px;margin-bottom:4px;">🪔</div>
                <div style="font-family:'Playfair Display',serif;
                            font-size:20px;font-weight:700;
                            color:#f5a832;
                            letter-spacing:2px;">HEM EXPORTS</div>
                <div style="font-size:10px;color:rgba(255,220,200,0.65);letter-spacing:3px;
                            text-transform:uppercase;margin-top:2px;">Catalogue Manager</div>
            </div>
            <div class="gold-divider" style="margin:0 0 16px;"></div>
            """,
            unsafe_allow_html=True,
        )

        # ── Cart summary ──────────────────────────────────────────────────
        cart_count = len(st.session_state.cart)
        cat_count  = len(set(i.get("Category", "") for i in st.session_state.cart))
        st.markdown(
            f"""
            <div style="background:rgba(200,16,46,0.10);
                        border:1px solid rgba(200,16,46,0.25);border-radius:12px;
                        padding:14px 18px;margin-bottom:16px;text-align:center;">
                <div style="font-size:11px;color:rgba(255,220,200,0.65);text-transform:uppercase;
                             letter-spacing:1px;margin-bottom:6px;">Current Cart</div>
                <div style="font-size:28px;font-weight:700;color:#f5a832;
                             font-family:'Playfair Display',serif;">{cart_count}</div>
                <div style="font-size:11px;color:rgba(255,220,200,0.55);">
                    products · {cat_count} categories
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Data sync ─────────────────────────────────────────────────────
        st.markdown("### 🔄 Data Sync")
        if st.button("Refresh Images & Excel", use_container_width=True):
            st.cache_data.clear()
            st.session_state.data_timestamp = time.time()
            st.session_state.gen_pdf_bytes  = None
            st.session_state.gen_excel_bytes= None
            st.toast("Data refreshed!", icon="🔄")
            st.rerun()

        st.markdown('<div class="gold-divider" style="margin:14px 0;"></div>',
                    unsafe_allow_html=True)

        # ── Template management ───────────────────────────────────────────
        st.markdown("### 💾 Templates")

        # Save current cart as a named template
        with st.expander("Save Current Cart as Template"):
            tpl_name = st.text_input(
                "Template Name",
                placeholder="e.g. Dubai Q2 Order",
                key="sidebar_tpl_name_input",
            )
            if st.button("Save Template", use_container_width=True,
                         key="sidebar_save_tpl_btn"):
                if tpl_name.strip() and st.session_state.cart:
                    save_template_to_disk(tpl_name.strip(), st.session_state.cart)
                elif not tpl_name.strip():
                    st.warning("Please enter a template name.")
                else:
                    st.warning("Cart is empty — nothing to save.")

        # Load / delete existing templates
        templates = load_saved_templates()
        if templates:
            with st.expander(f"Load / Delete Templates ({len(templates)})"):
                for tpl_name, tpl_items in templates.items():
                    col_load, col_del = st.columns([3, 1])
                    with col_load:
                        if st.button(
                            f"📂 {tpl_name} ({len(tpl_items)} items)",
                            key=f"load_tpl_{tpl_name}",
                            use_container_width=True,
                        ):
                            st.session_state.cart          = list(tpl_items)
                            st.session_state.gen_pdf_bytes = None
                            st.session_state.gen_excel_bytes = None
                            st.toast(f"Loaded '{tpl_name}'", icon="📂")
                            st.rerun()
                    with col_del:
                        if st.button("🗑", key=f"del_tpl_{tpl_name}",
                                     use_container_width=True):
                            delete_template(tpl_name)
                            st.toast(f"Deleted '{tpl_name}'", icon="🗑️")
                            st.rerun()
        else:
            st.caption("No templates saved yet.")

        st.markdown('<div class="gold-divider" style="margin:14px 0;"></div>',
                    unsafe_allow_html=True)

        # ── Database info ─────────────────────────────────────────────────
        st.markdown("### 🗄️ Database")
        with st.expander("View DB Stats"):
            db = load_products_db()
            st.markdown(
                f"""
                <div style="font-size:12px;color:rgba(255,220,200,0.65);line-height:2;">
                  📦 Custom products: <b style="color:#f5a832;">{len(db.get('custom_products', []))}</b><br>
                  ✏️ Edited products: <b style="color:#f5a832;">{len(db.get('product_overrides', {}))}</b><br>
                  🚫 Hidden products: <b style="color:#f5a832;">{len(db.get('deleted_products', []))}</b><br>
                  🕐 Last updated: <b style="color:#f5a832;">{db.get('last_updated','—')[:19] if db.get('last_updated') else '—'}</b>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown('<div class="gold-divider" style="margin:14px 0;"></div>',
                    unsafe_allow_html=True)

        # ── Debug logs ────────────────────────────────────────────────────
        debug_logs = st.session_state.get("debug_logs", [])
        if debug_logs:
            with st.expander("🔍 Debug Logs"):
                for line in debug_logs[:30]:
                    st.caption(line)

        # ── Footer ────────────────────────────────────────────────────────
        st.markdown(
            """
            <div style="margin-top:30px;text-align:center;
                        font-size:10px;color:rgba(255,220,200,0.45);letter-spacing:1px;">
                HEM EXPORTS · CATALOGUE v3<br>
                <span style="color:#f5a832;">◆</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
