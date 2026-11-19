# Trener VLSM – IPv4

Interaktywna aplikacja desktopowa do nauki podziału sieci IPv4 metodą VLSM *(Variable Length Subnet Masking)*. Pozwala ćwiczyć obliczenia jednocześnie w zapisie binarnym i dziesiętnym, z natychmiastową informacją zwrotną.

## Zrzut ekranu

> *Uruchom aplikację, aby zobaczyć interfejs — `python vlsm_trener.py`*

## Funkcje

- **Podwójny zapis** — każde pole adresu ma obok siebie cztery oktety BIN i jedno pole DEC; zmiana w jednym zapisie automatycznie aktualizuje drugi.
- **Walidacja krok po kroku** — sprawdzanie maski, adresu sieci, negacji maski, broadcastu, pierwszego i ostatniego hosta, liczby przydzielonych i dostępnych adresów.
- **Kolorowanie oktetów** — błędne oktety są zaznaczone na czerwono, poprawne na zielono, co ułatwia zlokalizowanie pomyłki w konkretnym bajcie.
- **Tryb ścisły VLSM** — opcjonalne wymaganie stosowania najmniejszej wystarczającej maski.
- **Losowe ćwiczenia** — 6 wbudowanych zadań o różnym stopniu trudności, losowanych przyciskiem.
- **Dowolna liczba podsieci** — od 1 do 50 wierszy, regulowana spinboksem.
- **Pokaż rozwiązanie** — generuje wzorcowy przydział VLSM i wypełnia nim pola.
- **Wykrywanie nakładania** — zgłasza konflikty adresowe między podsieciami.
- **Obsługa CIDR** — adres sieci bazowej można wpisać jako `192.168.10.0/24`.

## Wymagania

| Zależność | Wersja |
|-----------|--------|
| Python    | 3.9+   |
| Tkinter   | wbudowany w CPython |

Aplikacja nie wymaga instalacji żadnych zewnętrznych pakietów — korzysta wyłącznie z biblioteki standardowej.

## Instalacja i uruchomienie

```bash
# Klonowanie repozytorium
git clone https://github.com/<uzytkownik>/vlsm-trener.git
cd vlsm-trener

# Uruchomienie aplikacji
python vlsm_trener.py
```

Na systemach Linux może być wymagana instalacja Tkintera:

```bash
# Debian / Ubuntu
sudo apt install python3-tk

# Fedora
sudo dnf install python3-tkinter
```

## Struktura projektu

```
vlsm_trener/
├── vlsm_core.py      # Logika obliczeń VLSM (bez zależności od GUI)
└── vlsm_trener.py    # Aplikacja Tkinter
```

### `vlsm_core.py`

Biblioteka bez GUI eksponuje:

| Symbol | Opis |
|--------|------|
| `parse_ipv4(value)` | Parsuje adres IPv4 z zapisu dziesiętnego lub binarnego |
| `parse_prefix(value)` | Parsuje prefiks `/n`, liczbę lub maskę dziesiętną/binarną |
| `generate_solution(base, host_counts)` | Generuje wzorcowy przydział VLSM |
| `check_answers(base_address, base_mask, answers, ...)` | Waliduje odpowiedzi użytkownika |
| `Answer` | Dataclass przechowująca jedną odpowiedź (maska, sieć, broadcast, …) |
| `ValidationReport` | Wynik walidacji całego zestawu podsieci |

### `vlsm_trener.py`

Interfejs Tkinter zbudowany z klas:

| Klasa | Rola |
|-------|------|
| `PairedAddress` | Widget synchronizujący pola BIN (4 oktety) ↔ DEC |
| `SubnetRow` | Karta jednej podsieci z pełnym zestawem pól obliczeniowych |
| `VLSMTrainer` | Główne okno aplikacji |

## Sposób ćwiczenia

1. Ustaw sieć bazową (adres i maskę) lub kliknij **Losuj zadanie**.
2. Dla każdej podsieci wpisz liczbę wymaganych urządzeń.
3. Wypełnij kolejno pola obliczeń — BIN, DEC lub oba naraz:
   - Maska podsieci
   - Adres sieci
   - Negacja maski
   - Broadcast
   - Pierwszy host
   - Ostatni host
   - Łączna liczba przydzielonych adresów
   - Liczba dostępnych adresów hostów
4. Kliknij **Sprawdź** (lub naciśnij `Ctrl+Enter`).
5. Popraw zaznaczone na czerwono pola i sprawdź ponownie.

## Wbudowane ćwiczenia

| Sieć bazowa | Podsieci | Wymagane hosty |
|-------------|----------|----------------|
| 192.168.10.0/24 | 4 | 60, 30, 14, 6 |
| 10.20.0.0/22    | 5 | 220, 100, 60, 30, 12 |
| 172.16.8.0/23   | 5 | 180, 90, 50, 20, 10 |
| 192.168.50.0/24 | 4 | 110, 50, 25, 10 |
| 10.30.16.0/21   | 6 | 400, 180, 80, 50, 20, 10 |
| 172.18.4.0/22   | 6 | 190, 110, 70, 35, 15, 5 |

## Skróty klawiszowe

| Skrót | Akcja |
|-------|-------|
| `Ctrl+Enter` | Sprawdź odpowiedzi |
| `Shift+Scroll` | Przewijanie poziome |

## Licencja

Projekt udostępniony na licencji [MIT](LICENSE).
