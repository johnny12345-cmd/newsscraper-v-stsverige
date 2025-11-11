#!/usr/bin/env python3
"""
Multi-site nyhetsscraper med e-postsammanfattning
Hämtar artiklar från 29 svenska nyhetssajter
"""

import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import json
import os
import time

# ========== KONFIGURATION ==========
CONFIG_FILE = 'scraper_config.json'

# Standardkonfiguration
DEFAULT_CONFIG = {
    "email": {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "sender_email": "din.email@gmail.com",
        "sender_name": "SVT Nyheter Väst",
        "sender_password": "ditt_app_losenord",
        "recipient_email": "mottagare@example.com"
    },
    "websites": [
        # GP först med 5 artiklar
        {"name": "GP", "url": "https://www.gp.se", "max_items": 5, "type": "gp_style"},
        
        # Sveriges Radio direkt efter GP
        {"name": "SR P4 Göteborg", "url": "https://www.sverigesradio.se/nyheter/p4-goteborg", "max_items": 3, "type": "sverigesradio"},
        {"name": "SR P4 Skaraborg", "url": "https://www.sverigesradio.se/nyheter/p4-skaraborg", "max_items": 3, "type": "sverigesradio"},
        {"name": "SR P4 Sjuhärad", "url": "https://www.sverigesradio.se/nyheter/p4-sjuharad", "max_items": 3, "type": "sverigesradio"},
        {"name": "SR P4 Väst", "url": "https://www.sverigesradio.se/nyheter/p4-vast", "max_items": 3, "type": "sverigesradio"},
        
        # GP-gruppen i bokstavsordning
        {"name": "Alingsås Tidning", "url": "https://www.alingsastidning.se", "max_items": 3, "type": "gp_style"},
        {"name": "Bohusläningen", "url": "https://www.bohuslaningen.se", "max_items": 3, "type": "gp_style"},
        {"name": "Härryda Posten", "url": "https://www.harrydaposten.se", "max_items": 3, "type": "gp_style"},
        {"name": "Kungälvs-Posten", "url": "https://www.kungalvsposten.se", "max_items": 3, "type": "gp_style"},
        {"name": "Lerums Tidning", "url": "https://www.lerumstidning.se", "max_items": 3, "type": "gp_style"},
        {"name": "Mark-Posten", "url": "https://www.markposten.se", "max_items": 3, "type": "gp_style"},
        {"name": "Melleruds Nyheter", "url": "https://www.mellerudsnyheter.se", "max_items": 3, "type": "gp_style"},
        {"name": "Mölndals-Posten", "url": "https://www.molndalsposten.se", "max_items": 3, "type": "gp_style"},
        {"name": "Partille Tidning", "url": "https://www.partilletidning.se", "max_items": 3, "type": "gp_style"},
        {"name": "ST-tidningen", "url": "https://www.sttidningen.se", "max_items": 3, "type": "gp_style"},
        {"name": "Strömstads Tidning", "url": "https://www.stromstadstidning.se", "max_items": 3, "type": "gp_style"},
        {"name": "Ttela", "url": "https://www.ttela.se", "max_items": 3, "type": "gp_style"},
        
        # Övriga tidningar i bokstavsordning
        {"name": "Borås Tidning", "url": "https://www.bt.se/", "max_items": 3, "type": "bt_style"},
        {"name": "Dalslänningen", "url": "https://www.dalslanningen.se/", "max_items": 3, "type": "provins_style"},
        {"name": "Falköpings Tidning", "url": "https://www.falkopingstidning.se/", "max_items": 3, "type": "bt_style"},
        {"name": "Mariestads-Tidningen", "url": "https://www.mariestadstidningen.se/", "max_items": 3, "type": "provins_style"},
        {"name": "NLT", "url": "https://www.nlt.se/", "max_items": 3, "type": "provins_style"},
        {"name": "Provinstidningen Dalsland", "url": "https://www.provinstidningen.se", "max_items": 3, "type": "provins_style"},
        {"name": "Skaraborgs Bygden", "url": "https://www.skaraborgsbygden.se/", "max_items": 3, "type": "provins_style"},
        {"name": "Skaraborgs Läns Tidning", "url": "https://www.skaraborgslanstidning.se/", "max_items": 3, "type": "bt_style"},
        {"name": "Skövde Nyheter", "url": "https://www.skovdenyheter.se/", "max_items": 3, "type": "bt_style"},
        {"name": "SLA", "url": "https://www.sla.se/", "max_items": 3, "type": "provins_style"},
        {"name": "Ulricehamns Tidning", "url": "https://www.ut.se/", "max_items": 3, "type": "bt_style"},
        {"name": "Västgöta-Bladet", "url": "https://www.vastgotabladet.se/", "max_items": 3, "type": "bt_style"}
    ]
}


