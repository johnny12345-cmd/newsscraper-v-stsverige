#!/usr/bin/env python3
"""
Script för att ladda ner regionstyrelsens protokoll från Region Halland 2022-2025
Förbättrad version med flera strategier för att hantera webbplatsens säkerhet
"""

import requests
from bs4 import BeautifulSoup
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
import time
from urllib.parse import urljoin, urlparse
import json

# Konfiguration
BASE_URL = "https://politik.regionhalland.se"

# Output directory - använd Windows path om det finns, annars lokal test-mapp
if os.name == 'nt':  # Windows
    OUTPUT_DIR = r"C:\Users\anan17\OneDrive - Sveriges Television\AI\Regionprotokoll\Halland regionstyrelsen 2022-2025"
else:  # Linux/Mac
    OUTPUT_DIR = "/tmp/halland_protokoll"
    print(f"[INFO] Kör på {os.name}, använder test-mapp: {OUTPUT_DIR}")
    print(f"[INFO] På Windows kommer filerna sparas i: C:\\Users\\anan17\\OneDrive - Sveriges Television\\AI\\Regionprotokoll\\Halland regionstyrelsen 2022-2025\n")

def ensure_dir(directory):
    """Skapar mapp om den inte finns"""
    Path(directory).mkdir(parents=True, exist_ok=True)
    return directory

