# Übersicht

## Kurzbeschreibung

Dieses Verzeichnis enthält ein Skript `ea_fc26_bot.py`, das stündlich die Transfermarkt-Spieler neu listet (Re-List).

**Features:**

- ✅ **Cross-Platform**: Läuft auf Windows, Linux und macOS
- ✅ **Undetected-ChromeDriver**: Schwer für EA erkennbar als Bot
- ✅ **Menschliches Verhalten**: Zufällige Tippgeschwindigkeit und Verzögerungen
- ✅ **Cookie-Speicherung**: 2FA nur beim ersten Login nötig
- ✅ **Stealth-Optionen**: Deaktiviert Selenium-Indikatoren
- ✅ **Plattform-spezifischer User-Agent**: Automatische Erkennung (Windows/Linux/macOS)
- ✅ **Nachtpause**: Automatische Pause zwischen 1:00 - 6:00 Uhr

### Plattform-Support

- **Windows**: Volle Unterstützung (GUI & Headless)
- **Linux**: Volle Unterstützung (siehe `LINUX_SETUP.md` für Installation)
- **macOS**: Unterstützt (nicht getestet)

### Was bereits enthalten ist

- `ea_fc26_bot.py`: Hauptskript mit Cross-Platform Support
- `config.yaml`: Konfiguration mit Selektoren & Login
- `requirements.txt`: Benötigte Python-Pakete (plattformunabhängig)
- `test_login.py`: Schneller Test nur für Login-Flow
- `test_relist.py`: Test für Re-List Funktion
- `LINUX_SETUP.md`: Detaillierte Linux-Installationsanleitung
- `start_bot.sh`: Linux-Startskript (automatische venv-Aktivierung)

## Was ich von Dir benötige, damit ich das Script vollständig anpassen kann

1. Login-Daten: `username` und `password` für die EA WebApp (bitte nie in Chat posten). Wenn Du mir keine Zugangsdaten geben willst, kannst Du mir stattdessen:
   - Screenshots der Entwickler-Tools (Rechtsklick -> Untersuchen) die die Selektoren für Username/Password/Login-Button zeigen.
   - Alternativ die genauen CSS-Selektoren oder XPaths für die Login-Felder und den Login-Button.

2. Post-Login-Indikator: CSS-Selektor eines Elements, das nur nach erfolgreichem Login sichtbar ist (z.B. Profil-Icon).

3. Transfermarkt-Workflow: Screenshots oder Selektoren für:
   - Suchfeld (player search input)
   - Ergebnisliste / erster Treffer
   - Preis-Eingabefeld
   - Button zum Bestätigen der Listung

4. Falls die WebApp 2FA (z. B. Authenticator, SMS) nutzt: erklären ob Du 2FA temporär deaktivieren kannst oder ob wir einen alternativen Auth-Flow (API-Token) verwenden sollen.

5. Optional: Wenn es eine API gibt:
   - Endpoint-URL(s)
   - Auth-Token oder Auth-Flows (z.B. OAuth)


## Wie Du das Script lokal startest (Windows cmd.exe)

1. Erstelle ein virtuelles Environment und installiere Abhängigkeiten:

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Wichtig**: `undetected-chromedriver` wird automatisch installiert.

2.Konfiguriere die Datei `config_example.yaml` und benenne sie um in `config.yaml`.
3.Passe `players_example.json` an und speichere als `players.json`.
4.Erster Test (nur Login, sichtbar):

```cmd
python test_login.py
```

5. **Vollständiger Start** (stündlicher Scheduler):

```cmd
python list_players.py
```

**Tipp**: Beim ersten Login wird 2FA abgefragt. Danach werden Cookies gespeichert (`ea_cookies.pkl`) und zukünftige Logins überspringen 2FA automatisch.

Hinweis: Wenn Du Headless-Modus deaktivierst (headless: false), kannst Du die Aktionen in einem sichtbaren Browserfenster beobachten.

## Anti-Detection Features

### Was macht das Script "unsichtbar"?

1. **Undetected-ChromeDriver**: Ersetzt Standard-Selenium, entfernt `navigator.webdriver` Flag
2. **Menschliches Tippen**: Jedes Zeichen wird mit zufälliger Verzögerung (50-150ms) getippt
3. **Zufällige Delays**: Wartezeiten zwischen Aktionen variieren (0.3-3 Sekunden)
4. **Cookie-Persistenz**: Nach erstem Login werden Cookies gespeichert. Bei nächstem Start:
   - Cookies werden geladen
   - Seite wird neu geladen
   - Falls noch eingeloggt → kein Login-Flow nötig
   - Spart Zeit und vermeidet wiederholte 2FA

### Cookie-Verwaltung

- Cookies werden im `cookies/` Ordner gespeichert
- **Jeder Account hat eine separate Cookie-Datei**: `cookies/{username}.pkl`
- **Multi-Account-Support**: Mehrere Accounts können gleichzeitig verwaltet werden
- Cookies enthalten Session-Tokens, **nicht** dein Passwort

**Beispiel-Struktur:**
```
webApp/
  cookies/
    moritzs2002@web.de.pkl
    zweiter_account@gmail.com.pkl
```

**Cookie für einen Account zurücksetzen** (erzwingt neuen Login):
```cmd
del cookies\moritzs2002@web.de.pkl
```

**Alle Cookies löschen** (alle Accounts neu einloggen):
```cmd
rmdir /s /q cookies
```

**Wichtig**: Der `cookies/` Ordner ist in `.gitignore` eingetragen und wird nicht in Git committed.

## Nächste Schritte (wenn Du mir die Infos gibst)

- Ich passe `list_players.py` an mit den exakten Selektoren.
- Ich füge Fehlerbehandlung für 2FA und einfache Retry-Strategien hinzu.
- Ich implementiere optionalen API-Modus, falls du Endpunkte lieferst.
