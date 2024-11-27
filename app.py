import streamlit as st

# 設置網頁標題
st.set_page_config(
    page_title="數據分析與爬蟲系統",
    page_icon="📊",
    layout="wide"
)

# 標題
st.title("數據分析與爬蟲系統 / Data Analysis and Crawler System")

# 添加說明文字
st.markdown(
    """
    ### 歡迎使用數據分析與爬蟲系統！
    
    本系統提供兩大主要功能：
    
    1. **資料視覺化分析**
    - 支援 Excel 和 CSV 檔案上傳
    - 提供多種視覺化圖表
    - 支援中英文雙語介面
    
    2. **PTT 爬蟲與分析**
    - PTT 文章爬取
    - 關鍵字過濾
    - 情緒分析
    - 文字雲生成
    
    請從左側選單選擇您要使用的功能。
    """
) 