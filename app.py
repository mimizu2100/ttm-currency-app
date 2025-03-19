import streamlit as st
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# 📁 保存するTTMデータファイル
TTM_FILE = "ttm_data.xlsx"
BASE_URL = "https://www.murc-kawasesouba.jp/fx/past/index.php?id="

# 📌 2024年12月31日のデフォルトデータ（バックアップ）
DEFAULT_TTS = 159.18
DEFAULT_TTB = 157.18
DEFAULT_TTM = (DEFAULT_TTS + DEFAULT_TTB) / 2

# 📌 TTMデータをロードする関数
def load_ttm_data():
    if os.path.exists(TTM_FILE):
        return pd.read_excel(TTM_FILE, engine="openpyxl")
    return pd.DataFrame(columns=["Date", "TTS", "TTB", "TTM"])

# 📌 指定日付のTTS・TTBを取得
def fetch_tts_ttb(date_str):
    url = BASE_URL + date_str
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        return None, None  # エラー時はNoneを返す
    
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table")
    if not table:
        return None, None
    
    rows = table.find_all("tr")
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 5 and "US Dollar" in cols[0].text:
            try:
                tts = float(cols[3].text.strip())
                ttb = float(cols[4].text.strip())
                return tts, ttb
            except ValueError:
                return None, None
    
    return None, None

# 📌 TTMデータを更新
def update_ttm_data():
    df = load_ttm_data()
    last_date = df["Date"].max() if not df.empty else "2024-12-31"
    start_date = datetime.strptime(last_date, "%Y-%m-%d") + timedelta(days=1)
    today = datetime.today().strftime("%Y-%m-%d")
    new_data = []

    while start_date.strftime("%Y-%m-%d") < today:  # 当日のデータは取得しない
        date_str = start_date.strftime("%y%m%d")
        tts, ttb = fetch_tts_ttb(date_str)
        
        if tts is not None and ttb is not None:
            ttm = round((tts + ttb) / 2, 3)
            new_data.append([start_date.strftime("%Y-%m-%d"), tts, ttb, ttm])
        
        start_date += timedelta(days=1)
    
    if new_data:
        new_df = pd.DataFrame(new_data, columns=["Date", "TTS", "TTB", "TTM"])
        df = pd.concat([df, new_df], ignore_index=True)
        df.to_excel(TTM_FILE, index=False)

    return df


# 🌟 Streamlit UI 🌟
st.title("💱 TTM ドル円確定申告アプリ")
st.markdown("🔹 本アプリは、過去のTTMデータを取得・保存し、給与データの換算を行うものです。")

# 📌 TTMデータ取得ボタン
df_ttm = load_ttm_data()
latest_date = df_ttm["Date"].max() if not df_ttm.empty else "データなし"
st.info(f"📅 現在 {latest_date} までのTTMが取得されています")

if st.button("💾 最新のTTMを保存"):
    df_ttm = update_ttm_data()
    st.success("最新のTTMデータを取得しました！")

# 📌 取得済みのTTMデータ表示
ttm_display = df_ttm.tail(10)  # 直近10件を表示
st.subheader("📊 取得済みのTTMデータ")
st.dataframe(ttm_display)

# 📌 CSV処理関数
def process_csv(uploaded_file):
    df = pd.read_csv(uploaded_file)
    return df

# 📌 CSVデータを変換・整形
def create_download_csv(df, date_col, usd_col, ttm_data):
    # 給与データを数値化
    df[usd_col] = df[usd_col].replace('[\$,]', '', regex=True)  # '$' 記号を除去
    df[usd_col] = pd.to_numeric(df[usd_col], errors='coerce')  # 数値変換

    # 日付ごとに給与を合算
    grouped_df = df.groupby(date_col, as_index=False)[usd_col].sum()

    # TTMデータをマージ
    ttm_df = pd.DataFrame(ttm_data, columns=["Date", "TTS", "TTB", "TTM"])
    ttm_df["Date"] = pd.to_datetime(ttm_df["Date"]).dt.strftime('%Y-%m-%d')
    grouped_df[date_col] = pd.to_datetime(grouped_df[date_col]).dt.strftime('%Y-%m-%d')
    merged_df = pd.merge(grouped_df, ttm_df[["Date", "TTM"]], left_on=date_col, right_on="Date", how="left")
    merged_df.drop(columns=["Date"], inplace=True)

    # 日本円換算額を計算
    merged_df["JPY Amount"] = merged_df[usd_col] * merged_df["TTM"]

    # 日付順に並び替え
    merged_df[date_col] = pd.to_datetime(merged_df[date_col])  # 日付型に変換
    merged_df = merged_df.sort_values(by=[date_col]).reset_index(drop=True)  # 並び替え

    return merged_df


# 📂 CSVアップロードエリア
st.subheader("📂 CSVデータをアップロード")
uploaded_file = st.file_uploader("給与データのCSVをアップロード", type=["csv"])

