# -*- coding: utf-8 -*-
"""
股票代码与名称映射配置

支持的市场:
- A股上海: .SS
- A股深圳: .SZ
- 港股: .HK
- 美股: 直接代码

author: czsc
"""

# 股票代码映射表
# 格式: "代码.市场": "中文名称"
STOCK_MAPPING = {
    # A股 - 上海
    "603259.SS": "药明康德",
    "600519.SS": "贵州茅台",
    "000001.SS": "平安银行",
    "601318.SS": "中国平安",
    "600036.SS": "招商银行",
    
    # A股 - 深圳
    "000001.SZ": "平安银行",
    "000002.SZ": "万科A",
    "000858.SZ": "五粮液",
    "002594.SZ": "比亚迪",
    "300750.SZ": "宁德时代",
    
    # 港股
    "9988.HK": "阿里巴巴",
    "0700.HK": "腾讯控股",
    "3690.HK": "美团",
    "1810.HK": "小米集团",
    "2318.HK": "中国平安",
    "0005.HK": "汇丰控股",
    "1299.HK": "友邦保险",
    "0883.HK": "中国海洋石油",
    
    # 美股
    "BABA": "阿里巴巴",
    "TCEHY": "腾讯控股(ADR)",
    "JD": "京东",
    "PDD": "拼多多",
    "NIO": "蔚来",
    "LI": "理想汽车",
    "XPEV": "小鹏汽车",
}


def get_stock_info(symbol):
    """
    根据代码获取股票信息
    
    :param symbol: 股票代码，如 "9988.HK"
    :return: (symbol, name) 元组
    """
    name = STOCK_MAPPING.get(symbol)
    if name:
        return symbol, name
    else:
        # 如果找不到映射，返回代码作为名称
        return symbol, symbol


def list_all_stocks():
    """列出所有配置的股票"""
    print("=" * 60)
    print("已配置的股票列表")
    print("=" * 60)
    
    # 按市场分类
    markets = {
        "A股(上海)": [],
        "A股(深圳)": [],
        "港股": [],
        "美股": []
    }
    
    for code, name in STOCK_MAPPING.items():
        if code.endswith(".SS"):
            markets["A股(上海)"].append((code, name))
        elif code.endswith(".SZ"):
            markets["A股(深圳)"].append((code, name))
        elif code.endswith(".HK"):
            markets["港股"].append((code, name))
        else:
            markets["美股"].append((code, name))
    
    for market, stocks in markets.items():
        if stocks:
            print(f"\n【{market}】")
            for code, name in stocks:
                print(f"  {code:<12} {name}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    # 测试
    list_all_stocks()
    
    # 测试查询
    print("\n测试查询:")
    test_codes = ["9988.HK", "603259.SS", "BABA", "UNKNOWN"]
    for code in test_codes:
        symbol, name = get_stock_info(code)
        print(f"  {code} -> {symbol}: {name}")
