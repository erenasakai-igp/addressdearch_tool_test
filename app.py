import os, io, warnings, re
import streamlit as st
import pandas as pd

warnings.filterwarnings("ignore")
st.config.set_option("server.enableCORS", False)
st.config.set_option("server.enableXsrfProtection", False)
st.config.set_option("server.websocketAsByteArray", True)

st.set_page_config(page_title="物件検索ツール", page_icon="🏢", layout="wide")
st.title("🏢 不動産ポテンシャル 現場用一発検索ツール")
st.write("【公共データ × 有料データ 統合デモ画面】")

l2_excel_file = None
paid_company_files = []
for root, dirs, files in os.walk("/content"):
    for f_name in files:
        if "デモデータ" in f_name and f_name.endswith(".xlsx"): l2_excel_file = os.path.join(root, f_name)
        if "有料データ_" in f_name and f_name.endswith(".xlsx"): paid_company_files.append(os.path.join(root, f_name))

if l2_excel_file is None:
    st.error("⚠️ 左側のファイルエリアに『デモデータ_面積・路線価.xlsx』が見つかりません。")
else:
    df_l2 = pd.read_excel(l2_excel_file, header=1).fillna("")
    st.subheader("🔍 現場用・住所検索窓")
    search_query = st.text_input("土地の住所、または物件名を入力してください（例：九段南、赤坂見附、など）：", placeholder="例：東京都千代田区九段南一丁目2-1、など")

    if search_query:
        name_col, addr_col = None, None
        for col in df_l2.columns:
            c_str = str(col).strip()
            if "物件名" in c_str or "店舗名" in c_str or "名称" in c_str: name_col = col
            if "正規化住所" in c_str: addr_col = col
        if name_col is None: name_col = df_l2.columns[1]
        if addr_col is None: addr_col = df_l2.columns[3]

        l2_result = df_l2[df_l2[name_col].astype(str).str.contains(search_query, case=False) | df_l2[addr_col].astype(str).str.contains(search_query, case=False)]

        if not l2_result.empty:
            st.success(f"🗺️ 指定された住所周辺の公共データが {len(l2_result)} 件ヒットしました。")
            for idx, l2_row in l2_result.iterrows():
                target_address = str(l2_row[addr_col]).strip()
                
                with st.container():
                    st.markdown(f"### 📍 検索地点： {l2_row[name_col]} （{target_address}）")
                    col1, col2, col3,col4 = st.columns(4)
                    with col1:
                        area_val = "データなし"
                        for c in l2_result.columns:
                            if "面積" in str(c) and "土地利用" in str(c): area_val = l2_row[c]; break
                        st.metric(label="🏢 算出面積", value=f"{area_val} ㎡")
                    with col2:
                        price_val = "データなし"
                        for c in l2_result.columns:
                            if "路線価" in str(c): price_val = l2_row[c]; break
                        price_str = f"{price_val:,} 円/㎡" if isinstance(price_val, (int, float)) and price_val > 0 else f"{price_val}"
                        st.metric(label="💰 前面道路路線価", value=price_str)
                    with col3:
                        price_val = "データなし"
                        for c in l2_result.columns:
                            if "L01_042" in str(c): price_val = l2_row[c]; break
                        price_str = f"{price_val:,}m" if isinstance(price_val, (int, float)) and price_val > 0 else f"{price_val}"
                        st.metric(label="📐 前面道路幅員", value=price_str)
                    with col4:
                        youto_val = "不明"
                        for c in l2_result.columns:
                            if "L01_051" in str(c): youto_val = l2_row[c]; break
                        st.metric(label="🚧 用途区分名", value=str(youto_val))

                    with st.expander("📊 選択物件の『物件詳細データベース』（公共データ全情報）を表示"):
                        # 1行の辞書データにして見やすく縦型テーブル（シリーズ形式）で表示
                        detail_df = pd.DataFrame(l2_row).rename(columns={idx: "詳細データ"})
                        st.dataframe(detail_df, use_container_width=True)

                matched_company_name = None
                matched_company_df = None
                for comp_file in paid_company_files:
                    try:
                        df_comp_master = pd.read_excel(comp_file).fillna("")
                        comp_addr_col = None
                        for c in df_comp_master.columns:
                            if "address" in str(c).lower() or "住所" in str(c): comp_addr_col = c; break
                        if comp_addr_col is None: comp_addr_col = df_comp_master.columns[6]

                        for comp_idx, comp_row in df_comp_master.iterrows():
                            comp_addr = str(comp_row[comp_addr_col]).strip()
                            clean_comp = comp_addr
                            match = re.search(r"(\d+)[-－‐](\d+)(?:[-－‐](\d+))?", comp_addr)
                            if match:
                                chome = int(match.group(1))
                                banchi = match.group(2)
                                go = match.group(3)
                                num_to_kanji = {1:"一", 2:"二", 3:"三", 4:"四", 5:"五", 6:"六", 7:"七", 8:"八", 9:"九", 10:"十"}
                                if chome in num_to_kanji:
                                    kanji_chome = num_to_kanji[chome] + "丁目"
                                    if go:
                                        new_part = f"{kanji_chome}{banchi}-{go}"
                                    else:
                                        new_part = f"{kanji_chome}{banchi}"
                                    clean_comp = comp_addr.replace(match.group(0), new_part)

                            if (target_address in clean_comp) or (clean_comp in target_address):
                                matched_company_name = df_comp_master["company_name"].iloc[0]
                                matched_company_df = df_comp_master; break
                        if matched_company_name: break
                    except: continue

                st.markdown("#### 🔒 有料情報連携ステータス")
                if matched_company_name and matched_company_df is not None:
                    st.info(f"⚠️ 有料情報検知：この土地は【 {matched_company_name} 】が保有している資産であることが判明しました。")
                    st.write(f"💡 担当者発注済みの有料データがTeamsフォルダ内に存在するため、同社が国内に保有する全物件リスト（計 {len(matched_company_df)} 件）へアクセス可能です。")
                    comp_buffer = io.BytesIO()
                    with pd.ExcelWriter(comp_buffer, engine="openpyxl") as writer:
                        matched_company_df.to_excel(writer, index=False)
                    st.download_button(label=f"📥 {matched_company_name} の全物件保有リスト（{len(matched_company_df)}件）をExcelで一括取得", data=comp_buffer.getvalue(), file_name=f"L4_有料アセットリスト_{matched_company_name}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary", key=f"dl_{idx}")
                    with st.expander(f"👀 {matched_company_name} の保有資産マスタープレビュー（一部）"):
                        st.dataframe(matched_company_df.head(5))
                else:
                    st.warning("ℹ️ 有料情報なし：この住所に関する企業保有アセットの有料マスターデータは現在Teams内にありません。")
                st.markdown("---")
        else:
            st.warning(f"「{search_query}」に一致する公共データが登録されていません。別のキーワードをお試しください。")