# 📂 換算結果のダウンロードセクション
st.subheader("📂 換算結果のダウンロード")
if uploaded_file:
    df = process_csv(uploaded_file)
    date_col = st.selectbox("📅 日付の列を選択", df.columns)
    usd_col = st.selectbox("💰 給与の列を選択", df.columns)
    
    result_df = create_download_csv(df, date_col, usd_col, df_ttm)
    
    if result_df is not None:
        st.success("換算結果が生成されました！")
        st.write(result_df)
        
        csv = result_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📂 CSVをダウンロード",
            data=csv,
            file_name="converted_data.csv",
            mime="text/csv"
        )
    else:
        st.warning("⚠️ 換算結果がありません。")
else:
    st.warning("⚠️ CSVをアップロードしてください。")

# 📌 為替差損益の計算エリア
with st.expander("💰 為替差損益の計算"):
    rate = st.number_input("銀行の換算レート (例: 144.5)", value=0.0, step=0.01)
    amount = st.number_input("換金したドル金額", value=0.0, step=0.01)
    if st.button("💡 経費を計算"):
        latest_ttm = df_ttm.iloc[-1]["TTM"] if not df_ttm.empty else 144.5
        expense = amount * (latest_ttm - rate)
        color = "#ffcccc" if expense < 0 else "#ccffcc"
        st.markdown(f'<div style="background-color: {color}; padding: 10px; border-radius: 5px;">為替差損益: {expense:.2f} JPY</div>', unsafe_allow_html=True)

# ❓ Q&Aセクション
st.subheader("❓ よくある質問 (Q&A)")

faq_data = {
    "📌 このアプリはなに？": 
        "本アプリは、確定申告を一瞬で終わらせたいという目的のためだけに作られた、ドル円換算アプリです。"
        "日付と給与のデータ記載されたCSVをアップロードすることで、データを日付ごとにまとめ、"
        "給与を合算、給与とTTMを乗算した日本円換算額をCSV形式で出力します。"
        "三菱UFJ銀行のデータのみを用いているため、一貫性のあるデータを用いた確定申告用の資料としてお使いいただけます。",
    
    "📌 どうやって使うの？":
        "まず、前日のTTMが取得されているか確認してください。当日のTTMは翌日以降反映可能になります。"
        "TTMがしばらく取得されていない場合は、「TTMを取得する」ボタンを押してください。"
        "次に、日付と給与をまとめたCSVファイルをアップロードしてください。"
        "その後、選択フォームで日付の列と給与の列を選択すると、CSVが生成され、ダウンロード可能になります。",
    
    "📌 CSVは保存されますか？個人情報だから見られたくないんだけど...":
        "アップロードしていただいたCSVと、ダウンロード可能なCSVは、セッションをクリアするとすべて削除されます（リロード・ページを閉じるなど）。"
        "そのため、作成者を含めた第三者が閲覧することはできません。"
        "個人情報保護を最優先にした結果、ダウンロードしたCSVを保存しないうちにセッションをクリアすると、"
        "再度アップロードからやり直しになるのでご注意ください。",
    
    "📌 TTMを取得している銀行はどこ？": 
        "三菱UFJ銀行のTTMを取得しています。",
    
    "📌 TTMの計算式は？":
        "TTM = (TTS + TTB) / 2",
    
    "📌 今日のTTMが表示されてないんだけど":
        "TTMは、翌日以降反映できるようになります。"
        "これは、三菱UFJ銀行の情報アップデートの時間が不定期であるため、"
        "取得する時間によっては情報が更新されていない場合があります。"
        "翌日以降、「最新のTTMを取得」ボタンを押すと、追記・反映されます。"
        "お急ぎの場合は、以下から直接情報をご確認ください。"
        "（XXXXには、250101のように、年度/月/日が入ります）"
        "https://www.murc-kawasesouba.jp/fx/past/index.php?id=XXXXXXX",
    
    "📌 為替差損益の計算って？":
        "給与が発生した日のTTMと、ドルから円に換えたときの実際の為替レートとの間に差がある場合、"
        "その差額は経費あるいは為替差利益となります。"
        "2025年に得た給与を円に換えた場合にのみ使用してください。"
        "また、すべての日を正確に判別することは不可能なため、実際には、ドルから円に換えたときの実行レートをご記載ください。"
        "(例: Paypalで振り替えたときのレートが145円だった場合は、145と記入してください。)",
    
    "📌 おことわり":
        "本アプリで算出したデータについて指摘を受けることがあった場合、"
        "管轄の税務署やお近くの税理士の指示を優先してください。",
}

# Q&AをStreamlitのUIに表示
for question, answer in faq_data.items():
    with st.expander(question):
        st.write(answer)

import streamlit as st

# AdSenseコードを埋め込む
adsense_code = """
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2958467413596879"
     crossorigin="anonymous"></script>
"""
# Streamlit に広告スクリプトを挿入
st.markdown(adsense_code, unsafe_allow_html=True)

# Q&Aの下にもう一度広告を入れる
st.markdown(adsense_code, unsafe_allow_html=True)

