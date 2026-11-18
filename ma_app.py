import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

# yfinance 로드 확인
try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False

# 페이지 기본 설정
st.set_page_config(
    page_title="이평선 거래 - 40·200일선 골든크로스 분석기",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 앤트위키 스타일 커스텀 CSS
st.markdown("""
<style>
    .block-container { padding-top: 1.4rem; padding-bottom: 2rem; }
    .signal-card {
        background: #ffffff;
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 12px;
        border: 1px solid #e5e8eb;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .badge-gc {
        background: #ffe3e3; color: #c92a2a; padding: 5px 12px;
        border-radius: 20px; font-weight: 800; font-size: 0.85rem;
    }
    .badge-near {
        background: #fff3bf; color: #e67700; padding: 5px 12px;
        border-radius: 20px; font-weight: 800; font-size: 0.85rem;
    }
    .badge-bull {
        background: #d3f9d8; color: #2b8a3e; padding: 5px 12px;
        border-radius: 20px; font-weight: 700; font-size: 0.85rem;
    }
    .badge-bear {
        background: #e7f5ff; color: #1864ab; padding: 5px 12px;
        border-radius: 20px; font-weight: 700; font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 1. 한국 증시 & 미국 증시 스캔 대상 종목 유니버스
# ---------------------------------------------------------
KR_UNIVERSE = {
    "반도체·장비": [
        ("005930", "삼성전자"), ("000660", "SK하이닉스"), ("042700", "한미반도체"),
        ("036930", "주성엔지니어링"), ("058470", "리노공업"), ("000990", "DB하이텍"),
        ("403870", "HPSP"), ("039030", "이오테크닉스")
    ],
    "2차전지·소재": [
        ("373220", "LG에너지솔루션"), ("006400", "삼성SDI"), ("051910", "LG화학"),
        ("247540", "에코프로비엠"), ("086520", "에코프로"), ("003670", "포스코퓨처엠"),
        ("066970", "엘앤에프"), ("005490", "POSCO홀딩스")
    ],
    "IT·플랫폼·게임": [
        ("035420", "NAVER"), ("035720", "카카오"), ("259960", "크래프톤"),
        ("036570", "엔씨소프트"), ("251270", "넷마블"), ("012510", "더존비즈온"),
        ("018260", "삼성에스디에스")
    ],
    "바이오·헬스케어": [
        ("207940", "삼성바이오로직스"), ("068270", "셀트리온"), ("196170", "알테오젠"),
        ("128940", "한미약품"), ("000100", "유한양행"), ("326030", "SK바이오팜"),
        ("145020", "휴젤")
    ],
    "자동차·전력·중공업": [
        ("005380", "현대차"), ("000270", "기아"), ("012330", "현대모비스"),
        ("267260", "HD현대일렉트릭"), ("010120", "LS ELECTRIC"), ("012450", "한화에어로스페이스"),
        ("009540", "HD한국조선해양")
    ],
    "금융·엔터·소비재": [
        ("105560", "KB금융"), ("055550", "신한지주"), ("352820", "하이브"),
        ("041510", "에스엠"), ("090430", "아모레퍼시픽"), ("051900", "LG생활건강"),
        ("003230", "삼양식품")
    ]
}

US_UNIVERSE = {
    "AI·반도체": [
        ("NVDA", "엔비디아"), ("AMD", "AMD"), ("INTC", "인텔"),
        ("AVGO", "브로드컴"), ("QCOM", "퀄컴"), ("MU", "마이크론"), ("TSM", "TSMC")
    ],
    "빅테크·플랫폼": [
        ("AAPL", "애플"), ("MSFT", "마이크로소프트"), ("GOOGL", "알파벳"),
        ("AMZN", "아마존"), ("META", "메타"), ("NFLX", "넷플릭스")
    ],
    "전기차·모빌리티": [
        ("TSLA", "테슬라"), ("RIVN", "리비안"), ("LCID", "루시드"),
        ("F", "포드"), ("GM", "제너럴모터스"), ("UBER", "우버")
    ],
    "바이오·헬스케어": [
        ("PFE", "화이자"), ("MRNA", "모더나"), ("JNJ", "존슨앤드존슨"),
        ("LLY", "일라이릴리"), ("UNH", "유나이티드헬스"), ("BMY", "브리스톨마이어스")
    ],
    "소프트웨어·핀테크": [
        ("PLTR", "팔란티어"), ("SNOW", "스노우플레이크"), ("PYPL", "페이팔"),
        ("SQ", "블록"), ("COIN", "코인베이스"), ("CRM", "세일즈포스")
    ],
    "소비재·에너지·산업": [
        ("NKE", "나이키"), ("SBUX", "스타벅스"), ("DIS", "디즈니"),
        ("BA", "보잉"), ("ENPH", "엔페이즈에너지"), ("ALB", "앨버말")
    ]
}

# ---------------------------------------------------------
# 2. 500영업일(약 2년) 일봉 데이터 수집 및 이평선 분석 엔진
# ---------------------------------------------------------
def fetch_kr_ohlcv_500d(ticker):
    """네이버 금융 차트 API를 통해 최근 500영업일 일봉 데이터를 초고속으로 수집"""
    url = f"https://fchart.stock.naver.com/sise.nhn?symbol={ticker}&timeframe=day&count=500&requestType=0"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=3) as res:
        xml_data = res.read().decode("euc-kr", errors="ignore")
    root = ET.fromstring(xml_data)
    rows = []
    for item in root.findall(".//item"):
        parts = item.attrib.get("data", "").split("|")
        if len(parts) >= 6:
            dt_str, o, h, l, c, v = parts[:6]
            rows.append({
                "Date": pd.to_datetime(dt_str, format="%Y%m%d"),
                "Close": float(c),
                "Volume": float(v)
            })
    return pd.DataFrame(rows)


def analyze_ma_strategy(df_ohlcv, inv_days=220, inv_ratio_thr=75.0, gc_window=20):
    """
    40일선 & 200일선 계산 후 '1년 역배열 유지 + 골든크로스' 정밀 판별
    """
    if df_ohlcv is None or len(df_ohlcv) < 260:
        return None

    df = df_ohlcv.sort_values("Date").reset_index(drop=True).copy()
    df["MA40"] = df["Close"].rolling(40).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    df = df.dropna(subset=["MA200"]).reset_index(drop=True)

    if len(df) < 60:
        return None

    # 이격도(Spread %): (MA40 - MA200) / MA200 * 100
    df["Spread"] = ((df["MA40"] - df["MA200"]) / df["MA200"]) * 100.0
    # 이격도 변화 속도 (최근 5일 모멘텀)
    df["Spread_Mom"] = df["Spread"].diff(5).fillna(0.0)

    latest = df.iloc[-1]
    prev = df.iloc[-2]
    price = float(latest["Close"])
    prev_price = float(prev["Close"])
    change_pct = round(((price - prev_price) / prev_price) * 100, 2) if prev_price > 0 else 0.0

    # 거래대금 추정 (최근 거래량 * 현재가)
    est_turnover = price * float(latest["Volume"])

    # 역배열 체크 구간: 최근 gc_window 이전 시점부터 과거 inv_days 동안
    end_idx = max(len(df) - gc_window, 1)
    start_idx = max(0, end_idx - inv_days)
    check_slice = df.iloc[start_idx:end_idx]

    if len(check_slice) > 0:
        inv_count = int((check_slice["MA40"] < check_slice["MA200"]).sum())
        inv_ratio = round((inv_count / len(check_slice)) * 100, 1)
        inv_total_days = inv_count
    else:
        inv_ratio = 0.0
        inv_total_days = 0

    # 최근 골든크로스 발생 여부 탐색 (MA40이 MA200을 아래에서 위로 돌파한 날)
    cross_mask = (df["MA40"] >= df["MA200"]) & (df["MA40"].shift(1) < df["MA200"].shift(1))
    cross_indices = df.index[cross_mask].tolist()

    days_since_gc = None
    gc_date_str = "-"
    if cross_indices:
        last_gc_idx = cross_indices[-1]
        days_since_gc = (len(df) - 1) - last_gc_idx
        gc_date_str = df.loc[last_gc_idx, "Date"].strftime("%Y-%m-%d")

    cur_spread = round(float(latest["Spread"]), 2)
    cur_mom = round(float(latest["Spread_Mom"]), 2)
    is_currently_above = float(latest["MA40"]) >= float(latest["MA200"])

    # 4단계 시그널 판정
    if is_currently_above and days_since_gc is not None and days_since_gc <= gc_window and inv_ratio >= inv_ratio_thr:
        signal = "🔥 1년 역배열 후 골든크로스"
        sig_rank = 1
    elif (not is_currently_above) and (-3.5 <= cur_spread < 0.0) and cur_mom > 0 and inv_ratio >= inv_ratio_thr:
        signal = "⚡ 1년 역배열 후 돌파 임박"
        sig_rank = 2
    elif is_currently_above and inv_ratio >= 50.0 and days_since_gc is not None and days_since_gc <= 60:
        signal = "🔥 최근 골든크로스 돌파"
        sig_rank = 1
    elif is_currently_above:
        signal = "☀️ 정배열 순항 중"
        sig_rank = 3
    else:
        signal = "🌧️ 장기 역배열 구간"
        sig_rank = 4

    # 4분면 궤적 데이터 (최근 5주간 주간 단위 5포인트)
    step_indices = [max(0, len(df) - 1 - i * 4) for i in range(4, -1, -1)]
    traj_x = [round(100 + float(df.loc[idx, "Spread"]), 2) for idx in step_indices]
    traj_y = [round(100 + float(df.loc[idx, "Spread_Mom"]) * 2.5, 2) for idx in step_indices]

    return {
        "price": price,
        "change": change_pct,
        "ma40": round(float(latest["MA40"]), 2),
        "ma200": round(float(latest["MA200"]), 2),
        "spread": cur_spread,
        "spread_mom": cur_mom,
        "inv_ratio": inv_ratio,
        "inv_days": inv_total_days,
        "days_since_gc": days_since_gc if days_since_gc is not None else 999,
        "gc_date": gc_date_str,
        "signal": signal,
        "sig_rank": sig_rank,
        "turnover": est_turnover,
        "traj_x": traj_x,
        "traj_y": traj_y,
        "history": df.tail(260)[["Date", "Close", "MA40", "MA200", "Spread"]].to_dict("records")
    }


@st.cache_data(ttl=300)
def scan_market(is_kr, inv_days, inv_ratio_thr, gc_window, custom_tickers_str=""):
    universe = {k: list(v) for k, v in (KR_UNIVERSE if is_kr else US_UNIVERSE).items()}

    # 사용자 추가 종목 반영
    if custom_tickers_str.strip():
        custom_list = []
        for item in custom_tickers_str.split(","):
            tk = item.strip().upper()
            if tk:
                custom_list.append((tk, f"직접추가({tk})"))
        if custom_list:
            universe["⭐ 직접 추가 종목"] = custom_list

    results = []
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    if is_kr:
        for theme, stocks in universe.items():
            for ticker, name in stocks:
                try:
                    df_raw = fetch_kr_ohlcv_500d(ticker)
                    res = analyze_ma_strategy(df_raw, inv_days, inv_ratio_thr, gc_window)
                    if res:
                        weight = max(int(res["turnover"] // 100_000_000), 50)
                        results.append({
                            "theme": theme, "ticker": ticker, "name": name,
                            "label": f"{name}",
                            "price_str": f"{int(res['price']):,}원",
                            "weight": weight, **res
                        })
                except Exception:
                    pass
    else:
        all_tks = [tk for items in universe.values() for tk, _ in items]
        hist_all = None
        if YF_AVAILABLE:
            try:
                hist_all = yf.download(
                    all_tks, period="2y", group_by="ticker", auto_adjust=True, progress=False, threads=True
                )
            except Exception:
                pass

        for theme, stocks in universe.items():
            for ticker, name in stocks:
                try:
                    if hist_all is not None and ticker in hist_all.columns.get_level_values(0):
                        df_tk = hist_all[ticker].dropna(subset=["Close"]).reset_index()
                        df_raw = pd.DataFrame({
                            "Date": pd.to_datetime(df_tk["Date"]),
                            "Close": df_tk["Close"].astype(float),
                            "Volume": df_tk["Volume"].astype(float)
                        })
                        res = analyze_ma_strategy(df_raw, inv_days, inv_ratio_thr, gc_window)
                        if res:
                            weight = max(int(res["turnover"] // 1_000_000), 50)
                            results.append({
                                "theme": theme, "ticker": ticker, "name": name,
                                "label": f"{name}({ticker})",
                                "price_str": f"${res['price']:,.2f}",
                                "weight": weight, **res
                            })
                except Exception:
                    pass

    return pd.DataFrame(results), updated_at


# ---------------------------------------------------------
# 3. 상단 타이틀 & 『이평선 거래』 조건 설정 컨트롤러
# ---------------------------------------------------------
head_col1, head_col2 = st.columns([4, 1])
with head_col1:
    st.title("📈 이평선 거래 : 40일·200일선 역배열 돌파 분석기")
    st.caption("1년(약 200~240영업일)간 40일선이 200일선 아래에 머문 뒤 골든크로스(상향 돌파)가 발생한 종목을 앤트위키 UI로 포착합니다.")
with head_col2:
    if st.button("🔄 전 종목 재스캔", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# 조건 조절 패널
with st.container():
    c1, c2, c3, c4 = st.columns([1.3, 1.2, 1.2, 1.5])
    with c1:
        mkt = st.radio("🌐 분석 시장", ["🇰🇷 한국 주식 (KRX)", "🇺🇸 미국 주식 (US)"], horizontal=True)
    with c2:
        inv_ratio_thr = st.slider("📏 최근 1년 역배열 유지 비율 기준(%)", 50, 95, 75, step=5,
                                  help="과거 1년 중 40일선이 200일선 아래에 있었던 날의 최소 비율입니다.")
    with c3:
        gc_window = st.slider("🎯 골든크로스 탐색 범위(최근 영업일)", 5, 60, 25, step=5,
                              help="최근 며칠 이내에 40일선이 200일선을 뚫은 종목을 찾을지 설정합니다.")
    with c4:
        custom_input = st.text_input("➕ 직접 추가할 종목코드/티커 (쉼표 구분)", placeholder="예: 005930, 035720 또는 TSLA, IONQ")

is_kr = "한국" in mkt
with st.spinner("최근 500영업일(2년) 이동평균선 데이터를 계산하고 골든크로스 종목을 탐색 중입니다..."):
    df, updated_at = scan_market(is_kr, 220, inv_ratio_thr, gc_window, custom_input)

if df.empty:
    st.error("데이터를 불러오지 못했습니다. 잠시 후 '전 종목 재스캔' 버튼을 눌러주세요.")
    st.stop()

# 상단 핵심 요약 지표
gc_cnt = int((df["sig_rank"] == 1).sum())
near_cnt = int((df["sig_rank"] == 2).sum())
bull_cnt = int((df["sig_rank"] == 3).sum())
bear_cnt = int((df["sig_rank"] == 4).sum())

m1, m2, m3, m4 = st.columns(4)
m1.metric("🔥 골든크로스 돌파 포착", f"{gc_cnt}종목", "1년 역배열 후 상향 돌파")
m2.metric("⚡ 골든크로스 돌파 임박", f"{near_cnt}종목", "이격도 -3.5% 이내 추격 중")
m3.metric("☀️ 정배열 순항 종목", f"{bull_cnt}종목", "40일선 > 200일선 유지")
m4.metric("🌧️ 장기 역배열 종목", f"{bear_cnt}종목", "40일선 < 200일선 침체")

st.divider()

# ---------------------------------------------------------
# 4. 앤트위키 4대 화면 탭 구현
# ---------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "① 시그널 지도로 한눈에 (히트맵)",
    "② 골든크로스 & 돌파임박 종목 상세",
    "③ 종목별 40·200일 이평선 차트 검수",
    "④ 이평선 강도 4분면 궤적"
])

# 컬러 스케일 (역배열 파랑 ~ 보합 흰색 ~ 골든크로스 빨강)
ma_colorscale = [
    [0.0, "#1d4ed8"], [0.3, "#93c5fd"], [0.5, "#f8fafc"], [0.7, "#fca5a5"], [1.0, "#dc2626"]
]

# ---------------------------------------------------------
# [탭 1] 앤트위키 트리맵 히트맵
# ---------------------------------------------------------
with tab1:
    col_opt1, col_opt2 = st.columns([2, 2])
    with col_opt1:
        group_mode = st.radio("🗺️ 지도 묶음 기준", ["시그널 상태별로 묶기 (추천)", "테마별로 묶기"], horizontal=True)
    with col_opt2:
        color_metric = st.radio("🎨 타일 색상 기준", ["40·200일선 이격도(%)", "오늘 주가 등락률(%)"], horizontal=True)

    path_cols = [px.Constant("전체 시장"), "signal", "label"] if "시그널" in group_mode else [px.Constant("전체 시장"), "theme", "label"]
    color_col = "spread" if "이격도" in color_metric else "change"
    rng = [-10, 10] if color_col == "spread" else [-5, 5]

    fig_tree = px.treemap(
        df,
        path=path_cols,
        values="weight",
        color=color_col,
        color_continuous_scale=ma_colorscale,
        color_continuous_midpoint=0,
        range_color=rng,
        custom_data=["price_str", "change", "spread", "inv_ratio", "signal", "gc_date"]
    )
    fig_tree.update_traces(
        texttemplate="<b>%{label}</b><br>%{customdata[0]} (%{customdata[1]:+.2f}%)<br>이격도: %{customdata[2]:+.2f}%",
        textposition="middle center",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "상태: %{customdata[4]}<br>"
            "현재가: %{customdata[0]} (%{customdata[1]:+.2f}%)<br>"
            "40·200일 이격도: %{customdata[2]:+.2f}%<br>"
            "1년 역배열 유지율: %{customdata[3]}%<br>"
            "최근 골든크로스일: %{customdata[5]}<extra></extra>"
        )
    )
    fig_tree.update_layout(margin=dict(t=20, l=10, r=10, b=10), height=560)
    st.plotly_chart(fig_tree, use_container_width=True)

# ---------------------------------------------------------
# [탭 2] 골든크로스 & 돌파 임박 종목 카드 리스트
# ---------------------------------------------------------
with tab2:
    filter_opt = st.radio(
        "🔍 표시할 종목 그룹 선택",
        ["🔥 골든크로스 + ⚡ 돌파 임박만 보기", "전체 종목 시그널 순으로 보기"],
        horizontal=True
    )

    if "돌파 임박만" in filter_opt:
        sub_df = df[df["sig_rank"].isin([1, 2])].sort_values(["sig_rank", "days_since_gc", "spread"], ascending=[True, True, False])
        if sub_df.empty:
            st.info("현재 설정된 엄격한 기준에 정확히 일치하는 돌파 종목이 없어, 이격도가 0%에 가장 가까운 상위 후보 종목들을 표시합니다.")
            sub_df = df.iloc[(df["spread"].abs()).argsort()].head(10)
    else:
        sub_df = df.sort_values(["sig_rank", "spread"], ascending=[True, False])

    for _, row in sub_df.iterrows():
        if row["sig_rank"] == 1:
            b_cls = "badge-gc"
        elif row["sig_rank"] == 2:
            b_cls = "badge-near"
        elif row["sig_rank"] == 3:
            b_cls = "badge-bull"
        else:
            b_cls = "badge-bear"

        gc_info = f"골든크로스 발생: <b>{row['gc_date']}</b> ({row['days_since_gc']}영업일 전)" if row["days_since_gc"] < 900 else "골든크로스 대기 중"
        chg_color = "#e12343" if row["change"] >= 0 else "#1964d8"

        st.markdown(f"""
        <div class="signal-card">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                <div>
                    <span class="{b_cls}">{row['signal']}</span>
                    <b style="font-size:1.15rem; margin-left:8px;">{row['name']}</b>
                    <span style="color:#868e96; font-weight:600;">({row['ticker']} · {row['theme']})</span>
                    <div style="font-size:0.88rem; color:#343a40; margin-top:8px;">
                        • <b>1년 역배열 유지율:</b> <span style="color:#c92a2a; font-weight:700;">{row['inv_ratio']}%</span> ({row['inv_days']}일 유지) &nbsp;|&nbsp;
                        • <b>{gc_info}</b><br>
                        • <b>40일선:</b> {row['ma40']:,} &nbsp;/&nbsp; <b>200일선:</b> {row['ma200']:,} &nbsp;|&nbsp;
                        • <b>이격도(40 vs 200):</b> <b>{row['spread']:+.2f}%</b>
                    </div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:1.15rem; font-weight:800;">{row['price_str']}</div>
                    <div style="color:{chg_color}; font-weight:700; font-size:0.95rem;">오늘 {row['change']:+.2f}%</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ---------------------------------------------------------
# [탭 3] 종목별 40일선 vs 200일선 1년 차트 직접 검수
# ---------------------------------------------------------
with tab3:
    st.subheader("종목별 40일선(단기) · 200일선(장기) 역배열 및 골든크로스 차트 검수")
    sorted_for_select = df.sort_values(["sig_rank", "inv_ratio"], ascending=[True, False])
    stock_options = [f"[{r['signal']}] {r['name']} ({r['ticker']})" for _, r in sorted_for_select.iterrows()]
    selected_option = st.selectbox("🔎 차트를 확인할 종목을 선택하세요", stock_options)

    sel_idx = stock_options.index(selected_option)
    sel_row = sorted_for_select.iloc[sel_idx]
    hist_df = pd.DataFrame(sel_row["history"])
    hist_df["Date"] = pd.to_datetime(hist_df["Date"])

    fig_ma = go.Figure()

    # 종가선 (연한 회색 실선)
    fig_ma.add_trace(go.Scatter(
        x=hist_df["Date"], y=hist_df["Close"],
        mode="lines", name="종가(현재가)",
        line=dict(color="#adb5bd", width=1.5)
    ))
    # 200일 이동평균선 (파란 굵은 점선)
    fig_ma.add_trace(go.Scatter(
        x=hist_df["Date"], y=hist_df["MA200"],
        mode="lines", name="200일 이동평균선 (기준선)",
        line=dict(color="#1d4ed8", width=3, dash="dot")
    ))
    # 40일 이동평균선 (빨간 굵은 실선)
    fig_ma.add_trace(go.Scatter(
        x=hist_df["Date"], y=hist_df["MA40"],
        mode="lines", name="40일 이동평균선 (돌파선)",
        line=dict(color="#e11d48", width=3.5)
    ))

    # 골든크로스 지점 별표(★) 표시
    cross_pts = hist_df[(hist_df["MA40"] >= hist_df["MA200"]) & (hist_df["MA40"].shift(1) < hist_df["MA200"].shift(1))]
    if not cross_pts.empty:
        fig_ma.add_trace(go.Scatter(
            x=cross_pts["Date"], y=cross_pts["MA40"],
            mode="markers+text", name="골든크로스 돌파 지점",
            text=["★ 골든크로스!"] * len(cross_pts),
            textposition="top center",
            marker=dict(symbol="star", size=16, color="#f59f00", line=dict(width=1.5, color="#191f28"))
        ))

    fig_ma.update_layout(
        title=f"<b>{sel_row['name']} ({sel_row['ticker']})</b> - 최근 1년 주가 및 40일·200일 이평선 추이 (1년 역배열 유지율: {sel_row['inv_ratio']}%)",
        xaxis_title="날짜",
        yaxis_title="주가",
        height=520,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_ma, use_container_width=True)

# ---------------------------------------------------------
# [탭 4] 앤트위키 4분면 이평선 궤적 차트
# ---------------------------------------------------------
with tab4:
    st.subheader("이평선 4분면 상대강도 궤적 (역배열 ➔ 돌파 임박 ➔ 골든크로스)")
    st.write("가운데 세로선(100)을 오른쪽으로 넘어가면 **40일선이 200일선을 돌파(골든크로스)**한 상태이며, 가로선(100) 위쪽은 **40일선이 빠르게 치고 올라오는 상승 가속 구간**입니다.")

    fig_q = go.Figure()
    quads = [
        (100, 120, 100, 120, "rgba(254,202,202,0.35)", "1사분면: 골든크로스 & 상승가속", 112, 117),
        (80, 100, 100, 120, "rgba(254,240,138,0.35)", "2사분면: 역배열 축소 (돌파 임박!)", 88, 117),
        (80, 100, 80, 100, "rgba(191,219,254,0.35)", "3사분면: 장기 역배열 (침체)", 88, 83),
        (100, 120, 80, 100, "rgba(233,213,255,0.35)", "4사분면: 정배열 중 탄력 둔화", 112, 83),
    ]
    for x0, x1, y0, y1, c, lbl, lx, ly in quads:
        fig_q.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=c, line=dict(width=0), layer="below")
        fig_q.add_annotation(x=lx, y=ly, text=f"<b>{lbl}</b>", showarrow=False)

    fig_q.add_hline(y=100, line_dash="dash", line_color="#475569")
    fig_q.add_vline(x=100, line_dash="dash", line_color="#475569")

    # 시그널 상위 12개 종목의 궤적 표시
    top_targets = df.sort_values(["sig_rank", "inv_ratio"], ascending=[True, False]).head(12)
    for _, r in top_targets.iterrows():
        xs = np.clip(r["traj_x"], 81, 119)
        ys = np.clip(r["traj_y"], 81, 119)
        fig_q.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="lines+markers+text",
            name=r["name"],
            text=["", "", "", "", r["name"]],
            textposition="top center",
            line=dict(width=3, shape="spline"),
            marker=dict(size=[5, 6, 7, 8, 14])
        ))

    fig_q.update_layout(
        xaxis=dict(title="40일·200일선 상대 이격 지수 (100 이상 = 정배열 돌파)", range=[80, 120]),
        yaxis=dict(title="40일선 추격 모멘텀 (100 이상 = 이격 축소·상승 가속)", range=[80, 120]),
        height=560,
        margin=dict(t=20, l=20, r=20, b=20)
    )
    st.plotly_chart(fig_q, use_container_width=True)