def load_config():
    """Laddar konfiguration från fil eller skapar standardconfig"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
        print(f"Skapade konfigurationsfil: {CONFIG_FILE}")
        print("Vänligen uppdatera den med dina uppgifter!")
        return DEFAULT_CONFIG


def scrape_gp_style(soup, url, max_items):
    """Scrapar GP-stil sajter (teaser-title/teaser-lead)"""
    articles = []
    article_containers = soup.find_all('article')
    
    for container in article_containers:
        headline_elem = container.select_one('.teaser-title')
        if not headline_elem:
            continue
        
        headline = headline_elem.get_text(strip=True)
        
        # Hitta länk
        link_elem = container.select_one('a[href]')
        link = link_elem.get('href', '') if link_elem else ''
        if link and not link.startswith('http'):
            from urllib.parse import urlparse
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            link = base_url + link
        
        # Hitta ingress
        lead_elem = container.select_one('.teaser-lead')
        lead = lead_elem.get_text(strip=True) if lead_elem else ""
        
        if headline:
            articles.append({
                'headline': headline,
                'lead': lead,
                'link': link
            })
            
            if len(articles) >= max_items:
                break
    
    return articles


def scrape_sverigesradio(soup, url, max_items):
    """Scrapar Sveriges Radio sajter - hittar de översta featured artiklarna först"""
    articles = []
    seen_links = set()
    
    # STEG 1: Hitta alla artikel-länkar på sidan
    all_links = soup.find_all('a', href=True)
    article_links = []
    
    for link in all_links:
        href = link.get('href', '')
        # Filtrera: Bara artikel-länkar
        if '/artikel/' not in href:
            continue
        
        # Bygg fullständig URL
        if not href.startswith('http'):
            href = 'https://www.sverigesradio.se' + href
        
        # Skippa dubbletter
        if href in seen_links:
            continue
        
        # Hitta rubrik för denna länk
        # Försök 1: h3 inuti länken
        headline_elem = link.select_one('h3')
        
        # Försök 2: h3 är parent eller nära länken
        if not headline_elem:
            headline_elem = link.find_parent('h3') or link.find_previous('h3') or link.find_next('h3')
        
        if headline_elem:
            headline = headline_elem.get_text(strip=True)
            
            # Filtrera bort för korta rubriker (navigering etc)
            if len(headline) < 20:
                continue
            
            # Kolla storleken på rubriken för att prioritera
            classes = headline_elem.get('class', [])
            priority = 0
            if 'text-2xl' in classes:
                priority = 3  # Störst
            elif 'text-xl' in classes:
                priority = 2  # Stor
            elif 'text-lg' in classes:
                priority = 1  # Medel
            else:
                priority = 0  # Liten
            
            article_links.append({
                'headline': headline,
                'link': href,
                'priority': priority
            })
            
            seen_links.add(href)
    
    # STEG 2: Sortera efter prioritet (största först)
    article_links.sort(key=lambda x: x['priority'], reverse=True)
    
    # STEG 3: Ta de första X artiklarna
    for article_data in article_links[:max_items]:
        articles.append({
            'headline': article_data['headline'],
            'lead': "",
            'link': article_data['link']
        })
    
    return articles


def scrape_bt_style(soup, url, max_items):
    """Scrapar BT-stil sajter (teaser-j2)"""
    articles = []
    
    # Hitta alla teaser-containers istället för bara headlines
    teasers = soup.select('.teaser-j2')
    
    for teaser in teasers[:max_items * 2]:
        # Hitta headline
        headline_elem = teaser.select_one('.teaser-j2-headline')
        if not headline_elem:
            continue
        
        headline = headline_elem.get_text(strip=True)
        
        # Hitta länk - kan vara på flera ställen
        link = ""
        
        # Försök 1: Leta efter a-tag i teasern
        link_elem = teaser.select_one('a[href]')
        if link_elem:
            link = link_elem.get('href', '')
        
        # Försök 2: Kolla om teasern själv är inuti en a-tag
        if not link:
            parent_link = teaser.find_parent('a')
            if parent_link:
                link = parent_link.get('href', '')
        
        # Bygg fullständig URL om länken är relativ
        if link and not link.startswith('http'):
            from urllib.parse import urlparse
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            if link.startswith('/'):
                link = base_url + link
            else:
                link = base_url + '/' + link
        
        # Försök hitta ingress
        lead = ""
        lead_elem = teaser.select_one('.teaser-j2-text')
        if lead_elem:
            lead = lead_elem.get_text(strip=True)
        
        if headline:
            articles.append({
                'headline': headline,
                'lead': lead,
                'link': link
            })
            
            if len(articles) >= max_items:
                break
    
    return articles


def scrape_provins_style(soup, url, max_items):
    """Scrapar Provins-stil sajter"""
    articles = []
    headlines = soup.find_all('h2', class_=['text-base', 'leading-tight', 'font-semibold'])
    
    for headline_elem in headlines[:max_items * 2]:
        headline_text = headline_elem.get_text(strip=True)
        
        # Ta bort "Nyheter•" prefix om det finns
        if '•' in headline_text:
            headline_text = headline_text.split('•', 1)[-1].strip()
        
        # Skippa för korta rubriker
        if len(headline_text) < 15:
            continue
        
        # Hitta länk (ofta i parent a-tag)
        parent = headline_elem.find_parent('a')
        link = parent.get('href', '') if parent else ''
        
        if link and not link.startswith('http'):
            from urllib.parse import urlparse
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            link = base_url + link
        
        if headline_text:
            articles.append({
                'headline': headline_text,
                'lead': "",
                'link': link
            })
            
            if len(articles) >= max_items:
                break
    
    return articles


def scrape_website(url, site_name, site_type, max_items):
    """Scrapar en nyhetssida baserat på typ"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Välj rätt scraping-metod baserat på typ
        if site_type == 'gp_style':
            articles = scrape_gp_style(soup, url, max_items)
        elif site_type == 'sverigesradio':
            articles = scrape_sverigesradio(soup, url, max_items)
        elif site_type == 'bt_style':
            articles = scrape_bt_style(soup, url, max_items)
        elif site_type == 'provins_style':
            articles = scrape_provins_style(soup, url, max_items)
        else:
            articles = []
        
        return {
            'site_name': site_name,
            'url': url,
            'articles': articles,
            'success': True,
            'error': None
        }
        
    except Exception as e:
        return {
            'site_name': site_name,
            'url': url,
            'articles': [],
            'success': False,
            'error': str(e)
        }


