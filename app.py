import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import datetime
import plotly.graph_objects as go
import requests
import google.generativeai as genai

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Kombinat Giełdowy", layout="wide")
st.title("📈 Kombinat Giełdowy - Multi-Strategy Dashboard (2-Week Swing Pro)")

# --- PANEL BOCZNY (KLUCZE API I TELEGRAM) ---
st.sidebar.header("🔑 Klucze Dostępu")
gemini_api_key = st.sidebar.text_input("Gemini API Key", type="password")

st.sidebar.header("📱 Alerty Telegram")
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
        except:
            pass

# --- 1. POBIERANIE DANYCH ---
@st.cache_data(ttl=60)
def pobierz_portfel():
    sheet_id = "1-42YeBNnrJuzs9QTcWUy0Od4UQDyOvN2iX5yR591VlE"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        return pd.read_csv(csv_url)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=900)
def pobierz_dane_rynkowe(tickers):
    # Pobieramy rok danych, by wyłapywać historyczne szczyty (52W) i duże średnie
    return yf.download(tickers, period="1y", group_by="ticker", progress=False)

# Top NASDAQ + Giganci Tech + QQQ jako Benchmark
nasdaq_top = [
    'QQQ', 'AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'GOOGL', 'GOOG', 'TSLA', 'AVGO', 'PEP',
    'COST', 'LIN', 'AMD', 'NFLX', 'QCOM', 'TMUS', 'INTC', 'TXN', 'AMAT', 'HON',
    'AMGN', 'ISRG', 'SBUX', 'BKNG', 'ADP', 'GILD', 'MDLZ', 'REGN', 'ADI', 'VRTX',
    'LRCX', 'PANW', 'MU', 'SNPS', 'KLAC', 'CDNS', 'MELI', 'PYPL', 'ASML', 'CSCO',
    'CMCSA', 'ADBE', 'INTU', 'ORCL', 'PLTR', 'UBER', 'ABNB', 'MRNA', 'CRWD', 'MAR',
    'CTAS', 'CSX', 'DXCM', 'FAST', 'FTNT', 'KDP', 'MNST', 'ODFL', 'PAYX', 'PCAR',
    'ROST', 'SIRI', 'VRSK', 'VRSN', 'WBA', 'WBD', 'WDAY', 'XEL', 'ZM', 'ZS',
    'TEAM', 'DDOG', 'LCID', 'RIVN', 'PDD', 'JD', 'BIDU', 'NTES', 'CPRT', 'MCHP',
    'ADSK', 'IDXX', 'AEP', 'CSGP', 'ON', 'ORLY', 'ANSS', 'EXC', 'BKR', 'CTSH',
    'CRM', 'NOW', 'SQ', 'SHOP', 'TSM', 'BABA', 'SPOT', 'IBM', 'U', 'RBLX', 
    'COIN', 'HOOD', 'ARM', 'SNOW', 'MRVL', 'APP', 'CIEN'
]

# --- GŁÓWNA LOGIKA SYSTEMU ---
portfel_df = pobierz_portfel()

