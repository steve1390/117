import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import urllib.request
import json
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

st.set_page_config(
    page_title="이평선 거래 - 스윙 확인 포착형 스크리너",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
    .card-box {
        background: #ffffff;
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 14px;
        border: 1px solid #e5e8eb;
        box-shadow: 0 2px 10px rgba(0,0,0,0.04);
    }
    .grade-top { background: #ffe3e3; color: #c92a2a; padding: 4px 10px; border-radius: 16px; font-weight: 800; font-size: 0.85rem; }
    .grade-cand { background: #fff3bf; color: #d9480f; padding: 4px 10px; border-radius: 16px; font-weight: 800; font-size: 0.85rem; }
    .grade-watch { background: #e7f5ff; color: #1864ab; padding: 4px 10px; border-radius: 16px; font-weight: 800; font-size: 0.85rem; }
    .grade-excl { background: #f1f3f5; color: #868e96; padding: 4px 10px; border-radius: 16px; font-weight: 700; font-size: 0.85rem; }
    .tag-sig { background: #212529; color: #ffffff; padding: 4px 10px; border-radius: 16px; font-weight: 700; font-size: 0.8rem; margin-left: 6px; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 0. 예비 폴백 종목 리스트 (API 일시 지연 시에도 정상 작동)
# ---------------------------------------------------------
FALLBACK_STOCKS = [
    {"code": "005930", "name": "삼성전자", "market": "코스피", "mcap": 3500000},
    {"code": "000660", "name": "SK하이닉스", "market": "코스피", "mcap": 1300000},
    {"code": "373220", "name": "LG에너지솔루션", "market": "코스피", "mcap": 900000},
    {"code": "005380", "name": "현대차", "market": "코스피", "mcap": 500000},
    {"code": "000270", "name": "기아", "market": "코스피", "mcap": 400000},
    {"code": "035420", "name": "NAVER", "market": "코스피", "mcap": 300000},
    {"code": "035720", "name": "카카오", "market": "코스피", "mcap": 180000},
    {"code": "006400", "name": "삼성SDI", "market": "코스피", "mcap": 200000},
    {"code": "051910", "name": "LG화학", "market": "코스피", "mcap": 220000},
    {"code": "005490", "name": "POSCO홀딩스", "market": "코스피", "mcap": 260000},
    {"code": "068270", "name": "셀트리온", "market": "코스피", "mcap": 400000},
    {"code": "207940", "name": "삼성바이오로직스", "market": "코스피", "mcap": 650000},
    {"code": "003670", "name": "포스코퓨처엠", "market": "코스피", "mcap": 150000},
    {"code": "096770", "name": "SK이노베이션", "market": "코스피", "mcap": 120000},
    {"code": "011170", "name": "롯데케미칼", "market": "코스피", "mcap": 40000},
    {"code": "036570", "name": "엔씨소프트", "market": "코스피", "mcap": 45000},
    {"code": "090430", "name": "아모레퍼시픽", "market": "코스피", "mcap": 75000},
    {"code": "051900", "name": "LG생활건강", "market": "코스피", "mcap": 55000},
    {"code": "352820", "name": "하이브", "market": "코스피", "mcap": 85000},
    {"code": "066570", "name": "LG전자", "market": "코스피", "mcap": 150000},
    {"code": "009150", "name": "삼성전기", "market": "코스피", "mcap": 100000},
    {"code": "011070", "name": "LG이노텍", "market": "코스피", "mcap": 50000},
    {"code": "034220", "name": "LG디스플레이", "market": "코스피", "mcap": 50000},
    {"code": "009830", "name": "한화솔루션", "market": "코스피", "mcap": 40000},
    {"code": "247540", "name": "에코프로비엠", "market": "코스닥", "mcap": 150000},
    {"code": "086520", "name": "에코프로", "market": "코스닥", "mcap": 100000},
    {"code": "196170", "name": "알테오젠", "market": "코스닥", "mcap": 180000},
    {"code": "066970", "name": "엘앤에프", "market": "코스닥", "mcap": 40000},
    {"code": "058470", "name": "리노공업", "market": "코스닥", "mcap": 30000},
    {"code": "403870", "name": "HPSP", "market": "코스닥", "mcap": 25000},
    {"code": "036930", "name": "주성엔지니어링", "market": "코스닥", "mcap": 16000},
    {"code": "263750", "name": "펄어비스", "market": "코스닥", "mcap": 25000},
    {"code": "293490", "name": "카카오게임즈", "market": "코스닥", "mcap": 15000},
    {"code": "041510", "name": "에스엠", "market": "코스닥", "mcap": 18000},
    {"code": "035900", "name": "JYP Ent.", "market": "코스닥", "mcap": 22000},
    {"code": "122870", "name": "와이지엔터테인먼트", "market": "코스닥", "mcap": 9000},
]

# ---------------------------------------------------------
# 2단계: 종목 검색 대상 제외 필터 (ETF/ETN/ELW/SPAC/우선주/관리·정지)
# ---------------------------------------------------------
EXCLUDE_KEYWORDS = [
    "스팩", "SPAC", "ETF", "ETN", "ELW", "리츠", "인버스", "레버리지", "선물",
    "KODEX", "TIGER", "KBSTAR", "RISE", "ACE", "SOL", "HANARO", "ARIRANG",
    "PLUS", "KOSEF", "KIWOOM", "TIMEFOLIO", "WOORI", "TREX", "SMART", "FOCUS",
    "인프라", "맥쿼리", "펀드", "채권", "국고채", "회사채", "단기채"
]

def is_excluded_stock(code, name, raw_item=None):
    """요구사항 2번: 검색 제외 대상 판별"""
    if not code or len(code) != 6 or not code.isdigit():
        return True, "코드 형식 부적합"
    # 우선주 및 종류주식 제외 (보통주는 끝자리가 0)
    if code[-1] != "0":
        return True, "우선주/종류주식"
    upper_name = name.upper()
    if any(k in upper_name for k in EXCLUDE_KEYWORDS):
        return True, "ETF/ETN/SPAC/리츠"
    if name.endswith(("우", "우B", "우C", "1우", "2우", "3우B", "(전환)")):
        return True, "우선주"
    # 네이버 API 상태 필드 기반 거래정지·관리·투자위험·상장폐지 제외
    if raw_item:
        end_type = str(raw_item.get("stockEndType", "stock")).lower()
        if end_type != "stock":
            return True, f"비일반종목({end_type})"
        stop_info = raw_item.get("tradeStopType")
        if isinstance(stop_info, dict) and str(stop_info.get("code", "1")) not in ("1", "", "None"):
            return True, "거래정지"
        for risk_key in ["management", "investCaution", "investWarning", "investRisk", "delisting"]:
            val = raw_item.get(risk_key)
            if val is True or str(val).upper() in ("Y", "TRUE", "1"):
                return True, f"위험/관리종목({risk_key})"
    return False, ""


@st.cache_data(ttl=1800)
def fetch_krx_universe(kospi_count=120, kosdaq_count=120, min_mcap_eok=1000):
    """코스피/코스닥 시가총액 상위 종목 리스트 자동 수집 및 1차 제외 필터 적용"""
    stocks = []
    seen = set()

    def fetch_market(market_api, market_kr, limit_cnt):
        page = 1
        page_size = 100
        collected = []
        while len(collected) < limit_cnt and page <= 8:
            url = f"https://m.stock.naver.com/api/stocks/marketValue/{market_api}?page={page}&pageSize={page_size}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            try:
                with urllib.request.urlopen(req, timeout=4) as res:
                    payload = json.loads(res.read().decode("utf-8"))
                items = payload.get("stocks", [])
                if not items:
                    break
                for it in items:
                    code = str(it.get("itemCode", "")).strip()
                    name = str(it.get("stockName", "")).strip()
                    if not code or code in seen:
                        continue
                    excluded, _ = is_excluded_stock(code, name, it)
                    if excluded:
                        continue
                    # 시가총액 (억원 단위 파싱)
                    mcap_raw = str(it.get("marketValue", "0")).replace(",", "").strip()
                    mcap_eok = float(mcap_raw) if mcap_raw.replace(".", "", 1).isdigit() else 0.0
                    if mcap_eok > 0 and mcap_eok < min_mcap_eok:
                        continue
                    seen.add(code)
                    collected.append({
                        "code": code,
                        "name": name,
                        "market": market_kr,
                        "mcap": int(mcap_eok)
                    })
                    if len(collected) >= limit_cnt:
                        break
                page += 1
            except Exception:
                break
        return collected

    if kospi_count > 0:
        stocks.extend(fetch_market("KOSPI", "코스피", kospi_count))
    if kosdaq_count > 0:
        stocks.extend(fetch_market("KOSDAQ", "코스닥", kosdaq_count))

    if not stocks:
        stocks = [s for s in FALLBACK_STOCKS if s["mcap"] >= min_mcap_eok]

    return stocks


def fetch_ohlcv_3y(code):
    """최근 750거래일(약 3년) 일봉 OHLCV 수집"""
    url = f"https://fchart.stock.naver.com/sise.nhn?symbol={code}&timeframe=day&count=750&requestType=0"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=4) as res:
        xml_data = res.read().decode("euc-kr", errors="ignore")
    root = ET.fromstring(xml_data)
    rows = []
    for item in root.findall(".//item"):
        parts = item.attrib.get("data", "").split("|")
        if len(parts) >= 6:
            dt, o, h, l, c, v = parts[:6]
            try:
                o_f, h_f, l_f, c_f, v_f = float(o), float(h), float(l), float(c), float(v)
                if c_f <= 0 or h_f <= 0 or l_f <= 0 or h_f < l_f:
                    continue
                rows.append({
                    "Date": pd.to_datetime(dt, format="%Y%m%d"),
                    "Open": o_f, "High": h_f, "Low": l_f, "Close": c_f, "Volume": v_f
                })
            except ValueError:
                continue
    return pd.DataFrame(rows)


# ---------------------------------------------------------
# 5단계 보조지표 계산 엔진 (RSI, MACD, ATR, 볼린저밴드, ADX)
# ---------------------------------------------------------
def add_technical_indicators(df):
    df = df.sort_values("Date").reset_index(drop=True).copy()

    # 이동평균선 (40일, 200일)
    df["MA40"] = df["Close"].rolling(40).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    df["MA_Dist"] = ((df["MA40"] - df["MA200"]) / df["MA200"]) * 100.0

    # 거래량 이동평균 & 거래대금(억원)
    df["Vol_MA5"] = df["Volume"].rolling(5).mean()
    df["Vol_MA20"] = df["Volume"].rolling(20).mean()
    df["TradingVal_Eok"] = (df["Close"] * df["Volume"]) / 1e8

    # RSI(14)
    delta = df["Close"].diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI14"] = (100.0 - (100.0 / (1.0 + rs))).fillna(50.0)

    # MACD(12, 26, 9)
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Sig"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Sig"]

    # ATR(14) & 단기/중기 ATR 비교
    tr1 = df["High"] - df["Low"]
    tr2 = (df["High"] - df["Close"].shift(1)).abs()
    tr3 = (df["Low"] - df["Close"].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["ATR14"] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    df["ATR10"] = tr.rolling(10).mean()
    df["ATR40"] = tr.rolling(40).mean()

    # 볼린저밴드(20, 2)
    bb_mid = df["Close"].rolling(20).mean()
    bb_std = df["Close"].rolling(20).std()
    df["BB_Upper"] = bb_mid + 2.0 * bb_std
    df["BB_Lower"] = bb_mid - 2.0 * bb_std
    df["BB_Width"] = ((df["BB_Upper"] - df["BB_Lower"]) / bb_mid.replace(0, np.nan)) * 100.0
    df["BB_Width_MA60"] = df["BB_Width"].rolling(60).mean()

    # ADX(14)
    up_move = df["High"].diff()
    down_move = -df["Low"].diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    plus_di = 100.0 * pd.Series(plus_dm, index=df.index).ewm(alpha=1/14, min_periods=14, adjust=False).mean() / df["ATR14"].replace(0, np.nan)
    minus_di = 100.0 * pd.Series(minus_dm, index=df.index).ewm(alpha=1/14, min_periods=14, adjust=False).mean() / df["ATR14"].replace(0, np.nan)
    dx = (100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)).fillna(0.0)
    df["ADX14"] = dx.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

    return df


# ---------------------------------------------------------
# 1단계 ~ 7단계 통합 정밀 분석 & 100점 채점 엔진
# ---------------------------------------------------------
def evaluate_stock(meta, df_raw, cfg):
    # 데이터 완전성 및 상장 250일 미만 제외 (최소 최근 2년 = 450거래일 권장, 200MA + 250일 체크)
    if df_raw is None or len(df_raw) < 450:
        return None
    if df_raw[["Open", "High", "Low", "Close", "Volume"]].isna().any().any():
        return None

    # 최근 5거래일 거래정지(거래량 0) 제외
    if (df_raw["Volume"].tail(5) == 0).any():
        return None

    df = add_technical_indicators(df_raw)
    valid = df.dropna(subset=["MA200", "ATR14", "BB_Width"]).reset_index(drop=True)
    if len(valid) < 250:
        return None

    latest = valid.iloc[-1]
    prev = valid.iloc[-2]
    price = float(latest["Close"])
    prev_close = float(prev["Close"])
    chg_pct = round(((price - prev_close) / prev_close) * 100.0, 2) if prev_close > 0 else 0.0

    # 유동성 체크 (최근 20일 평균 거래대금 & 당일 거래대금 & 시가총액)
    today_tval = float(latest["TradingVal_Eok"])
    avg20_tval = float(valid["TradingVal_Eok"].tail(20).mean())
    vol_ma20 = float(latest["Vol_MA20"]) if pd.notna(latest["Vol_MA20"]) else 0.0
    if vol_ma20 < cfg["min_vol_20"]:
        return None
    liquidity_ok = (avg20_tval >= cfg["min_tval_eok"] * 0.5) and (today_tval >= cfg["min_tval_eok"] or avg20_tval >= cfg["min_tval_eok"]) and (meta["mcap"] == 0 or meta["mcap"] >= cfg["min_mcap_eok"])

    # =========================================================
    # [1단계] 장기 하락 추세 확인 (총 15점)
    # =========================================================
    win250 = valid.tail(250)
    inv_days_250 = int((win250["MA40"] < win250["MA200"]).sum())
    high_1y = float(win250["High"].max())
    low_1y = float(win250["Low"].min())
    low_1y_idx = win250["Low"].idxmin()
    days_since_low_1y = int(valid.index[-1] - low_1y_idx)

    # 최근 1년 고점 대비 현재 하락률(%) & 고점 대비 최저점 하락률(%)
    drawdown_now = round(((high_1y - price) / high_1y) * 100.0, 2) if high_1y > 0 else 0.0
    drawdown_max = round(((high_1y - low_1y) / high_1y) * 100.0, 2) if high_1y > 0 else 0.0
    rebound_from_low = round(((price - low_1y) / low_1y) * 100.0, 2) if low_1y > 0 else 0.0

    # 200일선 기울기 변화 (최근 20일 vs 직전 20일)
    ma200_now = float(latest["MA200"])
    ma200_20 = float(valid.iloc[-21]["MA200"])
    ma200_40 = float(valid.iloc[-41]["MA200"])
    ma200_slope_20 = round(((ma200_now - ma200_20) / ma200_20) * 100.0, 2)
    ma200_slope_prev20 = round(((ma200_20 - ma200_40) / ma200_40) * 100.0, 2)
    ma200_decelerating = (ma200_slope_20 > ma200_slope_prev20) or (ma200_slope_20 >= -0.6)

    bottom_formed = (days_since_low_1y >= 10) and (rebound_from_low >= 3.0)
    long_downtrend_ok = inv_days_250 >= cfg["inv_min_days"]

    score_s1 = 0.0
    if inv_days_250 >= cfg["inv_min_days"]:
        score_s1 += 6.0 if inv_days_250 >= 210 else 5.0
    elif inv_days_250 >= int(cfg["inv_min_days"] * 0.85):
        score_s1 += 2.5

    if drawdown_now >= cfg["min_drawdown"]:
        score_s1 += 4.0
    elif drawdown_max >= cfg["min_drawdown"] + 5.0 and drawdown_now >= cfg["min_drawdown"] * 0.6:
        score_s1 += 2.5

    if bottom_formed:
        score_s1 += 3.0
    if ma200_decelerating:
        score_s1 += 2.0
    score_s1 = min(15.0, round(score_s1, 1))

    # =========================================================
    # [2단계] 바닥 형성 및 박스권 확인 (최근 20~60거래일, 총 20점)
    # =========================================================
    box_len = cfg["box_days"]
    # 돌파 확인을 위해 직전 1~3일 제외 박스권과 직전 1일 제외 박스권을 비교해 기준 박스 산정
    base_slice = valid.iloc[-(box_len + 3):-3]
    recent_3 = valid.iloc[-3:]

    # 만약 최근 3일 내 종가 돌파가 있었으면 base_slice를 박스권으로, 아니면 직전 1일 제외 구간을 박스권으로 사용
    cand_top_3 = float(base_slice["Close"].max())
    if (recent_3["Close"] > cand_top_3).any():
        box_df = base_slice
        post_break_df = recent_3
    else:
        box_df = valid.iloc[-(box_len + 1):-1]
        post_break_df = valid.iloc[-1:]

    box_raw_high = float(box_df["High"].max())
    box_raw_low = float(box_df["Low"].min())
    # 박스권 상단/하단 (종가 기준 주요 저항·지지 레벨)
    box_high = float(box_df["Close"].max())
    box_low = float(box_df["Low"].quantile(0.05))
    box_range_pct = round(((box_high - box_low) / box_low) * 100.0, 2) if box_low > 0 else 99.0

    # 저점 지속 하락 중단 확인 (후반부 저점 >= 전반부 저점 * 0.98)
    half = len(box_df) // 2
    first_half_low = float(box_df.iloc[:half]["Low"].min())
    second_half_low = float(box_df.iloc[half:]["Low"].min())
    higher_or_flat_low = second_half_low >= first_half_low * 0.98

    # 박스권 하단 반복 지지 (하단 +3% 이내 터치 후 하단 위 마감 횟수 >= 2)
    support_touches = int(((box_df["Low"] <= box_low * 1.035) & (box_df["Close"] >= box_low * 0.99)).sum())
    repeated_support = support_touches >= 2

    # 최근 변동성 축소 (ATR10 < ATR40 또는 BB 폭 축소)
    vol_contracted = (float(latest["ATR10"]) <= float(latest["ATR40"]) * 1.02) or (float(latest["BB_Width"]) < float(latest["BB_Width_MA60"]))

    # 박스권 하단 이탈 여부
    holding_box_low = (price >= box_low * 0.99) and (float(valid["Close"].tail(5).min()) >= box_low * 0.98)

    box_ok = (box_range_pct <= cfg["max_box_range"] + 5.0) and holding_box_low and (higher_or_flat_low or repeated_support)

    score_s2 = 0.0
    if box_range_pct <= cfg["max_box_range"] * 0.75:
        score_s2 += 5.0
    elif box_range_pct <= cfg["max_box_range"]:
        score_s2 += 4.0
    elif box_range_pct <= cfg["max_box_range"] + 8.0:
        score_s2 += 2.0

    if higher_or_flat_low:
        score_s2 += 4.0
    if repeated_support:
        score_s2 += 4.0
    elif support_touches >= 1:
        score_s2 += 2.0
    if vol_contracted:
        score_s2 += 4.0
    if holding_box_low:
        score_s2 += 3.0
    score_s2 = min(20.0, round(score_s2, 1))

    # =========================================================
    # [3단계] 이동평균선 분석 (40일 & 200일, 총 20점)
    # =========================================================
    ma40_now = float(latest["MA40"])
    ma_dist_now = round(float(latest["MA_Dist"]), 2)
    ma_dist_20 = round(float(valid.iloc[-21]["MA_Dist"]), 2)

    ma40_5 = float(valid.iloc[-6]["MA40"])
    ma40_10 = float(valid.iloc[-11]["MA40"])
    ma40_20 = float(valid.iloc[-21]["MA40"])

    ma40_slope_5 = round(((ma40_now - ma40_5) / ma40_5) * 100.0, 2)
    ma40_slope_10 = round(((ma40_now - ma40_10) / ma40_10) * 100.0, 2)
    ma40_slope_20 = round(((ma40_now - ma40_20) / ma40_20) * 100.0, 2)

    # 골든크로스 발생 여부 및 경과 거래일
    gc_mask = (valid["MA40"] >= valid["MA200"]) & (valid["MA40"].shift(1) < valid["MA200"].shift(1))
    gc_indices = valid.index[gc_mask].tolist()
    last_gc_idx = gc_indices[-1] if gc_indices else None
    days_since_gc = int(valid.index[-1] - last_gc_idx) if last_gc_idx is not None else 999
    gc_occurred_recent = (last_gc_idx is not None) and (days_since_gc <= cfg["gc_window"]) and (ma40_now >= ma200_now)

    # 40일선 이격도 및 골든크로스 이후 수익률
    disparity_40 = round(((price - ma40_now) / ma40_now) * 100.0, 2)
    ret_since_gc = round(((price - float(valid.loc[last_gc_idx, "Close"])) / float(valid.loc[last_gc_idx, "Close"])) * 100.0, 2) if last_gc_idx is not None else 0.0
    ret_5d = round(((price - float(valid.iloc[-6]["Close"])) / float(valid.iloc[-6]["Close"])) * 100.0, 2)

    # 유형 A: 골든크로스 발생형
    is_type_a = (
        long_downtrend_ok
        and gc_occurred_recent
        and (price >= ma40_now)
        and (disparity_40 <= 18.0)
        and (ret_since_gc <= 25.0)
    )

    # 유형 B: 골든크로스 임박형 (단순 근접 배제: 40MA 상승전환 + 20일간 간격 축소 + 200MA 둔화 필수)
    gap_narrowed_20d = (ma_dist_now > ma_dist_20) and (abs(ma_dist_now) < abs(ma_dist_20))
    ma40_turning_up = (ma40_slope_5 > 0.0) and (ma40_slope_10 > 0.0)
    is_type_b = (
        long_downtrend_ok
        and (ma40_now < ma200_now)
        and (-cfg["imminent_gap"] <= ma_dist_now < 0.0)
        and ma40_turning_up
        and gap_narrowed_20d
        and ma200_decelerating
    )

    score_s3 = 0.0
    if is_type_a:
        score_s3 += 12.0
        if price >= ma40_now:
            score_s3 += 4.0
        if ma40_slope_5 > 0 and ma40_slope_10 > 0:
            score_s3 += 2.0
        if ma200_decelerating:
            score_s3 += 2.0
    elif is_type_b:
        score_s3 += 10.0
        score_s3 += 4.0 if abs(ma_dist_now) <= 1.5 else 2.5
        if ma40_slope_5 > 0 and ma40_slope_10 > 0 and ma40_slope_20 > 0:
            score_s3 += 3.0
        else:
            score_s3 += 1.5
        if ma200_decelerating:
            score_s3 += 3.0
    else:
        # 단순 근접만으로 신호를 주지 않음 (보수적 부분 점수만)
        if ma40_turning_up and gap_narrowed_20d:
            score_s3 += 6.0
        elif ma40_now >= ma200_now and price >= ma40_now:
            score_s3 += 5.0
    score_s3 = min(20.0, round(score_s3, 1))

    # =========================================================
    # [4단계] 거래량 및 가격 돌파 분석 (거래량 20점 + 돌파·모멘텀 20점)
    # =========================================================
    vol_today = float(latest["Volume"])
    vol_ratio_20 = round(vol_today / vol_ma20, 2) if vol_ma20 > 0 else 0.0
    vol_ma5 = float(latest["Vol_MA5"])
    vol_5_vs_20 = round(vol_ma5 / vol_ma20, 2) if vol_ma20 > 0 else 0.0

    # 최근 20일 상승일 vs 하락일 평균 거래량
    last20 = valid.tail(20).copy()
    last20["UpDay"] = last20["Close"] >= last20["Close"].shift(1).fillna(last20["Open"])
    up_vol_avg = float(last20[last20["UpDay"]]["Volume"].mean()) if last20["UpDay"].any() else 0.0
    dn_vol_avg = float(last20[~last20["UpDay"]]["Volume"].mean()) if (~last20["UpDay"]).any() else 1.0
    up_dn_vol_ratio = round(up_vol_avg / max(dn_vol_avg, 1.0), 2)

    # 박스권 상단 종가 기준 돌파 및 돌파 후 1~3일 지지 확인
    today_breakout = price > box_high
    recent3_breakout_mask = post_break_df["Close"] > box_high
    recent_breakout = bool(recent3_breakout_mask.any())
    breakout_held = recent_breakout and (price >= box_high * 0.995)

    # 최근 3일 중 돌파 시점(또는 당일)의 최대 거래량 비율
    if recent_breakout:
        break_bars = post_break_df[recent3_breakout_mask]
        break_vol_ratio = round(float((break_bars["Volume"] / break_bars["Vol_MA20"].replace(0, np.nan)).max()), 2)
        break_tval = float(break_bars["TradingVal_Eok"].max())
        break_price_up = bool((break_bars["Close"] > break_bars["Open"]).any() or chg_pct > 0)
    else:
        break_vol_ratio = vol_ratio_20
        break_tval = today_tval
        break_price_up = chg_pct > 0

    vol_confirmed = (
        (max(vol_ratio_20, break_vol_ratio) >= cfg["min_vol_ratio"])
        and (max(today_tval, break_tval) >= cfg["min_tval_eok"])
        and break_price_up
    )

    # 거래량 점수 (20점)
    score_s4_vol = 0.0
    eff_vol_ratio = max(vol_ratio_20, break_vol_ratio)
    if eff_vol_ratio >= 2.0:
        score_s4_vol += 8.0
    elif eff_vol_ratio >= cfg["min_vol_ratio"]:
        score_s4_vol += 6.5
    elif eff_vol_ratio >= 1.2:
        score_s4_vol += 3.0

    if vol_5_vs_20 >= 1.15:
        score_s4_vol += 4.0
    elif vol_5_vs_20 >= 1.0:
        score_s4_vol += 2.0

    if up_dn_vol_ratio >= 1.25:
        score_s4_vol += 4.0
    elif up_dn_vol_ratio >= 1.0:
        score_s4_vol += 2.0

    if vol_confirmed:
        score_s4_vol += 4.0
    elif max(today_tval, avg20_tval) >= cfg["min_tval_eok"]:
        score_s4_vol += 1.5
    score_s4_vol = min(20.0, round(score_s4_vol, 1))

    # 박스권 상단 돌파 및 가격 모멘텀 점수 (20점)
    dist_to_box_top = round(((price - box_high) / box_high) * 100.0, 2) if box_high > 0 else -99.0
    score_s4_brk = 0.0
    if breakout_held:
        score_s4_brk += 10.0
        # 돌파 후 1~3일 지지 또는 당일 강한 양봉 안착
        if len(post_break_df) >= 2 and (post_break_df["Close"] >= box_high * 0.995).sum() >= 2:
            score_s4_brk += 5.0
        elif today_breakout and chg_pct > 0:
            score_s4_brk += 4.0
    elif -2.5 <= dist_to_box_top <= 0.0 and chg_pct >= 0:
        score_s4_brk += 5.0  # 돌파 직전 상단 테스트

    # 40일선 대비 초기 건강한 상승 위치 (0% ~ 12% 이격)
    if 0.0 <= disparity_40 <= 12.0:
        score_s4_brk += 5.0
    elif -2.0 <= disparity_40 < 0.0:
        score_s4_brk += 3.0
    elif 12.0 < disparity_40 <= 16.0:
        score_s4_brk += 2.0
    score_s4_brk = min(20.0, round(score_s4_brk, 1))

    # =========================================================
    # [5단계] 보조지표 분석 (보완 용도, 총 5점)
    # =========================================================
    rsi_now = round(float(latest["RSI14"]), 1)
    rsi_prev5 = float(valid.iloc[-6]["RSI14"])
    rsi_cross_50 = (rsi_now >= 50.0) and (rsi_prev5 < 55.0)
    rsi_overbought = rsi_now >= 75.0

    macd_now = float(latest["MACD"])
    macd_sig = float(latest["MACD_Sig"])
    macd_bull = macd_now > macd_sig
    macd_label = "상승(골든)" if macd_bull else "하락(데드)"

    bb_squeeze = float(latest["BB_Width"]) < float(latest["BB_Width_MA60"])
    bb_break = price >= float(latest["BB_Upper"]) * 0.99
    adx_now = round(float(latest["ADX14"]), 1)
    atr_now = float(latest["ATR14"])

    score_s5 = 0.0
    if 50.0 <= rsi_now <= 70.0:
        score_s5 += 1.5
    elif 45.0 <= rsi_now < 50.0:
        score_s5 += 0.5
    if macd_bull:
        score_s5 += 1.5
    if bb_squeeze or bb_break:
        score_s5 += 1.0
    if adx_now >= 18.0:
        score_s5 += 1.0
    score_s5 = min(5.0, round(score_s5, 1))

    # =========================================================
    # [6단계] 최종 점수화 (100점) + 급등 감점 + 필수 통과 조건
    # =========================================================
    penalty = 0.0
    penalty_reasons = []
    if disparity_40 > 22.0:
        penalty += 15.0
        penalty_reasons.append(f"40일선 과도 이격(+{disparity_40}%)")
    elif disparity_40 > 15.0:
        penalty += 8.0
        penalty_reasons.append(f"40일선 이격 부담(+{disparity_40}%)")

    if ret_5d > 20.0:
        penalty += 8.0
        penalty_reasons.append(f"5일 단기 급등(+{ret_5d}%)")
    if rsi_now >= 78.0:
        penalty += 3.0
        penalty_reasons.append(f"RSI 과열({rsi_now})")

    raw_score = score_s1 + score_s2 + score_s3 + score_s4_vol + score_s4_brk + score_s5
    total_score = round(max(0.0, min(100.0, raw_score - penalty)), 1)

    # 신호 유형 결정
    if is_type_a and breakout_held:
        sig_type = "골든크로스+돌파"
    elif is_type_a:
        sig_type = "골든크로스"
    elif is_type_b and breakout_held:
        sig_type = "임박+돌파"
    elif is_type_b:
        sig_type = "임박"
    elif breakout_held:
        sig_type = "돌파"
    else:
        sig_type = "미충족"

    # 필수 통과 조건 (5대 Hard Gate)
    trend_intact = holding_box_low and (not (is_type_a and price < ma40_now * 0.98))
    mandatory_pass = (
        long_downtrend_ok
        and box_ok
        and trend_intact
        and liquidity_ok
        and (is_type_a or is_type_b or breakout_held)
    )

    fail_reasons = []
    if not long_downtrend_ok:
        fail_reasons.append(f"역배열 부족({inv_days_250}일<{cfg['inv_min_days']}일)")
    if not box_ok:
        fail_reasons.append(f"박스권 불안정(폭 {box_range_pct}%)")
    if not trend_intact:
        fail_reasons.append("하단/추세 이탈")
    if not liquidity_ok:
        fail_reasons.append(f"유동성 미달(거래대금 {today_tval:.1f}억)")
    if not (is_type_a or is_type_b or breakout_held):
        fail_reasons.append("전환/돌파 시그널 미충족")

    # 최종 등급 부여 (규칙: 박스권 돌파 & 거래량 미확인 시 관찰 종목 제한)
    confirmed_break_vol = breakout_held and vol_confirmed
    capped_to_watch = False

    if (not mandatory_pass) or (total_score < 65.0):
        grade = "제외"
        grade_rank = 4
    else:
        if not confirmed_break_vol:
            grade = "관찰 종목"
            grade_rank = 3
            if total_score >= 75.0:
                capped_to_watch = True
        else:
            if total_score >= 85.0:
                grade = "최우선 관심 종목"
                grade_rank = 1
            elif total_score >= 75.0:
                grade = "매매 후보"
                grade_rank = 2
            else:
                grade = "관찰 종목"
                grade_rank = 3

    # =========================================================
    # [7단계] 매매 적합성 및 위험 분석 (ATR, 박스권, 저항선 기반)
    # =========================================================
    recent_support = round(max(box_low, min(ma40_now, price * 0.97)), 0)
    # ATR 기반 손절선: 박스권 하단 지지와 (현재가 - 2.0*ATR) 중 합리적 손절가 채택
    atr_stop = price - 2.0 * atr_now
    stop_loss = min(price * 0.97, max(box_low * 0.985, atr_stop))
    if stop_loss >= price * 0.985:
        stop_loss = price * 0.95
    stop_loss = round(stop_loss, 0)

    box_height = max(box_high - box_low, atr_now * 2.0)
    res_120 = float(valid.tail(120)["High"].max())
    # 1차 목표가: 박스권 높이 투영 또는 ATR 2.8배 (최근 120일 저항 고려)
    target1 = max(box_high + box_height * 0.85, price + 2.8 * atr_now)
    if res_120 > price * 1.07:
        target1 = min(target1, res_120) if res_120 >= price + 1.8 * atr_now else target1
    target1 = round(max(target1, price * 1.06), 0)

    # 2차 목표가: 박스권 1.7배 투영 또는 1년 고점 90%선
    target2 = max(box_high + box_height * 1.7, price + 4.8 * atr_now, target1 * 1.08)
    if high_1y > target1 * 1.05:
        target2 = min(target2, high_1y * 0.95)
    target2 = round(max(target2, target1 * 1.07), 0)

    risk_pct = round(((price - stop_loss) / price) * 100.0, 2)
    reward1_pct = round(((target1 - price) / price) * 100.0, 2)
    reward2_pct = round(((target2 - price) / price) * 100.0, 2)
    rr_ratio = round(reward1_pct / max(risk_pct, 0.1), 2)

    entry_guide = f"{int(price):,}원(돌파안착)" if breakout_held else f"{int(box_high):,}원 돌파 확인 시"
    strategy_str = f"진입 {entry_guide} / 손절 {int(stop_loss):,}원(-{risk_pct}%) / 1차 {int(target1):,}원(+{reward1_pct}%)"

    # 위험 요인 (신호 무효화 조건)
    risk_factors = [f"종가 기준 박스권 하단({int(box_low):,}원) 이탈 시 무효화"]
    if is_type_a:
        risk_factors.append(f"40일선({int(ma40_now):,}원) 재이탈 시 무효화")
    if rr_ratio < 1.5:
        risk_factors.append(f"1차 손익비 낮음({rr_ratio:.2f} < 1.5)")
    if penalty_reasons:
        risk_factors.extend(penalty_reasons)
    if capped_to_watch:
        risk_factors.append("박스권 돌파/거래량 미확인으로 관찰 분류")
    risk_str = " · ".join(risk_factors[:3])

    # 구체적 검색 근거 문장 생성
    reasons = [
        f"최근 250일 중 {inv_days_250}일 역배열 유지, 1년 고점 대비 -{drawdown_now}% 조정 후 저점 형성.",
        f"최근 {box_len}일 박스권({int(box_low):,}~{int(box_high):,}원, 폭 {box_range_pct}%) 형성 및 하단 {support_touches}회 지지.",
        f"40일선({int(ma40_now):,}원, 5일 기울기 {ma40_slope_5:+.2f}%)·200일선({int(ma200_now):,}원, 20일 기울기 {ma200_slope_20:+.2f}%) 이격 {ma_dist_now:+.2f}%.",
        f"거래량 20일 평균 대비 {eff_vol_ratio:.2f}배(거래대금 {today_tval:,.0f}억), 박스권 종가 돌파 {'확인' if breakout_held else '미확인'}.",
        f"보조지표 RSI {rsi_now} / MACD {macd_label} / ADX {adx_now} / 1차 손익비 {rr_ratio:.2f}."
    ]

    # 4분면 궤적 (최근 20영업일 5포인트)
    step_idx = [max(0, len(valid) - 1 - i * 4) for i in range(4, -1, -1)]
    traj_x = [round(100.0 + float(valid.loc[i, "MA_Dist"]), 2) for i in step_idx]
    traj_y = [round(100.0 + float(valid.loc[i, "MA_Dist"] - valid.loc[max(0, i-5), "MA_Dist"]) * 3.0, 2) for i in step_idx]

    return {
        "code": meta["code"],
        "name": meta["name"],
        "종목명": f"{meta['name']} ({meta['code']})",
        "시장": meta["market"],
        "시가총액(억)": meta["mcap"],
        "현재가": int(price),
        "등락률(%)": chg_pct,
        "역배열 기간": f"{inv_days_250}일 / 250일",
        "inv_days": inv_days_250,
        "고점 대비 하락률": f"-{drawdown_now:.1f}%",
        "drawdown_now": drawdown_now,
        "40일선": f"{int(ma40_now):,}원 ({ma40_slope_5:+.2f}%)",
        "200일선": f"{int(ma200_now):,}원 ({ma200_slope_20:+.2f}%)",
        "이평선 간격": f"{ma_dist_now:+.2f}%",
        "ma_dist": ma_dist_now,
        "박스권": f"{int(box_high):,} / {int(box_low):,}",
        "box_high": box_high,
        "box_low": box_low,
        "box_range_pct": box_range_pct,
        "거래량": f"{eff_vol_ratio:.2f}배",
        "vol_ratio": eff_vol_ratio,
        "거래대금(억)": round(today_tval, 1),
        "RSI": rsi_now,
        "MACD": macd_label,
        "ADX": adx_now,
        "점수": total_score,
        "등급": grade,
        "grade_rank": grade_rank,
        "신호 유형": sig_type,
        "매매 전략": strategy_str,
        "위험 요인": risk_str,
        # 세부 항목 (상세 뷰 및 차트용)
        "scores": {
            "1.장기하락/바닥(15)": score_s1,
            "2.박스권/지지(20)": score_s2,
            "3.이평선전환(20)": score_s3,
            "4.거래량/수급(20)": score_s4_vol,
            "5.돌파/모멘텀(20)": score_s4_brk,
            "6.보조지표(5)": score_s5,
            "감점": -penalty,
        },
        "support": int(recent_support),
        "breakout_price": int(box_high),
        "stop_loss": int(stop_loss),
        "target1": int(target1),
        "target2": int(target2),
        "risk_pct": risk_pct,
        "reward1_pct": reward1_pct,
        "reward2_pct": reward2_pct,
        "rr_ratio": rr_ratio,
        "disparity_40": disparity_40,
        "days_since_gc": days_since_gc,
        "ma40_slopes": (ma40_slope_5, ma40_slope_10, ma40_slope_20),
        "ma200_slopes": (ma200_slope_20, ma200_slope_prev20),
        "up_dn_vol_ratio": up_dn_vol_ratio,
        "vol_5_vs_20": vol_5_vs_20,
        "reasons": reasons,
        "fail_reasons": fail_reasons,
        "traj_x": traj_x,
        "traj_y": traj_y,
        "box_start_date": box_df.iloc[0]["Date"].strftime("%Y-%m-%d"),
        "box_end_date": box_df.iloc[-1]["Date"].strftime("%Y-%m-%d"),
        "history": valid.tail(280)[
            ["Date", "Open", "High", "Low", "Close", "Volume", "MA40", "MA200", "RSI14", "MACD", "MACD_Sig", "MACD_Hist", "BB_Upper", "BB_Lower"]
        ].to_dict("records")
    }


@st.cache_data(ttl=600)
def run_full_scan(kospi_cnt, kosdaq_cnt, custom_codes_str, cfg_tuple):
    cfg = dict(cfg_tuple)
    universe = fetch_krx_universe(kospi_cnt, kosdaq_cnt, cfg["min_mcap_eok"])

    # 직접 입력 종목 추가
    existing = {u["code"] for u in universe}
    if custom_codes_str.strip():
        for raw in custom_codes_str.split(","):
            code = raw.strip()
            if len(code) == 6 and code.isdigit() and code not in existing:
                universe.append({"code": code, "name": f"추가종목({code})", "market": "직접추가", "mcap": cfg["min_mcap_eok"]})
                existing.add(code)

    results = []

    def worker(meta):
        try:
            df_raw = fetch_ohlcv_3y(meta["code"])
            return evaluate_stock(meta, df_raw, cfg)
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=14) as ex:
        futs = [ex.submit(worker, m) for m in universe]
        for f in as_completed(futs):
            res = f.result()
            if res is not None:
                results.append(res)

    return pd.DataFrame(results), len(universe), datetime.now().strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------
# UI: 상단 헤더 및 전략 설정 패널
# ---------------------------------------------------------
h1, h2 = st.columns([4, 1])
with h1:
    st.title("📈 이평선 거래 : 스윙 확인 포착형 스크리너")
    st.caption("최근 3년(750거래일) 일봉 기반 · 1년 역배열 ➔ 바닥 박스권 ➔ 40·200일선 골든크로스/임박 ➔ 거래량 돌파 100점 정밀 채점")
with h2:
    if st.button("🔄 전 종목 재스캔", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with st.expander("⚙️ 전략·유동성·스캔 범위 설정 (클릭하여 펼치기/접기)", expanded=False):
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        kospi_cnt = st.slider("코스피 시총 상위 스캔 수", 0, 200, 100, step=20)
        kosdaq_cnt = st.slider("코스닥 시총 상위 스캔 수", 0, 200, 100, step=20)
    with s2:
        min_mcap_eok = st.number_input("최소 시가총액 (억원)", min_value=0, max_value=50000, value=1000, step=500)
        min_tval_eok = st.number_input("최소 거래대금 (억원)", min_value=1, max_value=1000, value=30, step=10)
        min_vol_20 = st.number_input("최소 20일 평균 거래량 (주)", min_value=0, max_value=500000, value=30000, step=10000)
    with s3:
        inv_min_days = st.slider("최근 250일 중 최소 역배열 일수", 120, 240, 180, step=10)
        min_drawdown = st.slider("1년 고점 대비 최소 하락률 (%)", 10, 50, 20, step=5)
        box_days = st.slider("박스권 분석 기간 (거래일)", 20, 60, 40, step=5)
    with s4:
        max_box_range = st.slider("박스권 최대 허용 폭 (%)", 15, 40, 25, step=5)
        gc_window = st.slider("골든크로스 최근 인정 기간 (일)", 5, 40, 20, step=5)
        imminent_gap = st.slider("임박형 이평선 간격 기준 (%)", 1.0, 5.0, 3.0, step=0.5)
        min_vol_ratio = st.slider("돌파 거래량 배수 기준 (20일 대비)", 1.1, 3.0, 1.5, step=0.1)

    custom_codes = st.text_input("➕ 별도 검수할 종목코드 추가 (6자리, 쉼표로 구분)", placeholder="예: 005930, 035720, 011170")

cfg = {
    "min_mcap_eok": min_mcap_eok,
    "min_tval_eok": min_tval_eok,
    "min_vol_20": min_vol_20,
    "inv_min_days": inv_min_days,
    "min_drawdown": min_drawdown,
    "box_days": box_days,
    "max_box_range": max_box_range,
    "gc_window": gc_window,
    "imminent_gap": imminent_gap,
    "min_vol_ratio": min_vol_ratio,
}

with st.spinner(f"코스피 {kospi_cnt}개 + 코스닥 {kosdaq_cnt}개 종목의 3년 일봉(750거래일) 및 7단계 지표를 정밀 분석 중입니다..."):
    df_all, total_scanned, updated_at = run_full_scan(kospi_cnt, kosdaq_cnt, custom_codes, tuple(cfg.items()))

if df_all.empty:
    st.error("데이터를 수집하지 못했습니다. 잠시 후 '전 종목 재스캔'을 눌러주세요.")
    st.stop()

df_passed = df_all[df_all["등급"] != "제외"].sort_values(["grade_rank", "점수"], ascending=[True, False]).reset_index(drop=True)

top_cnt = int((df_passed["등급"] == "최우선 관심 종목").sum())
cand_cnt = int((df_passed["등급"] == "매매 후보").sum())
watch_cnt = int((df_passed["등급"] == "관찰 종목").sum())

m1, m2, m3, m4 = st.columns(4)
m1.metric("🔥 최우선 관심 (85~100점)", f"{top_cnt}종목", "돌파+거래량 확인")
m2.metric("🎯 매매 후보 (75~84점)", f"{cand_cnt}종목", "돌파+거래량 확인")
m3.metric("👀 관찰 종목 (65~74점·미돌파)", f"{watch_cnt}종목", "임박·돌파 대기")
m4.metric("📊 전체 분석 완료", f"{len(df_all)} / {total_scanned}종목", f"기준: {updated_at}")

st.divider()

# ---------------------------------------------------------
# 5대 메인 탭 (앤트위키 UI + 17개 항목 결과표 + 7단계 상세·차트)
# ---------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "① 앤트위키 시그널 지도",
    "② 검색 결과표 (17개 항목)",
    "③ 종목별 선정 근거 & 매매 전략",
    "④ 7단계 정밀 차트 검수",
    "⑤ 4분면 이평선 궤적"
])

# ---------------------------------------------------------
# [탭 1] 앤트위키 트리맵 히트맵
# ---------------------------------------------------------
with tab1:
    map_mode = st.radio(
        "지도 표시 대상",
        ["✅ 통과 종목만 (최우선·후보·관찰)", "📋 전체 분석 종목 상위 40개 (점수 순)"],
        horizontal=True
    )
    map_df = df_passed.copy() if "통과" in map_mode else df_all.sort_values("점수", ascending=False).head(40).copy()

    if map_df.empty:
        st.warning("현재 엄격 기준을 모두 통과한 종목이 0개입니다. 상단 설정에서 기준을 완화하거나 '전체 분석 종목 상위 40개'를 선택해 근접 후보를 확인해 보세요.")
    else:
        map_df["tile_size"] = map_df["거래대금(억)"].clip(lower=10)
        fig_tree = px.treemap(
            map_df,
            path=[px.Constant("이평선 거래 포착 지도"), "등급", "신호 유형", "종목명"],
            values="tile_size",
            color="점수",
            color_continuous_scale=[[0.0, "#bfdbfe"], [0.5, "#fef08a"], [0.8, "#fca5a5"], [1.0, "#dc2626"]],
            range_color=[50, 100],
            custom_data=["점수", "현재가", "등락률(%)", "이평선 간격", "거래량", "등급"]
        )
        fig_tree.update_traces(
            texttemplate="<b>%{label}</b><br>%{customdata[0]}점 (%{customdata[5]})<br>%{customdata[1]:,}원 (%{customdata[2]:+.2f}%)",
            textposition="middle center",
            hovertemplate=(
                "<b>%{label}</b><br>등급: %{customdata[5]} (%{customdata[0]}점)<br>"
                "현재가: %{customdata[1]:,}원 (%{customdata[2]:+.2f}%)<br>"
                "이평선 간격: %{customdata[3]} · 거래량: %{customdata[4]}<extra></extra>"
            )
        )
        fig_tree.update_layout(margin=dict(t=20, l=10, r=10, b=10), height=560)
        st.plotly_chart(fig_tree, use_container_width=True)

# ---------------------------------------------------------
# [탭 2] 요구사항 10번: 17개 항목 검색 결과표
# ---------------------------------------------------------
with tab2:
    t_col1, t_col2 = st.columns([3, 1])
    with t_col1:
        show_excl = st.checkbox("필수조건 미달/65점 미만 제외 종목도 하단에 함께 보기 (근접 후보 점검용)", value=False)
    table_df = df_all.sort_values(["grade_rank", "점수"], ascending=[True, False]) if show_excl else df_passed

    display_cols = [
        "종목명", "시장", "현재가", "역배열 기간", "고점 대비 하락률",
        "40일선", "200일선", "이평선 간격", "박스권", "거래량",
        "RSI", "MACD", "점수", "등급", "신호 유형", "매매 전략", "위험 요인"
    ]

    if table_df.empty:
        st.info("현재 조건을 모두 통과한 종목이 없습니다. 위 체크박스를 켜시면 점수 상위 근접 종목과 탈락 사유를 확인할 수 있습니다.")
    else:
        with t_col2:
            csv_bytes = table_df[display_cols].to_csv(index=False).encode("utf-8-sig")
            st.download_button("📥 결과 CSV 다운로드", data=csv_bytes, file_name="ma_swing_results.csv", mime="text/csv", use_container_width=True)
        st.dataframe(table_df[display_cols], use_container_width=True, height=540, hide_index=True)

# ---------------------------------------------------------
# [탭 3] 종목별 구체적 검색 근거 & 7단계 위험/손익비 카드
# ---------------------------------------------------------
with tab3:
    card_scope = st.radio(
        "표시 대상",
        ["✅ 통과 종목 (최우선·후보·관찰)", "🔎 점수 상위 15종목 (제외 포함)"],
        horizontal=True
    )
    card_df = df_passed if "통과" in card_scope else df_all.sort_values("점수", ascending=False).head(15)

    if card_df.empty:
        st.info("통과한 종목이 없습니다. '점수 상위 15종목'을 눌러 조건 근접 종목을 확인해 보세요.")
    else:
        for _, r in card_df.iterrows():
            g_cls = "grade-top" if r["등급"] == "최우선 관심 종목" else "grade-cand" if r["등급"] == "매매 후보" else "grade-watch" if r["등급"] == "관찰 종목" else "grade-excl"
            rr_badge = f"<span style='color:#2b8a3e; font-weight:800;'>손익비 {r['rr_ratio']:.2f} (양호)</span>" if r["rr_ratio"] >= 1.5 else f"<span style='color:#d9480f; font-weight:700;'>손익비 {r['rr_ratio']:.2f} (주의)</span>"
            sc = r["scores"]
            score_line = " · ".join([f"{k}: <b>{v}</b>" for k, v in sc.items() if v != 0])
            reasons_html = "".join([f"<li>{line}</li>" for line in r["reasons"]])
            fail_html = f"<div style='color:#c92a2a; font-size:0.84rem; margin-top:6px;'><b>❌ 미충족 항목:</b> {', '.join(r['fail_reasons'])}</div>" if r["fail_reasons"] else ""

            st.markdown(f"""
            <div class="card-box">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                    <div>
                        <span class="{g_cls}">{r['등급']} ({r['점수']}점)</span>
                        <span class="tag-sig">{r['신호 유형']}</span>
                        <b style="font-size:1.18rem; margin-left:8px;">{r['종목명']}</b>
                        <span style="color:#868e96; font-weight:600; margin-left:4px;">[{r['시장']}]</span>
                    </div>
                    <div style="text-align:right;">
                        <b style="font-size:1.15rem;">{r['현재가']:,}원</b>
                        <span style="font-weight:700; color:{'#e12343' if r['등락률(%)']>=0 else '#1964d8'}; margin-left:6px;">({r['등락률(%)']:+.2f}%)</span>
                    </div>
                </div>
                <div style="background:#f8f9fa; padding:10px 12px; border-radius:10px; margin-top:10px; font-size:0.84rem;">
                    <b>[100점 세부 채점]</b> {score_line}
                </div>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(170px, 1fr)); gap:8px; margin-top:10px; font-size:0.86rem;">
                    <div>• <b>박스권 상/하단:</b> {r['박스권']}원</div>
                    <div>• <b>최근 지지선:</b> {r['support']:,}원</div>
                    <div>• <b>ATR 손절 기준:</b> <span style="color:#1964d8; font-weight:700;">{r['stop_loss']:,}원 (-{r['risk_pct']}%)</span></div>
                    <div>• <b>1차 목표가:</b> <span style="color:#e12343; font-weight:700;">{r['target1']:,}원 (+{r['reward1_pct']}%)</span></div>
                    <div>• <b>2차 목표가:</b> {r['target2']:,}원 (+{r['reward2_pct']}%)</div>
                    <div>• <b>매매 적합성:</b> {rr_badge} · 40일 이격 {r['disparity_40']:+.1f}%</div>
                </div>
                <ul style="margin:10px 0 4px 18px; padding:0; font-size:0.86rem; color:#343a40; line-height:1.55;">
                    {reasons_html}
                </ul>
                <div style="font-size:0.84rem; color:#495057; margin-top:6px;">
                    <b>⚠️ 위험 요인(무효화):</b> {r['위험 요인']}
                </div>
                {fail_html}
            </div>
            """, unsafe_allow_html=True)

# ---------------------------------------------------------
# [탭 4] 7단계 정밀 차트 검수 (일봉 + 이평선 + 박스권 + 손절/목표 + 거래량/RSI/MACD)
# ---------------------------------------------------------
with tab4:
    sort_chart_df = df_all.sort_values(["grade_rank", "점수"], ascending=[True, False]).reset_index(drop=True)
    opts = [f"[{r['등급']} · {r['점수']}점] {r['종목명']} ({r['신호 유형']})" for _, r in sort_chart_df.iterrows()]
    sel_opt = st.selectbox("🔎 정밀 차트를 검수할 종목을 선택하세요", opts)
    sel_row = sort_chart_df.iloc[opts.index(sel_opt)]

    hdf = pd.DataFrame(sel_row["history"])
    hdf["Date"] = pd.to_datetime(hdf["Date"])

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04,
        row_heights=[0.60, 0.20, 0.20],
        subplot_titles=(f"{sel_row['종목명']} 일봉 · 40/200일선 · 박스권 · 손절/목표가", "거래량", "RSI(14) & MACD")
    )

    # 캔들차트
    fig.add_trace(go.Candlestick(
        x=hdf["Date"], open=hdf["Open"], high=hdf["High"], low=hdf["Low"], close=hdf["Close"],
        name="일봉", increasing_line_color="#e12343", decreasing_line_color="#1964d8"
    ), row=1, col=1)

    # 40일선, 200일선, 볼린저밴드
    fig.add_trace(go.Scatter(x=hdf["Date"], y=hdf["MA40"], name="40일선", line=dict(color="#e11d48", width=2.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=hdf["Date"], y=hdf["MA200"], name="200일선", line=dict(color="#1d4ed8", width=2.5, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=hdf["Date"], y=hdf["BB_Upper"], name="BB상단", line=dict(color="#adb5bd", width=1, dash="dash")), row=1, col=1)
    fig.add_trace(go.Scatter(x=hdf["Date"], y=hdf["BB_Lower"], name="BB하단", line=dict(color="#adb5bd", width=1, dash="dash")), row=1, col=1)

    # 박스권 영역 음영 표시
    fig.add_shape(
        type="rect",
        x0=sel_row["box_start_date"], x1=sel_row["box_end_date"],
        y0=sel_row["box_low"], y1=sel_row["box_high"],
        fillcolor="rgba(255, 243, 191, 0.35)", line=dict(color="#f59f00", width=1.5, dash="dash"),
        row=1, col=1
    )

    # 손절선 / 1차 목표가 선
    fig.add_hline(y=sel_row["stop_loss"], line_dash="dot", line_color="#1964d8", annotation_text=f"손절 {sel_row['stop_loss']:,}", row=1, col=1)
    fig.add_hline(y=sel_row["target1"], line_dash="dot", line_color="#e12343", annotation_text=f"1차목표 {sel_row['target1']:,}", row=1, col=1)

    # 거래량
    vol_colors = ["#fca5a5" if c >= o else "#93c5fd" for c, o in zip(hdf["Close"], hdf["Open"])]
    fig.add_trace(go.Bar(x=hdf["Date"], y=hdf["Volume"], name="거래량", marker_color=vol_colors), row=2, col=1)

    # RSI & MACD
    fig.add_trace(go.Scatter(x=hdf["Date"], y=hdf["RSI14"], name="RSI(14)", line=dict(color="#7c3aed", width=2)), row=3, col=1)
    fig.add_hline(y=50, line_dash="dash", line_color="#868e96", row=3, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#e12343", row=3, col=1)

    fig.update_layout(height=740, xaxis_rangeslider_visible=False, hovermode="x unified", margin=dict(t=40, l=20, r=20, b=20))
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# [탭 5] 앤트위키 4분면 이평선 궤적
# ---------------------------------------------------------
with tab5:
    st.subheader("이평선 4분면 궤적 (장기 역배열 ➔ 임박·접근 ➔ 골든크로스 돌파)")
    q_df = df_passed.head(15) if not df_passed.empty else df_all.sort_values("점수", ascending=False).head(15)

    fig_q = go.Figure()
    quads = [
        (100, 115, 100, 115, "rgba(254,202,202,0.35)", "1사분면: 골든크로스 & 상승가속", 107.5, 113.5),
        (85, 100, 100, 115, "rgba(254,240,138,0.35)", "2사분면: 골든크로스 임박 (접근 중)", 92.5, 113.5),
        (85, 100, 85, 100, "rgba(191,219,254,0.35)", "3사분면: 장기 역배열 침체", 92.5, 86.5),
        (100, 115, 85, 100, "rgba(233,213,255,0.35)", "4사분면: 정배열 중 탄력 둔화", 107.5, 86.5),
    ]
    for x0, x1, y0, y1, c, lbl, lx, ly in quads:
        fig_q.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=c, line=dict(width=0), layer="below")
        fig_q.add_annotation(x=lx, y=ly, text=f"<b>{lbl}</b>", showarrow=False)

    fig_q.add_hline(y=100, line_dash="dash", line_color="#475569")
    fig_q.add_vline(x=100, line_dash="dash", line_color="#475569")

    for _, r in q_df.iterrows():
        xs = np.clip(r["traj_x"], 85.5, 114.5)
        ys = np.clip(r["traj_y"], 85.5, 114.5)
        fig_q.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines+markers+text",
            name=f"{r['name']} ({r['점수']}점)",
            text=["", "", "", "", r["name"]], textposition="top center",
            line=dict(width=3, shape="spline"), marker=dict(size=[5, 6, 7, 8, 13])
        ))

    fig_q.update_layout(
        xaxis=dict(title="40·200일선 상대 이격 지수 (100 = 교차 / 100+ = 골든크로스)", range=[85, 115]),
        yaxis=dict(title="이격 변화 모멘텀 (100+ = 200일선 향해 접근·돌파 가속)", range=[85, 115]),
        height=560, margin=dict(t=20, l=20, r=20, b=20)
    )
    st.plotly_chart(fig_q, use_container_width=True)
