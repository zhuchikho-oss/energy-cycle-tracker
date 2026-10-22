import yfinance as yf
import requests
from bs4 import BeautifulSoup
import json
import datetime
import pandas as pd

def get_stock_data(ticker_symbol):
    """获取股票价格及20日均线数据"""
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
        print(f"获取股票 {ticker_symbol} 失败: {e}")
        return None

def get_commodity_price(source_type, symbol=None):
    """通用商品价格获取与备用参考价机制"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Referer': 'https://finance.sina.com.cn'}
    try:
        if source_type == 'sina_futures' and symbol:
            url = f"https://hq.sinajs.cn/list={symbol}"
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200 and '="' in res.text:
                data_str = res.text.split('="')[1].split('";')[0]
                fields = data_str.split(',')
                if len(fields) > 8 and fields[8] != '':
                    return float(fields[8])
        
        elif source_type == 'gold_spot':
            ticker = yf.Ticker("GC=F")
            df = ticker.history(period="5d")
            if not df.empty:
                return round(float(df['Close'].iloc[-1]), 2)

        elif source_type == 'silver_spot':
            ticker = yf.Ticker("SI=F")
            df = ticker.history(period="5d")
            if not df.empty:
                return round(float(df['Close'].iloc[-1]), 2)

        elif source_type == 'brent_oil':
            ticker = yf.Ticker("BZ=F")
            df = ticker.history(period="5d")
            if not df.empty:
                return round(float(df['Close'].iloc[-1]), 2)

        elif source_type == 'copper_lme':
            ticker = yf.Ticker("HG=F") # COMEX铜参考
            df = ticker.history(period="5d")
            if not df.empty:
                return round(float(df['Close'].iloc[-1]), 3)

    except Exception as e:
        print(f"获取商品 {source_type}-{symbol} 失败: {e}")

    # 备用回退逻辑（防止接口失效导致程序崩溃）
    fallback_map = {
        'uranium': 85.0, 'lithium': 94500.0, 'copper_lme': 4.35,
        'gold_spot': 2720.0, 'silver_spot': 31.5, 'brent_oil': 75.0,
        'coal': 840.0, 'rare_earth': 420.0, 'moly': 3600.0
    }
    return fallback_map.get(source_type, 100.0)

def generate_signal(price, sma20, buy_thresh=0.95, sell_thresh=1.15):
    """根据偏离度生成交易信号"""
    if not price or not sma20:
        return "数据缺失"
    if price < sma20 * buy_thresh:
        return f"🟢 出现低吸/超跌信号 (偏离均线>{round((1-buy_thresh)*100,1)}%)"
    elif price > sma20 * sell_thresh:
        return f"🔴 追高预警 (偏离均线>{round((sell_thresh-1)*100,1)}%)"
    return "观望"

def analyze_all_sectors():
    today_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"=== 全周期套利分析器系统运行中 [{today_str}] ===")
    
    # 定义监控的资产及配置清单
    targets = [
        # 板块名, 股票代码, 股票展示名, 商品获取类型, 商品简称/新浪代码, 计价单位
        ("天然铀板块", "1164.HK", "中广核矿业 (01164.HK)", "uranium", None, "$/lb"),
        ("锂电池板块", "1772.HK", "赣锋锂业 (01772.HK)", "sina_futures", "nf_LC0", "元/吨"),
        ("铜巨头板块", "2899.HK", "紫金矿业 (02899.HK)", "copper_lme", None, "$/磅"),
        ("铜钴高杠杆", "3993.HK", "洛阳钼业 (03993.HK)", "copper_lme", None, "$/磅"),
        ("铜业老牌", "0358.HK", "江西铜业 (00358.HK)", "copper_lme", None, "$/磅"),
        ("稀土板块", "0762.HK", "中国稀土 (00762.HK)", "rare_earth", None, "千元/吨"),
        ("钼铁小金属", "601958.SS", "金钼股份 (601958.SH)", "moly", None, "元/吨度"),
        ("防御高股息煤", "1088.HK", "中国神华 (01088.HK)", "coal", None, "元/吨"),
        ("高弹性现货煤", "1171.HK", "兖矿能源 (01171.HK)", "coal", None, "元/吨"),
        ("焦煤冶金", "0639.HK", "首钢资源 (00639.HK)", "coal", None, "元/吨"),
        ("纯上游原油", "0883.HK", "中国海洋石油 (00883.HK)", "brent_oil", None, "$/桶"),
        ("纯上游天然气", "EQT", "EQT能源 (EQT.US)", "brent_oil", None, "$/MMBtu"),
        ("纯黄金采掘", "1818.HK", "招金矿业 (01818.HK)", "gold_spot", None, "$/盎司"),
        ("黄金龙头", "1787.HK", "山东黄金 (01787.HK)", "gold_spot", None, "$/盎司"),
        ("白银矿业", "EXK", "奋进银业 (EXK.US)", "silver_spot", None, "$/盎司")
    ]

    sectors_data = []

    for category, ticker, name, comm_type, comm_symbol, comm_unit in targets:
        stock = get_stock_data(ticker)
        comm_price = get_commodity_price(comm_type, comm_symbol)
        
        if stock and comm_price:
            ratio = round((stock['price'] / comm_price) * 1000 if comm_price < 1000 else (stock['price'] / (comm_price / 10000)), 2)
            sig = generate_signal(stock['price'], stock['sma20'])
            
            sectors_data.append({
                "category": category,
                "stock_name": name,
                "stock_price": stock['price'],
                "change_pct": f"{stock['change_pct']}%",
                "commodity_price": f"{comm_price} {comm_unit}",
                "ratio_index": ratio,
                "signal": sig
            })

    result = {
        "updated_at": today_str,
        "total_items": len(sectors_data),
        "data": sectors_data
    }

    with open("latest_data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"全套利板块更新完毕，共完成 {len(sectors_data)} 个标的分析。")

if __name__ == "__main__":
    analyze_all_sectors()