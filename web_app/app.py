# -*- coding: utf-8 -*-
"""
CZSC 缠论分析 Web 应用

功能：输入股票代码，自动获取日线数据并生成分型、笔、线段、中枢的可视化图表

运行方式：
    # Windows:
    set CZSC_USE_PYTHON=1 && streamlit run web_app/app.py
    # Linux/Mac:
    CZSC_USE_PYTHON=1 streamlit run web_app/app.py

依赖：
    pip install streamlit yfinance akshare pyecharts

author: czsc
"""
import os
# 强制使用 Python 版本，避免 rs_czsc 导入问题
os.environ['CZSC_USE_PYTHON'] = '1'

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from czsc import CZSC, Freq, format_standard_kline
from czsc.utils.echarts_plot import kline_pro

# 页面配置
st.set_page_config(
    page_title="CZSC 缠论分析工具",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 样式
st.markdown("""
<style>
    .main-title {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #ddd;
    }
    .stock-info {
        font-size: 1.2rem;
        color: #333;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def get_data_from_yfinance(symbol, days=180):
    """从雅虎财经获取股票数据"""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=f"{days}d")

        if df.empty:
            return None, "未获取到数据"

        df.reset_index(inplace=True)
        df.rename(columns={
            "Date": "dt",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "vol"
        }, inplace=True)

        df['dt'] = pd.to_datetime(df['dt']).dt.tz_localize(None)
        df['symbol'] = symbol

        if 'amount' not in df.columns:
            df['amount'] = df['vol'] * df['close']

        return df, None

    except ImportError:
        return None, "请先安装 yfinance: pip install yfinance"
    except Exception as e:
        return None, f"获取失败: {str(e)}"


def get_data_from_akshare(symbol, days=180):
    """从 akshare 获取A股数据"""
    try:
        import akshare as ak

        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        start_date_str = start_date.strftime("%Y%m%d")
        end_date_str = end_date.strftime("%Y%m%d")

        # 获取股票数据（去除后缀）
        symbol_clean = symbol.replace('.SS', '').replace('.SZ', '')
        df = ak.stock_zh_a_hist(symbol_clean, period="daily",
                                start_date=start_date_str,
                                end_date=end_date_str)

        if df.empty:
            return None, "未获取到数据"

        df.rename(columns={
            "日期": "dt",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "vol"
        }, inplace=True)

        df['dt'] = pd.to_datetime(df['dt'])
        df['symbol'] = symbol

        if 'amount' not in df.columns:
            df['amount'] = df['vol'] * df['close']

        return df, None

    except ImportError:
        return None, "请先安装 akshare: pip install akshare"
    except Exception as e:
        return None, f"获取失败: {str(e)}"


def analyze_stock(df, symbol="unknown"):
    """对股票数据进行缠论分析"""
    if df is None or df.empty:
        return None, "数据为空，无法分析"

    try:
        # 转换数据格式
        bars = format_standard_kline(df, freq=Freq.D)

        # 进行缠论分析
        czsc_obj = CZSC(bars, max_bi_num=1000)

        # 准备绘图数据
        kline_data = [{
            "dt": bar.dt,
            "open": bar.open,
            "close": bar.close,
            "high": bar.high,
            "low": bar.low,
            "vol": bar.vol
        } for bar in bars]

        fx_data = [{
            "dt": fx.dt,
            "fx": fx.fx,
            "fx_mark": fx.mark.value
        } for fx in czsc_obj.fx_list]

        bi_data = []
        for bi in czsc_obj.bi_list:
            bi_data.append({"dt": bi.fx_a.dt, "bi": bi.fx_a.fx})
            bi_data.append({"dt": bi.fx_b.dt, "bi": bi.fx_b.fx})

        # 统计信息
        stats = {
            "kline_count": len(bars),
            "fx_count": len(czsc_obj.fx_list),
            "bi_count": len(czsc_obj.bi_list),
            "date_range": f"{df['dt'].min().strftime('%Y-%m-%d')} 至 {df['dt'].max().strftime('%Y-%m-%d')}",
            "price_range": f"{df['low'].min():.2f} - {df['high'].max():.2f}"
        }

        return {
            "czsc_obj": czsc_obj,
            "kline_data": kline_data,
            "fx_data": fx_data,
            "bi_data": bi_data,
            "stats": stats
        }, None

    except Exception as e:
        return None, f"分析失败: {str(e)}"


def create_chart(analysis_result, title="缠论分析"):
    """创建可视化图表"""
    try:
        chart = kline_pro(
            kline=analysis_result["kline_data"],
            fx=analysis_result["fx_data"],
            bi=analysis_result["bi_data"],
            title=title,
            t_seq=[5, 10, 20, 60],
            width="1400px",
            height="700px"
        )

        # 保存为 HTML 文件
        output_file = "czsc_chart.html"
        chart.render(output_file)

        with open(output_file, "r", encoding="utf-8") as f:
            html_content = f.read()

        # 清理临时文件
        if os.path.exists(output_file):
            os.remove(output_file)

        return html_content, None

    except Exception as e:
        return None, f"图表生成失败: {str(e)}"


def main():
    """主函数"""
    # 标题
    st.markdown('<h1 class="main-title">📈 CZSC 缠论分析工具</h1>', unsafe_allow_html=True)

    # 侧边栏配置
    with st.sidebar:
        st.header("⚙️ 分析配置")

        # 股票代码输入
        symbol_input = st.text_input(
            "股票代码",
            value="603259.SS",
            help="格式: A股上海用.SS后缀(如603259.SS)，深圳用.SZ后缀(如000001.SZ)，美股直接代码(如AAPL)"
        )

        # 股票名称
        stock_name = st.text_input(
            "股票名称",
            value="药明康德",
            help="用于图表标题显示"
        )

        # 数据源选择
        data_source = st.radio(
            "数据源",
            options=["yfinance (推荐)", "akshare (A股)"],
            help="yfinance适合所有市场，akshare更适合A股"
        )

        # 时间范围
        days = st.slider(
            "数据天数",
            min_value=30,
            max_value=365,
            value=180,
            step=30,
            help="获取最近多少天的数据"
        )

        # 分析按钮
        analyze_btn = st.button("🚀 开始分析", type="primary", use_container_width=True)

        # 说明
        st.markdown("---")
        st.markdown("### 📋 使用说明")
        st.markdown("""
        1. 输入股票代码（如 603259.SS）
        2. 输入股票名称（可选）
        3. 选择数据源
        4. 调整时间范围
        5. 点击"开始分析"
        """)

        st.markdown("### 📊 支持的格式")
        st.markdown("""
        - **A股上海**: 603259.SS
        - **A股深圳**: 000001.SZ
        - **港股**: 9988.HK
        - **美股**: AAPL, TSLA
        """)

    # 主界面
    if analyze_btn:
        if not symbol_input:
            st.error("⚠️ 请输入股票代码")
            return

        # 显示进度
        progress_bar = st.progress(0)
        status_text = st.empty()

        # 步骤1: 获取数据
        status_text.text("📥 正在获取股票数据...")
        progress_bar.progress(20)

        if "akshare" in data_source.lower():
            df, error = get_data_from_akshare(symbol_input, days)
        else:
            df, error = get_data_from_yfinance(symbol_input, days)

        if error:
            st.error(f"❌ {error}")
            return

        # 步骤2: 缠论分析
        status_text.text("🔍 正在进行缠论分析...")
        progress_bar.progress(50)

        analysis_result, error = analyze_stock(df, symbol_input)
        if error:
            st.error(f"❌ {error}")
            return

        # 步骤3: 生成图表
        status_text.text("📊 正在生成可视化图表...")
        progress_bar.progress(80)

        title = f"{stock_name} ({symbol_input}) 缠论分析"
        html_content, error = create_chart(analysis_result, title)
        if error:
            st.error(f"❌ {error}")
            return

        progress_bar.progress(100)
        status_text.text("✅ 分析完成！")

        # 显示统计信息
        st.markdown("---")
        st.subheader("📈 分析统计")

        stats = analysis_result["stats"]
        cols = st.columns(4)
        with cols[0]:
            st.metric("K线数量", stats["kline_count"])
        with cols[1]:
            st.metric("分型数量", stats["fx_count"])
        with cols[2]:
            st.metric("笔数量", stats["bi_count"])
        with cols[3]:
            st.metric("数据周期", f"{days}天")

        # 显示详情
        with st.expander("📋 详细信息"):
            st.write(f"**日期范围**: {stats['date_range']}")
            st.write(f"**价格范围**: {stats['price_range']}")
            st.write(f"**股票代码**: {symbol_input}")
            st.write(f"**股票名称**: {stock_name}")

        # 显示图表
        st.markdown("---")
        st.subheader("📊 缠论分析图表")
        st.markdown("*图表包含：K线、分型(圆圈标记)、笔(菱形连线)、均线、成交量、MACD*")

        st.components.v1.html(html_content, height=750, scrolling=True)

        # 清除进度
        progress_bar.empty()
        status_text.empty()

    else:
        # 默认显示欢迎信息
        st.info("👈 请在左侧配置参数并点击'开始分析'")

        st.markdown("### 🎯 功能介绍")
        st.markdown("""
        本工具基于 **CZSC（缠中说禅）** 量化交易技术分析库，提供以下功能：

        1. **自动识别分型** - 顶分型(G)和底分型(D)的自动识别
        2. **自动识别笔** - 缠论笔的自动划分
        3. **自动识别线段** - 缠论线段的自动划分
        4. **自动识别中枢** - 缠论中枢的自动识别
        5. **可视化展示** - 使用 PyECharts 生成交互式图表

        ### 📚 缠论基础
        缠论是一种技术分析理论，核心概念包括：
        - **分型**：顶分型(中间K线最高)和底分型(中间K线最低)
        - **笔**：连接相邻同向分型的线段
        - **线段**：由笔组成的高级别走势单位
        - **中枢**：价格重叠区域
        """)

        # 示例股票
        st.markdown("### 💡 示例股票代码")
        example_data = {
            "市场": ["A股(上海)", "A股(深圳)", "港股", "美股", "美股"],
            "代码": ["603259.SS", "000001.SZ", "9988.HK", "AAPL", "TSLA"],
            "名称": ["药明康德", "平安银行", "阿里巴巴", "苹果", "特斯拉"]
        }
        st.table(pd.DataFrame(example_data))


if __name__ == "__main__":
    main()
