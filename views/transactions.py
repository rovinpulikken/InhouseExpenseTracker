"""
Transactions Page — Consolidated into 3 clean sub-pages:
  1. Ledger   (read-first card/table view + Edit mode grid + CSV export)
  2. Import   (PDF / Excel / CSV / Image AI parser + Email IMAP sync + Review & Confirm)
  3. Clean up (Duplicate Detector + ML Auto-Categorizer + Bulk Delete Month)
"""

import datetime
import io
import pandas as pd
import streamlit as st

from config import EXPENSE_CATEGORIES, format_inr, format_inr_short, format_month_label
from categorizer import auto_categorize_records, apply_ml_auto_categorization
from database import update_user_profile
import data_layer
import ui


def _generate_excel_template() -> bytes:
    df_template = pd.DataFrame([
        {"Date (YYYY-MM-DD)": "2026-05-01", "Category": "Groceries & Provisions", "Description": "Weekly D-Mart shopping", "Amount (INR)": 4500.00, "Visibility": "Family"},
        {"Date (YYYY-MM-DD)": "2026-05-03", "Category": "Utilities (Electricity/Water/Gas)", "Description": "LPG Gas Cylinder", "Amount (INR)": 950.00, "Visibility": "Family"},
        {"Date (YYYY-MM-DD)": "2026-05-10", "Category": "Shopping & Apparel", "Description": "Personal clothing", "Amount (INR)": 1800.00, "Visibility": "Private"},
    ])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_template.to_excel(writer, index=False, sheet_name="Expense_Template")
    return output.getvalue()


def _import_from_excel_or_csv(file, visibility: str = "Family") -> tuple:
    try:
        df = pd.read_csv(file) if file.name.lower().endswith(".csv") else pd.read_excel(file)
        col_map = {}
        for col in df.columns:
            c_lower = str(col).lower().strip()
            if "date" in c_lower or "dt" in c_lower:
                col_map[col] = "date"
            elif "cat" in c_lower or "group" in c_lower or "head" in c_lower:
                col_map[col] = "category"
            elif "desc" in c_lower or "note" in c_lower or "item" in c_lower or "particular" in c_lower or "remark" in c_lower:
                col_map[col] = "description"
            elif "amt" in c_lower or "amount" in c_lower or "price" in c_lower or "inr" in c_lower or "rupee" in c_lower or "cost" in c_lower or "val" in c_lower or "exp" in c_lower:
                col_map[col] = "amount"
            elif "vis" in c_lower or "share" in c_lower or "mode" in c_lower:
                col_map[col] = "visibility"

        df.rename(columns=col_map, inplace=True)
        for col_req in ["date", "category", "description", "amount"]:
            if col_req not in df.columns:
                df[col_req] = "" if col_req != "amount" else 0.0
        if "visibility" not in df.columns:
            df["visibility"] = visibility

        df["amount"] = pd.to_numeric(
            df["amount"].astype(str).str.replace("₹", "").str.replace("Rs", "").str.replace(",", "").str.strip(),
            errors="coerce",
        ).fillna(0.0)
        df = df[df["amount"] > 0]
        if df.empty:
            return None, f"No valid rows with expense amounts > 0 were found in {file.name}."

        records = df[["date", "category", "description", "amount", "visibility"]].to_dict("records")
        records = auto_categorize_records(records)
        df_final = pd.DataFrame(records)
        df_final["transaction_type"] = "Expense"
        return df_final, f"Successfully parsed {len(df_final)} expense rows from {file.name}!"
    except Exception as e:
        return None, f"Error processing file: {e}"


def _detect_and_flag_duplicates(df_import: pd.DataFrame, username: str, view_mode: str, family_id) -> pd.DataFrame:
    existing = data_layer.get_expenses_df(
        fy="All FYs", username=username, view_mode=view_mode, family_id=family_id, transaction_type="All"
    )
    existing_sigs = set()
    if not existing.empty:
        for _, row in existing.iterrows():
            existing_sigs.add((str(row["expense_date"]).strip()[:10], float(row.get("amount", 0))))

    dup_list, imp_list = [], []
    for _, row in df_import.iterrows():
        sig = (str(row.get("date", "")).strip()[:10], float(row.get("amount", 0)))
        is_dup = sig in existing_sigs
        dup_list.append(is_dup)
        imp_list.append(not is_dup)

    df_import["duplicate_warning"] = dup_list
    df_import["import"] = imp_list
    return df_import