if not portfel_df.empty:
    twoje_tickery = portfel_df['Symbol'].tolist()
    wszystkie_tickery = list(set(nasdaq_top + twoje_tickery + ['QQQ']))
    
    st.write(f"🔄 *Skanuję bazę {len(wszystkie_tickery)} spółek z pełną analityką dla Swing Traderów...*")
    dane_rynkowe = pobierz_dane_rynkowe(wszystkie_tickery)
    
    # Wyciąganie Benchmarku QQQ
    try:
        qqq_close = dane_rynkowe['QQQ']['Close']
        qqq_ret_10d = qqq_close.pct_change(periods=10)
    except:
        qqq_ret_10d = None
    
    wyniki = []
    
    for ticker in wszystkie_tickery:
        if ticker == 'QQQ': continue # Ukrywamy indeks ze skanera
        
        try:
            df = dane_rynkowe[ticker].copy() if len(wszystkie_tickery) > 1 else dane_rynkowe.copy()
            df.dropna(inplace=True)
            if len(df) < 200: continue 
            
            cena_akt = df['Close'].iloc[-1]
            
            # WSKAŹNIKI TRENDU I ZMIENNOŚCI
            df['EMA10'] = ta.trend.ema_indicator(df['Close'], window=10)
            df['EMA20'] = ta.trend.ema_indicator(df['Close'], window=20)
            df['SMA50'] = ta.trend.sma_indicator(df['Close'], window=50)
            df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
            df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
            df['ADX'] = ta.trend.adx(df['High'], df['Low'], df['Close'], window=14)
            df['MACD_Hist'] = ta.trend.macd_diff(df['Close'])
            
            # WSKAŹNIKI SWING TRADING (Timing wejścia)
            stoch = ta.momentum.StochasticOscillator(high=df['High'], low=df['Low'], close=df['Close'], window=14, smooth_window=3)
            df['Stoch_K'] = stoch.stoch()
            df['Stoch_D'] = stoch.stoch_signal()
            df['Williams_R'] = ta.momentum.williams_r(high=df['High'], low=df['Low'], close=df['Close'], lbp=14)
            
            # WSKAŹNIKI WOLUMENU (Paliwo i Smart Money)
            df['OBV'] = ta.volume.on_balance_volume(df['Close'], df['Volume'])
            df['OBV_SMA10'] = ta.trend.sma_indicator(df['OBV'], window=10)
            df['Vol_SMA10'] = df['Volume'].rolling(window=10).mean()
            vol_akt = df['Volume'].iloc[-1]
            vol_sma10 = df['Vol_SMA10'].iloc[-1]
            rvol = vol_akt / vol_sma10 if pd.notna(vol_sma10) and vol_sma10 > 0 else 0
            
            # ZWROTY I SIŁA
            df['Return_5d'] = df['Close'].pct_change(periods=5)
            df['Return_10d'] = df['Close'].pct_change(periods=10)
            zwrot_5d = df['Return_5d'].iloc[-1]
            rs_vs_qqq = (df['Return_10d'].iloc[-1] - qqq_ret_10d.iloc[-1]) * 100 if qqq_ret_10d is not None else 0
            
            szczyt_52w = df['High'].tail(252).max()
            odleglosc_52w = ((szczyt_52w - cena_akt) / szczyt_52w) * 100
            atr_proc = (df['ATR'].iloc[-1] / cena_akt) * 100
            
            # OSTATNIE WARTOŚCI
            ema10 = df['EMA10'].iloc[-1]
            ema20 = df['EMA20'].iloc[-1]
            sma50 = df['SMA50'].iloc[-1]
            rsi = df['RSI'].iloc[-1]
            stoch_k = df['Stoch_K'].iloc[-1]
            stoch_k_wczoraj = df['Stoch_K'].iloc[-2]
            stoch_d = df['Stoch_D'].iloc[-1]
            stoch_d_wczoraj = df['Stoch_D'].iloc[-2]
            williams_r = df['Williams_R'].iloc[-1]
            obv_akt = df['OBV'].iloc[-1]
            obv_sma = df['OBV_SMA10'].iloc[-1]
            macd_hist = df['MACD_Hist'].iloc[-1]
            macd_rosnie = macd_hist > df['MACD_Hist'].iloc[-2]
            
            # --- SYSTEM TAGOWANIA (AGENTY AI) ---
            tagi = []
            
            # 1. Rakieta
            if cena_akt > ema10 and zwrot_5d > 0.07 and rvol > 1.2 and rsi > 60: 
                if odleglosc_52w < 5: tagi.append("🚀 RAKIETA (Wybicie 52W!)")
                else: tagi.append("🚀 RAKIETA (Świeży Rajd)")
            
            # 2. Timing wejścia (Swing)
            if stoch_k > stoch_d and stoch_k_wczoraj <= stoch_d_wczoraj and stoch_k < 80:
                tagi.append("🎯 STOCH CROSS")
            if williams_r > -20 and rsi > 55:
                tagi.append("🔥 W%R WYSTRZAŁ")
            
            # 3. Przepływ Kapitału (Smart Money)
            if rs_vs_qqq > 10: tagi.append("💪 LIDER (+10% nad rynek)")
            if obv_akt > obv_sma * 1.05 and rvol > 1.2: tagi.append("🌊 AKUMULACJA")
            if rsi > 65 and macd_hist > 0 and macd_rosnie: tagi.append("⚡ MACD PRZYSPIESZA")
                
            wyniki.append({
                "Symbol": ticker,
                "Cena": round(cena_akt, 2),
                "Wystrzał 5D": f"{(zwrot_5d * 100):.1f}%",
                "Williams %R": round(williams_r, 1),
                "RS vs QQQ": f"{rs_vs_qqq:+.1f}%",
                "Do Szczytu 52W": f"-{odleglosc_52w:.1f}%",
                "ATR %": f"{atr_proc:.1f}%",
                "RSI": round(rsi, 1),
                "RVOL 🔥": round(rvol, 2),
                "Krótki Trend (10/20)": "🟢 EMA10 > 20" if ema10 > ema20 else "🔴 EMA10 < 20",
                "Sygnały": ", ".join(tagi) if tagi else "Brak"
            })
        except Exception as e:
            pass

    wyniki_df = pd.DataFrame(wyniki)
    
    # --- BUDOWA ZAKŁADEK (TABS) ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "🛡️ Mój Portfel (Strażnik)", 
        f"🌐 Master Screener ({len(wyniki_df)} akcji)", 
        "📈 Wykresy Pro", 
        "🧠 AI Dyrektor Finansowy"
    ])
    
    # ZAKŁADKA 1: PORTFEL
    with tab1:
        st.header("Centrum Dowodzenia Portfelem (2-Week Horizon)")
        portfel_raport = []
        alerty_do_wyslania = []
        
        for index, row in portfel_df.iterrows():
            sym = row['Symbol']
            cena_zakupu = row['Cena_Kupna']
            dane_spolki = wyniki_df[wyniki_df['Symbol'] == sym]
            
            if not dane_spolki.empty:
                cena_teraz = dane_spolki['Cena'].values[0]
                rsi = dane_spolki['RSI'].values[0]
                rvol_akt = dane_spolki['RVOL 🔥'].values[0]
                wystrzal = dane_spolki['Wystrzał 5D'].values[0]
                rs_qqq = dane_spolki['RS vs QQQ'].values[0]
                trend_10_20 = dane_spolki['Krótki Trend (10/20)'].values[0]
                
                # Opcjonalny Pre-Market
                try:
                    info = yf.Ticker(sym).info
                    pre_market = info.get('preMarketPrice', None)
                    cena_wyswietlana = f"{cena_teraz:.2f}$ (Pre: {pre_market}$)" if pre_market else f"{cena_teraz:.2f}$"
                except:
                    cena_wyswietlana = f"{cena_teraz:.2f}$"

                # Radar Wyników Finansowych (Earnings)
                radar_wynikow = "Brak"
                try:
                    tk = yf.Ticker(sym)
                    daty = tk.get_earnings_dates(limit=1)
                    if daty is not None and not daty.empty:
                        najblizsza_data = daty.index[0]
                        dni_do_wynikow = (najblizsza_data.tz_localize(None) - datetime.datetime.now()).days
                        if 0 <= dni_do_wynikow <= 10:
                            radar_wynikow = f"⚠️ {dni_do_wynikow} DNI!"
                            alerty_do_wyslania.append(f"⚠️ {sym}: Raport finansowy za {dni_do_wynikow} dni!")
                        elif dni_do_wynikow > 10:
                            radar_wynikow = f"Za {dni_do_wynikow} dni"
                except:
                    pass

                wynik_proc = ((cena_teraz - cena_zakupu) / cena_zakupu) * 100
                
                try:
                    ema10_akt = dane_rynkowe[sym]['Close'].ewm(span=10, adjust=False).mean().iloc[-1]
                    status = "🟢 Trzymaj" if cena_teraz > ema10_akt else "🔴 Zagrożenie"
                    if "Zagrożenie" in status:
                        alerty_do_wyslania.append(f"🔴 {sym}: Cena spadła poniżej EMA10! ({cena_teraz}$)")
                except:
                    status = "Brak"
                
                portfel_raport.append({
                    "Symbol": sym,
                    "Zysk Całkowity": f"{wynik_proc:+.2f}%",
                    "Cena Aktualna": cena_wyswietlana,
                    "Status EMA10": status,
                    "Zysk 5D": wystrzal,
                    "EMA10 vs 20": trend_10_20,
                    "Wyniki Fin": radar_wynikow,
                    "RS vs QQQ": rs_qqq,
                    "RVOL 🔥": rvol_akt,
                    "RSI": rsi
                })
        
        st.dataframe(pd.DataFrame(portfel_raport), use_container_width=True)
        
        if st.button("🚨 Wyślij podsumowanie portfela na Telegram"):
            if not alerty_do_wyslania:
                wyslij_telegram("🛡️ Twój portfel jest bezpieczny. Brak krytycznych alertów na dziś.")
            else:
                wiadomosc = "*RAPORT PORTFELA (Swing)*\n\n" + "\n".join(alerty_do_wyslania)
                wyslij_telegram(wiadomosc)

    # ZAKŁADKA 2: SKANER
    with tab2:
        st.header("Master Screener: Wykryte Sygnały (Krótki Swing)")
        st.write("Szukaj przecięć Stochastycznych (setup do wejścia) i wystrzałów Williamsa (%R > -20) pod kątem 14 dni.")
        tylko_sygnaly = st.checkbox("🔍 Pokaż tylko akcje z sygnałem (Ukryj szum)", value=True)
        tabela_skaner = wyniki_df[wyniki_df['Sygnały'] != "Brak"] if tylko_sygnaly else wyniki_df
        
        st.dataframe(tabela_skaner.sort_values(by="Wystrzał 5D", ascending=False), use_container_width=True)

    # ZAKŁADKA 3: WYKRESY
    with tab3:
        st.header("Interaktywne Wykresy Pro (Timing 14-dniowy)")
        wybrany_ticker = st.selectbox("Wybierz spółkę do analizy wizualnej:", sorted([t for t in wszystkie_tickery if t != 'QQQ']))
        if wybrany_ticker:
            df_wykres = dane_rynkowe[wybrany_ticker].copy() if len(wszystkie_tickery) > 1 else dane_rynkowe.copy()
            df_wykres.dropna(inplace=True)
            df_wykres = df_wykres.tail(120) 
            
            df_wykres['EMA10'] = ta.trend.ema_indicator(df_wykres['Close'], window=10)
            df_wykres['EMA20'] = ta.trend.ema_indicator(df_wykres['Close'], window=20) 
            
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df_wykres.index, open=df_wykres['Open'], high=df_wykres['High'], low=df_wykres['Low'], close=df_wykres['Close'], name='Cena'))
            fig.add_trace(go.Scatter(x=df_wykres.index, y=df_wykres['EMA10'], line=dict(color='blue', width=2), name='EMA 10 (Szybka)'))
            fig.add_trace(go.Scatter(x=df_wykres.index, y=df_wykres['EMA20'], line=dict(color='orange', width=2, dash='dot'), name='EMA 20 (Swing Baza)'))
            
            fig.update_layout(title=f'Analiza Techniczna: {wybrany_ticker}', yaxis_title='Cena $', xaxis_rangeslider_visible=False, template='plotly_dark', height=600)
            st.plotly_chart(fig, use_container_width=True)

    # ZAKŁADKA 4: GEMINI AI
    with tab4:
        st.header("🧠 AI Dyrektor Finansowy (Model: Gemini 3.1 pro)")
        if gemini_api_key:
            if st.button("🤖 Generuj Raport Strategiczny"):
                with st.spinner("Czytam gęste dane z rynku i szukam snajperskich wejść na 2 tygodnie..."):
                    try:
                        genai.configure(api_key=gemini_api_key)
                        model = genai.GenerativeModel('gemini-2.5-pro')
                        skaner_txt = wyniki_df[wyniki_df['Sygnały'] != "Brak"].to_string(index=False)
                        
                        prompt = f"""
                        Jesteś Quants Swing Traderem. Twój ścisły horyzont inwestycyjny to 5-14 sesji giełdowych.
                        Masz przed sobą dzisiejszy skrypt skanera rynku:
                        {skaner_txt}
                        
                        ZADANIE:
                        1. Wskażnajlepsze spółki do ataku na najbliższe 1-2 tygodnie.
                        2. Uzasadnij wybór powołując się KONKRETNIE na tagi "STOCH CROSS" (dla timingu wejścia), "W%R WYSTRZAŁ", "RVOL" oraz "AKUMULACJA" oraz swoje spostrzezenia i dodaj czy jakies swiece sie tworzą oraz poszukaj dodatkowych informacji. 
                        3. Wyjaśnij, dlaczego te parametry dają nam przewagę w tak krótkim horyzoncie.
                        Pisz jak profesjonalista z Wall Street - konkretnie, w punkt. Nie marnuj słów.
                        4. oceń moje portfolio i jak powiniem sie zachować w kolejnych sesjach.
                        """
                        response = model.generate_content(prompt)
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"Błąd Gemini: Sprawdź swój klucz API. Szczegóły: {e}")
        else:
            st.warning("⚠️ Wpisz swój Gemini API Key w lewym panelu bocznym, aby odblokować Dyrektora Finansowego.")

else:
    st.warning("Baza Danych jest pusta lub brakuje dostępu. Upewnij się, że link do Arkusza Google został dodany poprawnie.")