def create_email_body(all_results, timestamp):
    """Skapar e-postmeddelande från alla scrapade sajter"""
    
    # Räkna totalt antal artiklar
    total_articles = sum(len(result['articles']) for result in all_results if result['success'])
    successful_sites = sum(1 for result in all_results if result['success'])
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ 
                font-family: Georgia, 'Times New Roman', serif; 
                line-height: 1.6; 
                color: #333;
                background-color: #f5f5f5;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background-color: white;
            }}
            .header {{ 
                background-color: #003366;
                color: white; 
                padding: 30px 20px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 32px;
                font-weight: normal;
            }}
            .header p {{
                margin: 10px 0 0 0;
                opacity: 0.9;
                font-size: 16px;
            }}
            .meta {{
                color: #666;
                font-size: 14px;
                padding: 15px 20px;
                border-bottom: 2px solid #e0e0e0;
                background-color: #fafafa;
            }}
            .site-section {{
                border-bottom: 2px solid #e0e0e0;
                padding: 15px 20px;
            }}
            .site-header {{
                background-color: #4a4a4a;
                color: white;
                padding: 10px 15px;
                margin: 0 -20px 15px -20px;
                border-left: 5px solid #0066cc;
            }}
            .site-header h2 {{
                margin: 0;
                font-size: 20px;
                color: white;
            }}
            .site-header .site-url {{
                font-size: 12px;
                color: #cccccc;
                margin-top: 3px;
            }}
            .article {{ 
                margin: 0 0 12px 0;
                padding: 10px 12px;
                background-color: #fafafa;
                border-left: 3px solid #ccc;
            }}
            .article:hover {{
                background-color: #f5f5f5;
                border-left-color: #003366;
            }}
            .headline {{ 
                font-size: 17px;
                font-weight: bold;
                color: #003366;
                margin: 0 0 6px 0;
                line-height: 1.3;
            }}
            .headline a {{
                color: #003366;
                text-decoration: none;
            }}
            .headline a:hover {{
                text-decoration: underline;
            }}
            .lead {{
                color: #555;
                font-size: 14px;
                line-height: 1.4;
                margin: 6px 0 0 0;
            }}
            .error-message {{
                color: #d32f2f;
                background-color: #ffebee;
                padding: 10px;
                margin: 10px 0;
                border-left: 3px solid #d32f2f;
                font-size: 14px;
            }}
            .footer {{ 
                padding: 20px;
                color: #666;
                font-size: 12px;
                text-align: center;
                background-color: #f5f5f5;
                border-top: 2px solid #e0e0e0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>💥😊 Morgonens nyheter i Västsverige</h1>
                <p>{datetime.now().strftime('%A %d %B %Y')}</p>
            </div>
            
            <div class="meta">
                <strong>Hämtad:</strong> {timestamp}<br>
                <strong>Källor:</strong> {successful_sites} nyhetssajter<br>
                <strong>Totalt artiklar:</strong> {total_articles} st
            </div>
    """
    
    # Lägg till varje sajt
    for result in all_results:
        # Välj emoji baserat på typ av källa
        if result['site_name'].startswith('SR'):
            emoji = '📻'
        else:
            emoji = '📰'
        
        html += f"""
            <div class="site-section">
                <div class="site-header">
                    <h2>{emoji} {result['site_name']}</h2>
                    <div class="site-url">{result['url']}</div>
                </div>
        """
        
        if result['success']:
            if result['articles']:
                for i, article in enumerate(result['articles'], 1):
                    lead_html = f'<p class="lead">{article["lead"]}</p>' if article['lead'] else ''
                    link_html = f'<a href="{article["link"]}" target="_blank">{article["headline"]}</a>' if article['link'] else article['headline']
                    
                    html += f"""
                <div class="article">
                    <h3 class="headline">{link_html}</h3>
                    {lead_html}
                </div>
                    """
            else:
                html += '<div class="error-message">Inga artiklar hittades på denna sajt.</div>'
        else:
            html += f'<div class="error-message">Kunde inte hämta artiklar: {result["error"]}</div>'
        
        html += """
            </div>
        """
    
    html += """
            <div class="footer">
                <p>Detta är en automatisk sammanställning från 29 svenska nyhetssajter</p>
                <p>Genererad av multi_news_scraper.py</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


def send_email(config, subject, html_body):
    """Skickar e-post med sammanställningen"""
    try:
        email_config = config['email']
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{email_config['sender_name']} <{email_config['sender_email']}>"
        
        # Hantera flera mottagare (kommaseparerade)
        recipients = email_config['recipient_email']
        if isinstance(recipients, str):
            # Om det är en sträng, dela upp på komma
            recipient_list = [r.strip() for r in recipients.split(',')]
        else:
            # Om det redan är en lista
            recipient_list = recipients
        
        msg['To'] = ', '.join(recipient_list)
        
        html_part = MIMEText(html_body, 'html', 'utf-8')
        msg.attach(html_part)
        
        with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
            server.starttls()
            server.login(email_config['sender_email'], email_config['sender_password'])
            server.sendmail(email_config['sender_email'], recipient_list, msg.as_string())
        
        print(f"✓ E-post skickad till {len(recipient_list)} mottagare: {', '.join(recipient_list)}")
        return True
        
    except Exception as e:
        print(f"✗ Fel vid e-postsändning: {str(e)}")
        return False


def main():
    """Huvudfunktion som kör hela processen"""
    print(f"\n{'='*70}")
    print(f"Multi-Site News Scraper startad: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")
    
    # Ladda konfiguration
    config = load_config()
    
    # Scrapa alla sajter
    all_results = []
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for i, site in enumerate(config['websites'], 1):
        print(f"[{i}/{len(config['websites'])}] Scrapar {site['name']}...", end=' ')
        
        result = scrape_website(
            site['url'],
            site['name'],
            site['type'],
            site['max_items']
        )
        
        all_results.append(result)
        
        if result['success']:
            print(f"✓ {len(result['articles'])} artiklar")
        else:
            print(f"✗ Fel: {result['error'][:50]}...")
        
        # Kort paus för att vara artig mot servrarna
        time.sleep(0.5)
    
    # Sammanfattning
    total_articles = sum(len(r['articles']) for r in all_results if r['success'])
    successful = sum(1 for r in all_results if r['success'])
    
    print(f"\n{'='*70}")
    print(f"Sammanfattning:")
    print(f"  Sajter som fungerade: {successful}/{len(config['websites'])}")
    print(f"  Totalt artiklar: {total_articles}")
    print(f"{'='*70}\n")
    
    # Skapa och skicka e-post
    subject = f"Morgonens nyheter i Västsverige - {datetime.now().strftime('%d %B %Y')}"
    html_body = create_email_body(all_results, timestamp)
    
    print("Skickar e-post...")
    send_email(config, subject, html_body)
    
    print(f"\n{'='*70}")
    print("Klart!")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
