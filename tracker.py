import yfinance as yf
import json
import datetime

def get_stock_data(ticker_symbol):
    """获取股票价格及20日均线数据（防超时控制）"""
    try:
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period="1mo", timeout=10)
        if df.empty or len(df) < 5:
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
    except Exception:
        return None

def get_commodity_price(source_type):
    """获取大宗商品现货/期货参考价格 (P)"""
    prices = {
        'copper': 4.35, 'cobalt': 14.5, 'aluminum': 2500.0, 'uranium': 85.0,
        'lithium': 95000.0, 'coal_thermal': 840.0, 'coal_coking': 1750.0,
        'oil': 75.0, 'gas': 2.85, 'gold': 2720.0, 'silver': 32.5,
        'rare_earth': 420.0, 'molybdenum': 380.0, 'potash': 320.0
    }
    return prices.get(source_type, 100.0)

def calculate_implied_value(comm_price, fundamental_config):
    """基于 P * C * Q 数学模型计算基本面隐含合理股价"""
    P = comm_price
    C = fundamental_config['cost']
    Q = fundamental_config['volume']
    pe = fundamental_config['fair_pe']
    shares = fundamental_config['shares_b']
    unit_mult = fundamental_config.get('unit_mult', 1.0)

    if P <= C:
        return round(C * 0.1, 2)

    est_profit_billion = ((P - C) * Q * unit_mult * 0.75) / 100000000 
    implied_price = round((est_profit_billion * pe) / shares, 2)
    return max(implied_price, 0.5)

def analyze_targets(target_list):
    """对传入的标的列表运行 P*C*Q + 均线套利模型"""
    result_list = []
    for item in target_list:
        stock = get_stock_data(item['ticker'])
        comm_p = get_commodity_price(item['comm_type'])
        
        if stock and comm_p:
            is_us = item.get('is_us', False)
            implied_p = calculate_implied_value(comm_p, item['fundamentals'])
            curr_symbol = "$" if is_us else "HK$"
            
            ma_ratio = stock['price'] / stock['sma20']
            value_ratio = stock['price'] / implied_p if implied_p > 0 else 1.0
            
            sig = "观望"
            if ma_ratio < 0.95 and value_ratio < 0.90:
                sig = "🟢 黄金级低吸 (基本面重度低估+超跌)"
            elif ma_ratio < 0.95:
                sig = "🟢 技术面低吸 (偏离20日均线)"
            elif ma_ratio > 1.15 or value_ratio > 1.30:
                sig = "🔴 追高预警 (透支基本面/严重超买)"

            result_list.append({
                "category": item['category'],
                "ticker": item['ticker'],
                "stock_name": item['name'],
                "stock_price": f"{curr_symbol} {stock['price']}",
                "change_pct": f"{stock['change_pct']}%",
                "commodity_price": f"{comm_p} {item['unit']}",
                "implied_price": f"{curr_symbol} {implied_p}",
                "cost_line": f"{item['fundamentals']['cost']} {item['unit']}",
                "signal": sig
            })
    return result_list

