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

def get_commodity_price(source_type, symbol=None):
    """获取大宗商品现货/期货价格 (P)"""
    try:
        if source_type == 'uranium': return 85.0       # $/lb 铀现货价
        elif source_type == 'lithium': return 95000.0   # 元/吨 碳酸锂
        elif source_type == 'copper': return 4.35       # $/磅 伦铜
        elif source_type == 'coal': return 840.0        # 元/吨 动力煤
        elif source_type == 'oil': return 75.0          # $/桶 布伦特原油
        elif source_type == 'gold': return 2720.0       # $/盎司 黄金
    except Exception as e:
        pass
    return 100.0

def calculate_implied_value(comm_price, fundamental_config):
    """
    基于 P * C * Q 数学模型计算基本面隐含合理股价
    """
    P = comm_price
    C = fundamental_config['cost']            # 单位生产成本
    Q = fundamental_config['volume']          # 年化销量/产量
    pe = fundamental_config['fair_pe']        # 板块合理PE估值
    shares = fundamental_config['shares_b']   # 总股本(亿股)
    unit_mult = fundamental_config.get('unit_mult', 1.0) # 单位换算乘数

    if P <= C:
        return round(C * 0.1, 2) # 跌破成本线时的保底清算参考

    # 计算预估年化净利润 (亿)
    est_profit_billion = ((P - C) * Q * unit_mult * 0.75) / 100000000 
    
    # 基本面估算合理股价 = (总利润 * 合理PE) / 总股本
    implied_price = round((est_profit_billion * pe) / shares, 2)
    return max(implied_price, 0.5)

def analyze_all_sectors():
    today_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"=== 全周期 [P*C*Q基本面+技术面] 联合套利分析器 [{today_str}] ===")
    
    # 标的基本面数据库 (新增 C:成本, Q:销量, fair_pe:合理PE, shares_b:总股本)
    targets = [
        {
            "category": "天然铀龙头", "ticker": "1164.HK", "name": "中广核矿业", "comm_type": "uranium", "unit": "$/lb",
            "fundamentals": {"cost": 40.0, "volume": 2800, "fair_pe": 15, "shares_b": 76.0, "unit_mult": 2204.62} # 吨转磅
        },
        {
            "category": "锂电池巨头", "ticker": "1772.HK", "name": "赣锋锂业", "comm_type": "lithium", "unit": "元/吨",
            "fundamentals": {"cost": 75000.0, "volume": 120000, "fair_pe": 18, "shares_b": 20.1, "unit_mult": 1.0}
        },
        {
            "category": "铜金超巨", "ticker": "2899.HK", "name": "紫金矿业", "comm_type": "copper", "unit": "$/磅",
            "fundamentals": {"cost": 2.2, "volume": 1000000, "fair_pe": 16, "shares_b": 266.0, "unit_mult": 2204.62}
        },
        {
            "category": "现货高弹性煤", "ticker": "1171.HK", "name": "兖矿能源", "comm_type": "coal", "unit": "元/吨",
            "fundamentals": {"cost": 420.0, "volume": 140000000, "fair_pe": 7, "shares_b": 74.0, "unit_mult": 1.0}
        },
        {
            "category": "纯上游原油", "ticker": "0883.HK", "name": "中国海洋石油", "comm_type": "oil", "unit": "$/桶",
            "fundamentals": {"cost": 30.0, "volume": 680000000, "fair_pe": 8, "shares_b": 475.0, "unit_mult": 7.8} # 桶转港币/汇率折算
        }
    ]

    sectors_data = []

    for item in targets:
        stock = get_stock_data(item['ticker'])
        comm_p = get_commodity_price(item['comm_type'])
        
        if stock and comm_p:
            implied_p = calculate_implied_value(comm_p, item['fundamentals'])
            
            # 综合计算技术偏离与基本面安全边际
            ma_ratio = stock['price'] / stock['sma20']
            value_ratio = stock['price'] / implied_p if implied_p > 0 else 1.0
            
            # 复合判决逻辑
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
                "stock_price": stock['price'],
                "change_pct": f"{stock['change_pct']}%",
                "commodity_price": f"{comm_p} {item['unit']}",
                "implied_price": f"HK$ {implied_p}",
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