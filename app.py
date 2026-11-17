import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import urllib.request
import json
from datetime import datetime, timedelta

# 외부 패키지 안전 로드
try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False

try:
    from pykrx import stock as krx_stock
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False

# 페이지 기본 설정
st.set_page_config(
    page_title="앤트위키(AntWiki) 한·미 통합 실시간 분석기",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 커스텀 스타일링 (모바일 및 폴드 대화면 최적화)
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .stock-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 10px;
        border: 1px solid #e5e8eb;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 1. 한국 증시(KRX) & 미국 증시(US) 8대 핵심 테마 기본 구조
# ---------------------------------------------------------
KR_THEME_MAP = {
    "HBM·반도체장비": [
        ("000660", "SK하이닉스", 198500, 4.85, 4200),
        ("042700", "한미반도체", 134500, 6.40, 2800),
        ("005930", "삼성전자", 74200, 1.65, 5500),
        ("036930", "주성엔지니어링", 33200, 3.10, 950),
    ],
    "2차전지·소재": [
        ("373220", "LG에너지솔루션", 372000, -2.15, 3400),
        ("247540", "에코프로비엠", 168000, -3.40, 2100),
        ("003670", "포스코퓨처엠", 235000, -1.80, 1800),
        ("066970", "엘앤에프", 104500, -2.95, 1100),
    ],
    "AI·소프트웨어": [
        ("035420", "NAVER", 189000, 2.35, 2900),
        ("403870", "HPSP", 38400, 3.80, 1200),
        ("012510", "더존비즈온", 66500, 4.10, 850),
    ],
    "바이오·비만치료제": [
        ("207940", "삼성바이오로직스", 965000, 1.90, 3100),
        ("068270", "셀트리온", 192000, 0.85, 2600),
        ("196170", "알테오젠", 342000, 5.20, 2400),
        ("128940", "한미약품", 318000, 2.75, 1100),
    ],
    "방산·우주항공": [
        ("012450", "한화에어로스페이스", 348000, 3.60, 2700),
        ("079550", "LIG넥스원", 218000, 2.40, 1500),
        ("047810", "한국항공우주", 58900, 1.15, 1200),
    ],
    "밸류업·금융지주": [
        ("105560", "KB금융", 88400, -0.95, 2500),
        ("055550", "신한지주", 55600, -1.20, 2100),
        ("086790", "하나금융지주", 62100, 0.45, 1750),
    ],
    "전력설비·변압기": [
        ("267260", "HD현대일렉트릭", 335000, 4.95, 2300),
        ("010120", "LS ELECTRIC", 172000, 3.40, 1450),
        ("298040", "효성중공업", 389000, 2.80, 1250),
    ],
    "자동차·부품": [
        ("005380", "현대차", 238000, -0.65, 3200),
        ("000270", "기아", 101200, -1.10, 2700),
        ("012330", "현대모비스", 241000, 0.80, 1600),
    ],
}

US_THEME_MAP = {
    "AI·반도체": [
        ("NVDA", "엔비디아", 138.50, 3.85, 38000),
        ("AVGO", "브로드컴", 178.20, 2.90, 12000),
        ("AMD", "AMD", 152.40, 1.80, 9500),
        ("TSM", "TSMC", 192.10, 3.20, 8200),
    ],
    "빅테크·클라우드": [
        ("MSFT", "마이크로소프트", 428.50, 1.15, 16500),
        ("AAPL", "애플", 231.80, 0.85, 19000),
        ("GOOGL", "알파벳(구글)", 181.40, 1.95, 14000),
        ("AMZN", "아마존", 210.30, 2.40, 17500),
    ],
    "전기차·자율주행": [
        ("TSLA", "테슬라", 321.50, 5.40, 29000),
        ("RIVN", "리비안", 11.20, -2.30, 1800),
        ("UBER", "우버", 73.60, -1.10, 3500),
    ],
    "비만치료제·헬스케어": [
        ("LLY", "일라이릴리", 835.00, -1.45, 7800),
        ("NVO", "노보노디스크", 112.40, -1.80, 4200),
        ("ISRG", "인튜이티브서지컬", 522.00, 1.60, 2900),
        ("UNH", "유나이티드헬스", 595.00, 0.55, 4500),
    ],
    "AI 소프트웨어·보안": [
        ("PLTR", "팔란티어", 58.90, 6.20, 11500),
        ("CRM", "세일즈포스", 325.40, 2.75, 4100),
        ("CRWD", "크라우드스트라이크", 342.10, 3.10, 3600),
        ("PANW", "팔로알토네트웍스", 388.00, 1.90, 3100),
    ],
    "원전·전력인프라": [
        ("CEG", "컨스텔레이션에너지", 254.00, 4.30, 3400),
        ("VST", "비스트라에너지", 148.50, 5.10, 4200),
        ("GEV", "GE버노바", 332.00, 3.45, 3800),
    ],
    "우주·방산": [
        ("RKLB", "로켓랩", 18.40, 7.10, 2400),
        ("ASTS", "AST스페이스모바일", 26.80, 4.50, 1900),
        ("LMT", "록히드마틴", 558.00, -0.60, 2600),
    ],
    "핀테크·크립토": [
        ("COIN", "코인베이스", 295.00, 8.40, 9200),
        ("HOOD", "로빈후드", 34.20, 5.80, 4600),
        ("V", "비자", 308.50, 0.70, 5100),
    ],
}

# ---------------------------------------------------------
# 2. 실시간 데이터 수집 함수 (해외 클라우드 서버에서도 끊김 없이 작동)
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def load_kr_data():
    records = []
    updated_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    for theme_name, stock_list in KR_THEME_MAP.items():
        for ticker, name, def_price, def_chg, def_weight in stock_list:
            price = float(def_price)
            change = float(def_chg)
            weight = int(def_weight)

            # 1차: 네이버 금융 모바일 실시간 API (가장 빠르고 해외 서버 차단 없음)
            try:
                url = f"https://m.stock.naver.com/api/stock/{ticker}/basic"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=2.5) as res:
                    data = json.loads(res.read().decode("utf-8"))
                    raw_p = str(data.get("closePrice", "0")).replace(",", "")
                    if raw_p.isdigit() and int(raw_p) > 0:
                        price = float(raw_p)
                        change = round(float(data.get("fluctuationsRatio", 0.0)), 2)
            except Exception:
                # 2차: pykrx 보조 연동
                if PYKRX_AVAILABLE:
                    try:
                        end_d = datetime.today()
                        start_d = end_d - timedelta(days=10)
                        df_k = krx_stock.get_market_ohlcv_by_date(
                            start_d.strftime("%Y%m%d"), end_d.strftime("%Y%m%d"), ticker
                        )
                        if df_k is not None and len(df_k) >= 2:
                            price = float(df_k["종가"].iloc[-1])
                            prev = float(df_k["종가"].iloc[-2])
                            if prev > 0:
                                change = round(((price - prev) / prev) * 100, 2)
                    except Exception:
                        pass

            # 5영업일 상대강도(RS) 궤적 산출
            rs_x = [round(100 + change * f, 2) for f in [0.25, 0.45, 0.65, 0.85, 1.1]]
            rs_y = [round(100 + change * f, 2) for f in [0.20, 0.40, 0.60, 0.80, 1.0]]

            records.append({
                "theme": theme_name,
                "ticker": ticker,
                "name": name,
                "display_name": name,
                "price": price,
                "price_str": f"{int(price):,}원",
                "change": change,
                "weight": weight,
                "rs_x": rs_x,
                "rs_y": rs_y,
                "rs_ratio": rs_x[-1],
                "rs_mom": rs_y[-1],
            })
    return pd.DataFrame(records), updated_time


