import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime
import jieba
import jieba.analyse
from snownlp import SnowNLP
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm
import re
import os
import plotly.express as px
import random

class PTTCrawler:
    def __init__(self):
        self.base_url = 'https://www.ptt.cc'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache'
        }
        # 使用 jieba 的預設詞典並添加自定義詞彙
        jieba.initialize()
        
        # 添加 PTT 相關常用詞彙
        custom_words = [
            'PTT', '八卦', '爆卦', '新聞', '討論', '問卦',
            '公告', '版規', '置底', '板主', '鄉民',
            '推文', '噓文', '箭頭', '發文', '回文',
            '轉錄', '分享', '新聞', '圖片', '影片',
            '標題', '內文', '連結', '網址', '原文'
        ]
        for word in custom_words:
            jieba.add_word(word)
        
        # 添加更多自定義詞彙
        custom_words.extend([
            '推', '噓', '→',  # PTT 特殊符號
            'Re:', 'Fw:', '[爆]', '[神]', '[帥]', '[馬]',  # 常見標題前綴
            '發信站', '看板', '作者', '標題', '時間',  # 文章欄位
            '※', '◆', '█', '▌', '▲', '▼',  # 特殊符號
        ])
        
        # 添加正負面情緒詞典
        self.positive_words = set([
            '推', '讚', '好', '棒', '優', '佳', '讚賞', '支持', '喜歡', '贊同',
            '精彩', '完美', '傑出', '優秀', '卓越', '出色', '厲害', '了不起',
            '感謝', '謝謝', '感恩', '開心', '快樂', '高興', '爽', '讚嘆',
            '期待', '希望', '加油', '鼓勵', '正面', '積極', '溫暖', '熱心',
            '成功', '進步', '成長', '突破', '創新', '優質', '可靠', '穩定',
            '專業', '效率', '便利', '實用', '划算', '超值', '物超所值'
        ])
        
        self.negative_words = set([
            '噓', '爛', '差', '糟', '壞', '廢', '反對', '討厭', '痛恨', '厭惡',
            '失望', '糟糕', '可怕', '恐怖', '慘', '悲慘', '難過', '傷心',
            '生氣', '憤怒', '不滿', '抱怨', '批評', '指責', '謾罵', '攻擊',
            '問題', '缺點', '缺陷', '瑕疵', '故障', '錯誤', '失誤', '失敗',
            '浪費', '虛假', '欺騙', '詐騙', '騙子', '垃圾', '廢物', '無用',
            '貴', '坑', '', '雞肋', '無聊', '無趣', '乏味', '枯燥'
        ])

    def get_board_url(self, board_name):
        """獲取看板 URL"""
        return f'{self.base_url}/bbs/{board_name}/index.html'
    
    def get_page_content(self, url):
        """獲取頁面內容"""
        try:
            # 創建新的 session
            session = requests.Session()
            
            # 首先嘗試訪問年齡驗證頁面
            verify_url = 'https://www.ptt.cc/ask/over18'
            verify_response = session.post(
                verify_url,
                headers=self.headers,
                data={'from': url, 'yes': 'yes'},
                timeout=10
            )
            
            # 然後直接訪問目標頁面
            response = session.get(
                url,
                headers=self.headers,
                timeout=10,
                allow_redirects=False  # 禁止自動重定向
            )
            
            # 如果是重定向，直接訪問新的 URL
            if response.status_code in [301, 302]:
                redirect_url = response.headers.get('location')
                if redirect_url:
                    if not redirect_url.startswith('http'):
                        redirect_url = 'https://www.ptt.cc' + redirect_url
                    response = session.get(
                        redirect_url,
                        headers=self.headers,
                        timeout=10,
                        allow_redirects=False
                    )
            
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
            
        except requests.exceptions.RequestException as e:
            st.error(f"獲取頁面時發生錯誤：{str(e)}")
            time.sleep(5)  # 出錯時等待 5 秒
            return None
        except Exception as e:
            st.error(f"處理頁面時發生錯誤：{str(e)}")
            time.sleep(5)  # 出錯時等待 5 秒
            return None

    def parse_article_meta(self, item):
        """解析文章元數據"""
        meta = {}
        try:
            # 獲取文章連結和標題
            title_element = item.find('div', class_='title')
            if title_element and title_element.a:
                meta['title'] = title_element.a.text.strip()
                meta['link'] = self.base_url + title_element.a['href']
            else:
                return None

            # 獲取作者和日期
            meta_elements = item.find_all('div', class_='meta')
            if meta_elements:
                author = meta_elements[0].find('div', class_='author')
                date = meta_elements[0].find('div', class_='date')
                meta['author'] = author.text.strip() if author else 'unknown'
                meta['date'] = date.text.strip() if date else 'unknown'

            # 獲取推文數
            nrec = item.find('div', class_='nrec')
            meta['push'] = nrec.text.strip() if nrec else '0'

            # 添加更多元數據
            meta['category'] = ''  # 文章分類
            if '[' in meta['title'] and ']' in meta['title']:
                meta['category'] = meta['title'].split('[')[1].split(']')[0]
                
            # 處理推文數格式
            if meta['push'].isdigit():
                meta['push_count'] = int(meta['push'])
            elif meta['push'] == '爆':
                meta['push_count'] = 100
            elif meta['push'] == 'X':
                meta['push_count'] = -100
            else:
                meta['push_count'] = 0
                
            return meta
        except Exception as e:
            st.error(f"解析文章元數據時發生錯誤：{str(e)}")
            return None

    def get_article_content(self, url):
        """獲取文章內容"""
        try:
            soup = self.get_page_content(url)
            if not soup:
                return None

            main_content = soup.find('div', id='main-content')
            if not main_content:
                return None

            # 移除不需要的元素
            for meta in main_content.find_all('div', class_='article-metaline'):
                meta.extract()
            for meta in main_content.find_all('div', class_='article-metaline-right'):
                meta.extract()

            # 獲取推文資訊
            pushes = []
            for push in main_content.find_all('div', class_='push'):
                push_data = {
                    'type': push.find('span', class_='push-tag').text.strip(),
                    'user': push.find('span', class_='push-userid').text.strip(),
                    'content': push.find('span', class_='push-content').text.strip(),
                    'time': push.find('span', class_='push-ipdatetime').text.strip()
                }
                pushes.append(push_data)
                push.extract()  # 移除推文

            # 返回主文內容和推文
            return {
                'main_content': main_content.text.strip(),
                'pushes': pushes
            }

        except Exception as e:
            st.error(f"獲取文章內容時發生錯誤：{str(e)}")
            return None

    def crawl_ptt(self, board_name, keywords, max_articles=5000):
        """爬取 PTT 文章"""
        articles = []
        url = self.get_board_url(board_name)
        page_count = 0
        
        with st.spinner('正在爬取文章...'):
            progress_bar = st.progress(0)
            
            while len(articles) < max_articles:
                # 添加隨機延遲
                time.sleep(random.uniform(1, 3))  # 隨機等待1-3秒
                
                soup = self.get_page_content(url)
                if not soup:
                    st.warning(f"無法獲取頁面，嘗試繼續下一頁")
                    continue
                
                # 獲取文章列表
                for item in soup.find_all('div', class_='r-ent'):
                    meta = self.parse_article_meta(item)
                    if not meta:
                        continue

                    # 檢查關鍵字
                    if keywords and not any(k.lower() in meta['title'].lower() for k in keywords):
                        continue

                    # 獲取文章內容
                    content_data = self.get_article_content(meta['link'])
                    if content_data:
                        meta['content'] = content_data['main_content']  # 只存儲主文內容
                        meta['pushes'] = content_data['pushes']  # 存儲推文
                        articles.append(meta)

                    # 更新進度條
                    progress = min(len(articles) / max_articles, 1.0)
                    progress_bar.progress(progress)

                    if len(articles) >= max_articles:
                        break

                # 獲取上一頁連結
                prev_link = soup.find('a', string='‹ 上頁')
                if not prev_link:
                    break
                url = self.base_url + prev_link['href']
                page_count += 1
                
                # 避免請求過於頻繁
                time.sleep(0.5)

        # 將文列表轉換為字串
        for article in articles:
            if 'pushes' in article:
                push_texts = [f"{p['type']} {p['user']}: {p['content']} {p['time']}" for p in article['pushes']]
                article['push_content'] = '\n'.join(push_texts)
                del article['pushes']  # 刪除原始推文列表

        return pd.DataFrame(articles)

    def analyze_sentiment(self, text):
        """情緒分析"""
        try:
            s = SnowNLP(text)
            return s.sentiments
        except:
            return 0.5

    def extract_keywords(self, text, topK=20):
        """關鍵字提取"""
        try:
            # 使用 jieba 的 TF-IDF 提取關鍵字
            keywords = jieba.analyse.extract_tags(text, topK=topK)
            return keywords
        except Exception as e:
            st.error(f"提取關鍵字時發生錯誤：{str(e)}")
            return []

    def generate_wordcloud(self, text):
        """生成文字雲"""
        try:
            # 使用正則表達式過濾英文和數字
            text = re.sub(r'[a-zA-Z0-9]+', '', text)
            
            # 定義要過濾的停用詞
            stop_words = {
                '標題', '編輯', '原文', '發信站', '看板', '作者', '時間', 
                '批踢踢', '實業坊', '看板', '文章', '連結', '網址',
                '推文', '回覆', '發表', '內容', '討論', '發文', '轉錄',
                '站內', '站外', '引用', '來自', '文章', '發信', '站內',
                '看板', '批踢踢', '實業坊', '分享', '已有', '這是', '那個',
                '這個', '就是', '可以', '還是', '還有', '一個', '沒有',
                '什麼', '如果', '因為', '所以', '但是', '只是', '真的',
                '現在', '知道', '覺得', '認為', '希望', '應該'
            }
            
            # 使用 jieba 進行分詞
            words = jieba.cut(text)
            
            # 只保留中文詞組，並過濾停用詞
            word_freq = {}
            for word in words:
                word = word.strip()
                # 檢查是否為純中文且長度大於1，且不在停用詞中
                if (len(word) > 1 and 
                    re.match(r'^[\u4e00-\u9fff]+$', word) and 
                    word not in stop_words):
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # 設定字體路徑
            font_paths = [
                'C:/Windows/Fonts/msjh.ttc',        # Windows 微軟���黑體
                'C:/Windows/Fonts/mingliu.ttc',     # Windows 細明體
                'C:/Windows/Fonts/simsun.ttc',      # Windows 新宋體
                '/System/Library/Fonts/PingFang.ttc'  # macOS
            ]
            
            font_path = next((path for path in font_paths if os.path.exists(path)), None)
            
            if not word_freq:
                st.warning("沒有找到足夠的中文詞組來生成文字雲")
                return None
            
            # 生成文字雲
            wordcloud = WordCloud(
                width=800,
                height=400,
                background_color='white',
                max_words=100,
                font_path=font_path,
                collocations=False,  # 避免重複詞組
                min_font_size=10,
                max_font_size=150,
                random_state=42
            ).generate_from_frequencies(word_freq)  # 使用詞頻生成文字雲
            
            # 顯示文字雲
            plt.figure(figsize=(10, 5))
            plt.imshow(wordcloud, interpolation='bilinear')
            plt.axis('off')
            return plt
        except Exception as e:
            st.error(f"生成文字雲時發生錯誤：{str(e)}")
            return None

    def analyze_content(self, df):
        """綜合分析"""
        analysis = {
            'total_articles': len(df),
            'authors': df['author'].nunique(),
            'avg_push': df['push_count'].mean(),
            'categories': df['category'].value_counts().to_dict(),
            'time_distribution': df['date'].value_counts().to_dict(),
        }
        return analysis

    def analyze_sentiment_keywords(self, text, topK=20):
        """改進的情緒關鍵詞分析"""
        try:
            words = list(jieba.cut(text))
            word_sentiments = []
            
            # 計算詞頻
            word_freq = {}
            for word in words:
                if len(word.strip()) > 1:
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # 評估每個詞的情緒傾向
            for word, freq in word_freq.items():
                # 基礎情緒分數
                try:
                    base_sentiment = SnowNLP(word).sentiments
                except:
                    base_sentiment = 0.5
                
                # 根據詞典調整情緒分數
                if word in self.positive_words:
                    base_sentiment = max(base_sentiment, 0.8)
                elif word in self.negative_words:
                    base_sentiment = min(base_sentiment, 0.2)
                
                # 考慮詞頻權重
                word_sentiments.append((word, base_sentiment, freq))
            
            # 分離並排序正負面詞彙
            positive_words = [(w, s, f) for w, s, f in word_sentiments if s > 0.6]
            negative_words = [(w, s, f) for w, s, f in word_sentiments if s < 0.4]
            
            # 按照頻率排序
            positive_words.sort(key=lambda x: x[2], reverse=True)  # 由高到低
            negative_words.sort(key=lambda x: x[2], reverse=True)  # 由高到低
            
            # 取前 topK 個
            positive_words = positive_words[:topK]
            negative_words = negative_words[:topK]
            
            return {
                'positive': [(w, s) for w, s, f in positive_words],
                'negative': [(w, s) for w, s, f in negative_words],
                'positive_with_freq': positive_words,
                'negative_with_freq': negative_words
            }
        except Exception as e:
            st.error(f"分析情緒關鍵詞時發生錯誤：{str(e)}")
            return {'positive': [], 'negative': [], 'positive_with_freq': [], 'negative_with_freq': []}

    def generate_sentiment_wordcloud(self, text, sentiment_type='all'):
        """生成情緒文字雲"""
        try:
            # 使用正則表達式過濾英文和數字
            text = re.sub(r'[a-zA-Z0-9]+', '', text)
            
            # 定義要過濾的停用詞（與上面相同）
            stop_words = {
                '標題', '編輯', '原文', '發信站', '看板', '作者', '時間', 
                '批踢踢', '實業坊', '看板', '文章', '連結', '網址',
                '推文', '回覆', '發表', '內容', '討論', '發文', '轉錄',
                '站內', '站外', '引用', '來自', '文章', '發信', '站內',
                '看板', '批踢踢', '實業坊', '分享', '已有', '這是', '那個',
                '這個', '就是', '可以', '還是', '還有', '一個', '沒有',
                '什麼', '如果', '因為', '所以', '但是', '只是', '真的',
                '現在', '知道', '覺得', '認為', '希望', '應該', '因此', '可能', '不過', '其他', '即時', '竟然', '以上', '這樣', '踢踢'
            }
            
            # 使用 jieba 進行分詞
            words = jieba.cut(text)
            
            # 只保留中文詞組，並過濾停用詞
            word_freq = {}
            for word in words:
                word = word.strip()
                # 檢查是否為純中文且長度大於1，且不在停用詞中
                if (len(word) > 1 and 
                    re.match(r'^[\u4e00-\u9fff]+$', word) and 
                    word not in stop_words):
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # 根據情緒類型選擇顏色
            if sentiment_type == 'positive':
                color = 'green'
            elif sentiment_type == 'negative':
                color = 'red'
            else:
                color = None
            
            # 設定字體路徑
            font_paths = [
                'C:/Windows/Fonts/msjh.ttc',        # Windows 微軟正黑體
                'C:/Windows/Fonts/mingliu.ttc',     # Windows 細明體
                'C:/Windows/Fonts/simsun.ttc',      # Windows 新宋體
                '/System/Library/Fonts/PingFang.ttc'  # macOS
            ]
            
            font_path = next((path for path in font_paths if os.path.exists(path)), None)
            
            if not word_freq:
                st.warning("沒有找到足夠的中文詞組來生成文字雲")
                return None
            
            # 生成文字雲
            wordcloud = WordCloud(
                width=800,
                height=400,
                background_color='white',
                max_words=100,
                font_path=font_path,
                collocations=False,
                min_font_size=10,
                max_font_size=150,
                color_func=lambda *args, **kwargs: color if color else 'black',
                random_state=42
            ).generate_from_frequencies(word_freq)
            
            # 顯示文字雲
            plt.figure(figsize=(10, 5))
            plt.imshow(wordcloud, interpolation='bilinear')
            plt.axis('off')
            return plt
            
        except Exception as e:
            st.error(f"生成文字雲時發生錯誤：{str(e)}")
            return None

