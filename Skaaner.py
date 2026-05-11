import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import ccxt

# --- KONFIGURACJA ---
st.set_page_config(page_title="Skaner PRO V9.9 - Momentum Sniper", layout="wide")

# MAPOWANIE KRYPTO (Zmieniono MATIC na POL)
KRYPTO_CCXT = {
    "BITCOIN": "BTC/USDT", "ETHEREUM": "ETH/USDT", "SOLANA": "SOL/USDT", 
    "CHAINLINK": "LINK/USDT", "POLYGON": "POL/USDT", "RIPPLE": "XRP/USDT", 
    "CARDANO": "ADA/USDT", "DOT": "DOT/USDT", "LITECOIN": "LTC/USDT", 
    "TRON": "TRX/USDT", "DOGECOIN": "DOGE/USDT", "AVALANCHE": "AVAX/USDT",
    "AAVE": "AAVE/USDT", "ALGORAND": "ALGO/USDT", "APTOS": "APT/USDT", 
    "COSMOS": "ATOM/USDT", "BITCOINCASH": "BCH/USDT", "CHILIZ": "CHZ/USDT", 
    "FANTOM": "FTM/USDT", "THE_GRAPH": "GRT/USDT", "NEAR": "NEAR/USDT", 
    "OPTIMISM": "OP/USDT", "RENDER": "RNDR/USDT", "UNISWAP": "UNI/USDT", 
    "STELLAR": "XLM/USDT", "KASPA": "KAS/USDT", "STACKS": "STX/USDT", 
    "SHIBA_INU": "SHIB/USDT", "ELROND": "EGLD/USDT", "SANDBOX": "SAND/USDT", 
    "DECENTRALAND": "MANA/USDT", "EOS": "EOS/USDT", "FLOW": "FLOW/USDT", 
    "GALA": "GALA/USDT", "HEDERA": "HBAR/USDT", "INTERNET_COMP": "ICP/USDT",
    "IMMUTABLE": "IMX/USDT", "LIDO_DAO": "LDO/USDT", "MAKER": "MKR/USDT", 
    "QUANT": "QNT/USDT", "VECHAIN": "VET/USDT", "WAVES": "WAVES/USDT", 
    "Z_CASH": "ZEC/USDT", "DYDX": "DYDX/USDT"
}

ZASOBY_XTB = {
    "DE40 (DAX)": "^GDAXI", "US100 (NQ)": "^IXIC", "US500 (SP)": "^GSPC",
    "GOLD": "GC=F", "SILVER": "SI=F", "OIL.WTI": "CL=F", "NATGAS": "NG=F", 
    "COPPER": "HG=F", "COCOA": "CC=F", "COFFEE": "KC=F", "SUGAR": "SB=F",
    "EURPLN": "EURPLN=X", "USDPLN": "USDPLN=X", "EURUSD": "EURUSD=X"
}

interval_map_yf = {"5 min": "5m", "15 min": "15m", "30 min": "30m", "1 godz": "1h", "4 godz": "4h", "1 dzień": "1d"}
interval_map_ccxt = {"5 min": "5m", "15 min": "15m", "30 min": "30m", "1 godz": "1h", "4 godz": "4h", "1 dzień": "1d"}

@st.cache_data(ttl=60)
def pobierz_krypto_ccxt(ticker_dict, int_label):
    exchange = ccxt.kucoin({'enableRateLimit': True})
    tf = interval_map_ccxt[int_label]
    data = {}
    bledy = []
    for name, symbol in ticker_dict.items():
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
            if not ohlcv:
                bledy.append(f"{name}: Brak danych")
                continue
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            data[name] = df
        except Exception as e:
            bledy.append(f"{name} ({symbol}): {str(e)}")
    return data, bledy

@st.cache_data(ttl=300)
def pobierz_zasoby_yf(ticker_dict, int_label):
    tf = interval_map_yf[int_label]
    data = {}
    bledy = []
    for name, ticker in ticker_dict.items():
        try:
            df = yf.download(ticker, period="60d", interval=tf, progress=False)
            if df.empty or len(df) < 20:
                bledy.append(f"{name}: Zbyt mało danych")
                continue
            
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            df = df.loc[:, ~df.columns.duplicated()]
            data[name] = df
        except Exception as e:
            bledy.append(f"{name}: {str(e)}")
    return data, bledy

