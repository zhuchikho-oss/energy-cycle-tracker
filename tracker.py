import yfinance as yf
import requests
import json
import datetime

def get_stock_data(ticker_symbol):
    """获取股票价格及20日均线数据（带防超时控制）"""
    try:
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period="1mo", timeout=10)
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

def get_commodity_price(source_type):
    """获取大宗商品现货/期货参考价格 (P)"""
    try:
        prices = {
            'copper': 4.35,      # $/磅 伦铜
            'cobalt': 14.5,      # $/磅 钴现货
            'uranium': 85.0,     # $/磅 U3O8铀现货
            'lithium': 95000.0,  # 元/吨 碳酸锂
            'coal_thermal': 840.0,# 元/吨 动力煤
            'coal_coking': 1750.0,# 元/吨 焦煤
            'oil': 75.0,         # $/桶 布伦特原油
            'gas': 2.85,         # $/MMBtu 天然气
            'gold': 2720.0,      # $/盎司 黄金
            'silver': 32.5,      # $/盎司 白银
            'rare_earth': 420.0, # 元/公斤 氧化镨钕
            'molybdenum': 380.0  # 元/公斤 钼铁
        }
        return prices.get(source_type, 100.0)
    except Exception:
        return 100.0

def calculate_implied_value(comm_price, fundamental_config, is_us_stock=False, is_a_stock=False):
    """
    基于 P * C * Q 数学模型计算基本面隐含合理股价
    """
    P = comm_price
    C = fundamental_config['cost']            # 单位生产成本
    Q = fundamental_config['volume']          # 年化销量/产量
    pe = fundamental_config['fair_pe']        # 板块合理PE估值
    shares = fundamental_config['shares_b']   # 总股本(亿股)
    unit_mult = fundamental_config.get('unit_mult', 1.0) # 单位/汇率换算乘数

    if P <= C:
        return round(C * 0.1, 2) # 跌破成本线保底估算

    # 估算预估年化净利润 (亿)
    est_profit_billion = ((P - C) * Q * unit_mult * 0.75) / 100000000 
    
    # 基本面估算合理股价
    implied_price = round((est_profit_billion * pe) / shares, 2)
    return max(implied_price, 0.5)

