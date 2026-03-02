# -*- coding: utf-8 -*-
"""
股票缠论图形分析示例

本示例展示如何对股票进行缠论分析并可视化
支持：
1. Mock 数据（无需外部数据源）
2. 真实股票数据（需要安装 akshare: pip install akshare）

author: czsc
"""
from czsc import CZSC, Freq, format_standard_kline
from czsc.utils.echarts_plot import kline_pro
from czsc.mock import generate_symbol_kines


def analyze_with_mock(symbol="000001", name="平安银行"):
    """
    使用 Mock 数据进行缠论分析
    
    :param symbol: 股票代码
    :param name: 股票名称
    """
    print(f"\n{'='*60}")
    print(f"开始分析: {name} ({symbol})")
    print(f"{'='*60}\n")
    
    # 1. 生成模拟K线数据（日线）
    print("步骤1: 获取K线数据...")
    df = generate_symbol_kines(symbol, '日线', '20220101', '20240101', seed=42)
    bars = format_standard_kline(df, freq=Freq.D)
    print(f"✓ 获取到 {len(bars)} 根K线")
    
    # 2. 进行缠论分析
    print("\n步骤2: 进行缠论分析...")
    czsc_obj = CZSC(bars, max_bi_num=1000)
    print(f"✓ 分析完成")
    print(f"  - 分型数量: {len(czsc_obj.fx_list)}")
    print(f"  - 笔数量: {len(czsc_obj.bi_list)}")
    # 线段功能可能需要额外配置，先注释掉
    # if hasattr(czsc_obj, 'xd_list') and czsc_obj.xd_list:
    #     print(f"  - 线段数量: {len(czsc_obj.xd_list)}")
    
    # 3. 准备绘图数据
    print("\n步骤3: 准备绘图数据...")
    
    # K线数据
    kline_data = [{
        "dt": bar.dt,
        "open": bar.open,
        "close": bar.close,
        "high": bar.high,
        "low": bar.low,
        "vol": bar.vol
    } for bar in bars]
    
    # 分型数据
    fx_data = [{
        "dt": fx.dt,
        "fx": fx.fx,
        "fx_mark": fx.fx_mark.value
    } for fx in czsc_obj.fx_list]
    
    # 笔数据（连接笔的起点和终点）
    bi_data = []
    for bi in czsc_obj.bi_list:
        bi_data.append({"dt": bi.fx_a.dt, "bi": bi.fx_a.fx})
        bi_data.append({"dt": bi.fx_b.dt, "bi": bi.fx_b.fx})
    
    print(f"✓ 数据准备完成")
    
    # 4. 绘制图表
    print("\n步骤4: 生成可视化图表...")
    chart = kline_pro(
        kline=kline_data,
        fx=fx_data,
        bi=bi_data,
        title=f"{name} ({symbol}) 缠论分析",
        t_seq=[5, 10, 20, 60],  # 5日、10日、20日、60日均线
        width="1400px",
        height="700px"
    )
    
    # 5. 保存图表
    output_file = f"{symbol}_{name}_缠论分析.html"
    chart.render(output_file)
    print(f"✓ 图表已保存: {output_file}")
    
    # 6. 分析统计
    print(f"\n{'='*60}")
    print("分析统计:")
    print(f"{'='*60}")
    print(f"股票代码: {symbol}")
    print(f"股票名称: {name}")
    print(f"分析周期: 日线")
    print(f"K线数量: {len(bars)}")
    print(f"分型数量: {len(czsc_obj.fx_list)}")
    print(f"笔数量: {len(czsc_obj.bi_list)}")
    print(f"图表文件: {output_file}")
    print(f"{'='*60}\n")
    
    return czsc_obj, output_file


def analyze_multiple_stocks():
    """分析多只股票"""
    stocks = [
        ("000001", "平安银行"),
        ("000002", "万科A"),
        ("000858", "五粮液"),
    ]
    
    for symbol, name in stocks:
        try:
            analyze_with_mock(symbol, name)
        except Exception as e:
            print(f"分析 {name} ({symbol}) 时出错: {e}")


def analyze_with_real_data(symbol="000001"):
    """
    使用真实股票数据（需要安装 akshare）
    pip install akshare
    """
    try:
        import akshare as ak
    except ImportError:
        print("请先安装 akshare: pip install akshare")
        return
    
    print(f"\n使用真实数据获取: {symbol}")
    
    # 获取股票数据
    df = ak.stock_zh_a_hist(symbol, period="daily", 
                           start_date="20220101", end_date="20240101")
    
    # 转换列名
    df.rename(columns={
        "日期": "dt",
        "开盘": "open",
        "收盘": "close",
        "最高": "high",
        "最低": "low",
        "成交量": "vol"
    }, inplace=True)
    
    # 转换为 bars
    bars = format_standard_kline(df, freq=Freq.D)
    
    # 缠论分析
    czsc_obj = CZSC(bars, max_bi_num=1000)
    
    # ... 绘图代码同上
    print(f"真实数据分析完成: 共 {len(bars)} 根K线")


if __name__ == "__main__":
    # 分析单只股票
    analyze_with_mock("000001", "平安银行")
    
    # 分析多只股票
    # analyze_multiple_stocks()
    
    # 使用真实数据（需要安装 akshare）
    # analyze_with_real_data("000001")
