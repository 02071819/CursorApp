import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import jieba
from wordcloud import WordCloud
import plotly.graph_objects as go
import folium
from streamlit_folium import folium_static

# 設置網頁標題
st.title("資料視覺化分析 / Data Visualization Analysis")

# 檔案上傳和編碼選擇
uploaded_file = st.file_uploader("請上傳您的Excel或CSV檔案 / Please upload your Excel or CSV file", 
                               type=['csv', 'xlsx'])

if uploaded_file is not None:
    try:
        # 如果是 CSV 檔案，提供編碼選擇
        if uploaded_file.name.endswith('.csv'):
            encoding_option = st.selectbox(
                "選擇檔案編碼 / Select file encoding",
                options=['utf-8', 'big5', 'gb18030', 'cp950'],
                index=0
            )
            df = pd.read_csv(uploaded_file, encoding=encoding_option)
        else:
            df = pd.read_excel(uploaded_file)
        
        # 顯示原始數據
        st.header("原始數據 / Raw Data")
        st.dataframe(df)
        
        # 數據基本信息
        st.header("數據基本資訊 / Basic Information")
        col1, col2 = st.columns(2)
        with col1:
            st.write("資料維度 / Data Dimensions:", df.shape)
        with col2:
            st.write("列名稱 / Column Names:", list(df.columns))
            
        # 視覺化部分
        st.header("資料視覺化 / Data Visualization")
        
        # 獲取數值型列
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        
        # 創建導航選單
        viz_type = st.sidebar.selectbox(
            "選擇視覺化類型 / Select Visualization Type",
            ["基本統計圖表 / Basic Charts",
             "直方圖 / Histogram",
             "箱形圖 / Box Plot",
             "散點圖 / Scatter Plot",
             "相關性熱圖 / Correlation Heatmap",
             "圓餅圖 / Pie Chart",
             "折線圖 / Line Chart",
             "面積圖 / Area Chart",
             "氣泡圖 / Bubble Chart",
             "雷達圖 / Radar Chart",
             "文字雲 / Word Cloud",
             "地圖 / Map"]
        )

        if viz_type == "基本統計圖表 / Basic Charts":
            st.subheader("數值型欄位的基本統計資訊 / Basic Statistics for Numeric Columns")
            st.write(df.describe())

        elif viz_type == "直方圖 / Histogram":
            st.subheader("直方圖 / Histogram")
            hist_column = st.selectbox(
                "選擇要顯示直方圖的列 / Select column for histogram",
                numeric_columns
            )
            fig_hist = px.histogram(df, x=hist_column)
            st.plotly_chart(fig_hist)

        elif viz_type == "箱形圖 / Box Plot":
            st.subheader("箱形圖 / Box Plot")
            box_column = st.selectbox(
                "選擇要顯示箱形圖的列 / Select column for box plot",
                numeric_columns
            )
            fig_box = px.box(df, y=box_column)
            st.plotly_chart(fig_box)

        elif viz_type == "散點圖 / Scatter Plot":
            st.subheader("散點圖 / Scatter Plot")
            if len(numeric_columns) >= 2:
                col1, col2 = st.columns(2)
                with col1:
                    x_column = st.selectbox("選擇X軸 / Select X axis", numeric_columns)
                with col2:
                    y_column = st.selectbox("選擇Y軸 / Select Y axis", numeric_columns)
                fig_scatter = px.scatter(df, x=x_column, y=y_column)
                st.plotly_chart(fig_scatter)
            else:
                st.warning("需要至少兩個數值型欄位來繪製散點圖 / Need at least two numeric columns for scatter plot")

        elif viz_type == "相關性熱圖 / Correlation Heatmap":
            st.subheader("相關性熱圖 / Correlation Heatmap")
            if len(numeric_columns) > 0:
                corr = df[numeric_columns].corr()
                fig_corr = px.imshow(corr, 
                                   labels=dict(color="相關係數 / Correlation"),
                                   color_continuous_scale="RdBu")
                st.plotly_chart(fig_corr)
            else:
                st.warning("需要數值型欄位來計算相關性 / Need numeric columns to calculate correlation")

        elif viz_type == "圓餅圖 / Pie Chart":
            st.subheader("圓餅圖 / Pie Chart")
            pie_column = st.selectbox(
                "選擇要顯示圓餅圖的列 / Select column for pie chart",
                df.columns
            )
            value_counts = df[pie_column].value_counts()
            fig_pie = px.pie(values=value_counts.values, names=value_counts.index)
            st.plotly_chart(fig_pie)

        elif viz_type == "折線圖 / Line Chart":
            st.subheader("折線圖 / Line Chart")
            if len(numeric_columns) > 0:
                col1, col2 = st.columns(2)
                with col1:
                    x_line = st.selectbox("選擇X軸 (折線圖) / Select X axis (Line)", df.columns)
                with col2:
                    y_line = st.selectbox("選擇Y軸 (折線圖) / Select Y axis (Line)", numeric_columns)
                
                try:
                    # 確保數據按X軸排序
                    df_sorted = df.sort_values(by=x_line)
                    
                    # 創建折線圖
                    fig_line = px.line(
                        df_sorted,
                        x=x_line,
                        y=y_line,
                        title=f"{y_line} vs {x_line}",
                        markers=True  # 顯示數據點
                    )
                    
                    # 更新布局
                    fig_line.update_layout(
                        xaxis_title=x_line,
                        yaxis_title=y_line,
                        showlegend=True
                    )
                    
                    st.plotly_chart(fig_line)
                    
                except Exception as e:
                    st.error(f"生成折線圖時發生錯誤: {str(e)}")
            else:
                st.warning("需要數值型欄位來繪製折線圖 / Need numeric columns for line chart")

        elif viz_type == "面積圖 / Area Chart":
            st.subheader("面積圖 / Area Chart")
            if len(numeric_columns) > 0:
                col1, col2 = st.columns(2)
                with col1:
                    x_area = st.selectbox("選擇X軸 (面積圖) / Select X axis (Area)", df.columns)
                with col2:
                    y_area = st.selectbox("選擇Y軸 (面積圖) / Select Y axis (Area)", numeric_columns)
                
                try:
                    # 確保數據按X軸排序
                    df_sorted = df.sort_values(by=x_area)
                    
                    # 創建面積圖
                    fig_area = px.area(
                        df_sorted,
                        x=x_area,
                        y=y_area,
                        title=f"{y_area} vs {x_area}"
                    )
                    
                    # 更新布局
                    fig_area.update_layout(
                        xaxis_title=x_area,
                        yaxis_title=y_area,
                        showlegend=True
                    )
                    
                    st.plotly_chart(fig_area)
                    
                except Exception as e:
                    st.error(f"生成面積圖時發生錯誤: {str(e)}")
            else:
                st.warning("需要數值型欄位來繪製面積圖 / Need numeric columns for area chart")

        elif viz_type == "氣泡圖 / Bubble Chart":
            st.subheader("氣泡圖 / Bubble Chart")
            if len(numeric_columns) >= 3:
                col1, col2, col3 = st.columns(3)
                with col1:
                    x_bubble = st.selectbox("選擇X軸 (氣泡圖) / Select X axis (Bubble)", numeric_columns)
                with col2:
                    y_bubble = st.selectbox("選擇Y軸 (氣泡圖) / Select Y axis (Bubble)", numeric_columns)
                with col3:
                    size_bubble = st.selectbox("選擇氣泡大小 / Select bubble size", numeric_columns)
                
                try:
                    # 處理氣泡大小數據：轉換為正值並標準化
                    size_values = df[size_bubble].values
                    size_values = np.abs(size_values)  # 轉換為絕對值
                    
                    # 標準化到合理的範圍（例如：10-50）
                    size_min, size_max = 10, 50
                    if size_values.max() != size_values.min():
                        size_normalized = size_min + (size_values - size_values.min()) * (size_max - size_min) / (size_values.max() - size_values.min())
                    else:
                        size_normalized = np.full_like(size_values, (size_min + size_max) / 2)
                    
                    # 創建包含處理後大小的數據框
                    plot_df = df.copy()
                    plot_df['bubble_size'] = size_normalized
                    
                    # 可選的顏色映射列
                    color_column = st.selectbox(
                        "選擇顏色映射列（可選）/ Select color column (optional)",
                        ["無 / None"] + list(df.columns),
                        index=0
                    )
                    
                    if color_column == "無 / None":
                        fig_bubble = px.scatter(
                            plot_df,
                            x=x_bubble,
                            y=y_bubble,
                            size='bubble_size',
                            title="氣泡圖 / Bubble Chart",
                            labels={
                                x_bubble: x_bubble,
                                y_bubble: y_bubble,
                                'bubble_size': size_bubble
                            }
                        )
                    else:
                        fig_bubble = px.scatter(
                            plot_df,
                            x=x_bubble,
                            y=y_bubble,
                            size='bubble_size',
                            color=color_column,
                            title="氣泡圖 / Bubble Chart",
                            labels={
                                x_bubble: x_bubble,
                                y_bubble: y_bubble,
                                'bubble_size': size_bubble,
                                color_column: color_column
                            }
                        )
                    
                    # 更新氣泡圖的布局
                    fig_bubble.update_layout(
                        showlegend=True,
                        xaxis_title=x_bubble,
                        yaxis_title=y_bubble
                    )
                    
                    st.plotly_chart(fig_bubble)
                    
                    # 顯示數據範圍信息
                    st.info(f"""
                    數據範圍信息 / Data Range Information:
                    - X軸範圍 / X-axis range: [{df[x_bubble].min():.2f}, {df[x_bubble].max():.2f}]
                    - Y軸範圍 / Y-axis range: [{df[y_bubble].min():.2f}, {df[y_bubble].max():.2f}]
                    - 原始大小範圍 / Original size range: [{df[size_bubble].min():.2f}, {df[size_bubble].max():.2f}]
                    """)
                    
                except Exception as e:
                    st.error(f"生成氣泡圖時發生錯誤 / Error generating bubble chart: {str(e)}")
            else:
                st.warning("需要至少三個數值型欄位來繪製氣泡圖 / Need at least three numeric columns for bubble chart")

        elif viz_type == "雷達圖 / Radar Chart":
            st.subheader("雷達圖 / Radar Chart")
            if len(numeric_columns) > 0:
                # 選擇要顯示的數值列（最多6個）
                selected_columns = st.multiselect(
                    "選擇要顯示的數值列 (最多6個) / Select numeric columns (max 6)",
                    numeric_columns,
                    default=list(numeric_columns)[:6] if len(numeric_columns) > 0 else []
                )
                
                if len(selected_columns) > 0:
                    if len(selected_columns) > 6:
                        st.warning("請最多選擇6個欄位 / Please select maximum 6 columns")
                        selected_columns = selected_columns[:6]
                    
                    # 準備雷達圖數據
                    df_radar = df[selected_columns].copy()
                    
                    # 標準化數據到0-1之間
                    for col in selected_columns:
                        df_radar[col] = (df_radar[col] - df_radar[col].min()) / (df_radar[col].max() - df_radar[col].min())
                    
                    # 計算平均值
                    radar_data = df_radar.mean()
                    
                    # 準備雷達圖數據格式
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatterpolar(
                        r=radar_data.values,
                        theta=radar_data.index,
                        fill='toself',
                        name='平均值 / Average'
                    ))
                    
                    fig.update_layout(
                        polar=dict(
                            radialaxis=dict(
                                visible=True,
                                range=[0, 1]
                            )),
                        showlegend=True,
                        title="雷達圖 / Radar Chart"
                    )
                    
                    st.plotly_chart(fig)
                    
                    # 顯示原始數據
                    st.subheader("數據統計 / Data Statistics")
                    st.write(df[selected_columns].describe())
                else:
                    st.warning("請選擇至少一個數值欄位 / Please select at least one numeric column")
            else:
                st.warning("需要數值型欄位來繪製雷達圖 / Need numeric columns for radar chart")

        elif viz_type == "文字雲 / Word Cloud":
            st.subheader("文字雲 / Word Cloud")
            text_columns = df.select_dtypes(include=['object']).columns
            if len(text_columns) > 0:
                text_column = st.selectbox(
                    "選擇文字列 / Select text column",
                    text_columns
                )
                try:
                    # 移除空值並轉換為字串
                    text = ' '.join(df[text_column].dropna().astype(str))
                    
                    # 使用結巴分詞處理中文
                    words = jieba.cut(text)
                    text_processed = ' '.join(words)
                    
                    # 設定中文字體路徑
                    font_paths = [
                        'C:/Windows/Fonts/mingliu.ttc',     # Windows 細明體
                        'C:/Windows/Fonts/msjh.ttc',        # Windows 微軟正黑體
                        'C:/Windows/Fonts/simsun.ttc',      # Windows 新宋體
                        'C:/Windows/Fonts/msyh.ttc',        # Windows 微軟雅黑
                        '/System/Library/Fonts/PingFang.ttc',  # macOS
                        '/System/Library/Fonts/STHeiti Light.ttc',  # macOS
                        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'  # Linux
                    ]
                    
                    # 尋找可用的字體
                    font_path = None
                    for path in font_paths:
                        if os.path.exists(path):
                            font_path = path
                            break
                    
                    if font_path is None:
                        st.warning("未找到合適的中文字體，將使用預設字體 / No suitable Chinese font found, using default font")
                    
                    # 創建文字雲
                    wordcloud = WordCloud(
                        width=800,
                        height=400,
                        background_color='white',
                        max_words=200,
                        font_path=font_path,
                        collocations=False,  # 避免重複詞組
                        min_font_size=10,
                        max_font_size=150,
                        random_state=42
                    ).generate(text_processed)
                    
                    # 顯示文字雲
                    plt.figure(figsize=(10, 5))
                    plt.imshow(wordcloud, interpolation='bilinear')
                    plt.axis('off')
                    st.pyplot(plt)
                    
                except Exception as e:
                    st.error(f"生成文字雲時發生錯誤: {str(e)}")
            else:
                st.info("沒有找到文字類型的列 / No text columns found")

        elif viz_type == "地圖 / Map":
            st.subheader("地圖視覺化 / Map Visualization")
            # 檢查是否有經緯度數據
            lat_cols = [col for col in df.columns if 'lat' in col.lower()]
            lon_cols = [col for col in df.columns if 'lon' in col.lower() or 'lng' in col.lower()]
            
            if lat_cols and lon_cols:
                lat_col = st.selectbox("選擇緯度列 / Select latitude column", lat_cols)
                lon_col = st.selectbox("選擇經度列 / Select longitude column", lon_cols)
                
                try:
                    # 確保經緯度為數值型別
                    df[lat_col] = pd.to_numeric(df[lat_col], errors='coerce')
                    df[lon_col] = pd.to_numeric(df[lon_col], errors='coerce')
                    
                    # 過濾有效的座標
                    valid_coords = df.dropna(subset=[lat_col, lon_col])
                    valid_coords = valid_coords[
                        (valid_coords[lat_col] >= -90) & 
                        (valid_coords[lat_col] <= 90) & 
                        (valid_coords[lon_col] >= -180) & 
                        (valid_coords[lon_col] <= 180)
                    ]
                    
                    if not valid_coords.empty:
                        # 創建地圖
                        m = folium.Map(
                            location=[20, 0],
                            zoom_start=2,
                            tiles='OpenStreetMap',
                            attr='© OpenStreetMap contributors'
                        )
                        
                        # 創建標記群組
                        marker_cluster = folium.plugins.MarkerCluster(name="Markers").add_to(m)
                        
                        for idx, row in valid_coords.iterrows():
                            popup_content = f"<b>Index:</b> {idx}<br>"
                            other_cols = [col for col in valid_coords.columns if col not in [lat_col, lon_col]][:5]
                            for col in other_cols:
                                popup_content += f"<b>{col}:</b> {row[col]}<br>"
                            
                            folium.Marker(
                                location=[row[lat_col], row[lon_col]],
                                popup=folium.Popup(popup_content, max_width=300),
                                tooltip=f"Point {idx}"
                            ).add_to(marker_cluster)
                        
                        folium.LayerControl().add_to(m)
                        
                        # 顯示地圖
                        st_data = folium_static(m, width=1000, height=600)
                        
                    else:
                        st.warning("沒有找到有效的經緯度數據 / No valid coordinate data found")
                        
                except Exception as e:
                    st.error(f"生成地圖時發生錯誤 / Error generating map: {str(e)}")
            else:
                st.info("未檢測到經緯度數據列 / No latitude/longitude columns detected")

    except Exception as e:
        st.error(f"發生錯誤 / An error occurred: {str(e)}")
else:
    st.info("請上傳檔案以開始分析 / Please upload a file to start analysis") 