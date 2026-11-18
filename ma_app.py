import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False

st.set_page_config(
    page_title="이평선 거래 - 1년 역배열 후 40·200일선 돌파 포착기",
    layout="wide",
    initial_sidebar_state="collapsed"
)

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
        background: #fff3bf; color: #d9480f; padding: 5px 12px;
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
# 1. 확장된 한국(80종목) & 미국(75종목) 스캔 유니버스
# ---------------------------------------------------------
KR_UNIVERSE = {
    "반도체·IT부품": [
        ("005930", "삼성전자"), ("000660", "SK하이닉스"), ("042700", "한미반도체"),
        ("036930", "주성엔지니어링"), ("058470", "리노공업"), ("000990", "DB하이텍"),
        ("403870", "HPSP"), ("039030", "이오테크닉스"), ("009150", "삼성전기"),
        ("011070", "LG이노텍"), ("066570", "LG전자"), ("034220", "LG디스플레이")
    ],
    "2차전지·화학·철강": [
        ("373220", "LG에너지솔루션"), ("006400", "삼성SDI"), ("051910", "LG화학"),
        ("247540", "에코프로비엠"), ("086520", "에코프로"), ("003670", "포스코퓨처엠"),
        ("066970", "엘앤에프"), ("005490", "POSCO홀딩스"), ("011170", "롯데케미칼"),
        ("010950", "S-Oil"), ("096770", "SK이노베이션"), ("009830", "한화솔루션")
    ],
    "인터넷·게임·통신": [
        ("035420", "NAVER"), ("035720", "카카오"), ("259960", "크래프톤"),
        ("036570", "엔씨소프트"), ("251270", "넷마블"), ("293490", "카카오게임즈"),
        ("263750", "펄어비스"), ("012510", "더존비즈온"), ("018260", "삼성에스디에스"),
        ("017670", "SK텔레콤"), ("030200", "KT"), ("032640", "LG유플러스")
    ],
    "바이오·헬스케어": [
        ("207940", "삼성바이오로직스"), ("068270", "셀트리온"), ("196170", "알테오젠"),
        ("128940", "한미약품"), ("000100", "유한양행"), ("326030", "SK바이오팜"),
        ("145020", "휴젤"), ("006280", "녹십자"), ("069620", "대웅제약"),
        ("185750", "종근당"), ("141080", "리가켐바이오"), ("214150", "클래시스")
    ],
    "자동차·조선·방산·전력": [
        ("005380", "현대차"), ("000270", "기아"), ("012330", "현대모비스"),
        ("011210", "현대위아"), ("267260", "HD현대일렉트릭"), ("010120", "LS ELECTRIC"),
        ("298040", "효성중공업"), ("012450", "한화에어로스페이스"), ("079550", "LIG넥스원"),
        ("047810", "한국항공우주"), ("009540", "HD한국조선해양"), ("329180", "HD현대중공업"),
        ("042660", "한화오션"), ("010140", "삼성중공업"), ("034020", "두산에너빌리티")
    ],
    "금융·엔터·소비재·인프라": [
        ("105560", "KB금융"), ("055550", "신한지주"), ("086790", "하나금융지주"),
        ("316140", "우리금융지주"), ("032830", "삼성생명"), ("352820", "하이브"),
        ("041510", "에스엠"), ("035900", "JYP Ent."), ("122870", "와이지엔터테인먼트"),
        ("090430", "아모레퍼시픽"), ("051900", "LG생활건강"), ("003230", "삼양식품"),
        ("097950", "CJ제일제당"), ("000720", "현대건설"), ("028260", "삼성물산"),
        ("003490", "대한항공"), ("015760", "한국전력")
    ]
}

