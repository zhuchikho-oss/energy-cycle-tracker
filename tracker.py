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

def get_commodity_demand_dashboard():
    """全球主要大宗原料需求热度仪表盘与现货价格矩阵"""
    # demand_score: 基于全球年消费量与供需紧平衡度的需求指数 (1-100)
    commodities = {
        'oil': {'price': 75.0, 'unit': '$/桶', 'name': '原油/石油', 'demand_score': 95, 'desc': '全球工业第一能源，日需求突破 1.02 亿桶'},
        'copper': {'price': 4.35, 'unit': '$/磅', 'name': '精炼铜', 'demand_score': 92, 'desc': '电网升级与 AI 数据中心硬件核心，供需缺口扩大'},
        'coal_coking': {'price': 1750.0, 'unit': '元/吨', 'name': '冶金焦煤', 'demand_score': 88, 'desc': '全球钢铁高炉开工刚性需求，高品质出口紧缺'},
        'uranium': {'price': 85.0, 'unit': '$/lb', 'name': '天然铀', 'demand_score': 85, 'desc': '全球核电重启与数据中心核能微堆需求爆发'},
        'coal_thermal': {'price': 840.0, 'unit': '元/吨', 'name': '动力煤', 'demand_score': 82, 'desc': '火电基底托底能源，基建与迎峰度夏/冬刚需'},
        'gold': {'price': 2720.0, 'unit': '$/盎司', 'name': '现货黄金', 'demand_score': 80, 'desc': '全球央行去美元化购金潮，避险信用对冲'},
        'aluminum': {'price': 2500.0, 'unit': '$/吨', 'name': '原铝', 'demand_score': 78, 'desc': '光伏支架与汽车轻量化用铝需求平稳增长'},
        'lithium': {'price': 95000.0, 'unit': '元/吨', 'name': '碳酸锂', 'demand_score': 72, 'desc': '储能与储能电池采买探底复苏，筑底蓄势'}
    }
    return commodities

def calculate_institutional_valuation(comm_price, f):
    """4大机构价值模型联合算力引擎"""
    P = comm_price
    C = f['cost']
    Q = f['volume']
    pe = f['fair_pe']
    shares = f['shares_b']
    unit_mult = f.get('unit_mult', 1.0)

    # 1. P*C*Q 经营杠杆估值
    if P <= C:
        pcq_price = C * 0.1
    else:
        annual_profit_b = ((P - C) * Q * unit_mult * 0.75) / 100000000.0
        pcq_price = (annual_profit_b * pe) / shares

    # 2. NAV 清算底线估值
    nav_base = f.get('nav_floor', C * 0.5)
    nav_price = max(round((nav_base * Q * unit_mult * 0.2) / (shares * 100000000.0), 2), 0.5)

    # 3. 所有者收益估值 (FCF)
    owner_earnings_price = pcq_price * 0.85

    # 4. 综合 4 大模型导出机构内在价值
    institutional_value = (pcq_price * 0.45) + (owner_earnings_price * 0.35) + (nav_price * 0.20)
    return max(round(institutional_value, 2), 0.5)

def analyze_targets(target_list, demand_dict):
    """联合分析标的并注入需求权重"""
    result_list = []
    for item in target_list:
        stock = get_stock_data(item['ticker'])
        comm_info = demand_dict.get(item['comm_type'], {'price': 100.0, 'demand_score': 50})
        comm_p = comm_info['price']
        
        if stock and comm_p:
            is_us = item.get('is_us', False)
            implied_p = calculate_institutional_valuation(comm_p, item['fundamentals'])
            curr_symbol = "$" if is_us else "HK$"
            
            ma_ratio = stock['price'] / stock['sma20']
            value_ratio = stock['price'] / implied_p if implied_p > 0 else 1.0
            
            sig = "观望"
            if ma_ratio < 0.95 and value_ratio < 0.88:
                sig = "🟢 黄金级低吸 (4大模型重度低估+超跌)"
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
                "demand_score": comm_info['demand_score'], # 需求热度分
                "signal": sig
            })
    return result_list

