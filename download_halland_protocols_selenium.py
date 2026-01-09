#!/usr/bin/env python3
"""
Script för att ladda ner regionstyrelsens protokoll från Region Halland 2022-2025
Selenium-baserad version som simulerar en riktig webbläsare
"""

import os
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠ Selenium är inte installerat. Installera med: pip install selenium")

# Konfiguration
BASE_URL = "https://www.regionhalland.se/demokrati-och-politik/moten-och-handlingar/"
POLITIK_BASE = "https://politik.regionhalland.se"

# Output directory
if os.name == 'nt':  # Windows
    OUTPUT_DIR = r"C:\Users\anan17\OneDrive - Sveriges Television\AI\Regionprotokoll\Halland regionstyrelsen 2022-2025"
else:  # Linux/Mac
    OUTPUT_DIR = "/tmp/halland_protokoll"

def ensure_dir(directory):
    """Skapar mapp om den inte finns"""
    Path(directory).mkdir(parents=True, exist_ok=True)
    print(f"✓ Mapp säkerställd: {directory}")

def setup_driver():
    """Skapar och konfigurerar en Selenium WebDriver"""
    chrome_options = Options()

    # Headless mode (kör utan att visa webbläsarfönster)
    # Kommentera ut nästa rad om du vill se webbläsaren
    # chrome_options.add_argument('--headless')

    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    # Sätt download-mapp
    prefs = {
        'download.default_directory': OUTPUT_DIR,
        'download.prompt_for_download': False,
        'download.directory_upgrade': True,
        'safebrowsing.enabled': True
    }
    chrome_options.add_experimental_option('prefs', prefs)

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        return driver
    except Exception as e:
        print(f"✗ Kunde inte starta Chrome WebDriver: {e}")
        print("\nTips:")
        print("1. Installera ChromeDriver: https://chromedriver.chromium.org/")
        print("2. Eller använd: pip install webdriver-manager")
        print("3. På Linux: sudo apt-get install chromium-chromedriver")
        return None

def find_and_download_protocols(driver, start_year=2022, end_year=2025):
    """Hittar och laddar ner protokoll från Region Hallands webbplats"""
    downloaded = []

    try:
        print(f"\nBesöker: {BASE_URL}")
        driver.get(BASE_URL)
        time.sleep(3)

        # Försök hitta länk till regionstyrelsen
        print("Letar efter Regionstyrelsen...")

        # Strategi 1: Sök efter text "regionstyrelsen"
        try:
            elements = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'REGIONSTYRELSEN', 'regionstyrelsen'), 'regionstyrelsen')]")

            for element in elements:
                if element.tag_name == 'a':
                    href = element.get_attribute('href')
                    if href:
                        print(f"  Hittat länk: {href}")
                        driver.get(href)
                        time.sleep(2)
                        break
        except Exception as e:
            print(f"  Sökning misslyckades: {e}")

        # Strategi 2: Testa direkt URL till politik.regionhalland.se
        politik_urls = [
            f"{POLITIK_BASE}/committees/regionstyrelsen",
            f"{POLITIK_BASE}/welcome-sv/namnder-styrelser/regionstyrelsen"
        ]

        for url in politik_urls:
            try:
                print(f"\nTestar direktlänk: {url}")
                driver.get(url)
                time.sleep(3)

                # Leta efter möteslänkar
                meeting_links = []

                # Hitta alla länkar som innehåller "mote" eller "meeting"
                all_links = driver.find_elements(By.TAG_NAME, 'a')

                for link in all_links:
                    href = link.get_attribute('href')
                    if href and ('mote' in href.lower() or 'meeting' in href.lower()):
                        # Extrahera år från URL
                        year_match = re.search(r'(\d{4})', href)
                        if year_match:
                            year = int(year_match.group(1))
                            if start_year <= year <= end_year:
                                meeting_links.append(href)

                # Ta bort dubbletter
                meeting_links = list(set(meeting_links))
                print(f"  Hittade {len(meeting_links)} möten")

                # Besök varje möte och leta efter protokoll
                for i, meeting_url in enumerate(meeting_links, 1):
                    print(f"\n  [{i}/{len(meeting_links)}] Besöker möte: {meeting_url}")

                    try:
                        driver.get(meeting_url)
                        time.sleep(2)

                        # Leta efter protokoll-länkar
                        protocol_links = driver.find_elements(
                            By.XPATH,
                            "//a[contains(translate(text(), 'PROTOKOLL', 'protokoll'), 'protokoll') and contains(@href, '.pdf')]"
                        )

                        for protocol_link in protocol_links:
                            pdf_url = protocol_link.get_attribute('href')
                            pdf_text = protocol_link.text

                            print(f"    ✓ Protokoll hittat: {pdf_text}")

                            # Klicka för att ladda ner
                            try:
                                protocol_link.click()
                                time.sleep(2)

                                downloaded.append({
                                    'url': pdf_url,
                                    'text': pdf_text,
                                    'meeting': meeting_url
                                })

                            except Exception as e:
                                print(f"    ✗ Kunde inte klicka på länk: {e}")

                    except Exception as e:
                        print(f"    ✗ Fel vid besök av möte: {e}")

                if meeting_links:
                    break  # Om vi hittat möten, sluta testa andra URLs

            except Exception as e:
                print(f"  ✗ Kunde inte nå {url}: {e}")

    except Exception as e:
        print(f"✗ Ett fel uppstod: {e}")

    return downloaded

def main():
    """Huvudfunktion"""
    if not SELENIUM_AVAILABLE:
        print("\n" + "="*70)
        print("Selenium krävs för att köra detta script!")
        print("="*70)
        print("\nInstallera med:")
        print("  pip install selenium")
        print("\nInstallera även ChromeDriver:")
        print("  - Windows: Ladda ner från https://chromedriver.chromium.org/")
        print("  - Mac: brew install chromedriver")
        print("  - Linux: sudo apt-get install chromium-chromedriver")
        return

    print("\n" + "="*70)
    print("Region Halland Regionstyrelsen - Protokollnedladdare (Selenium)")
    print(f"Startad: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")

    # Skapa output-mapp
    ensure_dir(OUTPUT_DIR)

    # Starta webbläsare
    print("\nStartar Chrome WebDriver...")
    driver = setup_driver()

    if not driver:
        return

    try:
        # Hitta och ladda ner protokoll
        downloaded = find_and_download_protocols(driver, start_year=2022, end_year=2025)

        # Sammanfattning
        print("\n" + "="*70)
        print("SAMMANFATTNING")
        print("="*70)
        print(f"Protokoll nedladdade: {len(downloaded)}")

        if downloaded:
            print(f"\nFiler sparade i: {OUTPUT_DIR}")
            print("\nNedladdade protokoll:")
            for doc in downloaded:
                print(f"  - {doc['text']}")
                print(f"    Från: {doc['meeting']}")
        else:
            print("\n⚠ Inga protokoll kunde laddas ner.")
            print("\nManuell nedladdning rekommenderas:")
            print("1. Besök: https://www.regionhalland.se/demokrati-och-politik/moten-och-handlingar/")
            print("2. Leta efter 'Regionstyrelsen'")
            print("3. Välj år 2022-2025")
            print("4. Ladda ner protokollen manuellt")

    finally:
        print("\nStänger webbläsare...")
        driver.quit()

    print("\n" + "="*70)
    print("Klart!")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
