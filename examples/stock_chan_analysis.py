# -*- coding: utf-8 -*-
"""
股票缠论图形分析示例

本示例展示如何对股票进行缠论分析并可视化
仅使用真实股票数据（优先 yfinance，A股代码支持回退 akshare）

author: czsc
"""
import argparse
import os
from datetime import datetime, timedelta
import re
import sys
import pandas as pd
import warnings
import time
from contextlib import contextmanager

# Hide noisy dependency mismatch warning from local requests installation
warnings.filterwarnings(
    "ignore",
    message=r".*urllib3 .* doesn't match a supported version.*",
)

from czsc import CZSC, Freq, format_standard_kline
from czsc.utils.echarts_plot import kline_pro


if hasattr(sys.stdout, "reconfigure"):
    # Avoid Windows console encoding crashes (e.g., gbk can't encode some symbols)
    sys.stdout.reconfigure(errors="replace")


def validate_yyyymmdd(date_str: str):
    """校验日期格式 YYYYMMDD"""
    datetime.strptime(date_str, "%Y%m%d")


def to_hk_code(symbol: str) -> str:
    """将港股代码规范化为 akshare 所需格式，例如 9988.HK -> 09988"""
    s = symbol.strip().upper()
    m = re.fullmatch(r"(\d{4,5})(?:\.HK)?", s)
    if not m:
        return ""
    return m.group(1).zfill(5)


@contextmanager
def without_proxy_env():
    """临时禁用环境代理，避免本机代理断开导致行情源不可用。"""
    proxy_vars = [
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ]
    old_values = {k: os.environ.get(k) for k in proxy_vars}
    for key in proxy_vars:
        os.environ.pop(key, None)
    try:
        yield
    finally:
        for key, value in old_values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _looks_like_proxy_error(error: Exception) -> bool:
    text = repr(error).lower()
    return "proxy" in text or "remote end closed connection" in text


def _fetch_akshare_hk(symbol: str, hk_symbol: str, sdt: str, edt: str) -> pd.DataFrame:
    import akshare as ak

    df = ak.stock_hk_hist(
        symbol=hk_symbol,
        period="daily",
        start_date=sdt,
        end_date=edt,
        adjust="",
    )
    if df is None or df.empty:
        raise RuntimeError(f"akshare 港股无数据: {symbol}")

    df.rename(
        columns={
            "日期": "dt",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "vol",
            "成交额": "amount",
        },
        inplace=True,
    )
    df["dt"] = pd.to_datetime(df["dt"])
    df["symbol"] = symbol
    if "amount" not in df.columns:
        df["amount"] = df["vol"] * df["close"]
    return df


def _fetch_akshare_a(symbol: str, symbol_clean: str, sdt: str, edt: str) -> pd.DataFrame:
    import akshare as ak

    df = ak.stock_zh_a_hist(
        symbol=symbol_clean,
        period="daily",
        start_date=sdt,
        end_date=edt,
        adjust="",
    )
    if df is None or df.empty:
        raise RuntimeError(f"akshare 无数据: {symbol}")

    df.rename(
        columns={
            "日期": "dt",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "vol",
            "成交额": "amount",
        },
        inplace=True,
    )
    df["dt"] = pd.to_datetime(df["dt"])
    df["symbol"] = symbol
    if "amount" not in df.columns:
        df["amount"] = df["vol"] * df["close"]
    return df


def get_real_kline_df(symbol: str, sdt: str, edt: str) -> pd.DataFrame:
    """获取真实行情数据：港股优先 akshare，其余优先 yfinance，A股可回退 akshare"""
    errors = []
    symbol = symbol.strip()
    if not symbol:
        raise ValueError("股票代码不能为空")

    upper_symbol = symbol.upper()
    is_hk = bool(re.fullmatch(r"\d{4,5}\.HK", upper_symbol))

    # 1) 港股优先 akshare（避免 yfinance 限流）
    if is_hk:
        hk_symbol = to_hk_code(upper_symbol)
        if hk_symbol:
            try:
                return _fetch_akshare_hk(symbol, hk_symbol, sdt, edt)
            except Exception as e:
                errors.append(f"akshare 港股失败: {e}")
                if _looks_like_proxy_error(e):
                    try:
                        with without_proxy_env():
                            return _fetch_akshare_hk(symbol, hk_symbol, sdt, edt)
                    except Exception as retry_error:
                        errors.append(f"akshare 港股关闭代理后仍失败: {retry_error}")
        else:
            errors.append(f"港股代码格式错误: {symbol}")

    # 2) yfinance（适合港股/美股/带后缀A股）
    try:
        import yfinance as yf

        yf_symbol = upper_symbol
        start_dt = datetime.strptime(sdt, "%Y%m%d").strftime("%Y-%m-%d")
        # yfinance 的 end 是开区间，所以 +1 天确保包含 edt 当天
        end_dt = (datetime.strptime(edt, "%Y%m%d") + timedelta(days=1)).strftime("%Y-%m-%d")

        # 纯6位A股代码对 yfinance 不友好，交给 akshare
        if not re.fullmatch(r"\d{6}", yf_symbol):
            for i in range(3):
                try:
                    df = yf.Ticker(yf_symbol).history(start=start_dt, end=end_dt, auto_adjust=False)
                except Exception as e:
                    if not _looks_like_proxy_error(e):
                        raise
                    with without_proxy_env():
                        df = yf.Ticker(yf_symbol).history(start=start_dt, end=end_dt, auto_adjust=False)
                if df is not None and not df.empty:
                    df = df.reset_index()
                    df.rename(
                        columns={
                            "Date": "dt",
                            "Open": "open",
                            "Close": "close",
                            "High": "high",
                            "Low": "low",
                            "Volume": "vol",
                        },
                        inplace=True,
                    )
                    df["dt"] = pd.to_datetime(df["dt"]).dt.tz_localize(None)
                    df["symbol"] = symbol
                    if "amount" not in df.columns:
                        df["amount"] = df["vol"] * df["close"]
                    return df
                if i < 2:
                    time.sleep(1.5 * (i + 1))
            errors.append(f"yfinance 无数据: {symbol}")
    except Exception as e:
        errors.append(f"yfinance 失败: {e}")

    # 3) 回退 akshare（主要用于A股6位代码，或 .SS/.SZ）
    symbol_clean = upper_symbol.replace(".SS", "").replace(".SZ", "")
    if re.fullmatch(r"\d{6}", symbol_clean):
        try:
            return _fetch_akshare_a(symbol, symbol_clean, sdt, edt)
        except Exception as e:
            errors.append(f"akshare 失败: {e}")
            if _looks_like_proxy_error(e):
                try:
                    with without_proxy_env():
                        return _fetch_akshare_a(symbol, symbol_clean, sdt, edt)
                except Exception as retry_error:
                    errors.append(f"akshare 关闭代理后仍失败: {retry_error}")
    else:
        errors.append(f"akshare A股接口不支持该代码格式: {symbol}")

    raise RuntimeError("获取真实行情失败；" + " | ".join(errors))