def render() -> None:
    current_user, user_family_id, _ = ui.get_active_user()
    ui.render_mobile_quick_bar("transactions")

    scope = ui.render_scope_bar(
        current_user, user_family_id, show_view=True, show_fy=True, show_month=True, page_key="tx"
    )
    view_mode = scope["view"]
    selected_fy = scope["fy"]
    selected_month = scope["month"]
    month_label = scope["month_label"]

    ui.render_page_header(
        "💸",
        "Transactions",
        subtitle="One unified ledger to inspect, edit, import, and clean your cash flow.",
        accent="#38bdf8",
        badge=f"{view_mode} · {month_label if selected_month != 'All Months' else selected_fy}",
    )

    sub_options = ["📅 Ledger", "📤 Import", "🧹 Clean up"]
    default_sub = ui.consume_target_sub("transactions", sub_options, sub_options[0])
    active_sub = ui.segmented_pills("Transactions Section", sub_options, key="tx_sub_nav", default=default_sub)

    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    if active_sub == "📅 Ledger":
        _render_ledger(current_user, user_family_id, view_mode, selected_fy, selected_month, month_label)
    elif active_sub == "📤 Import":
        _render_import(current_user, user_family_id, view_mode)
    else:
        _render_cleanup(current_user, user_family_id, view_mode, selected_fy)


