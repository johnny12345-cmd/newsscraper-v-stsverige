#!/usr/bin/env python3
"""
Script för att ladda ner regionstyrelsens protokoll från Region Halland 2022-2025
"""

import requests
from bs4 import BeautifulSoup
import os
import re
from datetime import datetime
from pathlib import Path
import time
from urllib.parse import urljoin, urlparse

# Konfiguration
BASE_URL = "https://politik.regionhalland.se"
REGIONSTYRELSEN_URL = f"{BASE_URL}/committees/regionstyrelsen"

# Output directory - använd Windows path om det finns, annars lokal test-mapp
if os.name == 'nt':  # Windows
    OUTPUT_DIR = r"C:\Users\anan17\OneDrive - Sveriges Television\AI\Regionprotokoll\Halland regionstyrelsen 2022-2025"
else:  # Linux/Mac
    OUTPUT_DIR = "/tmp/halland_protokoll"
    print(f"[INFO] Kör på {os.name}, använder test-mapp: {OUTPUT_DIR}")
    print(f"[INFO] På Windows kommer filerna sparas i: C:\\Users\\anan17\\OneDrive - Sveriges Television\\AI\\Regionprotokoll\\Halland regionstyrelsen 2022-2025")

# För att hantera både Windows och Linux/Mac paths
def ensure_dir(directory):
    """Skapar mapp om den inte finns"""
    Path(directory).mkdir(parents=True, exist_ok=True)
    print(f"✓ Mapp säkerställd: {directory}")

def get_soup(url, headers=None):
    """Hämtar och parsar en webbsida"""
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"✗ Fel vid hämtning av {url}: {e}")
        return None

def extract_meeting_year(meeting_url):
    """Extraherar år från mötets URL eller titel"""
    # Försök hitta år i URL (format: mote-2022-08-31)
    match = re.search(r'mote[/-](\d{4})', meeting_url)
    if match:
        return int(match.group(1))
    return None

def find_all_meetings(start_year=2022, end_year=2025):
    """Hittar alla möten för regionstyrelsen inom årsintervallet"""
    print(f"\n{'='*70}")
    print(f"Söker efter regionstyrelsemöten {start_year}-{end_year}...")
    print(f"{'='*70}\n")

    meetings = []

    # Försök olika URL-mönster
    url_patterns = [
        f"{BASE_URL}/committees/regionstyrelsen",
        f"{BASE_URL}/welcome-sv/namnder-styrelser/regionstyrelsen"
    ]

    for pattern_url in url_patterns:
        print(f"Söker på: {pattern_url}")
        soup = get_soup(pattern_url)

        if not soup:
            continue

        # Leta efter länkar till möten
        # MeetingPlus använder ofta länkar med /mote- eller /meeting-
        links = soup.find_all('a', href=True)

        for link in links:
            href = link.get('href', '')

            # Filtrera ut möteslänkar
            if 'mote' in href.lower() or 'meeting' in href.lower():
                full_url = urljoin(BASE_URL, href)

                # Extrahera år
                year = extract_meeting_year(full_url)

                # Filtrera på år
                if year and start_year <= year <= end_year:
                    meeting_title = link.get_text(strip=True)

                    if full_url not in [m['url'] for m in meetings]:
                        meetings.append({
                            'url': full_url,
                            'title': meeting_title or f"Möte {year}",
                            'year': year
                        })
                        print(f"  ✓ Hittade möte: {meeting_title} ({year})")

        # Försök också hitta ett arkiv eller kalenderview
        archive_links = soup.find_all('a', href=re.compile(r'(archive|arkiv|calendar|kalender)', re.I))
        for archive_link in archive_links:
            archive_url = urljoin(BASE_URL, archive_link.get('href', ''))
            print(f"  Kollar arkiv: {archive_url}")
            archive_soup = get_soup(archive_url)

            if archive_soup:
                archive_meetings = archive_soup.find_all('a', href=re.compile(r'mote'))
                for link in archive_meetings:
                    href = link.get('href', '')
                    full_url = urljoin(BASE_URL, href)
                    year = extract_meeting_year(full_url)

                    if year and start_year <= year <= end_year:
                        meeting_title = link.get_text(strip=True)
                        if full_url not in [m['url'] for m in meetings]:
                            meetings.append({
                                'url': full_url,
                                'title': meeting_title or f"Möte {year}",
                                'year': year
                            })
                            print(f"  ✓ Hittade möte i arkiv: {meeting_title} ({year})")

    # Sortera på år och datum
    meetings.sort(key=lambda x: (x['year'], x['url']))

    print(f"\n{'='*70}")
    print(f"Totalt {len(meetings)} möten hittade")
    print(f"{'='*70}\n")

    return meetings

