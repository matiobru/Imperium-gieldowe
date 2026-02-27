import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import datetime

# Konfiguracja strony
st.set_page_config(page_title="Kombinat Giełdowy", layout="wide")
st.title("📈 Kombinat Giełdowy - Multi-Strategy Dashboard")

# 1. Pobieranie Twojego Portfela z Google Sheets
@st.cache_data(ttl=60)
def pobierz_portfel():
    sheet_id = "1-42YeBNnrJuzs9QTcWUy0Od4UQDyOvN2iX5yR591VlE"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        st.error("Błąd pobierania Arkusza Google.")
        return pd.DataFrame()

# 2. Pobieranie danych giełdowych z Yahoo
@st.cache_data(ttl=900)
def pobierz_dane_rynkowe(tickers):
    dane = yf.download(tickers, period="6mo", group_by="ticker", progress=False)
    return dane

# PEŁNY NASDAQ 100 + GIGANCI TECH
nasdaq_top = [
    'AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'GOOGL', 'GOOG', 'TSLA', 'AVGO', 'PEP',
    'COST', 'LIN', 'AMD', 'NFLX', 'QCOM', 'TMUS', 'INTC', 'TXN', 'AMAT', 'HON',
    'AMGN', 'ISRG', 'SBUX', 'BKNG', 'ADP', 'GILD', 'MDLZ', 'REGN', 'ADI', 'VRTX',
    'LRCX', 'PANW', 'MU', 'SNPS', 'KLAC', 'CDNS', 'MELI', 'PYPL', 'ASML', 'CSCO',
    'CMCSA', 'ADBE', 'INTU', 'ORCL', 'PLTR', 'UBER', 'ABNB', 'MRNA', 'CRWD', 'MAR',
    'CTAS', 'CSX', 'DXCM', 'FAST', 'FTNT', 'KDP', 'MNST', 'ODFL', 'PAYX', 'PCAR',
    'ROST', 'SIRI', 'VRSK', 'VRSN', 'WBA', 'WBD', 'WDAY', 'XEL', 'ZM', 'ZS',
    'TEAM', 'DDOG', 'LCID', 'RIVN', 'PDD', 'JD', 'BIDU', 'NTES', 'CPRT', 'MCHP',
    'ADSK', 'IDXX', 'AEP', 'CSGP', 'ON', 'ORLY', 'ANSS', 'EXC', 'BKR', 'CTSH',
    'CRM', 'NOW', 'SQ', 'SHOP', 'TSM', 'BABA', 'SPOT', 'IBM', 'U', 'RBLX', 
    'COIN', 'HOOD', 'ARM', 'SNOW', 'MRVL', 'APP'
]

# --- GŁÓWNA LOGIKA ---
portfel_df = pobierz_portfel()