def analyze_all_sectors():
    today_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"=== 全周期 20 大标的 [P*C*Q基本面+技术面] 联合套利分析器 [{today_str}] ===")
    
    # 20 大核心标的基本面数据库 (C:成本, Q:销量, fair_pe:合理PE, shares_b:总股本)
    targets = [
        # 1. 铜与钴
        {"category": "铜金超巨", "ticker": "2899.HK", "name": "紫金矿业", "comm_type": "copper", "unit": "$/磅", "fundamentals": {"cost": 2.2, "volume": 1000000, "fair_pe": 16, "shares_b": 266.0, "unit_mult": 2204.62}},
        {"category": "铜钴龙头", "ticker": "3993.HK", "name": "洛阳钼业", "comm_type": "copper", "unit": "$/磅", "fundamentals": {"cost": 2.1, "volume": 550000, "fair_pe": 15, "shares_b": 215.0, "unit_mult": 2204.62}},
        {"category": "铜业老牌", "ticker": "0358.HK", "name": "江西铜业", "comm_type": "copper", "unit": "$/磅", "fundamentals": {"cost": 2.8, "volume": 200000, "fair_pe": 10, "shares_b": 34.6, "unit_mult": 2204.62}},
        {"category": "海外铜锌", "ticker": "1208.HK", "name": "五矿资源", "comm_type": "copper", "unit": "$/磅", "fundamentals": {"cost": 2.5, "volume": 340000, "fair_pe": 12, "shares_b": 122.0, "unit_mult": 2204.62}},
        {"category": "美股铜巨", "ticker": "FCX", "name": "麦克莫兰铜金", "comm_type": "copper", "unit": "$/磅", "fundamentals": {"cost": 1.6, "volume": 1800000, "fair_pe": 18, "shares_b": 14.3, "unit_mult": 2204.62}, "is_us": True},

        # 2. 能源金属 (铀 & 锂)
        {"category": "天然铀纯标", "ticker": "1164.HK", "name": "中广核矿业", "comm_type": "uranium", "unit": "$/lb", "fundamentals": {"cost": 40.0, "volume": 2800, "fair_pe": 15, "shares_b": 76.0, "unit_mult": 2204.62}},
        {"category": "锂盐龙头", "ticker": "1772.HK", "name": "赣锋锂业", "comm_type": "lithium", "unit": "元/吨", "fundamentals": {"cost": 75000.0, "volume": 120000, "fair_pe": 18, "shares_b": 20.1, "unit_mult": 1.0}},
        {"category": "锂矿巨头", "ticker": "9696.HK", "name": "天齐锂业", "comm_type": "lithium", "unit": "元/吨", "fundamentals": {"cost": 60000.0, "volume": 90000, "fair_pe": 16, "shares_b": 16.4, "unit_mult": 1.0}},
        {"category": "铀现货信托", "ticker": "SRUUF", "name": "Sprott铀信托", "comm_type": "uranium", "unit": "$/lb", "fundamentals": {"cost": 50.0, "volume": 10000, "fair_pe": 20, "shares_b": 2.5, "unit_mult": 2204.62}, "is_us": True},
        {"category": "美股铀巨", "ticker": "CCJ", "name": "Cameco", "comm_type": "uranium", "unit": "$/lb", "fundamentals": {"cost": 35.0, "volume": 32000, "fair_pe": 25, "shares_b": 4.35, "unit_mult": 2204.62}, "is_us": True},

        # 3. 化石能源 (煤炭 & 油气)
        {"category": "上游油气", "ticker": "0883.HK", "name": "中国海洋石油", "comm_type": "oil", "unit": "$/桶", "fundamentals": {"cost": 30.0, "volume": 680000000, "fair_pe": 8, "shares_b": 475.0, "unit_mult": 7.8}},
        {"category": "弹性动力煤", "ticker": "1171.HK", "name": "兖矿能源", "comm_type": "coal_thermal", "unit": "元/吨", "fundamentals": {"cost": 420.0, "volume": 140000000, "fair_pe": 7, "shares_b": 74.0, "unit_mult": 1.0}},
        {"category": "防守动力煤", "ticker": "1088.HK", "name": "中国神华", "comm_type": "coal_thermal", "unit": "元/吨", "fundamentals": {"cost": 360.0, "volume": 320000000, "fair_pe": 10, "shares_b": 198.0, "unit_mult": 1.0}},
        {"category": "焦煤龙头", "ticker": "0639.HK", "name": "首钢资源", "comm_type": "coal_coking", "unit": "元/吨", "fundamentals": {"cost": 650.0, "volume": 5200000, "fair_pe": 8, "shares_b": 50.5, "unit_mult": 1.0}},
        {"category": "综合动力煤", "ticker": "1898.HK", "name": "中煤能源", "comm_type": "coal_thermal", "unit": "元/吨", "fundamentals": {"cost": 390.0, "volume": 130000000, "fair_pe": 8, "shares_b": 132.0, "unit_mult": 1.0}},
        {"category": "美股天然气", "ticker": "EQT", "name": "EQT能源", "comm_type": "gas", "unit": "$/MMBtu", "fundamentals": {"cost": 1.8, "volume": 2000000000, "fair_pe": 12, "shares_b": 4.4, "unit_mult": 1.0}, "is_us": True},

        # 4. 贵金属 & 稀土小金属
        {"category": "纯金采掘", "ticker": "1818.HK", "name": "招金矿业", "comm_type": "gold", "unit": "$/盎司", "fundamentals": {"cost": 1250.0, "volume": 800000, "fair_pe": 20, "shares_b": 32.7, "unit_mult": 31.1035}},
        {"category": "国资黄金", "ticker": "1787.HK", "name": "山东黄金", "comm_type": "gold", "unit": "$/盎司", "fundamentals": {"cost": 1350.0, "volume": 1200000, "fair_pe": 22, "shares_b": 44.7, "unit_mult": 31.1035}},
        {"category": "美股纯白银", "ticker": "EXK", "name": "奋进银业", "comm_type": "silver", "unit": "$/盎司", "fundamentals": {"cost": 21.0, "volume": 9000000, "fair_pe": 18, "shares_b": 2.2, "unit_mult": 31.1035}, "is_us": True},
        {"category": "稀土龙头", "ticker": "0762.HK", "name": "中国稀土", "comm_type": "rare_earth", "unit": "元/公斤", "fundamentals": {"cost": 320.0, "volume": 5000000, "fair_pe": 25, "shares_b": 23.4, "unit_mult": 1.0}}
    ]

    sectors_data = []

    for item in targets:
        stock = get_stock_data(item['ticker'])
        comm_p = get_commodity_price(item['comm_type'])
        
        if stock and comm_p:
            is_us = item.get('is_us', False)
            implied_p = calculate_implied_value(comm_p, item['fundamentals'], is_us_stock=is_us)
            
            curr_symbol = "$" if is_us else "HK$"
            
            ma_ratio = stock['price'] / stock['sma20']
            value_ratio = stock['price'] / implied_p if implied_p > 0 else 1.0
            
            if ma_ratio < 0.95 and value_ratio < 0.90:
                sig = "🟢 黄金级低吸 (基本面重度低估+超跌)"
            elif ma_ratio < 0.95:
                sig = "🟢 技术面低吸 (偏离20日均线)"
            elif ma_ratio > 1.15 or value_ratio > 1.30:
                sig = "🔴 追高预警 (透支基本面/严重超买)"
            else:
                sig = "观望"

            sectors_data.append({
                "category": item['category'],
                "stock_name": item['name'],
                "stock_price": f"{curr_symbol} {stock['price']}",
                "change_pct": f"{stock['change_pct']}%",
                "commodity_price": f"{comm_p} {item['unit']}",
                "implied_price": f"{curr_symbol} {implied_p}",
                "cost_line": f"{item['fundamentals']['cost']} {item['unit']}",
                "signal": sig
            })

    result = {
        "updated_at": today_str,
        "total_items": len(sectors_data),
        "data": sectors_data
    }

    with open("latest_data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"全套利板块更新完毕，共完成 {len(sectors_data)} 个标的基本面+技术面联合分析。")

if __name__ == "__main__":
    analyze_all_sectors()