def download_protocols_from_meeting(meeting_url, output_dir):
    """Laddar ner alla protokoll från ett möte"""
    print(f"\nBearbetar: {meeting_url}")

    soup = get_soup(meeting_url)
    if not soup:
        return []

    downloaded = []

    # Leta efter protokoll-länkar
    # Vanliga mönster: .pdf, "protokoll", "protocol"
    protocol_keywords = ['protokoll', 'protocol']

    # Hitta alla PDF-länkar
    pdf_links = soup.find_all('a', href=re.compile(r'\.pdf', re.I))

    for link in pdf_links:
        link_text = link.get_text(strip=True).lower()
        href = link.get('href', '')

        # Kontrollera om det är ett protokoll
        is_protocol = any(keyword in link_text for keyword in protocol_keywords)
        is_protocol = is_protocol or any(keyword in href.lower() for keyword in protocol_keywords)

        if is_protocol:
            pdf_url = urljoin(BASE_URL, href)

            # Extrahera filnamn
            filename = os.path.basename(urlparse(pdf_url).path)

            # Om filnamnet inte är beskrivande, skapa ett bättre namn
            if not filename or len(filename) < 5:
                # Försök extrahera datum från URL eller sidinnehåll
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', meeting_url)
                if date_match:
                    date_str = date_match.group(1)
                    filename = f"Regionstyrelsen_Protokoll_{date_str}.pdf"
                else:
                    filename = f"Regionstyrelsen_Protokoll_{len(downloaded)+1}.pdf"

            # Ladda ner
            output_path = os.path.join(output_dir, filename)

            try:
                print(f"  Laddar ner: {filename}...", end=' ')

                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }

                response = requests.get(pdf_url, headers=headers, timeout=60, stream=True)
                response.raise_for_status()

                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                file_size = os.path.getsize(output_path) / 1024  # KB
                print(f"✓ ({file_size:.1f} KB)")

                downloaded.append({
                    'filename': filename,
                    'url': pdf_url,
                    'size': file_size
                })

                # Paus för att vara artig mot servern
                time.sleep(1)

            except Exception as e:
                print(f"✗ Fel: {e}")

    return downloaded

def main():
    """Huvudfunktion"""
    print(f"\n{'='*70}")
    print("Region Halland Regionstyrelsen - Protokollnedladdare")
    print(f"Startad: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")

    # Skapa output-mapp
    ensure_dir(OUTPUT_DIR)

    # Hitta alla möten
    meetings = find_all_meetings(2022, 2025)

    if not meetings:
        print("\n⚠ Inga möten hittades!")
        print("\nTips för manuell nedladdning:")
        print("1. Besök: https://politik.regionhalland.se/committees/regionstyrelsen")
        print("2. Eller: https://www.regionhalland.se/demokrati-och-politik/moten-och-handlingar/")
        print("3. Sök efter regionstyrelsen och välj år 2022-2025")
        return

    # Ladda ner protokoll från varje möte
    all_downloaded = []

    for i, meeting in enumerate(meetings, 1):
        print(f"\n[{i}/{len(meetings)}] {meeting['title']} ({meeting['year']})")

        downloaded = download_protocols_from_meeting(meeting['url'], OUTPUT_DIR)
        all_downloaded.extend(downloaded)

        # Kort paus mellan möten
        time.sleep(2)

    # Sammanfattning
    print(f"\n{'='*70}")
    print("SAMMANFATTNING")
    print(f"{'='*70}")
    print(f"Möten genomsökta: {len(meetings)}")
    print(f"Protokoll nedladdade: {len(all_downloaded)}")

    if all_downloaded:
        total_size = sum(p['size'] for p in all_downloaded)
        print(f"Total storlek: {total_size:.1f} KB ({total_size/1024:.1f} MB)")
        print(f"\nFiler sparade i: {OUTPUT_DIR}")

        print("\nNedladdade filer:")
        for doc in all_downloaded:
            print(f"  - {doc['filename']} ({doc['size']:.1f} KB)")

    print(f"\n{'='*70}")
    print("Klart!")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()
