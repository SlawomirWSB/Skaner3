import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import ccxt

# --- KONFIGURACJA ---
st.set_page_config(page_title="Skaner PRO V10.0 - Ostateczny Sniper", layout="wide")

# MAPOWANIE KRYPTO KUCOIN (Używane do analizy i gry na XTB)
KRYPTO_CCXT = {
    "BITCOIN": "BTC/USDT", "ETHEREUM": "ETH/USDT", "SOLANA": "SOL/USDT", 
    "CHAINLINK": "LINK/USDT", "POLYGON": "POL/USDT", "RIPPLE": "XRP/USDT", 
    "CARDANO": "ADA/USDT", "DOT": "DOT/USDT", "LITECOIN": "LTC/USDT", 
    "TRON": "TRX/USDT", "DOGECOIN": "DOGE/USDT", "AVALANCHE": "AVAX/USDT",
    "AAVE": "AAVE/USDT", "ALGORAND": "ALGO/USDT", "APTOS": "APT/USDT", 
    "COSMOS": "ATOM/USDT", "BITCOINCASH": "BCH/USDT", "CHILIZ": "CHZ/USDT", 
    "THE_GRAPH": "GRT/USDT", "NEAR": "NEAR/USDT", "OPTIMISM": "OP/USDT", 
    "RENDER": "RNDR/USDT", "UNISWAP": "UNI/USDT", "STELLAR": "XLM/USDT", 
    "KASPA": "KAS/USDT", "STACKS": "STX/USDT", "SHIBA_INU": "SHIB/USDT", 
    "ELROND": "EGLD/USDT", "SANDBOX": "SAND/USDT", "DECENTRALAND": "MANA/USDT", 
    "EOS": "EOS/USDT", "FLOW": "FLOW/USDT", "GALA": "GALA/USDT", 
    "HEDERA": "HBAR/USDT", "INTERNET_COMP": "ICP/USDT", "IMMUTABLE": "IMX/USDT", 
    "LIDO_DAO": "LDO/USDT", "MAKER": "MKR/USDT", "QUANT": "QNT/USDT", 
    "VECHAIN": "VET/USDT", "WAVES": "WAVES/USDT", "Z_CASH": "ZEC/USDT", "DYDX": "DYDX/USDT"
}

ZASOBY_XTB = {
    "DE40 (DAX)": "^GDAXI", "US100 (NQ)": "^IXIC", "US500 (SP)": "^GSPC",
    "GOLD": "GC=F", "SILVER": "SI=F", "OIL.WTI": "CL=F", "NATGAS": "NG=F", 
    "COPPER": "HG=F", "COCOA": "CC=F", "COFFEE": "KC=F", "SUGAR": "SB=F",
    "EURPLN": "EURPLN=X", "USDPLN": "USDPLN=X", "EURUSD": "EURUSD=X"
}

# --- MNOŻNIKI XTB ---
MNOZNIKI_XTB = {
    "EURPLN": 100000, "USDPLN": 100000, "EURUSD": 100000,
    "GOLD": 100, "OIL.WTI": 1000, "SILVER": 5000, "NATGAS": 30000,
    "COPPER": 100000, "COFFEE": 37500, "SUGAR": 112000, "COCOA": 10
}

interval_map_yf = {"5 min": "5m", "15 min": "15m", "30 min": "30m", "1 godz": "1h", "4 godz": "4h", "1 dzień": "1d"}
interval_map_ccxt = {"5 min": "5m", "15 min": "15m", "30 min": "30m", "1 godz": "1h", "4 godz": "4h", "1 dzień": "1d"}

@st.cache_data(ttl=60)
def pobierz_krypto_ccxt(ticker_dict, int_label):
    exchange = ccxt.kucoin({'enableRateLimit': True})
    tf = interval_map_ccxt[int_label]
    data, bledy = {}, []
    for name, symbol in ticker_dict.items():
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=150)
            if not ohlcv: continue
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            data[name] = df
        except: continue
    return data, bledy

@st.cache_data(ttl=300)
def pobierz_zasoby_yf(ticker_dict, int_label):
    tf = interval_map_yf[int_label]
    data, bledy = {}, []
    for name, ticker in ticker_dict.items():
        try:
            df = yf.download(ticker, period="60d", interval=tf, progress=False) 
            if df.empty or len(df) < 50: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = [c[0] for c in df.columns]
            df = df.loc[:, ~df.columns.duplicated()]
            data[name] = df
        except: continue
    return data, bledy