def run_global_scanner(demand_dict):
    """按照全球需求热度 (demand_score) 优先级从高到低进行全网扫描"""
    candidate_pool = [
        {"category": "美股油气", "ticker": "EOG", "name": "EOG能源", "comm_type": "oil", "unit": "$/桶", "fundamentals": {"cost": 34.0, "volume": 350000000, "fair_pe": 11, "shares_b": 5.8, "unit_mult": 1.0, "nav_floor": 22.0}, "is_us": True},
        {"category": "美股铜", "ticker": "TECK", "name": "泰克资源(Teck)", "comm_type": "copper", "unit": "$/磅", "fundamentals": {"cost": 1.8, "volume": 600000, "fair_pe": 14, "shares_b": 5.1, "unit_mult": 2204.62, "nav_floor": 1.1}, "is_us": True},
        {"category": "美股铀", "ticker": "UEC", "name": "美国铀能源", "comm_type": "uranium", "unit": "$/lb", "fundamentals": {"cost": 38.0, "volume": 5000, "fair_pe": 22, "shares_b": 4.0, "unit_mult": 2204.62, "nav_floor": 25.0}, "is_us": True},
        {"category": "美股铀", "ticker": "UUUU", "name": "能源燃料(Energy Fuels)", "comm_type": "uranium", "unit": "$/lb", "fundamentals": {"cost": 42.0, "volume": 3500, "fair_pe": 20, "shares_b": 1.6, "unit_mult": 2204.62, "nav_floor": 28.0}, "is_us": True},
        {"category": "美股铝", "ticker": "CENX", "name": "世纪铝业", "comm_type": "aluminum", "unit": "$/吨", "fundamentals": {"cost": 2200.0, "volume": 800000, "fair_pe": 10, "shares_b": 0.95, "unit_mult": 1.0, "nav_floor": 1800.0}, "is_us": True},
        {"category": "美股黄金", "ticker": "AU", "name": "盎格鲁黄金", "comm_type": "gold", "unit": "$/盎司", "fundamentals": {"cost": 1300.0, "volume": 2500000, "fair_pe": 16, "shares_b": 4.2, "unit_mult": 31.1035, "nav_floor": 900.0}, "is_us": True},
        {"category": "港股铜", "ticker": "358.HK", "name": "江西铜业", "comm_type": "copper", "unit": "$/磅", "fundamentals": {"cost": 2.8, "volume": 200000, "fair_pe": 10, "shares_b": 34.6, "unit_mult": 2204.62, "nav_floor": 1.8}},
        {"category": "港股黄金", "ticker": "1818.HK", "name": "招金矿业", "comm_type": "gold", "unit": "$/盎司", "fundamentals": {"cost": 1250.0, "volume": 800000, "fair_pe": 20, "shares_b": 32.7, "unit_mult": 31.1035, "nav_floor": 850.0}}
    ]
    
    # 按照需求指数对候选池进行降序排列
    candidate_pool.sort(key=lambda x: demand_dict.get(x['comm_type'], {}).get('demand_score', 0), reverse=True)
    
    scanned_results = analyze_targets(candidate_pool, demand_dict)
    bargain_stocks = [item for item in scanned_results if "低吸" in item['signal']]
    return bargain_stocks

