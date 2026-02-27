#!/usr/bin/env python3
"""
LPSE-X: pyproc Local Verification Script
=========================================
Run this from YOUR machine (not cloud/agent) to verify pyproc works.
The agent environment blocks .go.id domains — your local network should be fine.

Usage:
  pip install pyproc
  python test_pyproc_local.py
"""

import sys
import time

def test_pyproc():
    try:
        from pyproc import Lpse
    except ImportError:
        print('[FAIL] pyproc not installed. Run: pip install pyproc')
        return False

    print(f'[OK] pyproc imported successfully')
    print()

    # List of LPSE hosts to test (from eproc.lkpp.go.id)
    hosts = [
        ('Kemenkeu', 'https://lpse.kemenkeu.go.id'),
        ('Kemen PUPR', 'https://lpse.pu.go.id'),
        ('Kemenkes', 'https://lpse.kemenkes.go.id'),
        ('Jakarta', 'https://lpse.jakarta.go.id'),
        ('Jawa Barat', 'https://lpse.jabarprov.go.id'),
        ('Sumatera Barat', 'https://lpse.sumbarprov.go.id'),
    ]

    results = []
    for name, url in hosts:
        print(f'Testing {name} ({url})...', end=' ')
        try:
            lpse = Lpse(url)
            ver = lpse.version
            print(f'[OK] version={ver}')

            # Try fetching 3 tenders
            tenders = lpse.get_paket_tender(start=0, length=3)
            count = len(tenders.get('data', []))
            print(f'  -> Fetched {count} tender records')

            if count > 0:
                first = tenders['data'][0]
                print(f'  -> Sample: {str(first)[:120]}...')

            results.append((name, url, True, count))
            time.sleep(2)  # Rate limiting: 1 req per 2 seconds

        except Exception as e:
            print(f'[FAIL] {str(e)[:80]}')
            results.append((name, url, False, 0))
        print()

    # Summary
    print('=' * 60)
    print('SUMMARY')
    print('=' * 60)
    ok = sum(1 for r in results if r[2])
    print(f'Passed: {ok}/{len(results)}')
    for name, url, success, count in results:
        status = 'OK' if success else 'FAIL'
        print(f'  [{status}] {name}: {url} (records: {count})')

    if ok > 0:
        print()
        print('[CONCLUSION] pyproc WORKS from your machine.')
        print('You can use it as a supplementary data source alongside opentender.net API.')
    else:
        print()
        print('[CONCLUSION] pyproc cannot connect to any LPSE host.')
        print('Possible causes:')
        print('  1. LPSE sites are temporarily down')
        print('  2. Your network blocks .go.id domains')
        print('  3. LPSE sites have changed their URL structure')
        print()
        print('FALLBACK: Use opentender.net API as primary (1.1M tenders, REST API).')
        print('  Test: curl https://opentender.net/api/tender/?page=1')

    return ok > 0


if __name__ == '__main__':
    success = test_pyproc()
    sys.exit(0 if success else 1)