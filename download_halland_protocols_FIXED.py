#!/usr/bin/env python3
"""
Region Halland Regionstyrelsen - Protokollnedladdare (FIXAD VERSION)
Laddar ner protokoll från 2022-2025
"""

import requests
from bs4 import BeautifulSoup
import os
import re
from datetime import datetime
from pathlib import Path
import time
from urllib.parse import urljoin, urlparse, unquote
import json

# Konfiguration
BASE_URL = "https://politik.regionhalland.se"
SITEMAP_URL = f"{BASE_URL}/sitemap.xml"

# Output directory
if os.name == 'nt':  # Windows
    OUTPUT_DIR = r"C:\Users\anan17\OneDrive - Sveriges Television\AI\Regionprotokoll\Halland regionstyrelsen 2022-2025"
else:  # Linux/Mac
    OUTPUT_DIR = "/tmp/halland_protokoll"

def ensure_dir(directory):
    """Skapar mapp om den inte finns"""
    Path(directory).mkdir(parents=True, exist_ok=True)
    return directory

def get_session():
    """Skapar en requests session med headers"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'sv-SE,sv;q=0.9,en;q=0.8',
    })
    return session

def get_meetings_from_sitemap(session, start_year=2022, end_year=2025):
    """Hämtar alla regionstyrelsemöten från sitemap"""
    meetings = []

    try:
        response = session.get(SITEMAP_URL, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'xml')

        # Hitta alla URLs i sitemap
        urls = soup.find_all('loc')

        for url_elem in urls:
            url = url_elem.text.strip()

            # Filtrera: bara regionstyrelsen-möten
            if '/regionstyrelsen/mote-' in url:
                # Extrahera datum från URL
                date_match = re.search(r'mote-(\d{4})-(\d{2})-(\d{2})', url)
                if date_match:
                    year = int(date_match.group(1))

                    if start_year <= year <= end_year:
                        meetings.append({
                            'url': url,
                            'date': f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}",
                            'year': year
                        })

        # Sortera efter datum
        meetings.sort(key=lambda x: x['date'])

        # Gruppera per år
        meetings_by_year = {}
        for m in meetings:
            year = m['year']
            if year not in meetings_by_year:
                meetings_by_year[year] = []
            meetings_by_year[year].append(m)

        return meetings_by_year

    except Exception as e:
        print(f"✗ Kunde inte hämta sitemap: {e}")
        return {}

def find_protocol_pdfs(session, meeting_url):
    """
    Hittar protokoll-PDF:er från en mötessida.
    Protokoll finns ofta under /protocol/ istället för /agenda/
    """
    pdfs_found = []

    # URL-varianter att testa
    base_meeting_url = meeting_url.rstrip('/')
    urls_to_check = [
        base_meeting_url,  # Huvudsidan
        f"{base_meeting_url}/protocol",  # Protocol-sektionen
        f"{base_meeting_url}/agenda"  # Agenda-sektionen
    ]

    for check_url in urls_to_check:
        try:
            response = session.get(check_url, timeout=30)

            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.content, 'html.parser')

            # Hitta alla PDF-länkar
            all_links = soup.find_all('a', href=True)

            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)

                # Måste vara en PDF-fil
                if '.pdf' not in href.lower():
                    continue

                # Kolla om det är ett protokoll
                is_protocol = False

                # Metod 1: Texten innehåller "protokoll"
                if 'protokoll' in text.lower():
                    is_protocol = True

                # Metod 2: URL:en innehåller "protocol" (inte "protokoll-au" etc)
                if '/protocol/' in href.lower():
                    # Men undvik arbetsutskott-protokoll
                    if 'protokoll-au' not in href.lower() and 'au-' not in href.lower():
                        is_protocol = True

                # Metod 3: Filnamnet börjar med "protokoll" eller "rs-protokoll"
                filename = os.path.basename(unquote(href))
                if filename.lower().startswith('protokoll') or filename.lower().startswith('rs-protokoll'):
                    is_protocol = True

                if is_protocol:
                    full_url = urljoin(check_url, href)

                    # Undvik dubbletter
                    if not any(p['url'] == full_url for p in pdfs_found):
                        pdfs_found.append({
                            'url': full_url,
                            'text': text,
                            'filename': filename
                        })

            # Om vi hittade något under /protocol/, fortsätt inte
            if pdfs_found and '/protocol' in check_url:
                break

        except Exception as e:
            continue

    return pdfs_found

def download_pdf(session, pdf_info, output_dir, meeting_date):
    """Laddar ner en PDF-fil"""

    url = pdf_info['url']
    suggested_filename = pdf_info['filename']

    # Förbättra filnamnet
    if not suggested_filename or len(suggested_filename) < 5:
        suggested_filename = f"Regionstyrelsen_Protokoll_{meeting_date}.pdf"
    elif not meeting_date in suggested_filename:
        # Lägg till datum i filnamnet
        name_part = suggested_filename.rsplit('.', 1)[0]
        suggested_filename = f"{name_part}_{meeting_date}.pdf"

    output_path = os.path.join(output_dir, suggested_filename)

    # Undvik att ladda ner samma fil flera gånger
    if os.path.exists(output_path):
        file_size = os.path.getsize(output_path) / 1024
        return {
            'success': True,
            'filename': suggested_filename,
            'size': file_size,
            'already_exists': True
        }

    try:
        response = session.get(url, timeout=60, stream=True)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        file_size = os.path.getsize(output_path) / 1024

        return {
            'success': True,
            'filename': suggested_filename,
            'size': file_size,
            'already_exists': False
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def main():
    """Huvudfunktion"""
    print("="*70)
    print("Region Halland Regionstyrelsen - Protokollnedladdare")
    print("FIXAD VERSION - Söker i /protocol/ sektionen")
    print("="*70)
    print(f"Startad: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Skapa output-mapp
    ensure_dir(OUTPUT_DIR)
    print(f"✓ Mapp: {OUTPUT_DIR}\n")

    # Skapa session
    session = get_session()

    # Hämta möten från sitemap
    print("Hämtar möteslista från sitemap...")
    meetings_by_year = get_meetings_from_sitemap(session, 2022, 2025)

    if not meetings_by_year:
        print("✗ Kunde inte hämta möten från sitemap")
        return

    total_meetings = sum(len(m) for m in meetings_by_year.values())
    print(f"✓ Hittade {total_meetings} möten totalt\n")

    # Statistik
    stats = {
        'downloaded': 0,
        'already_exists': 0,
        'not_found': 0,
        'failed': 0
    }

    downloaded_files = []

    # Bearbeta varje år
    for year in sorted(meetings_by_year.keys()):
        meetings = meetings_by_year[year]

        print(f"\n{'='*70}")
        print(f"ÅR {year} ({len(meetings)} möten)")
        print(f"{'='*70}\n")

        for i, meeting in enumerate(meetings, 1):
            print(f"  Möte {i}/{len(meetings)} ({meeting['date']}):")

            # Leta efter protokoll
            protocol_pdfs = find_protocol_pdfs(session, meeting['url'])

            if not protocol_pdfs:
                print(f"    ⚠ Inget protokoll hittat")
                stats['not_found'] += 1
                time.sleep(0.5)
                continue

            # Ladda ner varje hittad PDF
            for pdf in protocol_pdfs:
                result = download_pdf(session, pdf, OUTPUT_DIR, meeting['date'])

                if result['success']:
                    if result.get('already_exists'):
                        print(f"    ○ {result['filename']} (finns redan, {result['size']:.0f} KB)")
                        stats['already_exists'] += 1
                    else:
                        print(f"    ✓ {result['filename']} ({result['size']:.0f} KB)")
                        stats['downloaded'] += 1
                        downloaded_files.append(result['filename'])
                else:
                    print(f"    ✗ Misslyckades: {result.get('error', 'Okänt fel')}")
                    stats['failed'] += 1

                time.sleep(1)  # Var artig mot servern

    # Sammanfattning
    print(f"\n{'='*70}")
    print("SAMMANFATTNING")
    print(f"{'='*70}")
    print(f"Totalt möten: {total_meetings}")
    print(f"Nedladdade nya filer: {stats['downloaded']}")
    print(f"Fanns redan: {stats['already_exists']}")
    print(f"Protokoll ej funna: {stats['not_found']}")
    print(f"Misslyckade: {stats['failed']}")

    if downloaded_files:
        print(f"\nNya nedladdade filer:")
        for filename in downloaded_files:
            print(f"  • {filename}")

    print(f"\n✓ Filer sparade i: {OUTPUT_DIR}")
    print(f"\n{'='*70}")
    print("KLART!")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()