US_UNIVERSE = {
    "AI·반도체": [
        ("NVDA", "엔비디아"), ("AMD", "AMD"), ("INTC", "인텔"), ("AVGO", "브로드컴"),
        ("QCOM", "퀄컴"), ("MU", "마이크론"), ("TSM", "TSMC"), ("ASML", "ASML"),
        ("TXN", "텍사스인스트루먼트"), ("AMAT", "어플라이드머티리얼즈"), ("LRCX", "램리서치"), ("KLAC", "KLA")
    ],
    "빅테크·소프트웨어": [
        ("AAPL", "애플"), ("MSFT", "마이크로소프트"), ("GOOGL", "알파벳"), ("AMZN", "아마존"),
        ("META", "메타"), ("NFLX", "넷플릭스"), ("ORCL", "오라클"), ("CRM", "세일즈포스"),
        ("ADBE", "어도비"), ("PLTR", "팔란티어"), ("SNOW", "스노우플레이크"),
        ("CRWD", "크라우드스트라이크"), ("PANW", "팔로알토네트웍스"), ("SHOP", "쇼피파이")
    ],
    "전기차·모빌리티·산업": [
        ("TSLA", "테슬라"), ("RIVN", "리비안"), ("LCID", "루시드"), ("F", "포드"),
        ("GM", "제너럴모터스"), ("UBER", "우버"), ("BA", "보잉"), ("CAT", "캐터필러"),
        ("GE", "GE에어로스페이스"), ("LMT", "록히드마틴"), ("RTX", "RTX"), ("RKLB", "로켓랩")
    ],
    "바이오·헬스케어": [
        ("LLY", "일라이릴리"), ("NVO", "노보노디스크"), ("PFE", "화이자"), ("MRNA", "모더나"),
        ("JNJ", "존슨앤드존슨"), ("UNH", "유나이티드헬스"), ("BMY", "브리스톨마이어스"),
        ("ABBV", "애브비"), ("MRK", "머크"), ("AMGN", "암젠"), ("GILD", "길리어드"), ("ISRG", "인튜이티브서지컬")
    ],
    "소비재·엔터·리테일": [
        ("NKE", "나이키"), ("SBUX", "스타벅스"), ("DIS", "디즈니"), ("MCD", "맥도날드"),
        ("KO", "코카콜라"), ("PEP", "펩시코"), ("WMT", "월마트"), ("COST", "코스트코"),
        ("TGT", "타겟"), ("LULU", "룰루레몬"), ("HD", "홈디포")
    ],
    "금융·핀테크·에너지": [
        ("JPM", "JP모건"), ("BAC", "뱅크오브아메리카"), ("V", "비자"), ("MA", "마스터카드"),
        ("PYPL", "페이팔"), ("COIN", "코인베이스"), ("HOOD", "로빈후드"), ("SOFI", "소파이"),
        ("XOM", "엑슨모빌"), ("CVX", "셰브론"), ("ENPH", "엔페이즈에너지"),
        ("NEE", "넥스트에라에너지"), ("ALB", "앨버말"), ("CEG", "컨스텔레이션에너지")
    ]
}

# ---------------------------------------------------------
# 2. 600영업일(약 2.5년) 일봉 수집 및 엄격한 1년 역배열 판별 엔진
# ---------------------------------------------------------
def fetch_kr_ohlcv_600d(ticker):
    url = f"https://fchart.stock.naver.com/sise.nhn?symbol={ticker}&timeframe=day&count=600&requestType=0"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=4) as res:
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


