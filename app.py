import streamlit as st
import pandas as pd
import os

# TTMデータの読み込み（仮の値）
TTM_RATE = 144.5  # ここは実際には取得したTTMデータを適用する

# アップロードしたCSVデータの処理
def process_csv(uploaded_file):
    df = pd.read_csv(uploaded_file)
    return df

# CSVをダウンロード用に作成
def create_download_csv(df, date_col, usd_col):
    output_df = df[[date_col, usd_col]].copy()
    output_df[usd_col] = output_df[usd_col].astype(str).str.replace('$', '').astype(float)
    output_df["JPY"] = output_df[usd_col] * TTM_RATE
    return output_df

# Streamlit UI
st.title("💱 TTM ドル円確定申告アプリ")
st.markdown("\U0001F539 本アプリは、アップロードされたCSVデータから、日付と給与データのみを抽出し、TTMに基づく実際の収入金額を算出するものです。為替差損益を算出することもできます。確定申告の際の面倒なドル計算を一瞬で終わらせることができます。詳細やご不明点は、Q&Aをご確認ください。")

# 最新TTM取得エリア
st.info(f"📅 現在 {pd.Timestamp.today().strftime('%Y-%m-%d')} までのTTMが取得されています")
st.button("💾 最新のTTMを取得")

# CSVアップロードエリア
st.subheader("📂 CSVデータをアップロード")
uploaded_file = st.file_uploader("給与データのCSVをアップロード", type=["csv"])

if uploaded_file:
    df = process_csv(uploaded_file)
    date_col = st.selectbox("📅 日付の列を選択", df.columns)
    usd_col = st.selectbox("💰 給与の列を選択", df.columns)
    
    if st.button("換算開始"):
        result_df = create_download_csv(df, date_col, usd_col)
        st.success("換算結果が生成されました！")
        
        # ダウンロード用CSVのプレビュー
        st.subheader("📂 換算結果のダウンロード")
        st.write(result_df.head())
        
        # 以前のダウンロードボタンに戻す
        csv = result_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📂 CSVをダウンロード",
            data=csv,
            file_name="converted_data.csv",
            mime="text/csv"
        )

# 為替差損益の計算エリア
with st.expander("💰 為替差損益の計算"):
    st.write("CSV内の給与を円に換えた場合、その差額が経費となります。")
    rate = st.number_input("銀行の実際の換算レート (例: 144.5)", value=0.0, step=0.01)
    amount = st.number_input("換金したドル金額", value=0.0, step=0.01)
    if st.button("💡 経費を計算"):
        expense = amount * (TTM_RATE - rate)
        color = "#ffcccc" if expense < 0 else "#ccffcc"  # 赤(マイナス) / 緑(プラス)
        st.markdown(f'<div style="background-color: {color}; padding: 10px; border-radius: 5px;">為替差損益: {expense:.2f} JPY</div>', unsafe_allow_html=True)

# よくある質問（Q&A）
st.subheader("❓ よくある質問 (Q&A)")
faq_data = {
    "📌 TTMを取得している銀行はどこ？": "三菱UFJ銀行のTTMを取得しています。",
    "📌 TTMの計算式は？": "TTM = (TTS + TTB) / 2",
    "📌 CSVは保存されますか？": "アップロードされるCSVは、給与データの記載された秘匿性の高いものです。そのため、本アプリの終了と同時にすべての情報が削除されます。開発者含め、第三者によりCSVファイルが保存・閲覧されることはありません。",
    "📌 CSVが正しく出力されません": "日付と給与(ドル)を入力した列を正しく選択できていない可能性があります。今一度ご確認ください。",
    "📌 為替差損益の計算": "為替差損益の換算レートは、ご自身のpaypalなどの金融機関でご確認ください。TTMレートで計算することはほとんど不可能ですので、実際に振り替えを行った際の為替レートをご自身で入力してください。"
}
for question, answer in faq_data.items():
    with st.expander(question):
        st.write(answer)