def run_global_scanner():
    """全网美股/港股上游原料潜在标的扫描池"""
    candidate_pool = [
        {"category": "美股铜", "ticker": "TECK", "name": "泰克资源(Teck)", "comm_type": "copper", "unit": "$/磅", "fundamentals": {"cost": 1.8, "volume": 600000, "fair_pe": 14, "shares_b": 5.1, "unit_mult": 2204.62}, "is_us": True},
        {"category": "美股铝", "ticker": "CENX", "name": "世纪铝业", "comm_type": "aluminum", "unit": "$/吨", "fundamentals": {"cost": 2200.0, "volume": 800000, "fair_pe": 10, "shares_b": 0.95, "unit_mult": 1.0}, "is_us": True},
        {"category": "美股铀", "ticker": "UEC", "name": "美国铀能源", "comm_type": "uranium", "unit": "$/lb", "fundamentals": {"cost": 38.0, "volume": 5000, "fair_pe": 22, "shares_b": 4.0, "unit_mult": 2204.62}, "is_us": True},
        {"category": "美股铀", "ticker": "UUUU", "name": "能源燃料(Energy Fuels)", "comm_type": "uranium", "unit": "$/lb", "fundamentals": {"cost": 42.0, "volume": 3500, "fair_pe": 20, "shares_b": 1.6, "unit_mult": 2204.62}, "is_us": True},
        {"category": "美股黄金", "ticker": "AU", "name": "盎格鲁黄金", "comm_type": "gold", "unit": "$/盎司", "fundamentals": {"cost": 1300.0, "volume": 2500000, "fair_pe": 16, "shares_b": 4.2, "unit_mult": 31.1035}, "is_us": True},
        {"category": "美股白银", "ticker": "PAAS", "name": "泛美白银", "comm_type": "silver", "unit": "$/盎司", "fundamentals": {"cost": 20.0, "volume": 21000000, "fair_pe": 18, "shares_b": 3.6, "unit_mult": 31.1035}, "is_us": True},
        {"category": "美股稀土", "ticker": "MP", "name": "MP材料", "comm_type": "rare_earth", "unit": "元/公斤", "fundamentals": {"cost": 280.0, "volume": 40000000, "fair_pe": 20, "shares_b": 1.7, "unit_mult": 0.14}, "is_us": True},
        {"category": "美股钾肥", "ticker": "NTR", "name": "纽崔安(Nutrien)", "comm_type": "potash", "unit": "$/吨", "fundamentals": {"cost": 190.0, "volume": 13000000, "fair_pe": 12, "shares_b": 4.9, "unit_mult": 1.0}, "is_us": True},
        {"category": "港股铜", "ticker": "358.HK", "name": "江西铜业", "comm_type": "copper", "unit": "$/磅", "fundamentals": {"cost": 2.8, "volume": 200000, "fair_pe": 10, "shares_b": 34.6, "unit_mult": 2204.62}},
        {"category": "港股黄金", "ticker": "1818.HK", "name": "招金矿业", "comm_type": "gold", "unit": "$/盎司", "fundamentals": {"cost": 1250.0, "volume": 800000, "fair_pe": 20, "shares_b": 32.7, "unit_mult": 31.1035}}
    ]
    
    scanned_results = analyze_targets(candidate_pool)
    # 仅过滤保留符合低吸信号（黄金低吸 或 技术低吸）的标的
    bargain_stocks = [item for item in scanned_results if "低吸" in item['signal']]
    return bargain_stocks

