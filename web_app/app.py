# -*- coding: utf-8 -*-
"""
CZSC Chan analysis web workspace.

Run:
    streamlit run web_app/app.py
"""
import json
import os
import re
import sys
import base64
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


os.environ["CZSC_USE_PYTHON"] = "1"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from czsc import CZSC, Freq, format_standard_kline
from czsc.utils.echarts_plot import kline_pro
from examples.stock_chan_analysis import get_real_kline_df, validate_yyyymmdd


COLLECTION_FILE = ROOT / ".chanAnalysisStockCollection.json"
DEFAULT_COLLECTION = [
    {"symbol": "9988.HK", "name": "Alibaba-W", "market": "HK"},
    {"symbol": "603259", "name": "Wuxi AppTec", "market": "A"},
    {"symbol": "000001.SZ", "name": "Ping An Bank", "market": "A"},
    {"symbol": "AAPL", "name": "Apple", "market": "US"},
]


st.set_page_config(
    page_title="CZSC Chan Analysis",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)


st.markdown(
    """
<style>
    :root {
        --bg: #f6f8fb;
        --ink: #17202a;
        --muted: #667085;
        --line: #d9e0ea;
        --accent: #0f9f6e;
        --accent-dark: #087452;
        --panel: #ffffff;
        --soft: #edf7f3;
    }
    .stApp {
        background:
            radial-gradient(circle at 8% 4%, rgba(15, 159, 110, .08), transparent 30%),
            linear-gradient(180deg, #fbfcfe 0%, var(--bg) 42%, #eef3f8 100%);
        color: var(--ink);
    }
    [data-testid="stSidebar"], .stDeployButton, [data-testid="stToolbar"] {
        display: none;
    }
    .block-container {
        padding: 24px 34px 32px;
        max-width: 1540px;
    }
    h1, h2, h3, p {
        letter-spacing: 0;
    }
    h1 {
        font-size: 30px !important;
        line-height: 1.18 !important;
        margin: 0 0 6px !important;
        color: #10243a;
    }
    h2 {
        font-size: 18px !important;
        line-height: 1.3 !important;
        margin: 0 0 12px !important;
        color: #10243a;
    }
    .app-subtitle {
        color: var(--muted);
        font-size: 14px;
        margin: 0 0 20px;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255, 255, 255, .88);
        border-color: var(--line);
        border-radius: 8px;
        box-shadow: 0 10px 34px rgba(31, 45, 61, .08);
    }
    .stock-row {
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 10px 12px;
        margin-bottom: 8px;
        background: #fff;
    }
    .stock-symbol {
        font-size: 15px;
        font-weight: 700;
        color: #10243a;
        margin-bottom: 2px;
    }
    .stock-meta {
        color: var(--muted);
        font-size: 12px;
    }
    .metric-strip {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 10px;
        margin: 12px 0 16px;
    }
    .metric-tile {
        background: #fff;
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 12px;
    }
    .metric-label {
        font-size: 12px;
        color: var(--muted);
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 20px;
        font-weight: 750;
        color: #10243a;
    }
    div[data-testid="stTextInput"] label,
    div[data-testid="stDateInput"] label,
    div[data-testid="stSelectbox"] label {
        color: #344054;
        font-size: 13px;
        font-weight: 650;
    }
    .stButton > button {
        border-radius: 7px;
        min-height: 38px;
        font-weight: 680;
        border: 1px solid var(--line);
    }
    .stButton > button[kind="primary"] {
        background: var(--accent);
        border-color: var(--accent);
    }
    .stButton > button[kind="primary"]:hover {
        background: var(--accent-dark);
        border-color: var(--accent-dark);
    }
    [data-testid="stAlert"] {
        border-radius: 8px;
    }
    @media (max-width: 900px) {
        .block-container { padding: 16px; }
        .metric-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
</style>
""",
    unsafe_allow_html=True,
)


def normalize_symbol(symbol: str) -> str:
    return re.sub(r"\s+", "", symbol or "").upper()


def looks_like_symbol(value: str) -> bool:
    value = normalize_symbol(value)
    return bool(
        re.fullmatch(r"\d{4,6}(\.(HK|SS|SZ))?", value)
        or re.fullmatch(r"[A-Z]{1,6}([.-][A-Z]{1,3})?", value)
    )


