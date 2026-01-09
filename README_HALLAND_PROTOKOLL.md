# Region Halland - Protokollnedladdare

Automatiserad nedladdning av regionstyrelsens protokoll från Region Halland (2022-2025).

## 📋 Översikt

Detta projekt innehåller tre olika versioner av scripts för att ladda ner protokoll från Region Hallands regionstyrelse:

1. **download_halland_protocols.py** - Grundläggande version
2. **download_halland_protocols_v2.py** - Förbättrad version med flera strategier
3. **download_halland_protocols_selenium.py** - Webbläsarautomation med Selenium

## 🎯 Målmapp

Protokollen laddas ner till:
```
C:\Users\anan17\OneDrive - Sveriges Television\AI\Regionprotokoll\Halland regionstyrelsen 2022-2025
```

På Linux/Mac används `/tmp/halland_protokoll` för testning.

## 📦 Installation

### Grundläggande beroenden

```bash
pip install requests beautifulsoup4
```

### För Selenium-versionen (rekommenderat)

```bash
pip install selenium
```

**ChromeDriver krävs också:**

- **Windows**: Ladda ner från [ChromeDriver](https://chromedriver.chromium.org/)
- **Mac**: `brew install chromedriver`
- **Linux**: `sudo apt-get install chromium-chromedriver`

## 🚀 Användning

### Alternativ 1: Grundläggande version

```bash
python download_halland_protocols.py
```

Försöker automatiskt hitta och ladda ner protokoll.

### Alternativ 2: Förbättrad version (Rekommenderad)

```bash
python download_halland_protocols_v2.py
```

Denna version:
- Testar flera URL-mönster
- Genererar troliga mötesdatum
- Har bättre felhantering
- Ger tydliga instruktioner vid problem

### Alternativ 3: Selenium-version (Mest robust)

```bash
python download_halland_protocols_selenium.py
```

Denna version:
- Simulerar en riktig webbläsare
- Kan hantera JavaScript
- Bäst för webbplatser med säkerhetsfunktioner
- Kräver ChromeDriver installation

## 🌐 Webbplatsinformation

Region Halland använder ett MeetingPlus-system för sina protokoll:

- **Huvudsida**: https://www.regionhalland.se/demokrati-och-politik/moten-och-handlingar/
- **Politik-portal**: https://politik.regionhalland.se/committees/regionstyrelsen

## 🔧 Felsökning

### Problem: 403 Forbidden

Webbplatsen blockerar automatiska requests. Lösningar:

1. **Använd Selenium-versionen** - Simulerar en riktig webbläsare
2. **Ändra nätverk** - Testa från ett annat nätverk eller med VPN
3. **Manuell nedladdning** - Se instruktioner nedan

### Problem: ChromeDriver fungerar inte

```bash
# Kontrollera Chrome-version
google-chrome --version

# Installera matchande ChromeDriver
# Alternativt, använd webdriver-manager:
pip install webdriver-manager
```

Uppdatera sedan selenium-scriptet för att använda webdriver-manager:

```python
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
```

### Problem: Inga protokoll hittas

Webbplatsen kan ha ändrat struktur. Prova:

1. Besök webbplatsen manuellt
2. Kontrollera URL-strukturen för möten
3. Uppdatera URL-mönstren i scriptet

## 📝 Manuell nedladdning

Om automatisk nedladdning inte fungerar:

1. **Gå till**: https://www.regionhalland.se/demokrati-och-politik/moten-och-handlingar/

2. **Leta efter "Regionstyrelsen"** i listan över nämnder och styrelser

3. **Välj år**: Filtrera på 2022, 2023, 2024, och 2025

4. **För varje möte**:
   - Klicka på mötet
   - Leta efter "Protokoll"
   - Ladda ner PDF:en
   - Spara i målmappen

## 📊 Förväntade resultat

Regionstyrelsen sammanträder vanligtvis:
- **Frekvens**: 10-12 gånger per år
- **Dagar**: Oftast onsdagar eller torsdagar
- **Undantag**: Sällan i juli

För perioden 2022-2025 bör det finnas:
- **2022**: ~10-12 protokoll
- **2023**: ~10-12 protokoll
- **2024**: ~10-12 protokoll
- **2025**: Beroende på när scriptet körs

**Totalt**: Ca 40-50 protokoll

## 🛠️ Teknisk information

### URL-mönster

Scripten försöker följande URL-mönster:

```
https://politik.regionhalland.se/committees/regionstyrelsen
https://politik.regionhalland.se/committees/regionstyrelsen/mote-YYYY-MM-DD
https://politik.regionhalland.se/welcome-sv/namnder-styrelser/regionstyrelsen
https://politik.regionhalland.se/welcome-sv/namnder-styrelser/regionstyrelsen/mote-YYYY-MM-DD
```

### Headers

För att undvika blockering använder scripten:

```python
{
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9...',
    'Accept-Language': 'sv-SE,sv;q=0.9,en;q=0.8',
    'Referer': 'https://www.regionhalland.se/'
}
```

## 📄 Filformat

Nedladdade filer namnges enligt mönster:
```
Regionstyrelsen_Protokoll_2022-08-31.pdf
Regionstyrelsen_Protokoll_2023-02-22.pdf
...
```

## ⚠️ Viktig information

- **Respektera webbplatsen**: Scripten använder pauser mellan requests
- **Cookies och sessions**: Vissa protokoll kan kräva cookies från webbläsaren
- **Autentisering**: Om protokoll är skyddade kan inloggning krävas
- **GDPR**: Protokoll är offentliga handlingar enligt offentlighetsprincipen

## 🔗 Relaterade länkar

- [Region Halland - Demokrati och politik](https://www.regionhalland.se/demokrati-och-politik/)
- [MeetingPlus - Politik](https://politik.regionhalland.se/)
- [Offentlighetsprincipen](https://www.riksdagen.se/sv/sa-funkar-riksdagen/demokrati/offentlighetsprincipen/)

## 📞 Support

Vid problem:

1. **Kontrollera webbplatsen** - Bekräfta att protokollen finns tillgängliga
2. **Testa manuellt** - Kan du ladda ner via webbläsaren?
3. **Kontakta Region Halland** - För frågor om tillgänglighet

## 📜 Licens

Detta script är skapat för Sveriges Television för journalistiskt bruk.

---

**Skapad**: 2026-01-09
**Syfet**: Automatisera nedladdning av offentliga protokoll för journalistisk granskning