def analyze_strict_ma_strategy(df_ohlcv, inv_days=240, inv_ratio_thr=90.0, gc_window=15, near_spread_thr=3.5):
    """
    [정밀 판별 로직]
    1) 🔥 1년 역배열 후 골든크로스:
       - 현재 MA40 >= MA200 (돌파 상태 유지)
       - 최근 gc_window 영업일 이내에 MA40이 MA200을 상향 돌파
       - 돌파 직전 1년(inv_days) 동안 MA40 < MA200 유지 비율 >= inv_ratio_thr
    2) ⚡ 1년 역배열 후 돌파 임박 (접근 중):
       - 현재 MA40 < MA200 (아직 역배열 상태)
       - 오늘 기준 과거 1년(inv_days) 동안 MA40 < MA200 유지 비율 >= inv_ratio_thr
       - 현재 이격도((MA40-MA200)/MA200*100)가 [-near_spread_thr%, 0%) 범위 이내
       - 최근 5영업일 및 10영업일 대비 이격도가 실제로 축소되며(상승 접근) MA40이 200일선으로 수렴 중
    """
    if df_ohlcv is None or len(df_ohlcv) < 200 + int(inv_days * 0.85):
        return None

    df = df_ohlcv.sort_values("Date").reset_index(drop=True).copy()
    df["MA40"] = df["Close"].rolling(40).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    df = df.dropna(subset=["MA200"]).reset_index(drop=True)

    min_required = int(inv_days * 0.85)
    if len(df) < min_required + 5:
        return None

    df["Spread"] = ((df["MA40"] - df["MA200"]) / df["MA200"]) * 100.0
    df["Spread_Diff5"] = df["Spread"].diff(5).fillna(0.0)
    df["Spread_Diff10"] = df["Spread"].diff(10).fillna(0.0)

    latest = df.iloc[-1]
    prev = df.iloc[-2]
    price = float(latest["Close"])
    prev_price = float(prev["Close"])
    change_pct = round(((price - prev_price) / prev_price) * 100, 2) if prev_price > 0 else 0.0
    est_turnover = price * float(latest["Volume"])

    cur_spread = round(float(latest["Spread"]), 2)
    diff5 = round(float(latest["Spread_Diff5"]), 2)
    diff10 = round(float(latest["Spread_Diff10"]), 2)
    is_currently_above = float(latest["MA40"]) >= float(latest["MA200"])

    # 골든크로스 발생 지점 탐색
    cross_mask = (df["MA40"] >= df["MA200"]) & (df["MA40"].shift(1) < df["MA200"].shift(1))
    cross_indices = df.index[cross_mask].tolist()

    last_gc_idx = cross_indices[-1] if cross_indices else None
    days_since_gc = (len(df) - 1) - last_gc_idx if last_gc_idx is not None else 999
    gc_date_str = df.loc[last_gc_idx, "Date"].strftime("%Y-%m-%d") if last_gc_idx is not None else "-"

    # [검증 구간 A] 최근 골든크로스 직전 1년(inv_days) 역배열 유지율 계산
    pre_gc_inv_ratio = 0.0
    pre_gc_inv_days = 0
    pre_gc_total_days = 0
    check_start_date = df.iloc[max(0, len(df) - inv_days)]["Date"].strftime("%Y-%m-%d")
    check_end_date = df.iloc[-1]["Date"].strftime("%Y-%m-%d")

    if last_gc_idx is not None and last_gc_idx >= min_required:
        pre_start = max(0, last_gc_idx - inv_days)
        pre_slice = df.iloc[pre_start:last_gc_idx]
        pre_gc_total_days = len(pre_slice)
        pre_gc_inv_days = int((pre_slice["MA40"] < pre_slice["MA200"]).sum())
        pre_gc_inv_ratio = round((pre_gc_inv_days / pre_gc_total_days) * 100, 1)

    # [검증 구간 B] 오늘 기준 과거 1년(inv_days) 역배열 유지율 계산
    cur_start = max(0, len(df) - inv_days)
    cur_slice = df.iloc[cur_start:]
    cur_total_days = len(cur_slice)
    cur_inv_days = int((cur_slice["MA40"] < cur_slice["MA200"]).sum())
    cur_inv_ratio = round((cur_inv_days / cur_total_days) * 100, 1)

    # ---------------------------------------------------------
    # 최종 시그널 판정 (사용자 요청 2대 핵심 시그널만 엄격히 분류)
    # ---------------------------------------------------------
    is_signal_gc = (
        is_currently_above
        and last_gc_idx is not None
        and days_since_gc <= gc_window
        and pre_gc_total_days >= min_required
        and pre_gc_inv_ratio >= inv_ratio_thr
    )

    is_signal_near = (
        (not is_currently_above)
        and (-near_spread_thr <= cur_spread < 0.0)
        and (diff5 > 0.0)
        and (diff10 > 0.0 or diff5 >= 0.3)
        and (cur_inv_ratio >= inv_ratio_thr)
    )

    if is_signal_gc:
        signal = "🔥 1년 역배열 → 골든크로스"
        sig_rank = 1
        final_inv_ratio = pre_gc_inv_ratio
        final_inv_days = pre_gc_inv_days
        final_check_days = pre_gc_total_days
        check_start_date = df.iloc[max(0, last_gc_idx - inv_days)]["Date"].strftime("%Y-%m-%d")
        check_end_date = df.iloc[last_gc_idx]["Date"].strftime("%Y-%m-%d")
        status_detail = f"돌파일: {gc_date_str} ({days_since_gc}영업일 전 돌파)"
    elif is_signal_near:
        signal = "⚡ 1년 역배열 → 돌파 임박"
        sig_rank = 2
        final_inv_ratio = cur_inv_ratio
        final_inv_days = cur_inv_days
        final_check_days = cur_total_days
        # 현재 접근 속도 기준 예상 돌파 소요일 추정
        daily_close_speed = diff5 / 5.0
        est_days = max(1, int(abs(cur_spread) / daily_close_speed)) if daily_close_speed > 0.02 else 99
        est_text = f"약 {est_days}영업일 내 돌파 추세" if est_days <= 25 else "200일선 근접 수렴 중"
        status_detail = f"200일선까지 {cur_spread:.2f}% 남음 (5일간 +{diff5:.2f}%p 접근 · {est_text})"
    elif is_currently_above:
        signal = "☀️ 일반 정배열 (대상 외)"
        sig_rank = 3
        final_inv_ratio = pre_gc_inv_ratio if last_gc_idx is not None else cur_inv_ratio
        final_inv_days = pre_gc_inv_days if last_gc_idx is not None else cur_inv_days
        final_check_days = pre_gc_total_days if pre_gc_total_days > 0 else cur_total_days
        status_detail = f"정배열 유지 중 (직전 1년 역배열 {final_inv_ratio}%)"
    else:
        signal = "🌧️ 장기 역배열 (대기 구간)"
        sig_rank = 4
        final_inv_ratio = cur_inv_ratio
        final_inv_days = cur_inv_days
        final_check_days = cur_total_days
        trend_txt = f"5일간 +{diff5:.2f}%p 접근 중" if diff5 > 0 else f"5일간 {diff5:.2f}%p 이격 확대"
        status_detail = f"200일선까지 {cur_spread:.2f}% ({trend_txt})"

    # 4분면 궤적 데이터 (최근 20영업일간 5포인트)
    step_indices = [max(0, len(df) - 1 - i * 4) for i in range(4, -1, -1)]
    traj_x = [round(100 + float(df.loc[idx, "Spread"]), 2) for idx in step_indices]
    traj_y = [round(100 + float(df.loc[idx, "Spread_Diff5"]) * 2.5, 2) for idx in step_indices]

    return {
        "price": price,
        "change": change_pct,
        "ma40": round(float(latest["MA40"]), 2),
        "ma200": round(float(latest["MA200"]), 2),
        "spread": cur_spread,
        "diff5": diff5,
        "inv_ratio": final_inv_ratio,
        "inv_days": final_inv_days,
        "check_days": final_check_days,
        "days_since_gc": days_since_gc,
        "gc_date": gc_date_str,
        "signal": signal,
        "sig_rank": sig_rank,
        "status_detail": status_detail,
        "check_start_date": check_start_date,
        "check_end_date": check_end_date,
        "turnover": est_turnover,
        "traj_x": traj_x,
        "traj_y": traj_y,
        "history": df.tail(320)[["Date", "Close", "MA40", "MA200", "Spread"]].to_dict("records")
    }


