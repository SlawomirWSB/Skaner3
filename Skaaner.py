import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import ccxt

# --- KONFIGURACJA ---
st.set_page_config(page_title="Skaner PRO V9.8 - Silnik Bybit & YF", layout="wide")

# MAPOWANIE KRYPTO: Używamy Bybit (Działa na serwerach USA)
KRYPTO_BYBIT = {
    "BITCOIN": "BTC/USDT", "ETHEREUM": "ETH/USDT", "SOLANA": "SOL/USDT", 
    "CHAINLINK": "LINK/USDT", "POLYGON": "MATIC/USDT", "RIPPLE": "XRP/USDT", 
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
    # Używamy giełdy Bybit zamiast Binance (omija blokady IP)
    exchange = ccxt.bybit({'enableRateLimit': True})
    tf = interval_map_ccxt[int_label]
    data = {}
    for name, symbol in ticker_dict.items():
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            data[name] = df
        except Exception as e:
            continue
    return data

@st.cache_data(ttl=300)
def pobierz_zasoby_yf(ticker_dict, int_label):
    tf = interval_map_yf[int_label]
    data = {}
    for name, ticker in ticker_dict.items():
        try:
            df = yf.download(ticker, period="60d", interval=tf, progress=False)
            if not df.empty and len(df) > 20:
                # Twarde spłaszczenie kolumn, żeby naprawić błędy nowego Yahoo Finance
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [c[0] for c in df.columns]
                
                # Upewnienie się, że mamy podstawowe kolumny i brak duplikatów
                df = df.loc[:, ~df.columns.duplicated()]
                data[name] = df
        except Exception as e:
            continue
    return data

def analizuj(df_raw, name, kapital, tryb, ryzyko):
    try:
        df = df_raw.copy()
        df.ta.rsi(append=True); df.ta.ema(length=20, append=True)
        df.ta.adx(append=True); df.ta.atr(append=True); df.ta.macd(append=True)
        df.ta.stochrsi(append=True)
        df['V_Avg'] = df['Volume'].rolling(20).mean()
        
        l = df.iloc[-2] 
        curr = df.iloc[-1] 
        c_zamkniete = float(l['Close'])
        c_akt = float(curr['Close']) 
        
        ema, atr = float(l['EMA_20']), float(l['ATRr_14'])
        adx, rsi, stoch = float(l['ADX_14']), float(l['RSI_14']), float(l['STOCHRSIk_14_14_3_3'])
        macd_h = float(l['MACDh_12_26_9'])
        
        if pd.isna(l['Volume']) or l['Volume'] == 0 or l['V_Avg'] == 0:
            v_rat = 100.0
        else:
            v_rat = (float(l['Volume'] / l['V_Avg']) * 100)
        
        adx_min = 18 if ryzyko == "Poluzowany" else 25
        st_b, st_s = (55, 45) if ryzyko == "Poluzowany" else (35, 65)
        
        long = (c_zamkniete > ema) and (adx > adx_min) and (stoch < st_b) and (macd_h > 0)
        short = (c_zamkniete < ema) and (adx > adx_min) and (stoch > st_s) and (macd_h < 0)
        
        sig = "KUP" if long else "SPRZEDAJ" if short else "CZEKAJ"
        wej = ema if tryb == "Limit (EMA20)" else c_akt
        
        sl_buffer = atr * 0.1
        sl = wej - (atr * 1.5) - sl_buffer if sig == "KUP" else wej + (atr * 1.5) + sl_buffer
        tp = wej + (atr * 2.5) if sig == "KUP" else wej - (atr * 2.5)
        
        return {
            "Instrument": name, "Sygnał": sig, "Siła %": (90 if sig in ["KUP", "SPRZEDAJ"] else 50),
            "Cena Rynkowa": round(c_akt, 4), "Cena Wejścia": round(wej, 4), "RSI": round(rsi, 1),
            "StochRSI": round(stoch, 1), "Pęd": "Wzrost" if macd_h > 0 else "Spadek",
            "ADX": round(adx, 1), "Wolumen %": round(v_rat), 
            "Ile (1%)": round((kapital*0.01)/abs(wej-sl), 4) if abs(wej-sl) > 0 else 0,
            "TP": round(tp, 4), "SL": round(sl, 4)
        }
    except Exception as e:
        # Zamiast chować błąd (None), wyświetlamy go w tabeli dla diagnostyki
        return {
            "Instrument": name, "Sygnał": f"BŁĄD: {e}", "Siła %": 0,
            "Cena Rynkowa": 0, "Cena Wejścia": 0, "RSI": 0, "StochRSI": 0, 
            "Pęd": "-", "ADX": 0, "Wolumen %": 0, "Ile (1%)": 0, "TP": 0, "SL": 0
        }

def stylizuj_v9_6(row):
    s = [''] * len(row)
    idx = row.index.tolist()
    sig = str(row['Sygnał'])
    
    if sig == 'KUP': s[idx.index('Sygnał')] = 'background-color: #00ff00; color: black; font-weight: bold'
    elif sig == 'SPRZEDAJ': s[idx.index('Sygnał')] = 'background-color: #ff0000; color: white; font-weight: bold'
    elif 'BŁĄD' in sig: s[idx.index('Sygnał')] = 'background-color: #ffcc00; color: black;' # Błędy na żółto
    
    def set_col(col_name, is_green):
        if col_name in idx and 'BŁĄD' not in sig:
            s[idx.index(col_name)] = 'color: #00ff00' if is_green else 'color: #ff4b4b'

    if 'Pęd' in idx:
        set_col('Pęd', (sig == "KUP" and row['Pęd'] == "Wzrost") or (sig == "SPRZEDAJ" and row['Pęd'] == "Spadek"))
    if 'RSI' in idx:
        set_col('RSI', (sig == "KUP" and float(row['RSI']) < 65) or (sig == "SPRZEDAJ" and float(row['RSI']) > 35) if row['RSI'] != 0 else False)
    if 'StochRSI' in idx:
        set_col('StochRSI', (sig == "KUP" and float(row['StochRSI']) < 50) or (sig == "SPRZEDAJ" and float(row['StochRSI']) > 50) if row['StochRSI'] != 0 else False)
    if 'ADX' in idx:
        set_col('ADX', float(row['ADX']) > 20 if row['ADX'] != 0 else False)
    
    if 'Wolumen %' in idx:
        v = float(row['Wolumen %'])
        s[idx.index('Wolumen %')] = 'color: #00ff00' if v > 105 else ('color: #ff4b4b' if v < 55 else '')
    
    return s

# --- UI ---
st.title("⚖️ Skaner PRO V9.8 - Silnik Bybit & YF")
st.markdown("**Dane Krypto pobierane w czasie rzeczywistym z Bybit API.** Tradycyjne rynki zasilane Yahoo Finance.")

with st.sidebar:
    st.header("⚙️ Ustawienia")
    u_kap = st.number_input("Kapitał (PLN):", value=10000)
    u_int = st.select_slider("Interwał:", options=list(interval_map_yf.keys()), value="1 godz")
    u_wej = st.radio("Metoda:", ["Rynkowa", "Limit (EMA20)"])
    u_ryz = st.radio("Ryzyko:", ["Poluzowany", "Rygorystyczny"])

t1, t2 = st.tabs(["₿ KRYPTOWALUTY (REAL-TIME)", "📊 INDEKSY & TOWARY"])

with t1:
    dane_krypto = pobierz_krypto_ccxt(KRYPTO_BYBIT, u_int)
    wyniki_krypto = [analizuj(df, n, u_kap, u_wej, u_ryz) for n, df in dane_krypto.items()]
    wyniki_krypto = [w for w in wyniki_krypto if w is not None]
    if wyniki_krypto:
        df_res = pd.DataFrame(wyniki_krypto).sort_values("Siła %", ascending=False)
        st.dataframe(df_res.style.apply(stylizuj_v9_6, axis=1), use_container_width=True)
    else:
        st.warning("Brak danych lub wszystkie instrumenty zwróciły błąd. Odśwież stronę.")

with t2:
    dane_zasoby = pobierz_zasoby_yf(ZASOBY_XTB, u_int)
    wyniki_zasoby = [analizuj(df, n, u_kap, u_wej, u_ryz) for n, df in dane_zasoby.items()]
    wyniki_zasoby = [w for w in wyniki_zasoby if w is not None]
    if wyniki_zasoby:
        df_res2 = pd.DataFrame(wyniki_zasoby).sort_values("Siła %", ascending=False)
        st.dataframe(df_res2.style.apply(stylizuj_v9_6, axis=1), use_container_width=True)
    else:
        st.warning("Brak sygnałów z rynków tradycyjnych lub błąd serwera Yahoo Finance.")