def get_session():
    """Skapar en requests session med realistiska headers"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'sv-SE,sv;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    })
    return session

def generate_meeting_dates(start_year=2022, end_year=2025):
    """
    Genererar troliga mötesdatum för regionstyrelsen.
    Regionstyrelsen brukar sammanträda ca 10-12 gånger per år.
    Vanliga dagar: Onsdagar, Torsdagar
    """
    possible_dates = []

    for year in range(start_year, end_year + 1):
        # Vanliga månader för möten (brukar vara varje månad utom juli)
        for month in [1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12]:
            # Testa sista onsdagen och torsdagen i månaden
            for day in range(20, 32):
                try:
                    date = datetime(year, month, day)
                    # 2 = Onsdag, 3 = Torsdag i weekday()
                    if date.weekday() in [2, 3]:
                        possible_dates.append(date.strftime('%Y-%m-%d'))
                except ValueError:
                    continue

    return possible_dates

def try_download_protocol_from_url(session, url, output_dir):
    """Försöker ladda ner protokoll från en specifik URL"""
    try:
        response = session.get(url, timeout=30, allow_redirects=True)

        # Om vi får 403, testa med fler headers
        if response.status_code == 403:
            session.headers.update({
                'Referer': 'https://www.regionhalland.se/',
                'Origin': 'https://www.regionhalland.se'
            })
            time.sleep(2)
            response = session.get(url, timeout=30, allow_redirects=True)

        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.content, 'html.parser')

        # Leta efter protokoll-PDF:er
        pdf_links = []

        # Strategi 1: Hitta alla länkar med "protokoll" i texten eller href
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()

            # Kolla om det är ett protokoll
            if 'protokoll' in text or 'protokoll' in href.lower():
                if href.endswith('.pdf') or '.pdf' in href:
                    full_url = urljoin(url, href)
                    pdf_links.append({
                        'url': full_url,
                        'text': link.get_text(strip=True)
                    })

        # Ladda ner hittade protokoll
        downloaded = []
        for pdf_link in pdf_links:
            filename = os.path.basename(urlparse(pdf_link['url']).path)

            # Förbättra filnamn
            if not filename or len(filename) < 5:
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', url)
                if date_match:
                    filename = f"Regionstyrelsen_Protokoll_{date_match.group(1)}.pdf"
                else:
                    filename = f"Regionstyrelsen_Protokoll_{int(time.time())}.pdf"

            output_path = os.path.join(output_dir, filename)

            # Undvik dubbletter
            if os.path.exists(output_path):
                continue

            try:
                pdf_response = session.get(pdf_link['url'], timeout=60, stream=True)
                pdf_response.raise_for_status()

                with open(output_path, 'wb') as f:
                    for chunk in pdf_response.iter_content(chunk_size=8192):
                        f.write(chunk)

                file_size = os.path.getsize(output_path) / 1024
                downloaded.append({
                    'filename': filename,
                    'size': file_size,
                    'url': pdf_link['url']
                })

                print(f"  ✓ {filename} ({file_size:.1f} KB)")
                time.sleep(1)

            except Exception as e:
                print(f"  ✗ Kunde inte ladda ner {filename}: {e}")

        return downloaded

    except Exception as e:
        return None

def strategy_1_try_direct_urls(session, output_dir, start_year=2022, end_year=2025):
    """
    Strategi 1: Försök konstruera direkta URLs till möten baserat på datum
    """
    print(f"\n{'='*70}")
    print("STRATEGI 1: Försöker konstruera direkta möteslänkar")
    print(f"{'='*70}\n")

    possible_dates = generate_meeting_dates(start_year, end_year)
    all_downloaded = []
    successful_urls = []

    # URL-mönster att testa
    url_patterns = [
        f"{BASE_URL}/committees/regionstyrelsen/mote-{{date}}",
        f"{BASE_URL}/welcome-sv/namnder-styrelser/regionstyrelsen/mote-{{date}}"
    ]

    print(f"Testar {len(possible_dates)} möjliga mötesdatum...")
    print("(Detta kan ta en stund...)\n")

    for i, date in enumerate(possible_dates):
        if i % 20 == 0 and i > 0:
            print(f"  [{i}/{len(possible_dates)}] fortsätter...")

        for pattern in url_patterns:
            url = pattern.format(date=date)

            downloaded = try_download_protocol_from_url(session, url, output_dir)

            if downloaded:
                print(f"\n✓ Möte hittat: {date}")
                all_downloaded.extend(downloaded)
                successful_urls.append(url)
                break  # Gå till nästa datum om vi hittat ett möte

        time.sleep(0.5)  # Var artig mot servern

    return all_downloaded, successful_urls

def strategy_2_manual_urls():
    """
    Strategi 2: Ange manuella URLs om automatisk sökning misslyckades
    """
    print(f"\n{'='*70}")
    print("STRATEGI 2: Manuell inmatning av möteslänkar")
    print(f"{'='*70}\n")
    print("Besök https://www.regionhalland.se/demokrati-och-politik/moten-och-handlingar/")
    print("och leta reda på regionstyrelsens möten.\n")
    print("Ange URL:er till möten (en per rad, tom rad för att avsluta):")

    urls = []
    while True:
        url = input("> ").strip()
        if not url:
            break
        urls.append(url)

    return urls

def main():
    """Huvudfunktion"""
    print(f"\n{'='*70}")
    print("Region Halland Regionstyrelsen - Protokollnedladdare v2")
    print(f"Startad: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")

    # Skapa output-mapp
    ensure_dir(OUTPUT_DIR)
    print(f"✓ Mapp säkerställd: {OUTPUT_DIR}\n")

    # Skapa session
    session = get_session()

    # Testa först om vi kan nå webbplatsen
    print("Testar anslutning till politik.regionhalland.se...", end=' ')
    try:
        test_response = session.get(f"{BASE_URL}", timeout=10)
        if test_response.status_code == 200:
            print("✓ OK")
        else:
            print(f"⚠ Status: {test_response.status_code}")
    except Exception as e:
        print(f"✗ Fel: {e}")
        print("\nWebbplatsen verkar blockera automatiska förfrågningar.")
        print("Det finns några alternativ:\n")
        print("1. Kör detta script på en Windows-dator med vanlig webbläsare")
        print("2. Använd VPN eller annat nätverk")
        print("3. Använd verktyget Selenium för att simulera en riktig webbläsare")
        print("\nFör manuell nedladdning:")
        print("- Besök: https://www.regionhalland.se/demokrati-och-politik/moten-och-handlingar/")
        print("- Sök efter 'Regionstyrelsen'")
        print("- Välj år 2022-2025 och ladda ner protokollen manuellt")
        return

    # Kör strategi 1
    all_downloaded, successful_urls = strategy_1_try_direct_urls(
        session,
        OUTPUT_DIR,
        start_year=2022,
        end_year=2025
    )

    # Sammanfattning
    print(f"\n{'='*70}")
    print("SAMMANFATTNING")
    print(f"{'='*70}")
    print(f"Protokoll nedladdade: {len(all_downloaded)}")

    if all_downloaded:
        total_size = sum(p['size'] for p in all_downloaded)
        print(f"Total storlek: {total_size:.1f} KB ({total_size/1024:.1f} MB)")
        print(f"\nFiler sparade i: {OUTPUT_DIR}")
        print("\nNedladdade filer:")
        for doc in all_downloaded:
            print(f"  - {doc['filename']} ({doc['size']:.1f} KB)")
    else:
        print("\n⚠ Inga protokoll kunde laddas ner automatiskt.")
        print("\nTips:")
        print("1. Webbplatsen kanske kräver inloggning eller cookies från en riktig webbläsare")
        print("2. Testa att köra scriptet från en annan dator/nätverk")
        print("3. Använd Selenium-baserad lösning (se download_halland_protocols_selenium.py)")
        print("\nFör manuell nedladdning, besök:")
        print("https://www.regionhalland.se/demokrati-och-politik/moten-och-handlingar/")

    print(f"\n{'='*70}")
    print("Klart!")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()
