# -*- coding: utf-8 -*-
"""
获取真实股票数据并进行缠论分析

使用 yfinance 获取A股数据
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from czsc import CZSC, Freq, format_standard_kline
from czsc.utils.echarts_plot import kline_pro


def get_stock_data(symbol="603259.SS", name="药明康德", days=90):
    """从雅虎财经获取股票数据"""
    print(f"\n{'='*60}")
    print(f"获取股票数据: {name} ({symbol})")
    print(f"{'='*60}\n")
    
    try:
        import os
        # 设置缓存目录
        cache_dir = os.path.join(os.getcwd(), '.yfinance_cache')
        os.makedirs(cache_dir, exist_ok=True)
        yf.set_tz_cache_location(cache_dir)
        
        # 下载数据
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=f"{days}d", auto_adjust=False)
        
        if df.empty:
            print("✗ 未获取到数据")
            return None
        
        # 重置索引
        df.reset_index(inplace=True)
        
        # 转换列名
        df.columns = [c.lower().replace(' ', '_') for c in df.columns]
        
        # 转换日期
        df['dt'] = pd.to_datetime(df['date'] if 'date' in df.columns else df['datetime'])
        df['dt'] = df['dt'].dt.tz_localize(None)
        
        # 确保列名正确
        column_mapping = {
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'vol'
        }
        df.rename(columns=column_mapping, inplace=True)
        
        # 添加必要列
        df['symbol'] = symbol
        df['amount'] = df['vol'] * df['close']
        
        print(f"✓ 成功获取 {len(df)} 条数据")
        print(f"  日期范围: {df['dt'].min().strftime('%Y-%m-%d')} 至 {df['dt'].max().strftime('%Y-%m-%d')}")
        print(f"  价格范围: {df['low'].min():.2f} - {df['high'].max():.2f}")
        print(f"\n数据预览:")
        print(df[['dt', 'open', 'high', 'low', 'close', 'vol']].head())
        
        return df
        
    except Exception as e:
        print(f"✗ 获取失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def analyze_and_plot(df, symbol="603259", name="药明康德"):
    """进行缠论分析并生成图表"""
    print(f"\n{'='*60}")
    print(f"缠论分析: {name} ({symbol})")
    print(f"{'='*60}\n")
    
    # 转换数据
    print("步骤1: 转换数据格式...")
    bars = format_standard_kline(df, freq=Freq.D)
    print(f"✓ 共 {len(bars)} 根K线")
    
    # 缠论分析
    print("\n步骤2: 进行缠论分析...")
    czsc_obj = CZSC(bars, max_bi_num=1000)
    print(f"✓ 分型数量: {len(czsc_obj.fx_list)}")
    print(f"✓ 笔数量: {len(czsc_obj.bi_list)}")
    
    # 准备绘图数据
    print("\n步骤3: 准备绘图数据...")
    kline_data = [{
        "dt": bar.dt,
        "open": bar.open,
        "close": bar.close,
        "high": bar.high,
        "low": bar.low,
        "vol": bar.vol
    } for bar in bars]
    
    fx_data = [{"dt": fx.dt, "fx": fx.fx, "fx_mark": fx.mark.value} 
               for fx in czsc_obj.fx_list]
    
    bi_data = []
    for bi in czsc_obj.bi_list:
        bi_data.append({"dt": bi.fx_a.dt, "bi": bi.fx_a.fx})
        bi_data.append({"dt": bi.fx_b.dt, "bi": bi.fx_b.fx})
    
    # 生成图表
    print("\n步骤4: 生成图表...")
    chart = kline_pro(
        kline=kline_data,
        fx=fx_data,
        bi=bi_data,
        title=f"{name} ({symbol}) 缠论分析 - 真实数据",
        t_seq=[5, 10, 20],
        width="1400px",
        height="700px"
    )
    
    # 保存
    output_file = f"{symbol.replace('.', '_')}_{name}_真实数据缠论分析.html"
    chart.render(output_file)
    print(f"✓ 图表已保存: {output_file}")
    
    # 统计
    print(f"\n{'='*60}")
    print("分析统计")
    print(f"{'='*60}")
    print(f"股票: {name} ({symbol})")
    print(f"K线数: {len(bars)}")
    print(f"分型数: {len(czsc_obj.fx_list)}")
    print(f"笔数: {len(czsc_obj.bi_list)}")
    print(f"文件: {output_file}")
    print(f"{'='*60}\n")
    
    return czsc_obj, output_file


if __name__ == "__main__":
    print("="*60)
    print("股票缠论分析 - 使用雅虎财经真实数据")
    print("="*60)
    
    # 导入股票配置
    from stock_config import get_stock_info, list_all_stocks
    
    # 显示所有可用股票
    # list_all_stocks()
    
    # 选择要分析的股票
    # 港股: 9988.HK(阿里巴巴), 0700.HK(腾讯), 3690.HK(美团)
    # A股: 603259.SS(药明康德), 600519.SS(茅台)
    # 美股: BABA(阿里), JD(京东)
    
    symbol = "9988.HK"  # 阿里巴巴港股
    days = 90  # 近3个月
    
    # 自动获取股票名称
    symbol, name = get_stock_info(symbol)
    
    print(f"\n分析股票: {name} ({symbol})")
    
    # 获取数据
    df = get_stock_data(symbol, name, days)
    
    if df is not None:
        # 分析并生成图表
        analyze_and_plot(df, symbol, name)
    else:
        print("\n✗ 数据获取失败，请检查网络连接或股票代码")