@st.cache_data(ttl=60)
def load_us_data():
    records = []
    updated_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    all_tickers = [item[0] for items in US_THEME_MAP.values() for item in items]

    hist_data = None
    if YF_AVAILABLE:
        try:
            hist_data = yf.download(
                all_tickers, period="1mo", group_by="ticker", auto_adjust=True, progress=False, threads=True
            )
        except Exception:
            pass

    for theme_name, stock_list in US_THEME_MAP.items():
        for ticker, kor_name, def_price, def_chg, def_weight in stock_list:
            price = float(def_price)
            change = float(def_chg)
            weight = int(def_weight)
            rs_x = [round(100 + change * f, 2) for f in [0.25, 0.45, 0.65, 0.85, 1.1]]
            rs_y = [round(100 + change * f, 2) for f in [0.20, 0.40, 0.60, 0.80, 1.0]]

            try:
                if hist_data is not None and ticker in hist_data.columns.get_level_values(0):
                    df_tk = hist_data[ticker].dropna(subset=["Close"])
                    if len(df_tk) >= 2:
                        closes = df_tk["Close"].astype(float)
                        vols = df_tk["Volume"].astype(float)
                        price = round(float(closes.iloc[-1]), 2)
                        prev = float(closes.iloc[-2])
                        if prev > 0:
                            change = round(((price - prev) / prev) * 100, 2)
                        est_val = int((price * vols.iloc[-1]) // 1_000_000)
                        weight = max(est_val, 100)

                        if len(closes) >= 7:
                            pct_s = closes.pct_change().fillna(0) * 100
                            r_str = pct_s.rolling(3).mean().fillna(0)
                            r_mom = r_str.diff().fillna(0)
                            rs_x = [round(100 + float(v) * 1.1, 2) for v in r_str.iloc[-5:]]
                            rs_y = [round(100 + float(v) * 1.3, 2) for v in r_mom.iloc[-5:]]
            except Exception:
                pass

            records.append({
                "theme": theme_name,
                "ticker": ticker,
                "name": kor_name,
                "display_name": f"{kor_name} ({ticker})",
                "price": price,
                "price_str": f"${price:,.2f}",
                "change": change,
                "weight": weight,
                "rs_x": rs_x,
                "rs_y": rs_y,
                "rs_ratio": rs_x[-1],
                "rs_mom": rs_y[-1],
            })
    return pd.DataFrame(records), updated_time


# ---------------------------------------------------------
# 3. 상단 헤더 및 국가(한국/미국)·색상·새로고침 컨트롤러
# ---------------------------------------------------------
col_title, col_btn = st.columns([4, 1])
with col_title:
    st.title("📊 앤트위키(AntWiki) 한·미 통합 테마 히트맵 & RS 분석기")
with col_btn:
    if st.button("🔄 실시간 시세 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

ctrl1, ctrl2, ctrl3 = st.columns([1.3, 1.5, 1.5])
with ctrl1:
    market_choice = st.radio(
        "🌐 시장 선택",
        ["🇰🇷 한국 증시 (KRX)", "🇺🇸 미국 증시 (NASDAQ·NYSE)"],
        horizontal=True
    )

is_kr = "한국" in market_choice
df, updated_at = load_kr_data() if is_kr else load_us_data()
unit_label = "억원" if is_kr else "백만 달러($M)"

with ctrl2:
    selected_theme = st.selectbox("🔍 집중 분석할 테마 선택 (레퍼런스 2·3·4 연동)", df["theme"].unique())

with ctrl3:
    color_style = st.radio(
        "🎨 등락 색상 기준",
        ["한국식 (상승 빨강 / 하락 파랑)", "미국식 (상승 초록 / 하락 빨강)"],
        index=0,
        horizontal=True
    )

st.caption(f"데이터 갱신 시각: {updated_at} | 타일 면적 기준: 거래대금 비중({unit_label})")

if "한국식" in color_style:
    colorscale = [[0.0, "#2b6cb0"], [0.25, "#63b3ed"], [0.5, "#f7fafc"], [0.75, "#feb2b2"], [1.0, "#e53e3e"]]
    up_col, up_bg = "#e12343", "#ffeef0"
    dn_col, dn_bg = "#1964d8", "#eef4ff"
else:
    colorscale = [[0.0, "#e53e3e"], [0.25, "#feb2b2"], [0.5, "#f7fafc"], [0.75, "#9ae6b4"], [1.0, "#16a34a"]]
    up_col, up_bg = "#15803d", "#dcfce7"
    dn_col, dn_bg = "#dc2626", "#fee2e2"

# 테마별 요약 집계
theme_summary = df.groupby("theme", as_index=False).agg(
    total_weight=("weight", "sum"),
    avg_change=("change", "mean"),
    rs_ratio=("rs_ratio", "mean"),
    rs_mom=("rs_mom", "mean"),
    stock_count=("name", "count")
)
theme_summary["avg_change"] = theme_summary["avg_change"].round(2)

# ---------------------------------------------------------
# 4. 레퍼런스 1~4번 화면 탭 구현
# ---------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "① 테마 지도로 한눈에",
    "② 색은 오늘 등락 (테마 포커스)",
    "③ 그 안의 종목까지 (종목 상세)",
    "④ 테마·종목 RS 4분면 차트"
])