def analizuj_momentum(df_raw, name, kapital, tryb, ryzyko):
    try:
        df = df_raw.copy()
        
        # SZYBKIE WSKAŹNIKI (SWING/DAY TRADING)
        df.ta.ema(length=9, append=True)   
        df.ta.ema(length=21, append=True)  
        df.ta.rsi(length=14, append=True)
        df.ta.adx(append=True); df.ta.atr(append=True); df.ta.macd(append=True)
        df['V_Avg'] = df['Volume'].rolling(20).mean()
        
        l = df.iloc[-2]   
        l2 = df.iloc[-3]  
        curr = df.iloc[-1] 
        
        c_zamkniete = float(l['Close'])
        c_akt = float(curr['Close']) 
        
        ema9, ema21 = float(l['EMA_9']), float(l['EMA_21'])
        atr, adx, rsi = float(l['ATRr_14']), float(l['ADX_14']), float(l['RSI_14'])
        macd_h = float(l['MACDh_12_26_9'])
        macd_h_prev = float(l2['MACDh_12_26_9'])
        
        if pd.isna(l['Volume']) or l['Volume'] == 0 or pd.isna(l['V_Avg']) or l['V_Avg'] == 0:
            v_rat = 100.0
        else:
            v_rat = (float(l['Volume'] / l['V_Avg']) * 100)
        
        adx_min = 20 if ryzyko == "Poluzowany" else 25
        v_min = 90 if ryzyko == "Poluzowany" else 115
        
        # LOGIKA MOMENTUM
        ema_bull = (ema9 > ema21)
        ema_bear = (ema9 < ema21)
        
        macd_bull = (macd_h > 0) and (macd_h > macd_h_prev)
        macd_bear = (macd_h < 0) and (macd_h < macd_h_prev)
        
        rsi_bull = rsi > 52 
        rsi_bear = rsi < 48
        
        long = ema_bull and macd_bull and rsi_bull and (adx > adx_min) and (v_rat >= v_min)
        short = ema_bear and macd_bear and rsi_bear and (adx > adx_min) and (v_rat >= v_min)
        
        sig = "KUP" if long else "SPRZEDAJ" if short else "CZEKAJ"
        wej = ema9 if tryb == "Limit (EMA20)" else c_akt
        
        sl_buffer = atr * 0.1
        sl = wej - (atr * 1.2) - sl_buffer if sig == "KUP" else wej + (atr * 1.2) + sl_buffer
        tp = wej + (atr * 2.4) if sig == "KUP" else wej - (atr * 2.4)
        
        return {
            "Instrument": name, "Sygnał": sig, "Siła %": (95 if sig in ["KUP", "SPRZEDAJ"] else 50),
            "Cena Rynkowa": round(c_akt, 4), "Cena Wejścia": round(wej, 4), "RSI": round(rsi, 1),
            "MACD Hist": round(macd_h, 4), 
            "Pęd": "Wzrost" if macd_bull else ("Spadek" if macd_bear else "Płaski"),
            "ADX": round(adx, 1), "Wolumen %": round(v_rat), 
            "Ile (1%)": round((kapital*0.01)/abs(wej-sl), 4) if abs(wej-sl) > 0 else 0,
            "TP": round(tp, 4), "SL": round(sl, 4)
        }
    except Exception as e:
        return {
            "Instrument": name, "Sygnał": f"BŁĄD WSK.: {e}", "Siła %": 0,
            "Cena Rynkowa": 0, "Cena Wejścia": 0, "RSI": 0, "MACD Hist": 0, 
            "Pęd": "-", "ADX": 0, "Wolumen %": 0, "Ile (1%)": 0, "TP": 0, "SL": 0
        }