def _render_ledger(current_user, user_family_id, view_mode: str, selected_fy: str, selected_month: str, month_label: str) -> None:
    all_tx_fy = data_layer.get_expenses_df(
        fy=selected_fy,
        username=current_user["username"],
        view_mode=view_mode,
        family_id=user_family_id,
        transaction_type="All",
    )
    period_df = ui.filter_df_by_month(all_tx_fy, selected_month)

    if not period_df.empty:
        if "transaction_type" not in period_df.columns:
            period_df["transaction_type"] = "Expense"
        period_df["transaction_type"] = period_df["transaction_type"].fillna("Expense").astype(str).str.strip().str.title()
        period_df["transaction_type"] = period_df["transaction_type"].apply(lambda x: "Income" if x.lower() == "income" else "Expense")
        period_df["amount"] = pd.to_numeric(period_df["amount"], errors="coerce").fillna(0.0)

    tx_exp = float(period_df[period_df["transaction_type"] == "Expense"]["amount"].sum()) if not period_df.empty else 0.0
    tx_inc = float(period_df[period_df["transaction_type"] == "Income"]["amount"].sum()) if not period_df.empty else 0.0

    inc_src_df = data_layer.cached_get_income_sources_df(
        username=current_user["username"], family_id=user_family_id, view_mode=view_mode
    )
    rec_mo_inc = float(inc_src_df["monthly_equivalent"].sum()) if not inc_src_df.empty and "monthly_equivalent" in inc_src_df.columns else 0.0
    num_m = 1 if selected_month != "All Months" else max(1, int(all_tx_fy["Month_Key"].nunique()) if not all_tx_fy.empty and "Month_Key" in all_tx_fy.columns else 1)
    total_inc = tx_inc if tx_inc > 0 else (rec_mo_inc * num_m)
    net_sav = total_inc - tx_exp
    sav_rate = (net_sav / total_inc * 100.0) if total_inc > 0 else 0.0

    ui.render_kpi_grid(
        [
            {"label": "Income", "value": format_inr_short(total_inc), "sub": "logged" if tx_inc > 0 else "recurring baseline", "color": "#38bdf8", "accent": "#38bdf8"},
            {"label": "Expenses", "value": format_inr_short(tx_exp), "sub": f"{len(period_df[period_df['transaction_type']=='Expense']) if not period_df.empty else 0} entries", "color": "#f43f5e", "accent": "#f43f5e"},
            {"label": "Net Savings", "value": f"{'+' if net_sav > 0 else ''}{format_inr_short(net_sav)}", "sub": "Income − Expenses", "color": "#34d399" if net_sav >= 0 else "#f87171"},
            {"label": "Savings Rate", "value": f"{sav_rate:.1f}%", "sub": f"{len(period_df)} total records", "color": "#c084fc"},
        ],
        cols=4,
    )

    # Action + Filter toolbar
    tb1, tb2, tb3, tb4 = st.columns([1.4, 1.8, 1.5, 1.2])
    with tb1:
        type_filter = st.selectbox("Type", ["All", "Expenses", "Income"], key="ledger_type_f", label_visibility="collapsed")
    with tb2:
        avail_cats = sorted(period_df["category"].dropna().unique().tolist()) if not period_df.empty and "category" in period_df.columns else []
        cat_opts = ["All Categories"] + avail_cats
        deep_cat = st.session_state.pop("_ledger_cat_filter", None)
        if deep_cat and deep_cat in cat_opts:
            st.session_state["ledger_cat_f"] = deep_cat
        cur_cat = st.session_state.get("ledger_cat_f", "All Categories")
        if cur_cat not in cat_opts:
            cur_cat = "All Categories"
        cat_filter = st.selectbox("Category", cat_opts, index=cat_opts.index(cur_cat), key="ledger_cat_f", label_visibility="collapsed")
    with tb3:
        search_q = st.text_input("Search", placeholder="🔍 Search description...", key="ledger_search", label_visibility="collapsed")
    with tb4:
        if st.button("➕ Add Entry", type="primary", use_container_width=True, key="ledger_add_btn"):
            ui.open_add_transaction_dialog(current_user, user_family_id)

    # Apply filters
    filtered = period_df.copy()
    if not filtered.empty:
        if type_filter == "Expenses":
            filtered = filtered[filtered["transaction_type"] == "Expense"]
        elif type_filter == "Income":
            filtered = filtered[filtered["transaction_type"] == "Income"]
        if cat_filter != "All Categories":
            filtered = filtered[filtered["category"] == cat_filter]
        if search_q.strip():
            filtered = filtered[
                filtered["description"].astype(str).str.contains(search_q.strip(), case=False, na=False)
                | filtered["category"].astype(str).str.contains(search_q.strip(), case=False, na=False)
            ]

    # Read vs Edit toggle + Contextual Export
    ctrl1, ctrl2, ctrl3 = st.columns([1.5, 1.5, 1.5])
    with ctrl1:
        edit_mode = st.toggle("✏️ Edit / Bulk Entry Mode", value=False, key="ledger_edit_mode")
    with ctrl2:
        view_style = st.radio("Display", ["Cards", "Table"], horizontal=True, key="ledger_display_style", label_visibility="collapsed") if not edit_mode else "Grid"
    with ctrl3:
        if not filtered.empty:
            exp_csv = filtered.drop(columns=["Month_Key"], errors="ignore").to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇ Export CSV",
                data=exp_csv,
                file_name=f"FinCompass_Ledger_{selected_month}_{type_filter}.csv",
                mime="text/csv",
                use_container_width=True,
                key="ledger_export_csv",
            )

    if edit_mode:
        st.caption("Edit cells directly, add new rows at the bottom, or check **Delete?** to remove records. Click **Save Changes** when done.")
        if filtered.empty:
            default_dt = datetime.date.today().isoformat()
            editor_data = pd.DataFrame([
                {"id": 0, "expense_date": default_dt, "transaction_type": "Expense", "category": EXPENSE_CATEGORIES[0], "description": "", "amount": 0.0, "visibility": "Family", "Delete?": False}
            ])
        else:
            ed = filtered.copy()
            ed["expense_date"] = pd.to_datetime(ed["expense_date"], errors="coerce").dt.strftime("%Y-%m-%d")
            ed["Delete?"] = False
            for c in ["id", "category", "description", "amount", "visibility", "transaction_type"]:
                if c not in ed.columns:
                    ed[c] = "" if c in ("category", "description") else 0.0
            editor_data = ed[["id", "expense_date", "transaction_type", "category", "description", "amount", "visibility", "Delete?"]].copy()

        edited_df = st.data_editor(
            editor_data,
            num_rows="dynamic",
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                "expense_date": st.column_config.TextColumn("Date (YYYY-MM-DD)", required=True),
                "transaction_type": st.column_config.SelectboxColumn("Type", options=["Expense", "Income"], required=True, width="small"),
                "category": st.column_config.SelectboxColumn("Category", options=ui.ALL_TRANSACTION_CATEGORIES, required=True),
                "description": st.column_config.TextColumn("Description"),
                "amount": st.column_config.NumberColumn("Amount (₹)", min_value=0.0, format="₹ %.2f", required=True),
                "visibility": st.column_config.SelectboxColumn("Visibility", options=["Family", "Private"], required=True, width="small"),
                "Delete?": st.column_config.CheckboxColumn("Delete?", default=False, width="small"),
            },
            use_container_width=True,
            hide_index=True,
            key=f"ledger_editor_{selected_month}_{type_filter}",
        )

        sc1, sc2 = st.columns(2)
        with sc1:
            save_clicked = st.button("💾 Save Changes", type="primary", use_container_width=True, key="ledger_save_btn")
        with sc2:
            auto_save_clicked = st.button("✨ Auto-Categorize New Rows & Save", use_container_width=True, key="ledger_autocat_save_btn")

        if save_clicked or auto_save_clicked:
            to_del = edited_df[edited_df["Delete?"] == True]["id"].dropna().tolist()
            int_ids = [int(i) for i in to_del if i and not pd.isna(i) and int(i) > 0]
            del_cnt = data_layer.delete_multiple_expenses(int_ids) if int_ids else 0

            keep_rows = edited_df[edited_df["Delete?"] != True].copy()
            existing_rows = keep_rows[keep_rows["id"].notna() & (keep_rows["id"] > 0)]
            upd_cnt = data_layer.update_expenses_df(existing_rows) if not existing_rows.empty else 0

            new_rows = keep_rows[keep_rows["id"].isna() | (keep_rows["id"] <= 0)]
            ins_cnt = 0
            if not new_rows.empty:
                recs = []
                for _, nr in new_rows.iterrows():
                    r_amt = float(nr.get("amount") or 0.0)
                    if r_amt > 0:
                        recs.append({
                            "date": str(nr.get("expense_date") or datetime.date.today().isoformat()),
                            "category": str(nr.get("category") or "Miscellaneous"),
                            "description": str(nr.get("description") or ""),
                            "amount": r_amt,
                            "visibility": str(nr.get("visibility") or "Family"),
                            "transaction_type": str(nr.get("transaction_type") or "Expense"),
                        })
                if recs:
                    if auto_save_clicked:
                        recs = auto_categorize_records(recs)
                    ins_cnt = data_layer.insert_expenses(
                        recs,
                        source="Ledger Grid",
                        username=current_user["username"],
                        visibility="Family",
                        family_id=user_family_id or 1,
                    )

            parts = []
            if upd_cnt: parts.append(f"updated {upd_cnt}")
            if ins_cnt: parts.append(f"added {ins_cnt}")
            if del_cnt: parts.append(f"deleted {del_cnt}")
            st.toast(f"✅ Saved: {', '.join(parts)}." if parts else "No changes detected.")
            st.rerun()
        return

    # Read-first display
    if filtered.empty:
        if ui.render_empty_state(
            "📭",
            f"No transactions match {month_label}",
            "Try changing the month/filter or log a new transaction.",
            cta_label="➕ Add Transaction",
            cta_key="ledger_empty_add",
        ):
            ui.open_add_transaction_dialog(current_user, user_family_id)
        return

    sorted_df = filtered.sort_values("expense_date", ascending=False)
    if view_style == "Cards":
        st.caption(f"Showing {len(sorted_df)} transaction(s) — toggle **✏️ Edit Mode** above to edit or add rows in bulk.")
        for _, row in sorted_df.head(60).iterrows():
            ui.render_tx_card(row.to_dict())
        if len(sorted_df) > 60:
            st.info(f"Showing most recent 60 of {len(sorted_df)} entries. Switch to **Table** view or search above to see all.")
    else:
        disp = sorted_df[["expense_date", "transaction_type", "category", "description", "amount", "visibility", "username"]].copy()
        st.dataframe(
            disp,
            column_config={
                "expense_date": st.column_config.DateColumn("Date"),
                "transaction_type": st.column_config.TextColumn("Type"),
                "category": st.column_config.TextColumn("Category"),
                "description": st.column_config.TextColumn("Description"),
                "amount": st.column_config.NumberColumn("Amount (₹)", format="₹ %.2f"),
                "visibility": st.column_config.TextColumn("Visibility"),
                "username": st.column_config.TextColumn("By"),
            },
            use_container_width=True,
            hide_index=True,
        )