def analyze_all_sectors():
    today_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    demand_dict = get_commodity_demand_dashboard()
    
    print(f"=== 全球大宗需求优先级 + 4大机构价值模型分析 [{today_str}] ===")
    
    core_targets = [
        {"category": "铜金超巨", "ticker": "2899.HK", "name": "紫金矿业", "comm_type": "copper", "unit": "$/磅", "fundamentals": {"cost": 2.2, "volume": 1000000, "fair_pe": 16, "shares_b": 266.0, "unit_mult": 2204.62, "nav_floor": 1.3}},
        {"category": "美股纯铜", "ticker": "FCX", "name": "麦克莫兰铜金", "comm_type": "copper", "unit": "$/磅", "fundamentals": {"cost": 1.6, "volume": 1800000, "fair_pe": 18, "shares_b": 14.3, "unit_mult": 2204.62, "nav_floor": 1.0}, "is_us": True},
        {"category": "美股焦煤", "ticker": "AMR", "name": "Alpha焦煤", "comm_type": "coal_coking", "unit": "元/吨", "fundamentals": {"cost": 850.0, "volume": 16000000, "fair_pe": 8, "shares_b": 0.13, "unit_mult": 0.14, "nav_floor": 550.0}, "is_us": True},
        {"category": "美股油气", "ticker": "OXY", "name": "西方石油", "comm_type": "oil", "unit": "$/桶", "fundamentals": {"cost": 32.0, "volume": 420000000, "fair_pe": 12, "shares_b": 8.8, "unit_mult": 1.0, "nav_floor": 20.0}, "is_us": True},
        {"category": "上游油气", "ticker": "0883.HK", "name": "中国海洋石油", "comm_type": "oil", "unit": "$/桶", "fundamentals": {"cost": 30.0, "volume": 680000000, "fair_pe": 8, "shares_b": 475.0, "unit_mult": 7.8, "nav_floor": 18.0}},
        {"category": "天然铀纯标", "ticker": "1164.HK", "name": "中广核矿业", "comm_type": "uranium", "unit": "$/lb", "fundamentals": {"cost": 40.0, "volume": 2800, "fair_pe": 15, "shares_b": 76.0, "unit_mult": 2204.62, "nav_floor": 22.0}},
        {"category": "美股铀巨", "ticker": "CCJ", "name": "Cameco", "comm_type": "uranium", "unit": "$/lb", "fundamentals": {"cost": 35.0, "volume": 32000, "fair_pe": 25, "shares_b": 4.35, "unit_mult": 2204.62, "nav_floor": 20.0}, "is_us": True},
        {"category": "防守动力煤", "ticker": "1088.HK", "name": "中国神华", "comm_type": "coal_thermal", "unit": "元/吨", "fundamentals": {"cost": 360.0, "volume": 320000000, "fair_pe": 10, "shares_b": 198.0, "unit_mult": 1.0, "nav_floor": 250.0}},
        {"category": "美股锂业", "ticker": "ALB", "name": "雅保锂业", "comm_type": "lithium", "unit": "元/吨", "fundamentals": {"cost": 68000.0, "volume": 180000, "fair_pe": 15, "shares_b": 1.17, "unit_mult": 0.14, "nav_floor": 45000.0}, "is_us": True}
    ]

    # 根据需求优先级排列核心监控池
    core_targets.sort(key=lambda x: demand_dict.get(x['comm_type'], {}).get('demand_score', 0), reverse=True)

    print("1. 正在按全球需求量优先级排序并运行 4 大估值模型...")
    core_results = analyze_targets(core_targets, demand_dict)

    print("2. 正在按需求量优先级从高到低全网扫描潜质低吸股...")
    discovered_bargains = run_global_scanner(demand_dict)

    # 计算需求榜单 Top Raw Material
    top_demand = sorted(demand_dict.items(), key=lambda x: x[1]['demand_score'], reverse=True)

    result = {
        "updated_at": today_str,
        "top_demand_material": f"{top_demand[0][1]['name']} (热度指数: {top_demand[0][1]['demand_score']})",
        "demand_dashboard": demand_dict,
        "total_items": len(core_results),
        "discovered_count": len(discovered_bargains),
        "data": core_results,
        "discovered_data": discovered_bargains
    }

    with open("latest_data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("计算与分析完成，已保存 JSON。")

if __name__ == "__main__":
    analyze_all_sectors()