if not portfel_df.empty:
    twoje_tickery = portfel_df['Symbol'].tolist()
    wszystkie_tickery = list(set(nasdaq_top + twoje_tickery))
    
    st.write(f"🔄 *Skanuję bazę {len(wszystkie_tickery)} spółek technologicznych...*")
    dane_rynkowe = pobierz_dane_rynkowe(wszystkie_tickery)
    
    wyniki = []
    
    for ticker in wszystkie_tickery:
        try:
            if len(wszystkie_tickery) > 1:
                df = dane_rynkowe[ticker].copy()
            else:
                df = dane_rynkowe.copy()
                
            df.dropna(inplace=True)
            if len(df) < 50: continue
            
            cena_akt = df['Close'].iloc[-1]
            
            df['EMA10'] = ta.trend.ema_indicator(df['Close'], window=10)
            df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
            df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
            df['ADX'] = ta.trend.adx(df['High'], df['Low'], df['Close'], window=14)
            
            bb = ta.volatility.BollingerBands(close=df['Close'], window=20, window_dev=2)
            df['BB_High'] = bb.bollinger_hband()
            df['BB_Low'] = bb.bollinger_lband()
            
            ema10 = df['EMA10'].iloc[-1]
            rsi = df['RSI'].iloc[-1]
            atr = df['ATR'].iloc[-1]
            adx = df['ADX'].iloc[-1]
            bb_low = df['BB_Low'].iloc[-1]
            
            tagi = []
            if cena_akt > ema10 and rsi > 70 and adx > 25: tagi.append("🚀 MOMENTUM")
            if rsi < 32 and cena_akt <= bb_low * 1.02: tagi.append("🚑 ODBICIE")
            
            szerokosc_bb = (df['BB_High'].iloc[-1] - df['BB_Low'].iloc[-1]) / cena_akt
            if szerokosc_bb < 0.05 and rsi > 50: tagi.append("🎯 SQUEEZE")
                
            wyniki.append({
                "Symbol": ticker,
                "Cena": round(cena_akt, 2),
                "RSI": round(rsi, 1),
                "ADX": round(adx, 1),
                "EMA10": round(ema10, 2),
                "ATR": round(atr, 2),
                "Sygnały": ", ".join(tagi) if tagi else "Brak"
            })
        except Exception as e:
            pass

    wyniki_df = pd.DataFrame(wyniki)
    
    # --- INTERFEJS STRONY ---
    tab1, tab2 = st.tabs(["🛡️ Mój Portfel (Agent 1)", f"🌐 Master Screener ({len(wszystkie_tickery)} akcji)"])
    
    with tab1:
        st.header("Centrum Dowodzenia Portfelem")
        st.markdown("Analiza Twoich pozycji pod kątem Momentum (ADX) oraz poziomów oporu.")
        
        portfel_raport = []
        for index, row in portfel_df.iterrows():
            sym = row['Symbol']
            cena_zakupu = row['Cena_Kupna']
            
            dane_spolki = wyniki_df[wyniki_df['Symbol'] == sym]
            if not dane_spolki.empty:
                cena_teraz = dane_spolki['Cena'].values[0]
                atr = dane_spolki['ATR'].values[0]
                rsi = dane_spolki['RSI'].values[0]
                ema10 = dane_spolki['EMA10'].values[0]
                adx = dane_spolki['ADX'].values[0]
                
                # WYCIĄGANIE PRE-MARKET
                try:
                    info = yf.Ticker(sym).info
                    pre_market = info.get('preMarketPrice', None)
                    if pre_market and pre_market > 0:
                        cena_wyswietlana = f"{cena_teraz:.2f}$ (Pre: {pre_market}$)"
                    else:
                        cena_wyswietlana = f"{cena_teraz:.2f}$"
                except:
                    cena_wyswietlana = f"{cena_teraz:.2f}$"

                # SZUKANIE OPORÓW (Najwyższe punkty z 20 i 60 dni)
                try:
                    df_sym = dane_rynkowe[sym] if len(wszystkie_tickery) > 1 else dane_rynkowe
                    opor_20 = df_sym['High'].tail(20).max()
                    opor_60 = df_sym['High'].tail(60).max()
                    
                    opory_lista = []
                    if opor_20 > cena_teraz * 1.015: # Opór wyższy o min 1.5% od ceny
                        opory_lista.append(f"{opor_20:.2f}$")
                    if opor_60 > opor_20 * 1.015: 
                        opory_lista.append(f"{opor_60:.2f}$")
                        
                    opory_str = " ➔ ".join(opory_lista) if opory_lista else "ATH 🚀 (Brak oporów)"
                except:
                    opory_str = "Brak danych"

                # OBLICZENIA WYNIKU I STOP LOSS
                wynik_proc = ((cena_teraz - cena_zakupu) / cena_zakupu) * 100
                stop_loss = cena_teraz - (1.5 * atr)
                take_profit = cena_teraz + (2 * atr)
                
                status = "🟢 BYKI" if cena_teraz > ema10 else "🔴 UWAGA (Spadek pod EMA10)"
                
                portfel_raport.append({
                    "Symbol": sym,
                    "Wynik": f"{wynik_proc:+.2f}%",
                    "Cena Aktualna": cena_wyswietlana,
                    "Trend": status,
                    "RSI": rsi,
                    "ADX (Siła)": adx,
                    "EMA10": ema10,
                    "Najbliższe Opory": opory_str,
                    "Stop Loss (ATR)": f"{stop_loss:.2f}$"
                })
        
        st.dataframe(pd.DataFrame(portfel_raport), use_container_width=True)

    with tab2:
        st.header("Skaner Rynku: Wykryte Sygnały")
        tylko_sygnaly = st.checkbox("🔍 Pokaż tylko akcje z sygnałem (Ukryj szum)", value=True)
        
        if tylko_sygnaly:
            tabela_skaner = wyniki_df[wyniki_df['Sygnały'] != "Brak"]
        else:
            tabela_skaner = wyniki_df
            
        st.dataframe(tabela_skaner.sort_values(by="RSI", ascending=False), use_container_width=True)

else:
    st.warning("Dodaj akcje do arkusza Google i upewnij się, że link został poprawnie sformatowany.")
