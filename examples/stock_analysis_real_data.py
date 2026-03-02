# -*- coding: utf-8 -*-
"""
使用真实数据的股票缠论分析

支持多个数据源:
1. yfinance (雅虎财经) - 推荐，无需API Key
2. baostock - 需要登录
3. 本地CSV文件
4. akshare - 可能需要处理反爬机制

author: czsc
"""
from czsc import CZSC, Freq, format_standard_kline
from czsc.utils.echarts_plot import kline_pro
from datetime import datetime, timedelta
import pandas as pd


def get_data_from_yfinance(symbol="603259.SS", name="药明康德", days=90):
    """
    从雅虎财经获取A股数据
    A股代码格式: 603259.SS (上海) 或 000001.SZ (深圳)
    
    优点:
    - 无需API Key
    - 国际通用
    - 稳定性较好
    """
    print(f"\n{'='*60}")
    print(f"从雅虎财经获取数据: {name} ({symbol})")
    print(f"{'='*60}\n")
    
    try:
        import yfinance as yf
        
        # 获取数据
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=f"{days}d")
        
        if df.empty:
            print("✗ 未获取到数据")
            return None
        
        # 重置索引，将日期变为列
        df.reset_index(inplace=True)
        
        # 转换列名以匹配 czsc 格式
        df.rename(columns={
            "Date": "dt",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "vol"
        }, inplace=True)
        
        # 转换日期格式
        df['dt'] = pd.to_datetime(df['dt']).dt.tz_localize(None)
        
        # 添加必要的列
        df['symbol'] = symbol
        if 'amount' not in df.columns:
            # 计算成交额 (成交量 * 收盘价)
            df['amount'] = df['vol'] * df['close']
        
        print(f"✓ 成功获取 {len(df)} 条数据")
        print(f"  日期范围: {df['dt'].min()} 至 {df['dt'].max()}")
        print(f"  价格范围: {df['low'].min():.2f} - {df['high'].max():.2f}")
        
        return df
        
    except ImportError:
        print("✗ 请先安装 yfinance: pip install yfinance")
        return None
    except Exception as e:
        print(f"✗ 获取失败: {e}")
        return None


def get_data_from_csv(filepath, symbol="603259", name="药明康德"):
    """
    从本地CSV文件读取数据
    
    CSV格式要求:
    - 必须包含列: dt, open, high, low, close, vol
    - dt 格式: YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS
    """
    print(f"\n{'='*60}")
    print(f"从CSV文件读取数据: {filepath}")
    print(f"{'='*60}\n")
    
    try:
        df = pd.read_csv(filepath)
        
        # 检查必要列
        required_cols = ['dt', 'open', 'high', 'low', 'close', 'vol']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            print(f"✗ CSV文件缺少必要列: {missing_cols}")
            return None
        
        # 转换日期格式
        df['dt'] = pd.to_datetime(df['dt'])
        
        print(f"✓ 成功读取 {len(df)} 条数据")
        print(f"  日期范围: {df['dt'].min()} 至 {df['dt'].max()}")
        
        return df
        
    except Exception as e:
        print(f"✗ 读取失败: {e}")
        return None


def analyze_stock(df, symbol="603259", name="药明康德"):
    """
    对股票数据进行缠论分析并生成图表
    
    :param df: DataFrame 包含 dt, open, high, low, close, vol 列
    :param symbol: 股票代码
    :param name: 股票名称
    """
    if df is None or df.empty:
        print("✗ 数据为空，无法分析")
        return None, None
    
    print(f"\n{'='*60}")
    print(f"开始缠论分析: {name} ({symbol})")
    print(f"{'='*60}\n")
    
    # 1. 转换数据格式
    print("步骤1: 转换数据格式...")
    bars = format_standard_kline(df, freq=Freq.D)
    print(f"✓ 转换完成，共 {len(bars)} 根K线")
    
    # 2. 进行缠论分析
    print("\n步骤2: 进行缠论分析...")
    czsc_obj = CZSC(bars, max_bi_num=1000)
    print(f"✓ 分析完成")
    print(f"  - 分型数量: {len(czsc_obj.fx_list)}")
    print(f"  - 笔数量: {len(czsc_obj.bi_list)}")
    
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
        "fx_mark": fx.mark.value
    } for fx in czsc_obj.fx_list]
    
    # 笔数据
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
        t_seq=[5, 10, 20],  # 5日、10日、20日均线
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


def create_sample_csv():
    """
    创建示例CSV文件，展示数据格式
    """
    sample_data = {
        'dt': ['2024-12-01', '2024-12-02', '2024-12-03'],
        'open': [50.0, 51.0, 50.5],
        'high': [52.0, 52.5, 51.5],
        'low': [49.5, 50.0, 49.8],
        'close': [51.0, 50.5, 51.2],
        'vol': [100000, 120000, 90000]
    }
    df = pd.DataFrame(sample_data)
    df.to_csv('sample_stock_data.csv', index=False)
    print("✓ 示例CSV文件已创建: sample_stock_data.csv")
    print("  格式: dt, open, high, low, close, vol")


if __name__ == "__main__":
    print("="*60)
    print("股票缠论分析 - 真实数据版本")
    print("="*60)
    
    # 方法1: 使用 yfinance (推荐)
    print("\n>>> 方法1: 使用 yfinance 获取数据")
    df = get_data_from_yfinance("603259.SS", "药明康德", days=90)
    
    if df is not None:
        analyze_stock(df, "603259", "药明康德")
    else:
        print("\n>>> yfinance 获取失败，尝试其他方法...")
        
        # 方法2: 使用本地CSV
        print("\n>>> 方法2: 使用本地CSV文件")
        print("请准备CSV文件，格式如下:")
        print("dt,open,high,low,close,vol")
        print("2024-12-01,50.0,52.0,49.5,51.0,100000")
        print("...")
        
        # 创建示例CSV
        create_sample_csv()
        
        # 如果有CSV文件，取消下面注释
        # df = get_data_from_csv("your_data.csv", "603259", "药明康德")
        # if df is not None:
        #     analyze_stock(df, "603259", "药明康德")
