# Dietly – Home Assistant Custom Component

[![GitHub Release](https://img.shields.io/github/v/release/LukaszP2/ha-dietly?style=flat-square)](https://github.com/LukaszP2/ha-dietly/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://hacs.xyz)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)

[![Otwórz repozytorium w HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=LukaszP2&repository=ha-dietly&category=integration)
[![Dodaj integrację do Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=dietly)

*(🇬🇧 English description below)*

---

## 🇵🇱 Opis

Nieoficjalna integracja z portalem Dietly.pl (catering dietetyczny, diety pudełkowe) dla Home Assistant. Pozwala na automatyczne śledzenie aktywnych zamówień, dostaw, posiłków oraz dziennych wartości kalorycznych i makroskładników.

### Główne funkcje
- Podsumowanie konta i liczba aktywnych diet
- Szczegóły aktywnego zamówienia (status, daty rozpoczęcia i zakończenia, dni do końca, adres i godzina dostawy)
- Dzienne podsumowanie makroskładników: kalorie (kcal), białko (g), tłuszcze (g), węglowodany (g)
- Sensory posiłków z informacjami o menu (śniadanie, II śniadanie, obiad, podwieczorek, kolacja)
- Obsługa wielu zamówień i automatyczne wykrywanie nowych diet

### Instalacja przez HACS (Niestandardowe repozytorium)

### 🚀 Szybka instalacja (1 kliknięcie przez My Home Assistant)

[![Otwórz repozytorium w HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=LukaszP2&repository=ha-dietly&category=integration)

Po zainstalowaniu i ponownym uruchomieniu Home Assistant, kliknij poniższy przycisk, aby skonfigurować integrację:

[![Dodaj integrację do Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=dietly)

#### Instalacja ręczna:
1. Upewnij się, że masz zainstalowany **HACS** w Home Assistant.
2. W HACS przejdź do: **Integracje** -> menu w prawym górnym rogu (trzy kropki) -> **Niestandardowe repozytoria** (*Custom repositories*).
3. W polu **Repozytorium** wklej adres:
   ```text
   https://github.com/LukaszP2/ha-dietly
   ```
4. W polu **Kategoria** wybierz: **Integracja** (*Integration*).
5. Kliknij **Dodaj**, a następnie wyszukaj **Dietly** i kliknij **Pobierz**.
6. Uruchom ponownie Home Assistant.

### Konfiguracja

1. W Home Assistant przejdź do: **Ustawienia** -> **Urządzenia oraz usługi** -> **Dodaj integrację**.
2. Wyszukaj **Dietly**.
3. Zaloguj się swoimi danymi konta.

### Gotowe szablony automatyzacji (Blueprints)

Integracja zawiera zestaw gotowych szablonów automatyzacji w katalogu `blueprints/automation/dietly/`:
1. **Codzienne menu i kalorie** (`daily_menu_notification.yaml`) – poranne powiadomienie z podsumowaniem posiłków i wartości odżywczych na dziś.
2. **Przypomnienie o końcu diety** (`diet_renewal_reminder.yaml`) – powiadomienie na 3 dni i 1 dzień przed końcem aktywnej diety, aby w porę złożyć kolejne zamówienie.
3. **Alert o braku dostawy na jutro** (`delivery_day_off_alert.yaml`) – wieczorny alert informujący o przerwie w cateringu (np. w weekend lub święto), aby zaplanować zakupy.
4. **Synchronizacja posiłków z Fitatu** (`dietly_to_fitatu_sync.yaml`) – automatyczne dodawanie dań i wartości makroskładników do dziennika w Fitatu.
5. **Wykrycie dostarczenia paczki pod drzwi** (`delivery_arrival_notification.yaml`) – powiadomienie o zostawieniu torby przez kuriera w nocnym oknie dostaw (kamera / czujnik ruchu).

---

## 🇬🇧 Description

Unofficial Dietly.pl (dietary catering) integration for Home Assistant. Monitors active orders, deliveries, daily meals, calories, and macronutrient targets.

### Included Automation Blueprints

Available in `blueprints/automation/dietly/`:
1. **Daily Menu Notification** – morning summary of scheduled meals and calories.
2. **Diet Renewal Reminder** – timely alerts before subscription ends to avoid delivery gaps.
3. **Delivery Day-Off Alert** – evening reminder when no catering is scheduled for tomorrow.
4. **Fitatu Sync** – automatically logs meals and macros into Fitatu food diary.
5. **Package Arrival Detection** – detects delivery courier arrival during overnight delivery hours.

### Installation via HACS (Custom Repository)

1. Open **HACS** in Home Assistant.
2. Navigate to **Integrations** -> top right menu (three dots) -> **Custom repositories**.
3. Enter repository URL:
   ```text
   https://github.com/LukaszP2/ha-dietly
   ```
4. Category: **Integration**.
5. Click **Add**, find **Dietly**, and install.
6. Restart Home Assistant.

---

## Licencja / License

Projekt objęty licencją [MIT](LICENSE).
