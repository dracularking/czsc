# -*- coding: utf-8 -*-
"""
测试不同的数据源获取方式
"""
import pandas as pd
from datetime import datetime, timedelta

def test_akshare():
    """测试 akshare"""
    print("="*60)
    print("测试 akshare 数据源")
    print("="*60)
    
    try:
        import akshare as ak
        
        # 方法1: 使用 stock_zh_a_hist
        print("\n方法1: stock_zh_a_hist")
        df = ak.stock_zh_a_hist("603259", period="daily", 
                                start_date="20241201", end_date="20250301",
                                timeout=30)
        print(f"✓ 成功获取 {len(df)} 条数据")
        print(df.head())
        return df
        
    except Exception as e:
        print(f"✗ 失败: {e}")
        return None

def test_yfinance():
    """测试 yfinance (雅虎财经)"""
    print("\n" + "="*60)
    print("测试 yfinance 数据源")
    print("="*60)
    
    try:
        import yfinance as yf
        
        # 药明康德在A股的代码是 603259.SS
        ticker = yf.Ticker("603259.SS")
        df = ticker.history(period="3mo")
        
        print(f"✓ 成功获取 {len(df)} 条数据")
        print(df.head())
        return df
        
    except Exception as e:
        print(f"✗ 失败: {e}")
        return None

def test_baostock():
    """测试 baostock"""
    print("\n" + "="*60)
    print("测试 baostock 数据源")
    print("="*60)
    
    try:
        import baostock as bs
        
        # 登录
        lg = bs.login()
        print(f"登录结果: {lg.error_code} - {lg.error_msg}")
        
        # 获取数据
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        
        rs = bs.query_history_k_data_plus("sh.603259",
            "date,code,open,high,low,close,volume",
            start_date=start_date, end_date=end_date,
            frequency="d")
        
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        
        df = pd.DataFrame(data_list, columns=rs.fields)
        print(f"✓ 成功获取 {len(df)} 条数据")
        print(df.head())
        
        bs.logout()
        return df
        
    except Exception as e:
        print(f"✗ 失败: {e}")
        return None

def test_tushare():
    """测试 tushare"""
    print("\n" + "="*60)
    print("测试 tushare 数据源")
    print("="*60)
    
    try:
        import tushare as ts
        
        # 需要设置 token
        # ts.set_token('your_token_here')
        pro = ts.pro_api()
        
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")
        
        df = pro.daily(ts_code="603259.SH", 
                      start_date=start_date, 
                      end_date=end_date)
        
        print(f"✓ 成功获取 {len(df)} 条数据")
        print(df.head())
        return df
        
    except Exception as e:
        print(f"✗ 失败: {e}")
        return None

if __name__ == "__main__":
    # 测试所有数据源
    print("测试多个数据源获取药明康德(603259)数据\n")
    
    # 1. 测试 akshare
    df_akshare = test_akshare()
    
    # 2. 测试 yfinance
    # df_yf = test_yfinance()
    
    # 3. 测试 baostock
    # df_bs = test_baostock()
    
    # 4. 测试 tushare (需要token)
    # df_ts = test_tushare()
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
