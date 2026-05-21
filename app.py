import streamlit as st
import json
import random
import os
import io
from datetime import datetime
from pydub import AudioSegment

# --- Konfiguracja strony ---
st.set_page_config(page_title="Zgadnij Hit", page_icon="🎵")
st.title("🎵 Zgadnij hit")

# --- Funkcje obsługi plików i statystyk ---

def wczytaj_piosenki_z_nazw_plikow():
    """
    Skanuje folder 'muzyka' i buduje bazę piosenek bezpośrednio na podstawie nazw plików MP3.
    Eliminuje potrzebę posiadania pliku piosenki.json!
    """
    folder_muzyka = "muzyka"
    if not os.path.exists(folder_muzyka):
        os.makedirs(folder_muzyka)
        st.warning(f"Stworzono pusty folder '{folder_muzyka}'. Wrzuć tam pliki MP3!")
        return []
        
    # Pobieramy tylko pliki z rozszerzeniem .mp3
    pliki = [f for f in os.listdir(folder_muzyka) if f.lower().endswith('.mp3')]
    baza_piosenek = []
    
    for plik in pliki:
        # Ścieżka do pliku (np. muzyka/Dawid Podsiadło - Małomiasteczkowy.mp3)
        # Używamy ukośników bezpiecznych dla każdego systemu
        sciezka_pliku = f"{folder_muzyka}/{plik}"
        
        # Odcinamy końcówkę ".mp3"
        nazwa_bez_rozszerzenia, _ = os.path.splitext(plik)
        
        # Dzielimy nazwę pliku na Wykonawcę i Tytuł według wzoru " - "
        if " - " in nazwa_bez_rozszerzenia:
            wykonawca, tytul = nazwa_bez_rozszerzenia.split(" - ", 1)
            wykonawca = wykonawca.strip()
            tytul = tytul.strip()
        else:
            wykonawca = "Nieznany"
            tytul = nazwa_bez_rozszerzenia.strip()
            
        baza_piosenek.append({
            "wykonawca": wykonawca,
            "tytul": tytul,
            "plik": sciezka_pliku
        })
        
    return baza_piosenek

