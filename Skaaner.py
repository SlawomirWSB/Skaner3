def analizuj(df_raw, name, kapital, tryb, ryzyko):
    try:
        df = df_raw.copy()
        
        # SZYBKIE WSKAŹNIKI DLA SHORT-TERM
        df.ta.ema(length=9, append=True)   # Szybka EMA
        df.ta.ema(length=21, append=True)  # Średnia EMA
        df.ta.rsi(length=14, append=True)
        df.ta.adx(append=True); df.ta.atr(append=True); df.ta.macd(append=True)
        df['V_Avg'] = df['Volume'].rolling(20).mean()
        
        # Bierzemy dwie ostatnie ZAMKNIĘTE świece, żeby zbadać dynamikę
        l = df.iloc[-2]   # Ostatnia świeca
        l2 = df.iloc[-3]  # Przedostatnia świeca (historia)
        curr = df.iloc[-1] # Aktualna świeca (do ceny rynkowej)
        
        c_zamkniete = float(l['Close'])
        c_akt = float(curr['Close']) 
        
        ema9, ema21 = float(l['EMA_9']), float(l['EMA_21'])
        atr, adx, rsi = float(l['ATRr_14']), float(l['ADX_14']), float(l['RSI_14'])
        macd_h = float(l['MACDh_12_26_9'])
        macd_h_prev = float(l2['MACDh_12_26_9']) # MACD z poprzedniej świecy
        
        # Bezpieczny licznik wolumenu (odporny na błędy Yahoo/Krypto)
        if pd.isna(l['Volume']) or l['Volume'] == 0 or pd.isna(l['V_Avg']) or l['V_Avg'] == 0:
            v_rat = 100.0
        else:
            v_rat = (float(l['Volume'] / l['V_Avg']) * 100)
        
        # --- USTAWIENIA RYZYKA DLA SWING TRADINGU ---
        adx_min = 20 if ryzyko == "Poluzowany" else 25
        v_min = 90 if ryzyko == "Poluzowany" else 115 # Twardy wymóg wolumenu dla Rygorystycznego
        
        # --- LOGIKA "MOMENTUM SNIPER" ---
        # 1. Trend: Szybka EMA nad Wolną EMA
        ema_bull = (ema9 > ema21)
        ema_bear = (ema9 < ema21)
        
        # 2. Przyspieszenie: MACD jest po dobrej stronie i ROŚNIE/MALEJE dynamika
        macd_bull = (macd_h > 0) and (macd_h > macd_h_prev)
        macd_bear = (macd_h < 0) and (macd_h < macd_h_prev)
        
        # 3. Potwierdzenie kierunku przez RSI (środek skali)
        rsi_bull = rsi > 52 
        rsi_bear = rsi < 48
        
        # Złożenie sygnału
        long = ema_bull and macd_bull and rsi_bull and (adx > adx_min) and (v_rat >= v_min)
        short = ema_bear and macd_bear and rsi_bear and (adx > adx_min) and (v_rat >= v_min)
        
        sig = "KUP" if long else "SPRZEDAJ" if short else "CZEKAJ"
        wej = ema9 if tryb == "Limit (EMA20)" else c_akt # Metoda limit teraz łapie cofnięcia do EMA9
        
        # Zarządzanie pozycją (R:R 1:2 na szybkie strzały)
        sl_buffer = atr * 0.1
        sl = wej - (atr * 1.2) - sl_buffer if sig == "KUP" else wej + (atr * 1.2) + sl_buffer
        tp = wej + (atr * 2.4) if sig == "KUP" else wej - (atr * 2.4)
        
        return {
            "Instrument": name, "Sygnał": sig, "Siła %": (95 if sig in ["KUP", "SPRZEDAJ"] else 50),
            "Cena Rynkowa": round(c_akt, 4), "Cena Wejścia": round(wej, 4), "RSI": round(rsi, 1),
            "StochRSI": round(macd_h, 4), # Zastąpiliśmy wyświetlanie StochRSI wartością Histogramu MACD (przydatniejsze)
            "Pęd": "Wzrost" if macd_bull else ("Spadek" if macd_bear else "Płaski"),
            "ADX": round(adx, 1), "Wolumen %": round(v_rat), 
            "Ile (1%)": round((kapital*0.01)/abs(wej-sl), 4) if abs(wej-sl) > 0 else 0,
            "TP": round(tp, 4), "SL": round(sl, 4)
        }
    except Exception as e:
        return {
            "Instrument": name, "Sygnał": f"BŁĄD WSK.: {e}", "Siła %": 0,
            "Cena Rynkowa": 0, "Cena Wejścia": 0, "RSI": 0, "StochRSI": 0, 
            "Pęd": "-", "ADX": 0, "Wolumen %": 0, "Ile (1%)": 0, "TP": 0, "SL": 0
        }