@st.cache_data(ttl=300)
def scan_market(is_kr, inv_days, inv_ratio_thr, gc_window, near_spread_thr, custom_tickers_str=""):
    universe = {k: list(v) for k, v in (KR_UNIVERSE if is_kr else US_UNIVERSE).items()}

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
        tasks = [(theme, tk, name) for theme, stocks in universe.items() for tk, name in stocks]

        def worker_kr(task):
            theme, ticker, name = task
            try:
                df_raw = fetch_kr_ohlcv_600d(ticker)
                res = analyze_strict_ma_strategy(df_raw, inv_days, inv_ratio_thr, gc_window, near_spread_thr)
                if res:
                    weight = max(int(res["turnover"] // 100_000_000), 50)
                    return {
                        "theme": theme, "ticker": ticker, "name": name,
                        "label": name,
                        "price_str": f"{int(res['price']):,}원",
                        "ma40_str": f"{int(res['ma40']):,}원",
                        "ma200_str": f"{int(res['ma200']):,}원",
                        "weight": weight, **res
                    }
            except Exception:
                return None
            return None

        with ThreadPoolExecutor(max_workers=12) as executor:
            futures = [executor.submit(worker_kr, t) for t in tasks]
            for f in as_completed(futures):
                r = f.result()
                if r:
                    results.append(r)
    else:
        all_tks = [tk for items in universe.values() for tk, _ in items]
        hist_all = None
        if YF_AVAILABLE and all_tks:
            try:
                hist_all = yf.download(
                    all_tks, period="3y", group_by="ticker", auto_adjust=True, progress=False, threads=True
                )
            except Exception:
                pass

        for theme, stocks in universe.items():
            for ticker, name in stocks:
                try:
                    if hist_all is not None and isinstance(hist_all.columns, pd.MultiIndex) and ticker in hist_all.columns.get_level_values(0):
                        df_tk = hist_all[ticker].dropna(subset=["Close"]).reset_index()
                        df_raw = pd.DataFrame({
                            "Date": pd.to_datetime(df_tk["Date"]),
                            "Close": df_tk["Close"].astype(float),
                            "Volume": df_tk["Volume"].astype(float)
                        })
                        res = analyze_strict_ma_strategy(df_raw, inv_days, inv_ratio_thr, gc_window, near_spread_thr)
                        if res:
                            weight = max(int(res["turnover"] // 1_000_000), 50)
                            results.append({
                                "theme": theme, "ticker": ticker, "name": name,
                                "label": f"{name}({ticker})",
                                "price_str": f"${res['price']:,.2f}",
                                "ma40_str": f"${res['ma40']:,.2f}",
                                "ma200_str": f"${res['ma200']:,.2f}",
                                "weight": weight, **res
                            })
                except Exception:
                    pass

    return pd.DataFrame(results), updated_at


# ---------------------------------------------------------
# 3. 상단 헤더 & 정밀 조건 설정 컨트롤러
# ---------------------------------------------------------
head_col1, head_col2 = st.columns([4, 1])
with head_col1:
    st.title("📈 이평선 거래 : 1년 역배열 후 40·200일선 돌파 포착기")
    st.caption("과거 1년간(약 240영업일) 40일선·200일선 역배열을 유지하다 ① 최근 골든크로스가 발생했거나 ② 200일선 턱밑까지 올라온 돌파 임박 종목만 정밀 포착합니다.")
with head_col2:
    if st.button("🔄 전 종목 재스캔", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with st.expander("⚙️ 정밀 탐색 조건 설정 (클릭해서 기준 미세 조정)", expanded=True):
    r1_c1, r1_c2 = st.columns([1.2, 2.0])
    with r1_c1:
        mkt = st.radio("🌐 분석 시장", ["🇰🇷 한국 주식 (80종목)", "🇺🇸 미국 주식 (75종목)"], horizontal=True)
    with r1_c2:
        custom_input = st.text_input("➕ 관심 종목 추가 스캔 (쉼표 구분)", placeholder="예: 005930, 035720 또는 TSLA, IONQ")

    r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
    with r2_c1:
        inv_days = st.slider("📅 역배열 체크 기간(영업일)", 180, 260, 240, step=10,
                             help="1년은 약 240~250영업일입니다.")
    with r2_c2:
        inv_ratio_thr = st.slider("📏 1년 중 역배열 유지 비율(%)", 70, 100, 90, step=5,
                                  help="100%로 올리면 1년 내내 단 하루도 빠짐없이 역배열이었던 종목만 찾습니다.")
    with r2_c3:
        gc_window = st.slider("🔥 골든크로스 최근 인정 기간(영업일)", 5, 40, 15, step=5,
                              help="최근 며칠 이내에 돌파한 종목을 '최근 골든크로스'로 볼지 설정합니다.")
    with r2_c4:
        near_spread_thr = st.slider("⚡ 돌파 임박 이격도 기준(-%)", 1.0, 6.0, 3.5, step=0.5,
                                    help="40일선이 200일선 아래 몇 % 이내로 접근했을 때 '돌파 임박'으로 볼지 설정합니다.")

is_kr = "한국" in mkt
with st.spinner("최근 600영업일(2.5년) 일봉을 불러와 1년 역배열 유지 여부와 골든크로스를 계산 중입니다..."):
    df, updated_at = scan_market(is_kr, inv_days, inv_ratio_thr, gc_window, near_spread_thr, custom_input)

if df.empty:
    st.error("데이터를 불러오지 못했습니다. 잠시 후 '전 종목 재스캔' 버튼을 눌러주세요.")
    st.stop()

# 핵심 요약 카드
gc_cnt = int((df["sig_rank"] == 1).sum())
near_cnt = int((df["sig_rank"] == 2).sum())
bull_cnt = int((df["sig_rank"] == 3).sum())
bear_cnt = int((df["sig_rank"] == 4).sum())

m1, m2, m3, m4 = st.columns(4)
m1.metric("🔥 1년 역배열 → 골든크로스", f"{gc_cnt}종목", f"최근 {gc_window}일 내 돌파")
m2.metric("⚡ 1년 역배열 → 돌파 임박", f"{near_cnt}종목", f"-{near_spread_thr}% 이내 상승 접근")
m3.metric("☀️ 일반 정배열 (대상 외)", f"{bull_cnt}종목", "이미 정배열 진행")
m4.metric("🌧️ 장기 역배열 (대기)", f"{bear_cnt}종목", "아직 이격 큼/하락 중")

st.divider()

# ---------------------------------------------------------
# 4. 앤트위키 스타일 4대 화면 탭
# ---------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "① 시그널 지도로 한눈에 (히트맵)",
    "② 포착 종목 정밀 리스트 (🔥돌파 · ⚡임박)",
    "③ 1년 역배열·돌파 차트 검수",
    "④ 이평선 4분면 접근 궤적"
])

ma_colorscale = [
    [0.0, "#1d4ed8"], [0.3, "#93c5fd"], [0.5, "#f8fafc"], [0.7, "#fca5a5"], [1.0, "#dc2626"]
]

# [탭 1] 앤트위키 트리맵 히트맵
with tab1:
    h_c1, h_c2 = st.columns([2, 2])
    with h_c1:
        map_scope = st.radio(
            "🗺️ 지도 표시 범위",
            ["🎯 포착 종목만 집중 보기 (🔥돌파 + ⚡임박)", "🌐 전체 종목 시그널별로 보기", "🏷️ 전체 종목 테마별로 보기"],
            horizontal=True
        )
    with h_c2:
        color_metric = st.radio("🎨 타일 색상 기준", ["40·200일선 이격도(%)", "오늘 주가 등락률(%)"], horizontal=True)

    if "집중 보기" in map_scope:
        map_df = df[df["sig_rank"].isin([1, 2])].copy()
        path_cols = [px.Constant("핵심 포착 종목"), "signal", "label"]
        if map_df.empty:
            st.info(f"현재 조건(1년 역배열 {inv_ratio_thr}% 이상)에 딱 맞는 돌파/임박 종목이 0개입니다. 아래에 조건에 가장 근접한 예비 후보 15종목의 지도를 대신 표시합니다. (상단 슬라이더에서 유지 비율을 낮추거나 이격도 기준을 넓혀보세요.)")
            map_df = df[(df["inv_ratio"] >= max(50, inv_ratio_thr - 25)) & (df["spread"] <= 5.0)].sort_values("spread", ascending=False).head(15)
            path_cols = [px.Constant("조건 근접 예비 후보"), "signal", "label"]
    elif "시그널별" in map_scope:
        map_df = df.copy()
        path_cols = [px.Constant("전체 시장"), "signal", "label"]
    else:
        map_df = df.copy()
        path_cols = [px.Constant("전체 시장"), "theme", "label"]

    color_col = "spread" if "이격도" in color_metric else "change"
    rng = [-8, 8] if color_col == "spread" else [-5, 5]

    if not map_df.empty:
        fig_tree = px.treemap(
            map_df,
            path=path_cols,
            values="weight",
            color=color_col,
            color_continuous_scale=ma_colorscale,
            color_continuous_midpoint=0,
            range_color=rng,
            custom_data=["price_str", "change", "spread", "inv_ratio", "signal", "status_detail"]
        )
        fig_tree.update_traces(
            texttemplate="<b>%{label}</b><br>%{customdata[0]} (%{customdata[1]:+.2f}%)<br>이격도: %{customdata[2]:+.2f}%",
            textposition="middle center",
            hovertemplate=(
                "<b>%{label}</b><br>"
                "시그널: %{customdata[4]}<br>"
                "상세: %{customdata[5]}<br>"
                "현재가: %{customdata[0]} (%{customdata[1]:+.2f}%)<br>"
                "40·200일 이격도: %{customdata[2]:+.2f}%<br>"
                "1년 역배열 유지율: %{customdata[3]}%<extra></extra>"
            )
        )
        fig_tree.update_layout(margin=dict(t=20, l=10, r=10, b=10), height=560)
        st.plotly_chart(fig_tree, use_container_width=True)

# [탭 2] 포착 종목 정밀 카드 리스트
with tab2:
    filter_opt = st.radio(
        "🔍 필터 선택",
        ["🎯 핵심 타겟만 (🔥골든크로스 + ⚡돌파 임박)", "🔥 골든크로스 돌파만", "⚡ 돌파 임박만", "📋 1년 역배열 예비 후보 포함 전체 보기"],
        horizontal=True
    )

    if "핵심 타겟만" in filter_opt:
        sub_df = df[df["sig_rank"].isin([1, 2])].sort_values(["sig_rank", "days_since_gc", "spread"], ascending=[True, True, False])
    elif "골든크로스 돌파만" in filter_opt:
        sub_df = df[df["sig_rank"] == 1].sort_values(["days_since_gc", "inv_ratio"], ascending=[True, False])
    elif "돌파 임박만" in filter_opt:
        sub_df = df[df["sig_rank"] == 2].sort_values(["spread", "diff5"], ascending=[False, False])
    else:
        sub_df = df.sort_values(["sig_rank", "inv_ratio", "spread"], ascending=[True, False, False])

    if sub_df.empty:
        st.warning(f"현재 설정한 엄격 기준(1년 중 역배열 {inv_ratio_thr}% 이상, 이격도 -{near_spread_thr}% 이내, 최근 {gc_window}일 돌파)에 정확히 일치하는 종목이 없습니다.")
        st.markdown("#### 💡 조건에 가장 근접한 예비 후보 TOP 10 (역배열 70% 이상 & 200일선 근접 순)")
        sub_df = df[(df["inv_ratio"] >= 70.0) & (df["spread"] < 3.0)].sort_values(["spread", "diff5"], ascending=[False, False]).head(10)

    for _, row in sub_df.iterrows():
        b_cls = "badge-gc" if row["sig_rank"] == 1 else "badge-near" if row["sig_rank"] == 2 else "badge-bull" if row["sig_rank"] == 3 else "badge-bear"
        chg_color = "#e12343" if row["change"] >= 0 else "#1964d8"

        st.markdown(f"""
        <div class="signal-card">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                <div>
                    <span class="{b_cls}">{row['signal']}</span>
                    <b style="font-size:1.15rem; margin-left:8px;">{row['name']}</b>
                    <span style="color:#868e96; font-weight:600;">({row['ticker']} · {row['theme']})</span>
                    <div style="font-size:0.88rem; color:#343a40; margin-top:8px; line-height:1.6;">
                        • <b>1년 역배열 검증:</b> <span style="color:#c92a2a; font-weight:800;">{row['inv_ratio']}%</span> ({row['check_days']}영업일 중 {row['inv_days']}일 역배열 · 구간: {row['check_start_date']} ~ {row['check_end_date']})<br>
                        • <b>시그널 상태:</b> <b>{row['status_detail']}</b><br>
                        • <b>40일선:</b> {row['ma40_str']} &nbsp;/&nbsp; <b>200일선:</b> {row['ma200_str']} &nbsp;|&nbsp;
                        <b>현재 이격도:</b> <b>{row['spread']:+.2f}%</b> (최근 5일 변화: {row['diff5']:+.2f}%p)
                    </div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:1.15rem; font-weight:800;">{row['price_str']}</div>
                    <div style="color:{chg_color}; font-weight:700; font-size:0.95rem;">오늘 {row['change']:+.2f}%</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# [탭 3] 종목별 1년 역배열 구간 음영 + 40·200일선 정밀 차트 검수
with tab3:
    st.subheader("종목별 1년 역배열 유지 구간 & 40·200일선 골든크로스 차트 검수")
    sorted_for_select = df.sort_values(["sig_rank", "inv_ratio", "spread"], ascending=[True, False, False])
    stock_options = [f"[{r['signal']}] {r['name']} ({r['ticker']}) - 역배열 {r['inv_ratio']}%, 이격도 {r['spread']:+.2f}%" for _, r in sorted_for_select.iterrows()]
    selected_option = st.selectbox("🔎 차트를 검수할 종목을 선택하세요 (포착 종목이 맨 위에 표시됩니다)", stock_options)

    sel_row = sorted_for_select.iloc[stock_options.index(selected_option)]
    hist_df = pd.DataFrame(sel_row["history"])
    hist_df["Date"] = pd.to_datetime(hist_df["Date"])

    fig_ma = go.Figure()

    # 1년 역배열 체크 구간 음영 강조
    fig_ma.add_vrect(
        x0=sel_row["check_start_date"],
        x1=sel_row["check_end_date"],
        fillcolor="rgba(190, 227, 248, 0.25)",
        line_width=0,
        annotation_text=f"1년 역배열 검증 구간 ({sel_row['inv_ratio']}% 유지)",
        annotation_position="top left"
    )

    fig_ma.add_trace(go.Scatter(
        x=hist_df["Date"], y=hist_df["Close"],
        mode="lines", name="종가(주가)",
        line=dict(color="#adb5bd", width=1.4)
    ))
    fig_ma.add_trace(go.Scatter(
        x=hist_df["Date"], y=hist_df["MA200"],
        mode="lines", name="200일 이동평균선 (장기 기준선)",
        line=dict(color="#1d4ed8", width=3, dash="dot")
    ))
    fig_ma.add_trace(go.Scatter(
        x=hist_df["Date"], y=hist_df["MA40"],
        mode="lines", name="40일 이동평균선 (단기 돌파선)",
        line=dict(color="#e11d48", width=3.5)
    ))

    # 골든크로스 발생 지점 별표(★) 표시
    cross_pts = hist_df[(hist_df["MA40"] >= hist_df["MA200"]) & (hist_df["MA40"].shift(1) < hist_df["MA200"].shift(1))]
    if not cross_pts.empty:
        fig_ma.add_trace(go.Scatter(
            x=cross_pts["Date"], y=cross_pts["MA40"],
            mode="markers+text", name="골든크로스 돌파 지점",
            text=["★ 골든크로스!"] * len(cross_pts),
            textposition="top center",
            marker=dict(symbol="star", size=17, color="#f59f00", line=dict(width=1.5, color="#191f28"))
        ))

    fig_ma.update_layout(
        title=f"<b>{sel_row['name']} ({sel_row['ticker']})</b> | {sel_row['signal']} · {sel_row['status_detail']}",
        xaxis_title="날짜 (최근 약 1.3년)",
        yaxis_title="주가",
        height=540,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_ma, use_container_width=True)

# [탭 4] 앤트위키 4분면 이평선 접근 궤적
with tab4:
    st.subheader("이평선 4분면 상대강도 궤적 (장기 역배열 ➔ 돌파 임박 ➔ 골든크로스)")
    st.write("파란색 3사분면(장기 역배열)에서 **노란색 2사분면(돌파 임박·접근 중)**을 거쳐 **빨간색 1사분면(골든크로스 돌파)**으로 넘어오는 시계 방향 궤적을 추적합니다.")

    fig_q = go.Figure()
    quads = [
        (100, 115, 100, 115, "rgba(254,202,202,0.35)", "1사분면: 🔥 골든크로스 돌파 & 상승가속", 107.5, 113.5),
        (85, 100, 100, 115, "rgba(254,240,138,0.35)", "2사분면: ⚡ 돌파 임박 (200일선 접근 중)", 92.5, 113.5),
        (85, 100, 85, 100, "rgba(191,219,254,0.35)", "3사분면: 🌧️ 장기 역배열 침체", 92.5, 86.5),
        (100, 115, 85, 100, "rgba(233,213,255,0.35)", "4사분면: 정배열 중 탄력 둔화", 107.5, 86.5),
    ]
    for x0, x1, y0, y1, c, lbl, lx, ly in quads:
        fig_q.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=c, line=dict(width=0), layer="below")
        fig_q.add_annotation(x=lx, y=ly, text=f"<b>{lbl}</b>", showarrow=False)

    fig_q.add_hline(y=100, line_dash="dash", line_color="#475569")
    fig_q.add_vline(x=100, line_dash="dash", line_color="#475569")

    # 포착 종목 우선 표시 + 부족하면 역배열 근접 상위 종목 보강
    targets = df[df["sig_rank"].isin([1, 2])].sort_values(["sig_rank", "spread"], ascending=[True, False])
    if len(targets) < 10:
        runners_up = df[(~df.index.isin(targets.index)) & (df["inv_ratio"] >= 70.0)].sort_values("spread", ascending=False).head(10 - len(targets))
        targets = pd.concat([targets, runners_up])

    for _, r in targets.head(14).iterrows():
        xs = np.clip(r["traj_x"], 85.5, 114.5)
        ys = np.clip(r["traj_y"], 85.5, 114.5)
        fig_q.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="lines+markers+text",
            name=f"{r['name']} ({r['spread']:+.1f}%)",
            text=["", "", "", "", r["name"]],
            textposition="top center",
            line=dict(width=3, shape="spline"),
            marker=dict(size=[5, 6, 7, 8, 14])
        ))

    fig_q.update_layout(
        xaxis=dict(title="40·200일선 이격 지수 (100 = 정확히 교차 / 100 이상 = 골든크로스)", range=[85, 115]),
        yaxis=dict(title="접근 모멘텀 (100 이상 = 40일선이 200일선 향해 상승 접근 중)", range=[85, 115]),
        height=560,
        margin=dict(t=20, l=20, r=20, b=20)
    )
    st.plotly_chart(fig_q, use_container_width=True)
