import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import datetime
import plotly.graph_objects as go
import requests

# Konfiguracja strony
st.set_page_config(page_title="Kombinat Giełdowy", layout="wide")
st.title("📈 Kombinat Giełdowy - Multi-Strategy Dashboard")

# --- MODUŁ TELEGRAM (PUNKT 5) ---
st.sidebar.header("📱 Alerty Telegram")
st.sidebar.write("Chcesz powiadomienia na telefon? Wpisz dane bota z BotFather:")
tg_token = st.sidebar.text_input("Telegram Bot Token", type="password")
tg_chat_id = st.sidebar.text_input("Telegram Chat ID", type="password")

def wyslij_telegram(wiadomosc):
    if tg_token and tg_chat_id:
        url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
        payload = {"chat_id": tg_chat_id, "text": wiadomosc, "parse_mode": "Markdown"}
        try:
            r = requests.post(url, json=payload)
            if r.status_code == 200:
                st.sidebar.success("✅ Alert wysłany!")
            else:
                st.sidebar.error("❌ Błąd wysyłania (sprawdź Token/ID).")
        except:
            st.sidebar.error("❌ Błąd połączenia z Telegramem.")
    else:
        st.sidebar.warning("⚠️ Uzupełnij Token i Chat ID, aby wysłać.")

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
            
            # NOWOŚĆ: RVOL (Punkt 1) - Wolumen wzgędny z 10 dni
            df['Vol_SMA10'] = df['Volume'].rolling(window=10).mean()
            vol_akt = df['Volume'].iloc[-1]
            vol_sma10 = df['Vol_SMA10'].iloc[-1]
            rvol = vol_akt / vol_sma10 if pd.notna(vol_sma10) and vol_sma10 > 0 else 0
            
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
                "RVOL 🔥": round(rvol, 2), # Dodany RVOL
                "EMA10": round(ema10, 2),
                "ATR": round(atr, 2),
                "Sygnały": ", ".join(tagi) if tagi else "Brak"
            })
        except Exception as e:
            pass

    wyniki_df = pd.DataFrame(wyniki)
    
    # --- INTERFEJS STRONY ---
    # NOWOŚĆ: Zakładka z Wykresami (Punkt 2)
    tab1, tab2, tab3 = st.tabs(["🛡️ Mój Portfel", f"🌐 Master Screener ({len(wszystkie_tickery)} akcji)", "📈 Analiza Wykresów"])
    
    with tab1:
        st.header("Centrum Dowodzenia Portfelem")
        st.markdown("Analiza Twoich pozycji pod kątem Momentum (ADX), RVOL oraz Raportów Finansowych.")
        
        portfel_raport = []
        alerty_do_wyslania = [] # Zbieramy info do Telegrama
        
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
                rvol_akt = dane_spolki['RVOL 🔥'].values[0]
                
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
                    if opor_20 > cena_teraz * 1.015: 
                        opory_lista.append(f"{opor_20:.2f}$")
                    if opor_60 > opor_20 * 1.015: 
                        opory_lista.append(f"{opor_60:.2f}$")
                        
                    opory_str = " ➔ ".join(opory_lista) if opory_lista else "ATH 🚀"
                except:
                    opory_str = "Brak danych"
                    
                # NOWOŚĆ: RADAR WYNIKÓW FINANSOWYCH (Punkt 3)
                radar_wynikow = "Brak danych"
                try:
                    tk = yf.Ticker(sym)
                    daty = tk.get_earnings_dates(limit=1)
                    if daty is not None and not daty.empty:
                        najblizsza_data = daty.index[0]
                        dni_do_wynikow = (najblizsza_data.tz_localize(None) - datetime.datetime.now()).days
                        if 0 <= dni_do_wynikow <= 7:
                            radar_wynikow = f"⚠️ WYNIKI ZA {dni_do_wynikow} DNI!"
                            alerty_do_wyslania.append(f"⚠️ {sym}: Raport finansowy za {dni_do_wynikow} dni!")
                        elif dni_do_wynikow > 7:
                            radar_wynikow = f"Za {dni_do_wynikow} dni"
                        else:
                            radar_wynikow = "Po wynikach"
                except:
                    pass

                # OBLICZENIA WYNIKU I STOP LOSS
                wynik_proc = ((cena_teraz - cena_zakupu) / cena_zakupu) * 100
                stop_loss = cena_teraz - (1.5 * atr)
                
                status = "🟢 BYKI" if cena_teraz > ema10 else "🔴 UWAGA (Poniżej EMA10)"
                if "UWAGA" in status:
                    alerty_do_wyslania.append(f"🔴 {sym}: Spadek poniżej średniej EMA10! (Cena: {cena_teraz}$)")
                
                portfel_raport.append({
                    "Symbol": sym,
                    "Wynik": f"{wynik_proc:+.2f}%",
                    "Cena Aktualna": cena_wyswietlana,
                    "Trend": status,
                    "RVOL 🔥": rvol_akt,
                    "RSI": rsi,
                    "ADX": adx,
                    "Radar Wyników": radar_wynikow,
                    "Najbliższe Opory": opory_str,
                    "Stop Loss (ATR)": f"{stop_loss:.2f}$"
                })
        
        st.dataframe(pd.DataFrame(portfel_raport), use_container_width=True)
        
        # Przycisk wysyłania alertów
        if st.button("🚨 Wyślij podsumowanie portfela na Telegram"):
            if not alerty_do_wyslania:
                wyslij_telegram("🛡️ Twój portfel jest bezpieczny. Brak krytycznych alertów na dziś.")
            else:
                wiadomosc = "*RAPORT PORTFELA - Kombinat Giełdowy*\n\n" + "\n".join(alerty_do_wyslania)
                wyslij_telegram(wiadomosc)

    with tab2:
        st.header("Skaner Rynku: Wykryte Sygnały")
        tylko_sygnaly = st.checkbox("🔍 Pokaż tylko akcje z sygnałem (Ukryj szum)", value=True)
        
        if tylko_sygnaly:
            tabela_skaner = wyniki_df[wyniki_df['Sygnały'] != "Brak"]
        else:
            tabela_skaner = wyniki_df
            
        st.dataframe(tabela_skaner.sort_values(by="RSI", ascending=False), use_container_width=True)
        
        if st.button("🚨 Wyślij okazje rynkowe na Telegram"):
            okazje = tabela_skaner[tabela_skaner['Sygnały'] != "Brak"]
            if okazje.empty:
                wyslij_telegram("🔍 Dzisiejszy skan: Brak silnych okazji spełniających kryteria.")
            else:
                wiadomosc = "*TOP OKAZJE - Kombinat Giełdowy*\n\n"
                for idx, row in okazje.head(10).iterrows():
                    wiadomosc += f"• {row['Symbol']} - {row['Sygnały']} (RSI: {row['RSI']}, ADX: {row['ADX']})\n"
                wyslij_telegram(wiadomosc)

    # NOWOŚĆ: INTERAKTYWNE WYKRESY (Punkt 2)
    with tab3:
        st.header("Interaktywne Wykresy i Wizualizacja")
        st.write("Wybierz akcję, by zobaczyć moment wejścia instytucji (RVOL) i poziomy EMA10.")
        
        wybrany_ticker = st.selectbox("Wybierz spółkę:", sorted(wszystkie_tickery))
        
        if wybrany_ticker:
            df_wykres = dane_rynkowe[wybrany_ticker].copy() if len(wszystkie_tickery) > 1 else dane_rynkowe.copy()
            df_wykres.dropna(inplace=True)
            df_wykres = df_wykres.tail(90) # Ostatnie 3 miesiące dla czytelności
            
            # Wskaźniki do wykresu
            df_wykres['EMA10'] = ta.trend.ema_indicator(df_wykres['Close'], window=10)
            atr_wartosc = ta.volatility.average_true_range(df_wykres['High'], df_wykres['Low'], df_wykres['Close'], window=14).iloc[-1]
            stop_loss_linia = df_wykres['Close'].iloc[-1] - (1.5 * atr_wartosc)
            
            fig = go.Figure()
            
            # Świece japońskie
            fig.add_trace(go.Candlestick(x=df_wykres.index,
                open=df_wykres['Open'], high=df_wykres['High'],
                low=df_wykres['Low'], close=df_wykres['Close'],
                name='Cena'))
                
            # Średnia EMA10
            fig.add_trace(go.Scatter(x=df_wykres.index, y=df_wykres['EMA10'], 
                                     line=dict(color='blue', width=2), name='EMA 10 (Trend)'))
                                     
            # Linia Stop Loss
            fig.add_hline(y=stop_loss_linia, line_dash="dot", line_color="red", 
                          annotation_text=f"Stop Loss (ATR): {stop_loss_linia:.2f}$", annotation_position="bottom right")

            fig.update_layout(title=f'Analiza Techniczna: {wybrany_ticker}', yaxis_title='Cena $', 
                              xaxis_rangeslider_visible=False, template='plotly_dark')
            
            st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Dodaj akcje do arkusza Google i upewnij się, że link został poprawnie sformatowany.")