def analizuj_momentum(df_raw, name, kapital, tryb, ryzyko):
    try:
        df = df_raw.copy()
        df.ta.ema(length=9, append=True)   
        df.ta.ema(length=21, append=True)  
        df.ta.rsi(length=14, append=True)
        df.ta.adx(append=True); df.ta.atr(append=True); df.ta.macd(append=True)
        
        if 'Volume' in df.columns:
            df['V_Avg'] = df['Volume'].rolling(20).mean()
        else:
            df['Volume'] = 0; df['V_Avg'] = 0
        
        l, l2, curr = df.iloc[-2], df.iloc[-3], df.iloc[-1]
        c_akt = float(curr['Close']) 
        
        ema9, ema21 = float(l['EMA_9']), float(l['EMA_21'])
        atr, adx, rsi = float(l['ATRr_14']), float(l['ADX_14']), float(l['RSI_14'])
        macd_h, macd_h_prev = float(l['MACDh_12_26_9']), float(l2['MACDh_12_26_9'])
        
        is_volume_valid = not (pd.isna(l['Volume']) or l['Volume'] == 0 or pd.isna(l['V_Avg']) or l['V_Avg'] == 0)
        v_rat = (float(l['Volume'] / l['V_Avg']) * 100) if is_volume_valid else 100.0
        
        adx_min = 20 if ryzyko == "Poluzowany" else 25
        v_min = 90 if ryzyko == "Poluzowany" else 115
        
        sig = "CZEKAJ"
        if (ema9 > ema21) and (macd_h > 0) and (macd_h > macd_h_prev) and (rsi > 52) and (adx > adx_min) and (v_rat >= v_min if is_volume_valid else True):
            sig = "KUP"
        elif (ema9 < ema21) and (macd_h < 0) and (macd_h < macd_h_prev) and (rsi < 48) and (adx > adx_min) and (v_rat >= v_min if is_volume_valid else True):
            sig = "SPRZEDAJ"
            
        wej = ema9 if tryb == "Limit (EMA9)" else c_akt
        sl = wej - (atr * 1.2) if sig == "KUP" else wej + (atr * 1.2)
        tp = wej + (atr * 2.4) if sig == "KUP" else wej - (atr * 2.4)
        
        ile_jednostek = (kapital*0.01)/abs(wej-sl) if abs(wej-sl) > 0 else 0
        
        # OBLICZANIE LOTÓW Z OPISAMI
        if name in ["DE40 (DAX)", "US100 (NQ)", "US500 (SP)"]:
            lot_wynik = "Kalk. XTB"
        elif name in MNOZNIKI_XTB:
            obliczony_lot = ile_jednostek / MNOZNIKI_XTB[name]
            lot_wynik = str(round(obliczony_lot, 2)) if obliczony_lot >= 0.01 else "< 0.01 (Odrzuć)"
        else:
            # Kryptowaluty (W XTB 1 Lot = 1 Sztuka Monety dla głównych walut)
            lot_wynik = f"{round(ile_jednostek, 3)} (Lot/Szt)"
            
        return {
            "Instrument": name, "Sygnał": sig, "Siła %": (95 if sig != "CZEKAJ" else 50),
            "Cena Rynkowa": round(c_akt, 4), "Cena Wejścia": round(wej, 4), "RSI": round(rsi, 1),
            "MACD Hist": round(macd_h, 4), "Pęd": "Wzrost" if macd_h > macd_h_prev else "Spadek",
            "ADX": round(adx, 1), "Wolumen %": round(v_rat) if is_volume_valid else "Brak", 
            "Lot / Sztuki": lot_wynik, "TP": round(tp, 4), "SL": round(sl, 4)
        }
    except: return None

def stylizuj(row):
    s = [''] * len(row)
    idx = row.index.tolist()
    sig = str(row['Sygnał'])
    if sig == 'KUP': s[idx.index('Sygnał')] = 'background-color: rgba(0, 255, 0, 0.2); color: #00ff00; font-weight: bold'
    elif sig == 'SPRZEDAJ': s[idx.index('Sygnał')] = 'background-color: rgba(255, 0, 0, 0.2); color: #ff0000; font-weight: bold'
    if 'Lot / Sztuki' in idx and '< 0.01' in str(row['Lot / Sztuki']): s[idx.index('Lot / Sztuki')] = 'color: #ffcc00'
    return s

# --- UI ---
st.title("⚡ Skaner PRO V10.0 - Ostateczny Sniper")
st.markdown("**Platforma Handlowa: XTB | Źródła danych: KuCoin (Krypto) & Yahoo Finance (Rynki Tradycyjne)**")

with st.sidebar:
    st.header("⚙️ Ustawienia")
    u_kap = st.number_input("Całkowity Kapitał (PLN):", value=3000)
    u_int = st.select_slider("Interwał:", options=list(interval_map_yf.keys()), value="1 godz")
    u_wej = st.radio("Metoda:", ["Rynkowa", "Limit (EMA9)"])
    u_ryz = st.radio("Ryzyko:", ["Poluzowany", "Rygorystyczny"])

tabs = st.tabs(["📊 RYNKI TRADYCYJNE (XTB)", "₿ KRYPTOWALUTY (Dane: KuCoin | Gra: XTB)"])

with tabs[0]:
    dane, bledy = pobierz_zasoby_yf(ZASOBY_XTB, u_int)
    if bledy: st.warning(f"Brak danych: {bledy[0]}")
    wyniki = [analizuj_momentum(df, n, u_kap, u_wej, u_ryz) for n, df in dane.items()]
    wyniki = [w for w in wyniki if w is not None]
    if wyniki: st.dataframe(pd.DataFrame(wyniki).sort_values("Siła %", ascending=False).style.apply(stylizuj, axis=1), use_container_width=True)

with tabs[1]:
    st.info("💡 **Pro-Tip:** Krypto zasilane jest danymi Real-Time z giełdy KuCoin. Przy stawianiu zleceń Limit na XTB pamiętaj, aby zweryfikować strefę wejścia z aktualnym wykresem na platformie ze względu na spread brokera.")
    dane_c, bledy_c = pobierz_krypto_ccxt(KRYPTO_CCXT, u_int)
    if bledy_c: st.warning(f"Brak danych: {bledy_c[0]}")
    wyniki = [analizuj_momentum(df, n, u_kap, u_wej, u_ryz) for n, df in dane_c.items()]
    wyniki = [w for w in wyniki if w is not None]
    if wyniki: st.dataframe(pd.DataFrame(wyniki).sort_values("Siła %", ascending=False).style.apply(stylizuj, axis=1), use_container_width=True)