def infer_market(symbol: str) -> str:
    symbol = normalize_symbol(symbol)
    if symbol.endswith(".HK"):
        return "HK"
    if re.fullmatch(r"\d{6}(\.SS|\.SZ)?", symbol):
        return "A"
    return "US"


def load_collection() -> list[dict]:
    if COLLECTION_FILE.exists():
        try:
            data = json.loads(COLLECTION_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [item for item in data if item.get("symbol")]
        except Exception:
            pass
    return DEFAULT_COLLECTION.copy()


def save_collection(collection: list[dict]) -> None:
    COLLECTION_FILE.write_text(
        json.dumps(collection, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def upsert_stock(collection: list[dict], symbol: str, name: str) -> list[dict]:
    symbol = normalize_symbol(symbol)
    name = (name or symbol).strip()
    next_item = {"symbol": symbol, "name": name, "market": infer_market(symbol)}
    remaining = [item for item in collection if normalize_symbol(item.get("symbol")) != symbol]
    return [next_item] + remaining


def delete_stock(collection: list[dict], symbol: str) -> list[dict]:
    symbol = normalize_symbol(symbol)
    return [item for item in collection if normalize_symbol(item.get("symbol")) != symbol]


def set_active(symbol: str, name: str) -> None:
    symbol = normalize_symbol(symbol)
    name = (name or symbol).strip()
    st.session_state.symbol = symbol
    st.session_state.name = name
    st.session_state.symbol_input = symbol
    st.session_state.name_input = name


@st.cache_data(show_spinner=False, ttl=86400)
def load_a_share_name_map() -> list[dict]:
    import akshare as ak

    df = ak.stock_info_a_code_name()
    code_col = "code" if "code" in df.columns else "代码"
    name_col = "name" if "name" in df.columns else "名称"
    return [
        {"symbol": str(row[code_col]).zfill(6), "name": str(row[name_col]), "market": "A"}
        for _, row in df.iterrows()
        if str(row.get(code_col, "")).strip() and str(row.get(name_col, "")).strip()
    ]


@st.cache_data(show_spinner=False, ttl=86400)
def load_hk_name_map() -> list[dict]:
    import akshare as ak

    df = ak.stock_hk_spot_em()
    code_col = "代码"
    name_col = "名称"
    if code_col not in df.columns or name_col not in df.columns:
        return []
    items = []
    for _, row in df.iterrows():
        code = str(row[code_col]).strip()
        name = str(row[name_col]).strip()
        if not code or not name:
            continue
        items.append({"symbol": f"{code.lstrip('0') or code}.HK", "name": name, "market": "HK"})
    return items


def match_stock_name(query: str, candidates: list[dict]) -> list[dict]:
    exact_matches = [item for item in candidates if query == item["name"].casefold()]
    contains_matches = [item for item in candidates if query in item["name"].casefold()]
    return exact_matches or contains_matches


def resolve_stock_input(raw_value: str, fallback_name: str, collection: list[dict]) -> dict:
    raw_value = (raw_value or "").strip()
    fallback_name = (fallback_name or "").strip()
    if not raw_value:
        raise ValueError("股票代码或名称不能为空")

    if looks_like_symbol(raw_value):
        symbol = normalize_symbol(raw_value)
        return {"symbol": symbol, "name": fallback_name or symbol, "market": infer_market(symbol)}

    query = raw_value.casefold()
    for item in collection:
        item_name = str(item.get("name", "")).casefold()
        item_symbol = normalize_symbol(str(item.get("symbol", "")))
        if query == item_name:
            return {
                "symbol": item_symbol,
                "name": item.get("name") or item_symbol,
                "market": item.get("market") or infer_market(item_symbol),
            }

    matches = match_stock_name(query, load_a_share_name_map())
    if not matches:
        try:
            matches = match_stock_name(query, load_hk_name_map())
        except Exception:
            matches = []
    if not matches:
        raise ValueError(f"未识别股票名称：{raw_value}。可以输入股票代码，或确认 akshare 能查询到该名称。")
    if len(matches) > 1:
        preview = "、".join(f'{item["name"]}({item["symbol"]})' for item in matches[:5])
        raise ValueError(f"股票名称匹配到多个结果：{preview}。请改用股票代码。")

    match = matches[0]
    return {"symbol": match["symbol"], "name": match["name"], "market": match["market"]}


def preview_stock_input(raw_value: str, fallback_name: str, collection: list[dict]) -> tuple[str, str | None]:
    raw_value = (raw_value or "").strip()
    if not raw_value:
        return "empty", None
    try:
        resolved = resolve_stock_input(raw_value, fallback_name, collection)
    except Exception as exc:
        return "error", str(exc)

    symbol = resolved["symbol"]
    name = resolved["name"]
    market = resolved["market"]
    if looks_like_symbol(raw_value):
        return "warning", f"代码格式有效：{symbol} · {market}。点击“开始分析”验证是否有行情数据。"
    return "success", f"已识别：{name} ({symbol}) · {market}，可以点击“开始分析”。"


def get_initial_dates() -> tuple[datetime, datetime]:
    return datetime(2022, 1, 1), datetime.today()


def make_chart_html_fullscreen(html_content: str) -> str:
    html_content, _ = re.subn(
        r'class="chart-container"\s+style="[^"]*"',
        'class="chart-container" style="width: 100vw !important; height: 100vh !important;"',
        html_content,
        count=0,
    )
    if "<head>" in html_content:
        html_content = html_content.replace(
            "<head>",
            """<head>
<style>
html, body {
    width: 100vw !important;
    height: 100vh !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
    background: #1f212d;
}
.chart-container {
    width: 100vw !important;
    height: 100vh !important;
}
</style>""",
            1,
        )
    if "</body>" in html_content:
        html_content = html_content.replace(
            "</body>",
            """
<script>
function resizeCZSCCharts() {
    document.querySelectorAll(".chart-container").forEach(function (el) {
        el.style.width = window.innerWidth + "px";
        el.style.height = window.innerHeight + "px";
        if (window.echarts) {
            const chart = echarts.getInstanceByDom(el);
            if (chart) {
                chart.resize({ width: window.innerWidth, height: window.innerHeight });
            }
        }
    });
}
window.addEventListener("load", resizeCZSCCharts);
window.addEventListener("resize", resizeCZSCCharts);
setTimeout(resizeCZSCCharts, 80);
</script>
</body>""",
            1,
        )
    return html_content


def render_new_tab_button(html_content: str, title: str) -> None:
    encoded_html = base64.b64encode(html_content.encode("utf-8")).decode("ascii")
    safe_title = json.dumps(title, ensure_ascii=False)
    components.html(
        f"""
        <div style="font-family: Inter, 'Segoe UI', Arial, sans-serif; height: 58px; display: flex; align-items: center; gap: 12px;">
            <a id="open-chart" target="_blank" rel="noopener"
               style="display: inline-flex; align-items: center; justify-content: center; height: 40px; padding: 0 18px; border-radius: 7px; background: #0f9f6e; color: #fff; font-size: 14px; font-weight: 700; text-decoration: none;">
               在新标签页打开图表
            </a>
            <span style="color: #667085; font-size: 13px;">{title}</span>
        </div>
        <script>
            const pageTitle = {safe_title};
            const encoded = "{encoded_html}";
            const binary = atob(encoded);
            const bytes = Uint8Array.from(binary, c => c.charCodeAt(0));
            const html = new TextDecoder("utf-8").decode(bytes);
            const url = URL.createObjectURL(new Blob([html], {{ type: "text/html;charset=utf-8" }}));
            const link = document.getElementById("open-chart");
            link.href = url;
            link.title = pageTitle;
        </script>
        """,
        height=64,
    )


@st.cache_data(show_spinner=False)
def fetch_and_analyze(symbol: str, name: str, sdt: str, edt: str) -> dict:
    df = get_real_kline_df(symbol=symbol, sdt=sdt, edt=edt)
    bars = format_standard_kline(df, freq=Freq.D)
    czsc_obj = CZSC(bars, max_bi_num=1000)

    kline_data = [
        {
            "dt": bar.dt,
            "open": bar.open,
            "close": bar.close,
            "high": bar.high,
            "low": bar.low,
            "vol": bar.vol,
        }
        for bar in bars
    ]
    fx_data = [{"dt": fx.dt, "fx": fx.fx, "fx_mark": fx.mark.value} for fx in czsc_obj.fx_list]
    bi_data = []
    for bi in czsc_obj.bi_list:
        bi_data.append({"dt": bi.fx_a.dt, "bi": bi.fx_a.fx})
        bi_data.append({"dt": bi.fx_b.dt, "bi": bi.fx_b.fx})

    chart = kline_pro(
        kline=kline_data,
        fx=fx_data,
        bi=bi_data,
        title=f"{name} ({symbol}) 缠论分析",
        t_seq=[5, 10, 20, 60],
        width="100%",
        height="760px",
    )
    html_file = ROOT / "output" / "chanAnalysis" / "_streamlit_chart.html"
    html_file.parent.mkdir(parents=True, exist_ok=True)
    chart.render(str(html_file))
    html_content = make_chart_html_fullscreen(html_file.read_text(encoding="utf-8"))

    return {
        "html": html_content,
        "stats": {
            "kline_count": len(bars),
            "fx_count": len(czsc_obj.fx_list),
            "bi_count": len(czsc_obj.bi_list),
            "date_range": f"{df['dt'].min().strftime('%Y-%m-%d')} 至 {df['dt'].max().strftime('%Y-%m-%d')}",
        },
    }


if "collection" not in st.session_state:
    st.session_state.collection = load_collection()
if "symbol" not in st.session_state:
    st.session_state.symbol = st.session_state.collection[0]["symbol"]
if "name" not in st.session_state:
    st.session_state.name = st.session_state.collection[0]["name"]
if "symbol_input" not in st.session_state:
    st.session_state.symbol_input = st.session_state.symbol
if "name_input" not in st.session_state:
    st.session_state.name_input = st.session_state.name
if "start_date_input" not in st.session_state or "end_date_input" not in st.session_state:
    st.session_state.start_date_input, st.session_state.end_date_input = get_initial_dates()
if st.session_state.pop("use_today_date", False):
    st.session_state.end_date_input = datetime.today()


st.markdown("<h1>CZSC Chan Analysis</h1>", unsafe_allow_html=True)
st.markdown(
    '<p class="app-subtitle">股票选择、收藏与缠论图表集中在一个网页工作台中。</p>',
    unsafe_allow_html=True,
)


left, right = st.columns([0.28, 0.72], gap="large")

with left:
    with st.container(border=True):
        st.markdown("## 股票集合")

        for item in st.session_state.collection:
            symbol = item["symbol"]
            name = item.get("name") or symbol
            st.markdown(
                f"""
                <div class="stock-row">
                    <div class="stock-symbol">{symbol}</div>
                    <div class="stock-meta">{name} · {item.get("market", infer_market(symbol))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns([0.62, 0.38])
            with c1:
                if st.button("选择", key=f"select_{symbol}", use_container_width=True):
                    set_active(symbol, name)
                    st.rerun()
            with c2:
                if st.button("删除", key=f"delete_{symbol}", use_container_width=True):
                    st.session_state.collection = delete_stock(st.session_state.collection, symbol)
                    save_collection(st.session_state.collection)
                    if st.session_state.collection:
                        first = st.session_state.collection[0]
                        set_active(first["symbol"], first.get("name", first["symbol"]))
                    st.rerun()

        st.markdown("---")
        st.caption("点“保存到集合”后，下次打开网页仍会保留。")


with right:
    with st.container(border=True):
        st.markdown("## 分析设置")

        form_cols = st.columns([0.28, 0.28, 0.19, 0.19, 0.06])
        with form_cols[0]:
            symbol = st.text_input("股票代码或名称", key="symbol_input", placeholder="通威股份 / 9988.HK / AAPL")
        with form_cols[1]:
            name = st.text_input("股票名称", key="name_input", placeholder="Alibaba-W")
        with form_cols[2]:
            start_date = st.date_input("开始日期", key="start_date_input", format="YYYY/MM/DD")
        with form_cols[3]:
            end_date = st.date_input("结束日期", key="end_date_input", format="YYYY/MM/DD")
        with form_cols[4]:
            st.write("")
            st.write("")
            if st.button("今天", use_container_width=True):
                st.session_state.use_today_date = True
                st.rerun()

        actions = st.columns([0.18, 0.2, 0.62])
        with actions[0]:
            save_btn = st.button("保存到集合", use_container_width=True)
        with actions[1]:
            analyze_btn = st.button("开始分析", type="primary", use_container_width=True)

        preview_status, preview_message = preview_stock_input(
            st.session_state.symbol_input,
            st.session_state.name_input,
            st.session_state.collection,
        )
        if preview_status == "success":
            st.success(preview_message)
        elif preview_status == "warning":
            st.info(preview_message)
        elif preview_status == "error":
            st.warning(preview_message)

    if save_btn:
        try:
            resolved = resolve_stock_input(
                st.session_state.symbol_input,
                st.session_state.name_input,
                st.session_state.collection,
            )
            st.session_state.symbol = resolved["symbol"]
            st.session_state.name = resolved["name"]
            st.session_state.collection = upsert_stock(st.session_state.collection, resolved["symbol"], resolved["name"])
            save_collection(st.session_state.collection)
            st.success(f'已保存 {resolved["name"]} ({resolved["symbol"]})')
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

    if analyze_btn:
        sdt = pd.Timestamp(start_date).strftime("%Y%m%d")
        edt = pd.Timestamp(end_date).strftime("%Y%m%d")

        try:
            resolved = resolve_stock_input(
                st.session_state.symbol_input,
                st.session_state.name_input,
                st.session_state.collection,
            )
            clean_symbol = resolved["symbol"]
            clean_name = resolved["name"]

            validate_yyyymmdd(sdt)
            validate_yyyymmdd(edt)
            if sdt >= edt:
                raise ValueError("开始日期必须早于结束日期")

            st.session_state.collection = upsert_stock(st.session_state.collection, clean_symbol, clean_name)
            save_collection(st.session_state.collection)
            st.session_state.symbol = clean_symbol
            st.session_state.name = clean_name

            with st.spinner(f"正在分析 {clean_name} ({clean_symbol})..."):
                st.session_state.analysis = fetch_and_analyze(clean_symbol, clean_name, sdt, edt)
                st.session_state.analysis_title = f"{clean_name} ({clean_symbol})"
                st.session_state.analysis_dates = f"{sdt} - {edt}"
            st.success(f"分析完成：{clean_name} ({clean_symbol})")
        except Exception as exc:
            st.error(str(exc))

    analysis = st.session_state.get("analysis")
    if analysis:
        stats = analysis["stats"]
        st.markdown(
            f"""
            <div class="metric-strip">
                <div class="metric-tile"><div class="metric-label">当前股票</div><div class="metric-value">{st.session_state.analysis_title}</div></div>
                <div class="metric-tile"><div class="metric-label">K线数量</div><div class="metric-value">{stats["kline_count"]}</div></div>
                <div class="metric-tile"><div class="metric-label">分型 / 笔</div><div class="metric-value">{stats["fx_count"]} / {stats["bi_count"]}</div></div>
                <div class="metric-tile"><div class="metric-label">日期范围</div><div class="metric-value">{stats["date_range"]}</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_new_tab_button(analysis["html"], st.session_state.analysis_title)
        components.html(analysis["html"], height=800, scrolling=False)
    else:
        st.info("选择集合中的股票，或输入新股票后点击“开始分析”。分析成功后会自动保存到股票集合。")
        example_data = pd.DataFrame(
            [
                {"市场": "港股", "代码": "9988.HK", "名称": "Alibaba-W"},
                {"市场": "A股", "代码": "603259", "名称": "Wuxi AppTec"},
                {"市场": "A股", "代码": "000001.SZ", "名称": "Ping An Bank"},
                {"市场": "美股", "代码": "AAPL", "名称": "Apple"},
            ]
        )
        st.dataframe(example_data, hide_index=True, use_container_width=True)