def wczytaj_statystyki():
    if os.path.exists("statystyki.json"):
        with open("statystyki.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def zapisz_statystyki(staty):
    with open("statystyki.json", "w", encoding="utf-8") as f:
        json.dump(staty, f, ensure_ascii=False, indent=4)

def zapisz_log_wynikow(imie, wykonawca, tytul, czy_zgadnieto):
    data_gry = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "Zgadnięto" if czy_zgadnieto else "Pudło"
    wpis = f"[{data_gry}] Gracz: {imie} | Piosenka: {wykonawca} - {tytul} | Wynik: {status}\n"
    with open("wyniki.txt", "a", encoding="utf-8") as f:
        f.write(wpis)

@st.cache_data
def przygotuj_fragment(sciezka, sekundy):
    """Tnie plik audio do wskazanej długości w pamięci (RAM)."""
    try:
        dzwiek = AudioSegment.from_file(sciezka)
        fragment = dzwiek[:sekundy * 1000]
        buf = io.BytesIO()
        fragment.export(buf, format="mp3")
        return buf.getvalue()
    except Exception as e:
        st.error(f"Błąd przetwarzania audio: {e}")
        return None

# --- Definicja wyskakującego okienka (Modal Dialog) ---
@st.dialog("Koniec rundy! 🏁", width="large")
def pokaz_okno_koncowe(status, prawidlowa_odpowiedz):
    if status == 'wygrana':
        st.success(f"🎉 **Doskonale!** Odgadłeś ten hit:\n\n### {prawidlowa_odpowiedz}")
        st.balloons()
    else:
        st.error(f"❌ Tym razem się nie udało. Prawidłowa odpowiedź to:\n\n### {prawidlowa_odpowiedz}")
        st.info("💡 Ta piosenka pozostała w Twojej puli. Trafisz na nią ponownie w kolejnych rundach!")
    
    st.write("---")
    st.write("Kliknij poniższy przycisk, aby wylosować kolejny utwór.")
    
    if st.button("Rozpocznij następną piosenkę ⏭", type="primary", use_container_width=True):
        if "aktualna" in st.session_state:
            del st.session_state.aktualna
        st.session_state.etap = 0
        st.rerun()

# --- EKRAN LOGOWANIA / PROFILU ---
if "gracz" not in st.session_state:
    st.subheader("👋 Witaj w grze muzycznej!")
    imie_input = st.text_input("Wpisz swoje imię, aby rozpocząć lub wczytać swój zapis:", placeholder="Twoje imię...").strip()
    
    if st.button("Rozpocznij grę", type="primary", use_container_width=True):
        if imie_input:
            st.session_state.gracz = imie_input
            st.rerun()
        else:
            st.warning("Imię nie może być puste!")
    st.stop()

# --- INICJALIZACJA DANYCH GRACZA ---
imie = st.session_state.gracz

# ZMIANA: Pobieramy bazę bezpośrednio skanując pliki w folderze muzyka
baza = wczytaj_piosenki_z_nazw_plikow()

if baza:
    staty = wczytaj_statystyki()
    
    if imie not in staty:
        staty[imie] = {"rekord": 0, "odgadniete": []}
        zapisz_statystyki(staty)
        
    odgadniete_pliki = staty[imie]["odgadniete"]
    
    # Filtrujemy bazę, odrzucając ścieżki plików, które gracz już odgadł
    pula_dostepnych = [p for p in baza if p["plik"] not in odgadniete_pliki]
    
    ilosc_odgadnietych = len(odgadniete_pliki)
    ilosc_wszystkich = len(baza)

    # Panel boczny (Sidebar)
    st.sidebar.title(f"👤 Profil: {imie}")
    st.sidebar.metric("Odgadnięte hity", f"{ilosc_odgadnietych} pkt")
    st.sidebar.write(f"📊 Twój całkowity postęp: **{ilosc_odgadnietych} / {ilosc_wszystkich}**")
    
    if st.sidebar.button("🚪 Zmień gracza / Wyloguj"):
        del st.session_state.gracz
        if "aktualna" in st.session_state:
            del st.session_state.aktualna
        st.rerun()

    # Ekran końca CAŁEJ gry
    if not pula_dostepnych:
        st.balloons()
        st.success(f"🎉 Gratulacje {imie}! Ukończyłeś całą grę i odgadłeś wszystkie hity z folderu ({ilosc_odgadnietych}/{ilosc_wszystkich})!")
        if st.button("Zresetuj swoją pulę i zagraj od nowa", type="primary"):
            staty[imie]["odgadniete"] = []
            zapisz_statystyki(staty)
            st.rerun()
        st.stop()

    # --- LOGIKA LOSOWANIA UTWORU ---
    if "aktualna" not in st.session_state or st.session_state.aktualna not in pula_dostepnych:
        st.session_state.aktualna = random.choice(pula_dostepnych)
        st.session_state.etap = 0

    DLUGOSCI = [1, 3, 6, 10]
    aktualny_etap = st.session_state.etap
    dozwolone_sekundy = DLUGOSCI[aktualny_etap]

    # Licznik postępu na ekranie głównym
    st.write(f"📊 Runda: **{ilosc_odgadnietych + 1} / {ilosc_wszystkich}** (Odgadnięte ogółem: {ilosc_odgadnietych})")
    st.write(f"🎵 Posłuchaj fragmentu (**{dozwolone_sekundy}s**) i spróbuj odgadnąć:")

    # Odtwarzacz audio
    plik_audio = st.session_state.aktualna["plik"]
    if os.path.exists(plik_audio):
        dane_audio = przygotuj_fragment(plik_audio, dozwolone_sekundy)
        if dane_audio:
            st.audio(dane_audio, format="audio/mp3")
    else:
        st.error(f"Brak pliku audio: {plik_audio}")

    # --- INTERFEJS ROZGRYWKI ---
    prawdziwa_odpowiedz = f"{st.session_state.aktualna['wykonawca']} - {st.session_state.aktualna['tytul']}"
    lista_podpowiedzi = [f"{p['wykonawca']} - {p['tytul']}" for p in baza]
    lista_podpowiedzi.sort()

    # Dynamiczny klucz resetuje pole wyszukiwania po zmianie pliku piosenki
    wybor = st.selectbox(
        "Wpisz wykonawcę lub tytuł hitu:", 
        options=lista_podpowiedzi, 
        index=None, 
        placeholder="Zacznij pisać...",
        key=f"wybor_{st.session_state.aktualna['plik']}"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ Sprawdź odpowiedź", use_container_width=True):
            if not wybor:
                st.warning("Wybierz piosenkę z listy przed sprawdzeniem!")
            else:
                if wybor == prawdziwa_odpowiedz:
                    if plik_audio not in staty[imie]["odgadniete"]:
                        staty[imie]["odgadniete"].append(plik_audio)
                        zapisz_statystyki(staty)
                    zapisz_log_wynikow(imie, st.session_state.aktualna['wykonawca'], st.session_state.aktualna['tytul'], True)
                    
                    pokaz_okno_koncowe('wygrana', prawdziwa_odpowiedz)
                else:
                    if st.session_state.etap < 3:
                        st.session_state.etap += 1
                        st.error("❌ To nie ten hit! Spróbuj ponownie z dłuższym fragmentem.")
                        st.rerun()
                    else:
                        zapisz_log_wynikow(imie, st.session_state.aktualna['wykonawca'], st.session_state.aktualna['tytul'], False)
                        pokaz_okno_koncowe('przegrana', prawdziwa_odpowiedz)

    with col2:
        if st.session_state.etap < 3:
            nastepne_sekundy = DLUGOSCI[st.session_state.etap + 1]
            if st.button(f"⏭️ Pomiń (+{nastepne_sekundy}s)", use_container_width=True):
                st.session_state.etap += 1
                st.rerun()
        else:
            if st.button("⏭️ Nie wiem (Pokaż odpowiedź)", use_container_width=True):
                zapisz_log_wynikow(imie, st.session_state.aktualna['wykonawca'], st.session_state.aktualna['tytul'], False)
                pokaz_okno_koncowe('przegrana', prawdziwa_odpowiedz)
