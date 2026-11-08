"""Regression coverage for sandbox merchant initialization."""
import json
import sqlite3

from app.merchant import identity, merchant, setup


def configure_merchants(monkeypatch, domains):
    for index in range(1, 4):
        monkeypatch.setenv(f'SHOPSIDE_MERCHANT_{index}_DOMAIN', domains[index - 1])
        monkeypatch.setenv(f'SHOPSIDE_MERCHANT_{index}_TOKEN', f'sandbox-token-{index}-long-enough-for-tests')


def assert_three_tenants(db, domains):
    rows = db.execute('SELECT id FROM merchants ORDER BY id').fetchall()
    assert [row[0] for row in rows] == [f'sandbox-merchant-{index}' for index in range(1, 4)]
    for index, domain in enumerate(domains, 1):
        merchant_id = f'sandbox-merchant-{index}'
        data = merchant(db, merchant_id)
        assert data['verified_domain'] == domain.lower()
        assert data['sandbox'] is True
        assert data['opt_in'] is False
        assert data['active'] is False
        assert data['policy']['max_discount_bps'] == 0
        token_hash = identity(f'sandbox-token-{index}-long-enough-for-tests')
        assert db.execute('SELECT merchant_id FROM merchant_users WHERE token_hash=?', (token_hash,)).fetchone()[0] == merchant_id


def test_first_startup_with_domains_configured(monkeypatch):
    domains = ['First.Example', 'Second.Example', 'Third.Example']
    configure_merchants(monkeypatch, domains)
    with sqlite3.connect(':memory:') as db:
        setup(db)
        assert_three_tenants(db, domains)


def test_restart_with_existing_merchant_records(monkeypatch):
    domains = ['first.example', 'second.example', 'third.example']
    configure_merchants(monkeypatch, domains)
    with sqlite3.connect(':memory:') as db:
        setup(db)
        existing = merchant(db, 'sandbox-merchant-2')
        existing['opt_in'] = True
        existing['policy']['max_discount_bps'] = 500
        db.execute('UPDATE merchants SET state=? WHERE id=?', (json.dumps(existing), existing['id']))
        db.commit()
        setup(db)
        assert db.execute('SELECT COUNT(*) FROM merchants').fetchone()[0] == 3
        assert merchant(db, 'sandbox-merchant-2')['opt_in'] is True
        assert merchant(db, 'sandbox-merchant-2')['policy']['max_discount_bps'] == 500
        for index, domain in enumerate(domains, 1):
            assert merchant(db, f'sandbox-merchant-{index}')['verified_domain'] == domain
            token_hash = identity(f'sandbox-token-{index}-long-enough-for-tests')
            assert db.execute('SELECT merchant_id FROM merchant_users WHERE token_hash=?', (token_hash,)).fetchone()[0] == f'sandbox-merchant-{index}'


def test_startup_with_empty_domains(monkeypatch):
    domains = ['', '', '']
    configure_merchants(monkeypatch, domains)
    with sqlite3.connect(':memory:') as db:
        setup(db)
        assert_three_tenants(db, domains)