def main():
    st.title("PTT爬蟲分析 / PTT Crawler and Analysis")
    
    # 創建爬蟲實例
    crawler = PTTCrawler()
    
    # 預設熱門看板列表
    popular_boards = {
        "熱門看板 / Popular Boards": "",
        "Gossiping (八卦)": "Gossiping",
        "Stock (股票)": "Stock",
        "C_Chat (希洽)": "C_Chat",
        "Baseball (棒球)": "Baseball",
        "LoL (英雄聯盟)": "LoL",
        "NBA (籃球)": "NBA",
        "Tech_Job (科技職場)": "Tech_Job",
        "PC_Shopping (電腦購物)": "PC_Shopping",
        "Movie (電影)": "Movie",
        "Japan_Travel (日本旅遊)": "Japan_Travel",
        "Beauty (美妝)": "Beauty",
        "MobileComm (通訊)": "MobileComm",
        "car (汽車)": "car",
        "Food (美食)": "Food",
        "WomenTalk (女性)": "WomenTalk",
        "Boy-Girl (男女)": "Boy-Girl",
        "PlayStation (遊戲)": "PlayStation",
        "Steam (遊戲)": "Steam",
        "Lifeismoney (省錢)": "Lifeismoney",
        "HardwareSale (電腦零件)": "HardwareSale",
        "Soft_Job (軟體工作)": "Soft_Job",
        "iOS (蘋果)": "iOS",
        "Android (安卓)": "Android",
        "DigiCurrency (數位貨幣)": "DigiCurrency"
    }
    
    # 主頁面布局
    st.header("看板選擇 / Board Selection")
    
    # 使用 columns 來創建並排的選擇方式
    col1, col2 = st.columns(2)
    
    with col1:
        board_selection = st.radio(
            "選擇看板方式 / Board Selection Method",
            ["從熱門看板選擇 / Select from Popular Boards", 
             "自定義看板 / Custom Board"]
        )
    
    with col2:
        if board_selection == "從熱門看板選擇 / Select from Popular Boards":
            board_name = st.selectbox(
                "選擇看板 / Select Board",
                options=list(popular_boards.keys()),
                format_func=lambda x: x
            )
            board_name = popular_boards[board_name] if board_name in popular_boards else ""
        else:
            board_name = st.text_input(
                "輸入看板名稱 / Enter Board Name",
                help="請輸入看板代號，例如：Gossiping、Stock 等"
            )
    
    # 搜尋設定
    st.header("搜尋設定 / Search Settings")
    
    # 使用 columns 來並排顯示搜尋設定
    col1, col2 = st.columns(2)
    
    with col1:
        keywords = st.text_input(
            "關鍵字（多個關鍵字請用英文逗號分隔）/ Keywords ",
            help="例如：新聞,爆卦,討論"
        ).split(',')
        keywords = [k.strip() for k in keywords if k.strip()]
    
    with col2:
        max_articles = st.number_input(
            "最大爬取文章數(最多5000) / Max Articles",
            min_value=1,
            max_value=5000,
            value=100,
            step=50
        )
    
    # 主要內容區域
    if not board_name:
        st.info("請選擇或輸入看板名稱 / Please select or enter a board name")
        return
    
    st.info(f"當前選擇看板：{board_name} / Current Board: {board_name}")
    
    # 置中顯示爬取按鈕
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        start_crawl = st.button("開始爬取 / Start Crawling", type="primary", use_container_width=True)
    
    if start_crawl:
        # 爬取文章
        df = crawler.crawl_ptt(board_name, keywords, max_articles)
        
        if df is not None and not df.empty:
            # 使用標籤頁來組織不同的分析結果
            tabs = st.tabs(["原始數據", "統計分析", "情緒分析", "文字雲"])
            
            with tabs[0]:
                st.subheader("原始數據 / Raw Data")
                st.dataframe(df)
            
            with tabs[1]:
                st.subheader("統計分析 / Statistical Analysis")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("總文章數", len(df))
                    st.metric("不同作者數", df['author'].nunique())
                with col2:
                    avg_push = df['push_count'].mean() if 'push_count' in df.columns else 0
                    st.metric("平均推文數", f"{avg_push:.2f}")
                
                # 顯示推文分布
                st.subheader("推文分布")
                fig_push = px.histogram(df, x='push_count', title="推文數分布")
                st.plotly_chart(fig_push)
            
            with tabs[2]:
                st.subheader("情緒分析 / Sentiment Analysis")
                
                # 合併所有文章內容
                all_content = ' '.join(df['content'].fillna(''))
                
                # 分析情緒關鍵詞
                sentiment_results = crawler.analyze_sentiment_keywords(all_content)
                
                # 顯示正負面關鍵詞的直方圖
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("正面關鍵詞 Top 20")
                    positive_df = pd.DataFrame(
                        sentiment_results['positive_with_freq'],
                        columns=['關鍵詞', '情緒分數', '出現次數']
                    )
                    # 按出現次數降序排序
                    positive_df = positive_df.sort_values('出現次數', ascending=False)
                    
                    fig_pos = px.bar(
                        positive_df,
                        x='關鍵詞',
                        y='出現次數',
                        title="正面關鍵詞出現頻率",
                        color='情緒分數',
                        color_continuous_scale='Greens',
                    )
                    fig_pos.update_layout(
                        xaxis_tickangle=-45,
                        showlegend=True,
                        height=500,
                        xaxis={'categoryorder': 'total descending'}  # 確保X軸按照數值降序排序
                    )
                    st.plotly_chart(fig_pos)
                
                with col2:
                    st.write("負面關鍵詞 Top 20")
                    negative_df = pd.DataFrame(
                        sentiment_results['negative_with_freq'],
                        columns=['關鍵詞', '情緒分數', '出現次數']
                    )
                    # 按出現次數降序排序
                    negative_df = negative_df.sort_values('出現次數', ascending=False)
                    
                    fig_neg = px.bar(
                        negative_df,
                        x='關鍵詞',
                        y='出現次數',
                        title="負面關鍵詞出現頻率",
                        color='情緒分數',
                        color_continuous_scale='Reds',
                    )
                    fig_neg.update_layout(
                        xaxis_tickangle=-45,
                        showlegend=True,
                        height=500,
                        xaxis={'categoryorder': 'total descending'}  # 確保X軸按照數值降序排序
                    )
                    st.plotly_chart(fig_neg)
                
                # 顯示整體情緒分布
                st.subheader("整體情緒分")
                df['sentiment'] = df['content'].apply(crawler.analyze_sentiment)
                
                # 計算情緒分布
                sentiment_dist = pd.cut(
                    df['sentiment'],
                    bins=[0, 0.3, 0.7, 1],
                    labels=['負面', '中性', '正面']
                ).value_counts()
                
                # 顯示情緒分布圓餅圖
                fig_sentiment_pie = px.pie(
                    values=sentiment_dist.values,
                    names=sentiment_dist.index,
                    title="文章情緒分布",
                    color_discrete_map={
                        '正面': 'lightgreen',
                        '中性': 'lightgray',
                        '負面': 'lightcoral'
                    }
                )
                st.plotly_chart(fig_sentiment_pie)
                
                # 顯示情緒分數直方圖
                fig_sentiment_hist = px.histogram(
                    df,
                    x='sentiment',
                    nbins=20,
                    title="情緒分數分布",
                    labels={'sentiment': '情緒分數 (0=極負面, 1=極正面)'},
                    color_discrete_sequence=['lightblue']
                )
                fig_sentiment_hist.update_layout(
                    showlegend=False,
                    xaxis_title="情緒分數",
                    yaxis_title="文章數量"
                )
                st.plotly_chart(fig_sentiment_hist)
                
                # 顯示統計信息
                st.subheader("情緒統計摘要")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("平均情緒分數", f"{df['sentiment'].mean():.3f}")
                with col2:
                    st.metric("正面文章比例", f"{(df['sentiment'] > 0.7).mean()*100:.1f}%")
                with col3:
                    st.metric("負面文章比例", f"{(df['sentiment'] < 0.3).mean()*100:.1f}%")
            
            with tabs[3]:
                st.subheader("文字雲 / Word Cloud")
                # 一般文字雲
                st.write("整體文字雲")
                wordcloud_plt = crawler.generate_wordcloud(all_content)
                if wordcloud_plt:
                    st.pyplot(wordcloud_plt)
                
                # 分別生成正面和負面文字雲
                col1, col2 = st.columns(2)
                with col1:
                    st.write("正面文字雲")
                    positive_text = ' '.join([word for word, score in sentiment_results['positive']])
                    positive_wordcloud = crawler.generate_sentiment_wordcloud(positive_text, 'positive')
                    if positive_wordcloud:
                        st.pyplot(positive_wordcloud)
                
                with col2:
                    st.write("負面文字雲")
                    negative_text = ' '.join([word for word, score in sentiment_results['negative']])
                    negative_wordcloud = crawler.generate_sentiment_wordcloud(negative_text, 'negative')
                    if negative_wordcloud:
                        st.pyplot(negative_wordcloud)
            
            # 提供下載功能
            st.sidebar.download_button(
                label="下載分析結果 / Download Results",
                data=df.to_csv(index=False),
                file_name=f'ptt_{board_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                mime='text/csv'
            )
        else:
            st.error("沒有找到符合條件的文章！/ No articles found!")

if __name__ == "__main__":
    main() 