def make_html_fullscreen(output_file: str):
    """将输出 HTML 的图表区域调整为浏览器全屏显示"""
    abs_output = os.path.abspath(output_file)
    with open(abs_output, "r", encoding="utf-8") as f:
        html_text = f.read()

    html_text, _ = re.subn(
        r'style="width:\s*[^;"]+;\s*height:\s*[^;"]+;"',
        'style="width: 100vw; height: 100vh;"',
        html_text,
        count=1,
    )

    if "<head>" in html_text:
        html_text = html_text.replace(
            "<head>",
            "<head>\n<style>html, body {width: 100%; height: 100%; margin: 0; padding: 0; overflow: hidden;}</style>",
            1,
        )

    with open(abs_output, "w", encoding="utf-8") as f:
        f.write(html_text)


def analyze_with_real_data(symbol="000001", name="平安银行", sdt="20220101", edt="20240101", output_dir="output/chanAnalysis"):
    """
    使用真实数据进行缠论分析
    
    :param symbol: 股票代码
    :param name: 股票名称
    """
    print(f"\n{'='*60}")
    print(f"开始分析: {name} ({symbol})")
    print(f"{'='*60}\n")
    
    validate_yyyymmdd(sdt)
    validate_yyyymmdd(edt)
    if sdt >= edt:
        raise ValueError(f"开始日期必须早于结束日期：sdt={sdt}, edt={edt}")

    # 1. 获取真实K线数据（日线）
    print("步骤1: 获取K线数据...")
    df = get_real_kline_df(symbol=symbol, sdt=sdt, edt=edt)
    bars = format_standard_kline(df, freq=Freq.D)
    print(f"[OK] 获取到 {len(bars)} 根K线")
    
    # 2. 进行缠论分析
    print("\n步骤2: 进行缠论分析...")
    czsc_obj = CZSC(bars, max_bi_num=1000)
    print(f"[OK] 分析完成")
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
        "fx_mark": fx.mark.value
    } for fx in czsc_obj.fx_list]
    
    # 笔数据（连接笔的起点和终点）
    bi_data = []
    for bi in czsc_obj.bi_list:
        bi_data.append({"dt": bi.fx_a.dt, "bi": bi.fx_a.fx})
        bi_data.append({"dt": bi.fx_b.dt, "bi": bi.fx_b.fx})
    
    print(f"[OK] 数据准备完成")
    
    # 4. 绘制图表
    print("\n步骤4: 生成可视化图表...")
    chart = kline_pro(
        kline=kline_data,
        fx=fx_data,
        bi=bi_data,
        title=f"{name} ({symbol}) 缠论分析",
        t_seq=[5, 10, 20, 60],  # 5日、10日、20日、60日均线
        width="100vw",
        height="100vh"
    )
    
    # 5. 保存图表
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{symbol}_{name}_{sdt}_{edt}_缠论分析.html")
    chart.render(output_file)
    make_html_fullscreen(output_file)
    abs_output = os.path.abspath(output_file)
    print(f"[OK] 图表已保存: {abs_output}")
    print(f"OUTPUT_HTML={abs_output}")
    
    # 6. 分析统计
    print(f"\n{'='*60}")
    print("分析统计:")
    print(f"{'='*60}")
    print(f"股票代码: {symbol}")
    print(f"股票名称: {name}")
    print(f"分析周期: 日线")
    print(f"日期区间: {sdt} - {edt}")
    print(f"K线数量: {len(bars)}")
    print(f"分型数量: {len(czsc_obj.fx_list)}")
    print(f"笔数量: {len(czsc_obj.bi_list)}")
    print(f"图表文件: {output_file}")
    print(f"{'='*60}\n")
    
    return czsc_obj, output_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="股票缠论图形分析（真实数据）")
    parser.add_argument("--symbol", default="603259", help="股票代码，例如 603259")
    parser.add_argument("--name", default="药明康德", help="股票名称，用于图表标题")
    parser.add_argument("--sdt", default="20220101", help="开始日期，格式 YYYYMMDD")
    parser.add_argument("--edt", default="20240101", help="结束日期，格式 YYYYMMDD")
    parser.add_argument("--output-dir", default="output/chanAnalysis", help="输出目录")
    args = parser.parse_args()

    print("使用真实数据进行缠论分析")
    analyze_with_real_data(
        symbol=args.symbol,
        name=args.name,
        sdt=args.sdt,
        edt=args.edt,
        output_dir=args.output_dir,
    )
