import xml.etree.ElementTree as ET
import sys
sys.stdout.reconfigure(encoding='utf-8')

root = ET.parse('tests/fixtures/ff_current_week.xml').getroot()

print('=== FOMC + Crude Oil + Oil ===')
for e in root.findall('event'):
    title = e.findtext('title') or ''
    if 'FOMC' in title or 'Crude' in title or 'Oil' in title:
        date = e.findtext('date') or ''
        time = e.findtext('time') or ''
        country = e.findtext('country') or ''
        impact = e.findtext('impact') or ''
        print(f'{date} {time} | {country} | {impact} | {title}')

print()
print('=== All USD + High ===')
for e in root.findall('event'):
    country = (e.findtext('country') or '').strip()
    impact = (e.findtext('impact') or '').strip()
    if country == 'USD' and impact == 'High':
        date = e.findtext('date') or ''
        time = e.findtext('time') or ''
        title = e.findtext('title') or ''
        print(f'{date} {time} | {country} | {impact} | {title}')

print()
print('=== All ALL + High ===')
for e in root.findall('event'):
    country = (e.findtext('country') or '').strip()
    impact = (e.findtext('impact') or '').strip()
    if country == 'ALL' and impact == 'High':
        date = e.findtext('date') or ''
        time = e.findtext('time') or ''
        title = e.findtext('title') or ''
        print(f'{date} {time} | {country} | {impact} | {title}')