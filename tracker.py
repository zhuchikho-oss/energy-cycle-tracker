import yfinance as yf
import requests
from bs4 import BeautifulSoup
import json
import datetime
import pandas as pd

def get_stock_data(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period="1mo")
        if df.empty:
            return None
        
        latest_price = round(float(df['Close'].iloc[-1]), 3)
        sma20 = round(float(df['Close'].rolling(window=min(len(df), 20)).mean().iloc[-1]), 3)
        
        pct_change = 0.0
        if len(df) >= 2:
            pct_change = round(((latest_price - float(df['Close'].iloc[-2])) / float(df['Close'].iloc[-2])) * 100, 2)
        
        return {
            "price": latest_price,
            "sma20": sma20,
            "change_pct": pct_change
        }
    except Exception as e:
        print(f"获取股票 {ticker_symbol} 数据失败: {e}")
        return None

def get_lithium_price():
    try:
        url = "https://hq.sinajs.cn/list=nf_LC0"
        headers = {'Referer': 'https://finance.sina.com.cn', 'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200 and '="' in res.text:
            data_str = res.text.split('="')[1].split('";')[0]
            fields = data_str.split(',')
            if len(fields) > 8 and fields[8] != '':
                return float(fields[8])
    except Exception as e:
        print(f"获取碳酸锂价格失败，使用备用参考价: {e}")
    return 94760.0

def get_uranium_price():
    try:
        url = "https://tradingeconomics.com/commodity/uranium"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            price_element = soup.find("div", {"id": "market_price"})
            if price_element:
                return float(price_element.text.strip())
    except Exception as e:
        print(f"抓取天然铀价格失败，使用备用参考价: {e}")
    return 85.0

def analyze_signals():
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    print(f"=== 运行能源周期套利分析器 [{today_str}] ===")
    
    # 1. 分析天然铀板块 (中广核矿业 1164.HK)
    cgn_stock = get_stock_data("1164.HK") or get_stock_data("01164.HK")
    uranium_p = get_uranium_price()
    
    uranium_analysis = {}
    if cgn_stock:
        ratio = round((cgn_stock['price'] / uranium_p) * 1000, 2)
        signal = "观望"
        if cgn_stock['price'] < cgn_stock['sma20'] * 0.95:
            signal = "🟢 出现低吸/超跌信号 (偏离均线>5%)"
        elif cgn_stock['price'] > cgn_stock['sma20'] * 1.15:
            signal = "🔴 追高预警 (偏离均线>15%)"

        uranium_analysis = {
            "stock_name": "中广核矿业 (01164.HK)",
            "stock_price": cgn_stock['price'],
            "stock_change_pct": f"{cgn_stock['change_pct']}%",
            "uranium_spot_price": f"${uranium_p}/lb",
            "ratio_index": ratio,
            "signal": signal
        }

    # 2. 分析锂电池板块 (赣锋锂业 1772.HK)
    ganfeng_stock = get_stock_data("1772.HK") or get_stock_data("01772.HK")
    lithium_p = get_lithium_price()
    
    lithium_analysis = {}
    if ganfeng_stock:
        ratio_li = round((ganfeng_stock['price'] / (lithium_p / 10000)), 2)
        signal_li = "观望"
        if ganfeng_stock['price'] < ganfeng_stock['sma20'] * 0.93:
            signal_li = "🟢 出现低吸/超跌信号"
        elif ganfeng_stock['price'] > ganfeng_stock['sma20'] * 1.15:
            signal_li = "🔴 追高预警"

        lithium_analysis = {
            "stock_name": "赣锋锂业 (01772.HK)",
            "stock_price": ganfeng_stock['price'],
            "lithium_futures_price": f"¥{lithium_p}/吨",
            "ratio_index": ratio_li,
            "signal": signal_li
        }

    result = {
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "uranium_sector": uranium_analysis,
        "lithium_sector": lithium_analysis
    }

    print("\n[分析结果]")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    with open("latest_data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    analyze_signals()