def analyze_all_sectors():
    today_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"=== 全周期大宗标的更新 + 全网低吸扫描引擎 [{today_str}] ===")
    
    # 1. 核心监控标的池
    core_targets = [
        {"category": "铜金超巨", "ticker": "2899.HK", "name": "紫金矿业", "comm_type": "copper", "unit": "$/磅", "fundamentals": {"cost": 2.2, "volume": 1000000, "fair_pe": 16, "shares_b": 266.0, "unit_mult": 2204.62}},
        {"category": "美股纯铜", "ticker": "FCX", "name": "麦克莫兰铜金", "comm_type": "copper", "unit": "$/磅", "fundamentals": {"cost": 1.6, "volume": 1800000, "fair_pe": 18, "shares_b": 14.3, "unit_mult": 2204.62}, "is_us": True},
        {"category": "低成本铜", "ticker": "SCCO", "name": "南方铜业", "comm_type": "copper", "unit": "$/磅", "fundamentals": {"cost": 1.2, "volume": 950000, "fair_pe": 20, "shares_b": 7.7, "unit_mult": 2204.62}, "is_us": True},
        {"category": "美股铝业", "ticker": "AA", "name": "美国铝业", "comm_type": "aluminum", "unit": "$/吨", "fundamentals": {"cost": 2100.0, "volume": 2500000, "fair_pe": 12, "shares_b": 1.8, "unit_mult": 1.0}, "is_us": True},
        {"category": "天然铀纯标", "ticker": "1164.HK", "name": "中广核矿业", "comm_type": "uranium", "unit": "$/lb", "fundamentals": {"cost": 40.0, "volume": 2800, "fair_pe": 15, "shares_b": 76.0, "unit_mult": 2204.62}},
        {"category": "美股铀巨", "ticker": "CCJ", "name": "Cameco", "comm_type": "uranium", "unit": "$/lb", "fundamentals": {"cost": 35.0, "volume": 32000, "fair_pe": 25, "shares_b": 4.35, "unit_mult": 2204.62}, "is_us": True},
        {"category": "美股锂业", "ticker": "ALB", "name": "雅保锂业", "comm_type": "lithium", "unit": "元/吨", "fundamentals": {"cost": 68000.0, "volume": 180000, "fair_pe": 15, "shares_b": 1.17, "unit_mult": 0.14}, "is_us": True},
        {"category": "锂盐龙头", "ticker": "1772.HK", "name": "赣锋锂业", "comm_type": "lithium", "unit": "元/吨", "fundamentals": {"cost": 75000.0, "volume": 120000, "fair_pe": 18, "shares_b": 20.1, "unit_mult": 1.0}},
        {"category": "美股油气", "ticker": "OXY", "name": "西方石油", "comm_type": "oil", "unit": "$/桶", "fundamentals": {"cost": 32.0, "volume": 420000000, "fair_pe": 12, "shares_b": 8.8, "unit_mult": 1.0}, "is_us": True},
        {"category": "上游油气", "ticker": "0883.HK", "name": "中国海洋石油", "comm_type": "oil", "unit": "$/桶", "fundamentals": {"cost": 30.0, "volume": 680000000, "fair_pe": 8, "shares_b": 475.0, "unit_mult": 7.8}},
        {"category": "美股焦煤", "ticker": "AMR", "name": "Alpha焦煤", "comm_type": "coal_coking", "unit": "元/吨", "fundamentals": {"cost": 850.0, "volume": 16000000, "fair_pe": 8, "shares_b": 0.13, "unit_mult": 0.14}, "is_us": True},
        {"category": "防守动力煤", "ticker": "1088.HK", "name": "中国神华", "comm_type": "coal_thermal", "unit": "元/吨", "fundamentals": {"cost": 360.0, "volume": 320000000, "fair_pe": 10, "shares_b": 198.0, "unit_mult": 1.0}},
        {"category": "美股黄金", "ticker": "NEM", "name": "纽蒙特黄金", "comm_type": "gold", "unit": "$/盎司", "fundamentals": {"cost": 1200.0, "volume": 5800000, "fair_pe": 18, "shares_b": 11.5, "unit_mult": 31.1035}, "is_us": True},
        {"category": "美股纯白银", "ticker": "EXK", "name": "奋进银业", "comm_type": "silver", "unit": "$/盎司", "fundamentals": {"cost": 21.0, "volume": 9000000, "fair_pe": 18, "shares_b": 2.2, "unit_mult": 31.1035}, "is_us": True},
        {"category": "美股化肥", "ticker": "MOS", "name": "美盛化肥", "comm_type": "potash", "unit": "$/吨", "fundamentals": {"cost": 210.0, "volume": 18000000, "fair_pe": 11, "shares_b": 3.2, "unit_mult": 1.0}, "is_us": True}
    ]

    print("1. 开始更新固定核心监控标的...")
    core_results = analyze_targets(core_targets)

    print("2. 启动全网上游原料潜质股扫描...")
    discovered_bargains = run_global_scanner()
    print(f"全网扫描完毕，共发现 {len(discovered_bargains)} 个低吸信号标的。")

    result = {
        "updated_at": today_str,
        "total_items": len(core_results),
        "discovered_count": len(discovered_bargains),
        "data": core_results,
        "discovered_data": discovered_bargains  # 专门存放扫描发现的低吸标的
    }

    with open("latest_data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("数据保存成功。")

if __name__ == "__main__":
    analyze_all_sectors()