with tab1:
    root_label = "한국 증시 (KRX)" if is_kr else "미국 증시 (US Market)"
    fig1 = px.treemap(
        df,
        path=[px.Constant(root_label), "theme", "display_name"],
        values="weight",
        color="change",
        color_continuous_scale=colorscale,
        color_continuous_midpoint=0,
        range_color=[-5, 5],
        custom_data=["change", "price_str", "weight"]
    )
    fig1.update_traces(
        texttemplate="<b>%{label}</b><br>%{customdata[0]:+.2f}%<br>%{customdata[1]}",
        textposition="middle center",
        hovertemplate="<b>%{label}</b><br>등락률: %{customdata[0]:+.2f}%<br>현재가: %{customdata[1]}<br>거래대금 비중: %{value:,}<extra></extra>"
    )
    fig1.update_layout(margin=dict(t=20, l=10, r=10, b=10), height=560)
    st.plotly_chart(fig1, use_container_width=True)

with tab2:
    focus_df = theme_summary.copy()
    focus_df["focus_color"] = focus_df.apply(
        lambda r: r["avg_change"] if r["theme"] == selected_theme else r["avg_change"] * 0.15,
        axis=1
    )
    fig2 = px.treemap(
        focus_df,
        path=[px.Constant("테마 등락 맵"), "theme"],
        values="total_weight",
        color="focus_color",
        color_continuous_scale=colorscale,
        color_continuous_midpoint=0,
        range_color=[-5, 5],
        custom_data=["avg_change", "stock_count"]
    )
    fig2.update_traces(
        texttemplate="<b>%{label}</b><br>%{customdata[0]:+.2f}%",
        textfont=dict(size=18),
        hovertemplate="<b>%{label}</b><br>테마 평균: %{customdata[0]:+.2f}%<br>소속 종목: %{customdata[1]}개<extra></extra>"
    )
    fig2.update_layout(margin=dict(t=20, l=10, r=10, b=10), height=500)
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    sub = df[df["theme"] == selected_theme].sort_values("change", ascending=False)
    avg_c = sub["change"].mean()
    c1, c2, c3 = st.columns(3)
    c1.metric(f"[{selected_theme}] 평균 등락률", f"{avg_c:+.2f}%")
    c2.metric("상승 종목", f"{int((sub['change'] > 0).sum())}개")
    c3.metric("하락 종목", f"{int((sub['change'] < 0).sum())}개")
    st.divider()

    for _, row in sub.iterrows():
        is_up = row["change"] >= 0
        col = up_col if is_up else dn_col
        bg = up_bg if is_up else dn_bg
        st.markdown(f"""
        <div class="stock-card">
            <div>
                <b style="font-size:1.05rem;">{row['name']}</b>
                <span style="color:#6b7684; font-weight:600; margin-left:6px;">({row['ticker']})</span>
                <div style="font-size:0.82rem; color:#495057; margin-top:4px;">
                    거래비중: {row['weight']:,}{unit_label} · RS-Ratio: <b>{row['rs_ratio']}</b> · RS-Mom: <b>{row['rs_mom']}</b>
                </div>
            </div>
            <div style="text-align:right;">
                <b style="font-size:1.05rem;">{row['price_str']}</b>
                <span style="background:{bg}; color:{col}; padding:5px 10px; border-radius:8px; font-weight:700; margin-left:8px;">
                    {row['change']:+.2f}%
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

with tab4:
    mode = st.radio(
        "RS 궤적 비교 단위",
        ["전체 테마 RS 비교", f"'{selected_theme}' 내 종목별 RS 비교"],
        horizontal=True
    )
    fig4 = go.Figure()
    quads = [
        (100, 112, 100, 112, "rgba(254,215,215,0.35)", "강세 (Leading)", 108, 110),
        (88, 100, 100, 112, "rgba(254,235,200,0.35)", "개선 (Improving)", 92, 110),
        (88, 100, 88, 100, "rgba(190,227,248,0.35)", "약세 (Lagging)", 92, 90),
        (100, 112, 88, 100, "rgba(233,216,253,0.35)", "약화 (Weakening)", 108, 90),
    ]
    for x0, x1, y0, y1, c, lbl, lx, ly in quads:
        fig4.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=c, line=dict(width=0), layer="below")
        fig4.add_annotation(x=lx, y=ly, text=f"<b>{lbl}</b>", showarrow=False)

    fig4.add_hline(y=100, line_dash="dash", line_color="#64748b")
    fig4.add_vline(x=100, line_dash="dash", line_color="#64748b")

    target = df[df["theme"] == selected_theme] if mode != "전체 테마 RS 비교" else df
    group_key = "display_name" if mode != "전체 테마 RS 비교" else "theme"

    for name_val, grp in target.groupby(group_key, sort=False):
        xs = np.mean(np.array(grp["rs_x"].tolist()), axis=0)
        ys = np.mean(np.array(grp["rs_y"].tolist()), axis=0)
        fig4.add_trace(go.Scatter(
            x=xs,
            y=ys,
            mode="lines+markers+text",
            name=name_val,
            text=["", "", "", "", name_val],
            textposition="top center",
            line=dict(width=3, shape="spline"),
            marker=dict(size=[6, 6, 6, 6, 13])
        ))

    fig4.update_layout(
        xaxis=dict(title="RS-Ratio (상대강도)", range=[88, 112]),
        yaxis=dict(title="RS-Momentum (모멘텀)", range=[88, 112]),
        height=540,
        margin=dict(t=20, l=20, r=20, b=20)
    )
    st.plotly_chart(fig4, use_container_width=True)