def stylizuj_momentum(row):
    s = [''] * len(row)
    idx = row.index.tolist()
    sig = str(row['Sygnał'])
    
    if sig == 'KUP': s[idx.index('Sygnał')] = 'background-color: #00ff00; color: black; font-weight: bold'
    elif sig == 'SPRZEDAJ': s[idx.index('Sygnał')] = 'background-color: #ff0000; color: white; font-weight: bold'
    elif 'BŁĄD' in sig: s[idx.index('Sygnał')] = 'background-color: #ffcc00; color: black;'
    
    def set_col(col_name, is_green):
        if col_name in idx and 'BŁĄD' not in sig:
            s[idx.index(col_name)] = 'color: #00ff00' if is_green else 'color: #ff4b4b'

    if 'Pęd' in idx:
        set_col('Pęd', (sig == "KUP" and row['Pęd'] == "Wzrost") or (sig == "SPRZEDAJ" and row['Pęd'] == "Spadek"))
    if 'RSI' in idx:
        set_col('RSI', (sig == "KUP" and float(row['RSI']) < 65) or (sig == "SPRZEDAJ" and float(row['RSI']) > 35) if row['RSI'] != 0 else False)
    if 'MACD Hist' in idx:
        set_col('MACD Hist', float(row['MACD Hist']) > 0 if row['MACD Hist'] != 0 else False)
    if 'ADX' in idx:
        set_col('ADX', float(row['ADX']) > 20 if row['ADX'] != 0 else False)
    
    if 'Wolumen %' in idx:
        v = float(row['Wolumen %'])
        s[idx.index('Wolumen %')] = 'color: #00ff00' if v > 105 else ('color: #ff4b4b' if v < 55 else '')
    
    return s

# --- UI ---
st.title("⚡ Skaner PRO V9.9 - Momentum Sniper")
st.markdown("**Strategia krótkoterminowa (Swing/Day Trading).** Wymaga potwierdzenia przyspieszenia MACD oraz silnego wolumenu.")

with st.sidebar:
    st.header("⚙️ Ustawienia")
    u_kap = st.number_input("Kapitał (PLN):", value=10000)
    u_int = st.select_slider("Interwał:", options=list(interval_map_yf.keys()), value="1 godz")
    u_wej = st.radio("Metoda:", ["Rynkowa", "Limit (EMA9)"])
    u_ryz = st.radio("Ryzyko:", ["Poluzowany", "Rygorystyczny"])

t1, t2 = st.tabs(["₿ KRYPTOWALUTY (REAL-TIME)", "📊 INDEKSY & TOWARY"])

with t1:
    dane_krypto, bledy_krypto = pobierz_krypto_ccxt(KRYPTO_CCXT, u_int)
    
    if bledy_krypto and not dane_krypto:
        st.error(f"🚨 KRYTYCZNY BŁĄD: {bledy_krypto[0]}")
    elif len(bledy_krypto) > 0:
        st.warning(f"⚠️ Niektóre monety odrzuciły połączenie (np. {bledy_krypto[0]}), ale analizuję resztę.")
        
    wyniki_krypto = [analizuj_momentum(df, n, u_kap, u_wej, u_ryz) for n, df in dane_krypto.items()]
    wyniki_krypto = [w for w in wyniki_krypto if w is not None]
    
    if wyniki_krypto:
        df_res = pd.DataFrame(wyniki_krypto).sort_values("Siła %", ascending=False)
        st.dataframe(df_res.style.apply(stylizuj_momentum, axis=1), use_container_width=True)

with t2:
    dane_zasoby, bledy_zasoby = pobierz_zasoby_yf(ZASOBY_XTB, u_int)
    
    if bledy_zasoby and not dane_zasoby:
        st.error(f"🚨 BŁĄD YAHOO FINANCE: {bledy_zasoby[0]}")
    elif len(bledy_zasoby) > 0:
        st.warning(f"⚠️ Brak danych dla niektórych symboli (np. {bledy_zasoby[0]}).")
        
    wyniki_zasoby = [analizuj_momentum(df, n, u_kap, u_wej, u_ryz) for n, df in dane_zasoby.items()]
    wyniki_zasoby = [w for w in wyniki_zasoby if w is not None]
    
    if wyniki_zasoby:
        df_res2 = pd.DataFrame(wyniki_zasoby).sort_values("Siła %", ascending=False)
        st.dataframe(df_res2.style.apply(stylizuj_momentum, axis=1), use_container_width=True)
