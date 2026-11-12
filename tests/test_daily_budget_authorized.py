from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.research.config import ResearchSettings, settings


def test_authorized_daily_limit_and_unchanged_defaults(monkeypatch):
    monkeypatch.setenv('RESEARCH_DAILY_USD', '0.20')
    monkeypatch.setenv('RESEARCH_MONTHLY_USD', '10')
    config = settings()
    assert config.daily_usd == Decimal('0.20')
    assert config.monthly_usd == Decimal('10')
    assert str(config.at) == '22:30:00'
    assert ResearchSettings().daily_usd == Decimal('0.15')


@pytest.mark.parametrize('value', ['0.500001', '-0.01', 'NaN', 'Infinity'])
def test_reject_unauthorized_daily_limits(value):
    with pytest.raises(ValidationError):
        ResearchSettings(daily_usd=Decimal(value))