def _render_import(current_user, user_family_id, view_mode: str) -> None:
    st.markdown("#### 📤 Import Bank / Card Statements or Receipts")
    st.caption("Step 1: Upload PDF, Excel, CSV, or Receipt Images (or sync Gmail) → Step 2: Review duplicates & categories → Step 3: Save.")

    col_up, col_tpl = st.columns([2.2, 1])
    with col_tpl:
        st.markdown("##### 📥 Offline Template")
        st.caption("Prefer Excel? Download our pre-formatted template.")
        st.download_button(
            "📥 Download Excel Template",
            data=_generate_excel_template(),
            file_name="FinCompass_Expense_Template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with col_up:
        upload_vis = st.radio("Visibility for imported entries", ["Family", "Private"], horizontal=True, key="imp_upload_vis")
        uploaded_files = st.file_uploader(
            "Upload PDF, Excel, CSV, or Receipt Images",
            type=["xlsx", "xls", "csv", "pdf", "jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff", "gif", "heic"],
            accept_multiple_files=True,
            key="imp_file_uploader",
        )
        _IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".heic")

        pdf_password = ""
        if uploaded_files and any(f.name.lower().endswith(".pdf") for f in uploaded_files):
            pdf_password = st.text_input(
                "PDF Password (if protected)",
                value=current_user.get("pdf_password", ""),
                type="password",
                key="imp_pdf_pwd",
            )

        _img_files = [f for f in uploaded_files if f.name.lower().endswith(_IMAGE_EXTS)] if uploaded_files else []
        if _img_files:
            pcols = st.columns(min(len(_img_files), 3))
            for i, imgf in enumerate(_img_files):
                with pcols[i % len(pcols)]:
                    st.image(imgf, caption=f"📷 {imgf.name}", use_container_width=True)

        gemini_api_key = data_layer.get_gemini_api_key(current_user)

        if uploaded_files:
            st.markdown(f"📎 **{len(uploaded_files)} file(s)** selected")
            if st.button("🚀 Parse & Auto-Categorize", type="primary", use_container_width=True, key="imp_parse_btn"):
                if pdf_password and pdf_password.strip() != current_user.get("pdf_password", ""):
                    update_user_profile(current_user["username"], {"pdf_password": pdf_password.strip()})
                    current_user["pdf_password"] = pdf_password.strip()
                    st.session_state["user"]["pdf_password"] = pdf_password.strip()

                all_frames = []
                pbar = st.progress(0, text="Parsing...")
                for idx, uf in enumerate(uploaded_files):
                    pbar.progress(idx / len(uploaded_files), text=f"Parsing {idx+1}/{len(uploaded_files)}: {uf.name}")
                    is_img = uf.name.lower().endswith(_IMAGE_EXTS)
                    is_std = (
                        not is_img
                        and uf.name.lower().endswith((".xlsx", ".csv"))
                        and "statement" not in uf.name.lower()
                        and "bill" not in uf.name.lower()
                    )
                    if is_std:
                        df_p, msg = _import_from_excel_or_csv(uf, visibility=upload_vis)
                        if df_p is not None and not df_p.empty:
                            df_p["_source_file"] = uf.name
                            df_p = _detect_and_flag_duplicates(df_p, current_user["username"], view_mode, user_family_id)
                            all_frames.append(df_p)
                            st.success(f"✅ {uf.name}: {msg}")
                        else:
                            st.warning(f"⚠️ {uf.name}: {msg}")
                    else:
                        if not gemini_api_key:
                            st.error(f"⚠️ {uf.name}: Gemini API Key required for AI parsing. Configure it in **Settings → Integrations**.")
                        else:
                            from statement_parser import parse_expense_statement_with_gemini
                            try:
                                raw_json = parse_expense_statement_with_gemini(uf.getvalue(), uf.name, gemini_api_key, pdf_password)
                                df_p = pd.DataFrame(raw_json)
                                if not df_p.empty:
                                    for col in ["date", "description", "amount", "transaction_type", "category"]:
                                        if col not in df_p.columns:
                                            df_p[col] = ""
                                    df_p["transaction_type"] = df_p["transaction_type"].astype(str).str.strip().str.title()
                                    df_p["category"] = df_p["category"].astype(str).str.strip().str.title()
                                    df_p = df_p[df_p["transaction_type"] != "Income"]
                                    df_p = df_p[~df_p["category"].str.contains("Refund", case=False, na=False)]
                                    if not df_p.empty:
                                        df_p["amount"] = pd.to_numeric(df_p["amount"], errors="coerce").fillna(0.0)
                                        df_p["date"] = pd.to_datetime(df_p["date"], errors="coerce").dt.strftime("%Y-%m-%d").fillna(str(datetime.date.today()))
                                        df_p["_source_file"] = uf.name
                                        df_p = _detect_and_flag_duplicates(df_p, current_user["username"], view_mode, user_family_id)
                                        all_frames.append(df_p)
                                        st.success(f"✅ {uf.name}: {len(df_p)} transactions extracted")
                                    else:
                                        st.warning(f"⚠️ {uf.name}: No expense rows found (only Income/Refunds).")
                                else:
                                    st.warning(f"⚠️ {uf.name}: No transactions found.")
                            except Exception as e:
                                st.error(f"❌ {uf.name}: {e}")
                pbar.progress(1.0, text="Done!")
                if all_frames:
                    st.session_state["parsed_statement_df"] = pd.concat(all_frames, ignore_index=True)
                    st.rerun()

    # Email Sync expander
    with st.expander("📩 Sync from Email (GPay / Amazon Pay / Bank Statements)"):
        st.caption("Connect your Gmail with a 16-character Google App Password (configure permanently in **Settings → Integrations**).")
        ec1, ec2 = st.columns(2)
        with ec1:
            sync_email = st.text_input("IMAP Email (Gmail)", value=current_user.get("imap_email") or "", key="imp_imap_email")
            imap_days = st.slider("Look back (days)", 1, 30, 3, key="imp_imap_days")
        with ec2:
            sync_pwd = st.text_input("IMAP App Password", value=current_user.get("imap_app_password") or "", type="password", key="imp_imap_pwd")
            email_pdf_pwd = st.text_input("Statement PDF Password", value=current_user.get("pdf_password") or "", type="password", key="imp_email_pdf_pwd")

        sb1, sb2 = st.columns(2)
        with sb1:
            if st.button("💾 Save Credentials", use_container_width=True, key="imp_save_imap"):
                update_user_profile(current_user["username"], {
                    "imap_email": sync_email.strip(),
                    "imap_app_password": sync_pwd.strip().replace(" ", ""),
                    "pdf_password": email_pdf_pwd.strip(),
                })
                st.session_state["user"]["imap_email"] = sync_email.strip()
                st.session_state["user"]["imap_app_password"] = sync_pwd.strip().replace(" ", "")
                st.session_state["user"]["pdf_password"] = email_pdf_pwd.strip()
                st.toast("✅ Email sync credentials saved.")
        with sb2:
            if st.button("🚀 Start Email Sync", type="primary", use_container_width=True, key="imp_run_imap"):
                gemini_api_key = data_layer.get_gemini_api_key(current_user)
                if not gemini_api_key:
                    st.error("Gemini API Key required. Add it in **Settings → Integrations**.")
                elif not sync_email.strip() or not sync_pwd.strip():
                    st.error("Enter IMAP Email and 16-character App Password.")
                else:
                    try:
                        from imap_sync import fetch_recent_transaction_emails, parse_emails_to_dataframe
                        with st.spinner("Scanning inbox..."):
                            emails_list = fetch_recent_transaction_emails(sync_email.strip(), sync_pwd.strip().replace(" ", ""), days=imap_days)
                        if not emails_list:
                            st.warning(f"No payment emails found in the last {imap_days} days.")
                        else:
                            with st.spinner(f"AI parsing {len(emails_list)} email(s)..."):
                                df_emails = parse_emails_to_dataframe(emails_list, gemini_api_key, email_pdf_pwd.strip())
                            if df_emails is not None and not df_emails.empty:
                                df_emails = _detect_and_flag_duplicates(df_emails, current_user["username"], view_mode, user_family_id)
                                if "parsed_statement_df" in st.session_state:
                                    st.session_state["parsed_statement_df"] = pd.concat([st.session_state["parsed_statement_df"], df_emails], ignore_index=True)
                                else:
                                    st.session_state["parsed_statement_df"] = df_emails
                                st.toast("✅ Extracted email transactions for review.")
                                st.rerun()
                            else:
                                st.warning("Could not extract any expenses from emails.")
                    except Exception as e:
                        st.error(f"Email Sync Error: {e}")

    # Step 2 & 3: Review & Confirm
    if "parsed_statement_df" in st.session_state:
        st.markdown("---")
        st.markdown("#### 🔍 Step 2: Review & Confirm Extracted Transactions")
        st.info("Duplicates are unchecked automatically. Adjust categories or amounts, then click **Confirm & Save**.")
        edited_df = st.data_editor(
            st.session_state["parsed_statement_df"],
            num_rows="dynamic",
            column_config={
                "import": st.column_config.CheckboxColumn("Import?", default=True),
                "duplicate_warning": st.column_config.CheckboxColumn("Duplicate?", disabled=True),
                "_source_file": st.column_config.TextColumn("Source", disabled=True),
                "date": st.column_config.TextColumn("Date (YYYY-MM-DD)"),
                "description": st.column_config.TextColumn("Description"),
                "amount": st.column_config.NumberColumn("Amount (₹)", required=True),
                "transaction_type": st.column_config.SelectboxColumn("Type", options=["Expense", "Income"], required=True),
                "category": st.column_config.SelectboxColumn("Category", options=ui.ALL_TRANSACTION_CATEGORIES, required=True),
            },
            use_container_width=True,
            key="imp_review_editor",
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 Confirm & Save to Database", type="primary", use_container_width=True, key="imp_confirm_btn"):
                valid_records = []
                for r in edited_df.to_dict("records"):
                    if r.get("import", True):
                        r["visibility"] = upload_vis
                        try:
                            r["amount"] = abs(float(str(r.get("amount", 0)).replace(",", "")))
                        except Exception:
                            pass
                        valid_records.append(r)
                if valid_records:
                    cnt = data_layer.insert_expenses(
                        valid_records,
                        source="AI Import / Bulk",
                        username=current_user["username"],
                        visibility=upload_vis,
                        family_id=user_family_id or 1,
                    )
                    st.toast(f"✅ Saved {cnt} imported transaction(s)!")
                del st.session_state["parsed_statement_df"]
                st.rerun()
        with c2:
            if st.button("❌ Discard", use_container_width=True, key="imp_discard_btn"):
                del st.session_state["parsed_statement_df"]
                st.rerun()


def _render_cleanup(current_user, user_family_id, view_mode: str, selected_fy: str) -> None:
    # 1. ML Auto-Categorizer (moved from Settings)
    st.markdown("#### 🤖 ML Auto-Categorizer")
    st.caption("Automatically classify Miscellaneous or all expenses using your learned spending history & Indian merchant rules.")
    fy_df = data_layer.get_expenses_df(
        fy=selected_fy, username=current_user["username"], view_mode=view_mode, family_id=user_family_id
    )
    ml1, ml2 = st.columns(2)
    with ml1:
        if st.button("🤖 Auto-Categorize Misc / Uncategorized", use_container_width=True, key="cln_ml_misc", disabled=fy_df.empty):
            hist_df = data_layer.get_expenses_df(fy="All FYs", username=None, view_mode="All", family_id=user_family_id)
            updated_df, mod_cnt, t_cnt = apply_ml_auto_categorization(fy_df, hist_df.to_dict("records"), overwrite_all=False)
            if mod_cnt > 0:
                data_layer.update_expenses_df(updated_df)
                st.toast(f"🎉 Auto-categorized {mod_cnt} record(s) from {t_cnt} patterns!")
                st.rerun()
            else:
                st.info("All records in this FY are already categorized.")
    with ml2:
        if st.button("⚡ Re-Categorize All Items in Scope", use_container_width=True, key="cln_ml_all", disabled=fy_df.empty):
            hist_df = data_layer.get_expenses_df(fy="All FYs", username=None, view_mode="All", family_id=user_family_id)
            updated_df, mod_cnt, t_cnt = apply_ml_auto_categorization(fy_df, hist_df.to_dict("records"), overwrite_all=True)
            if mod_cnt > 0:
                data_layer.update_expenses_df(updated_df)
                st.toast(f"⚡ Re-categorized {mod_cnt} item(s) using {t_cnt} patterns!")
                st.rerun()
            else:
                st.info("All categories are already up to date.")

    st.markdown("---")

    # 2. Duplicate Detector
    st.markdown("#### 🕵️ Detect & Remove Duplicates")
    st.caption("Scans all Financial Years for entries with the exact same Date + Amount.")
    all_time_df = data_layer.get_expenses_df(
        fy="All FYs", username=current_user["username"], view_mode=view_mode, family_id=user_family_id
    )
    if all_time_df.empty:
        st.info("No records to scan.")
    else:
        dup_counts = all_time_df.groupby(["expense_date", "amount"]).size().reset_index(name="count")
        dup_groups = dup_counts[dup_counts["count"] > 1]
        if dup_groups.empty:
            st.success("✅ No duplicate entries found across any Financial Year!")
        else:
            st.warning(f"Found **{len(dup_groups)}** duplicate group(s).")
            merged = pd.merge(all_time_df, dup_groups, on=["expense_date", "amount"]).sort_values(["expense_date", "amount", "id"])
            merged["Delete"] = merged.duplicated(subset=["expense_date", "amount"], keep="first")
            show_cols = [c for c in ["Delete", "id", "expense_date", "category", "description", "amount", "source_note"] if c in merged.columns]
            edited_dups = st.data_editor(
                merged[show_cols],
                num_rows="fixed",
                column_config={
                    "Delete": st.column_config.CheckboxColumn("🗑️ Delete?"),
                    "id": st.column_config.NumberColumn("ID", disabled=True),
                    "expense_date": st.column_config.DateColumn("Date", disabled=True),
                    "category": st.column_config.TextColumn("Category", disabled=True),
                    "description": st.column_config.TextColumn("Description", disabled=True),
                    "amount": st.column_config.NumberColumn("Amount", format="₹ %.2f", disabled=True),
                    "source_note": st.column_config.TextColumn("Source", disabled=True),
                },
                use_container_width=True,
                hide_index=True,
                key="cln_dup_editor",
            )
            to_delete = edited_dups[edited_dups["Delete"] == True]["id"].tolist()
            if to_delete:
                if st.button(f"🗑️ Delete {len(to_delete)} Selected Duplicate(s)", type="primary", key="cln_del_dups"):
                    data_layer.delete_multiple_expenses([int(i) for i in to_delete])
                    st.toast(f"🗑️ Deleted {len(to_delete)} duplicate(s).")
                    st.rerun()

    st.markdown("---")

    # 3. Danger Zone — Bulk Delete Month (collapsed)
    with st.expander("⚠️ Danger Zone — Bulk Delete Entire Month", expanded=False):
        st.warning("**This cannot be undone.** Permanently removes all entries for a selected month.")
        if not all_time_df.empty and "expense_date" in all_time_df.columns:
            if "Month_Year" not in all_time_df.columns:
                all_time_df["Month_Year"] = pd.to_datetime(all_time_df["expense_date"], errors="coerce").dt.strftime("%b %Y")
            avail_m = all_time_df.sort_values("expense_date", ascending=False)["Month_Year"].dropna().drop_duplicates().tolist()
        else:
            avail_m = []

        if avail_m:
            del_m = st.selectbox("Select Month to Wipe", avail_m, format_func=format_month_label, key="cln_bulk_del_m")
            m_recs = all_time_df[all_time_df["Month_Year"] == del_m]
            st.error(f"Month **{del_m}** → **{len(m_recs)} entries**, total **{format_inr(float(m_recs['amount'].sum()))}**.")
            confirm_chk = st.checkbox(f"I confirm — permanently delete ALL entries for {del_m}", key="cln_chk_del")
            if st.button(f"🔥 Wipe All Data for {del_m}", type="primary", disabled=not confirm_chk, use_container_width=True, key="cln_btn_wipe"):
                cnt_del = data_layer.delete_month_expenses(del_m)
                st.toast(f"🔥 Deleted {cnt_del} records for {del_m}.")
                st.rerun()
        else:
            st.caption("No months available to delete.")

