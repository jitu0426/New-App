"""
HEM Product Catalogue v3 — Tab 4: Add Product
Custom product creation, management, and admin tools
(override reset, hidden product restore).
"""
import time
import streamlit as st

from config import CATALOGUE_PATHS
from database import (
    load_products_db, add_custom_item, delete_custom_item,
    get_custom_products_from_db, remove_product_override, unmark_product_deleted,
)
from ui.components import section_header, confirm_action, gold_divider, empty_state


def render_add_product_tab(products_df) -> None:
    """Render Tab 4 — Add Product + Admin panels."""

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 1 — Add new custom product
    # ═══════════════════════════════════════════════════════════════════════
    section_header("Add New Product", icon="➕")
    st.markdown(
        '<div style="font-size:13px;color:#6b4040;margin-bottom:16px;">'
        'Create a custom product to include in any catalogue. '
        'It will be tagged <span class="badge-custom">CUSTOM</span> '
        'and optionally <span class="badge-new">NEW</span>.</div>',
        unsafe_allow_html=True,
    )

    with st.form("add_product_form_v3", clear_on_submit=True):
        col_a, col_b = st.columns(2)

        with col_a:
            existing_catalogues = list(CATALOGUE_PATHS.keys()) + ["Custom Items"]
            new_catalogue = st.selectbox("📚 Catalogue *", existing_catalogues)

            # Dynamic existing categories for chosen catalogue
            if not products_df.empty:
                existing_cats = (
                    products_df[products_df["Catalogue"] == new_catalogue]["Category"]
                    .unique().tolist()
                )
            else:
                existing_cats = []

            cat_mode = st.radio(
                "Category input mode",
                ["Select Existing", "Type New"],
                horizontal=True,
            )
            if cat_mode == "Select Existing" and existing_cats:
                new_category = st.selectbox("🏷️ Category *", existing_cats)
            else:
                new_category = st.text_input(
                    "🏷️ Category Name *",
                    placeholder="e.g. Hexa Incense Sticks",
                )

            new_subcategory = st.text_input(
                "Sub-Category",
                placeholder="Optional — e.g. Premium Range",
            )

        with col_b:
            new_item_name = st.text_input(
                "Product Name *",
                placeholder="e.g. Lavender Hexa",
            )
            new_fragrance = st.text_input(
                "Fragrance / Description",
                placeholder="e.g. Lavender",
            )
            new_sku = st.text_input(
                "SKU Code",
                placeholder="e.g. HEM-LAV-HEX-001",
            )
            new_is_new = st.checkbox("Mark as NEW product ✨", value=True)

        st.markdown("**Product Image** (optional)")
        new_image = st.file_uploader(
            "Upload image — JPG, PNG, or WebP",
            type=["jpg", "jpeg", "png", "webp"],
        )
        if new_image:
            st.image(new_image, caption="Preview", width=180)

        submitted = st.form_submit_button(
            "➕ Add Product to Catalogue",
            use_container_width=True,
            type="primary",
        )

        if submitted:
            errors = []
            if not new_catalogue:   errors.append("Catalogue is required.")
            if not new_category:    errors.append("Category is required.")
            if not new_item_name:   errors.append("Product Name is required.")

            for err in errors:
                st.error(err)

            if not errors:
                # Duplicate check
                if not products_df.empty:
                    dup = (
                        (products_df["ItemName"].str.lower()  == new_item_name.lower()) &
                        (products_df["Category"].str.lower()  == new_category.lower()) &
                        (products_df["Catalogue"]             == new_catalogue)
                    )
                    if dup.any():
                        st.warning(
                            f"'{new_item_name}' already exists in "
                            f"{new_catalogue} › {new_category}. "
                            "It will be saved as a separate custom product."
                        )

                with st.spinner("Saving product…"):
                    added = add_custom_item(
                        catalogue=new_catalogue,
                        category=new_category,
                        subcategory=new_subcategory or "N/A",
                        item_name=new_item_name,
                        fragrance=new_fragrance,
                        sku_code=new_sku,
                        is_new=new_is_new,
                        image_file=new_image,
                    )

                st.success(
                    f"✅ '{new_item_name}' added! (ID: {added['ProductID']})\n\n"
                    f"Click **Refresh Images & Excel** in the sidebar to see it in the list."
                )

    gold_divider()

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 2 — Manage custom products
    # ═══════════════════════════════════════════════════════════════════════
    section_header("Manage Custom Products", icon="🛠")

    custom_items = get_custom_products_from_db()
    if custom_items:
        st.markdown(
            f'<div style="font-size:12px;color:#6b4040;margin-bottom:10px;">'
            f'{len(custom_items)} custom product(s) in database.</div>',
            unsafe_allow_html=True,
        )
        for i, item in enumerate(custom_items):
            c_info, c_del = st.columns([6, 1])
            with c_info:
                new_tag = (
                    " <span class='badge-new'>NEW</span>"
                    if item.get("IsNew") == 1 else ""
                )
                st.markdown(
                    f"**{i+1}.** {item['ItemName']}{new_tag} &nbsp;|&nbsp; "
                    f"<span style='color:#6b4040;font-size:12px;'>"
                    f"{item['Catalogue']} › {item['Category']}</span>",
                    unsafe_allow_html=True,
                )
            with c_del:
                if confirm_action(
                    f"del_cust_{item['ProductID']}",
                    "🗑",
                    f"Delete '{item['ItemName']}'?",
                    danger=True,
                ):
                    delete_custom_item(item["ProductID"])
                    st.session_state.data_timestamp = time.time()
                    st.cache_data.clear()
                    st.toast(f"Deleted '{item['ItemName']}'", icon="🗑️")
                    st.rerun()
    else:
        empty_state("📦", "No custom products added yet.")

    gold_divider()

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 3 — Product override management
    # ═══════════════════════════════════════════════════════════════════════
    section_header("Manage Product Edits", icon="✏️")

    db        = load_products_db()
    overrides = db.get("product_overrides", {})

    if overrides:
        st.markdown(
            f'<div style="font-size:12px;color:#6b4040;margin-bottom:10px;">'
            f'{len(overrides)} product(s) have been edited.</div>',
            unsafe_allow_html=True,
        )
        for pid, changes in overrides.items():
            change_str = " · ".join(f"**{k}**: `{v}`" for k, v in changes.items())
            c_info, c_reset = st.columns([6, 1])
            with c_info:
                st.markdown(
                    f'<span style="font-size:11px;color:#a07070;">{pid}</span>'
                    f' &nbsp;→&nbsp; {change_str}',
                    unsafe_allow_html=True,
                )
            with c_reset:
                if st.button("↩ Reset", key=f"reset_{pid}", use_container_width=True):
                    remove_product_override(pid)
                    st.session_state.data_timestamp = time.time()
                    st.cache_data.clear()
                    st.toast(f"Reset edits for {pid}", icon="↩️")
                    st.rerun()
    else:
        empty_state("✏️", "No product edits have been made.")

    gold_divider()

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 4 — Hidden products
    # ═══════════════════════════════════════════════════════════════════════
    section_header("Hidden Products", icon="🚫")

    deleted_pids = db.get("deleted_products", [])

    if deleted_pids:
        st.markdown(
            f'<div style="font-size:12px;color:#6b4040;margin-bottom:10px;">'
            f'{len(deleted_pids)} product(s) are hidden from the catalogue.</div>',
            unsafe_allow_html=True,
        )
        for pid in deleted_pids:
            c_info, c_restore = st.columns([6, 1])
            with c_info:
                st.markdown(
                    f'<span style="font-size:12px;color:#a07070;">🚫 {pid}</span>',
                    unsafe_allow_html=True,
                )
            with c_restore:
                if st.button("↩ Restore", key=f"restore_{pid}", use_container_width=True):
                    unmark_product_deleted(pid)
                    st.session_state.data_timestamp = time.time()
                    st.cache_data.clear()
                    st.toast(f"Restored {pid}", icon="✅")
                    st.rerun()
    else:
        empty_state("🚫", "No products are currently hidden.")
