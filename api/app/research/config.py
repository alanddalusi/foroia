import os
from datetime import datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

MADRID = ZoneInfo('Europe/Madrid')


class ResearchSettings(BaseModel):
    model_config = ConfigDict(frozen=True, hide_input_in_errors=True)
    api_key: SecretStr = SecretStr('')
    model: Literal['gpt-5-mini', 'gpt-5.4-mini', 'gpt-5.4-nano'] = 'gpt-5-mini'
    at: time = time(22, 30)
    monthly_usd: Decimal = Field(default=Decimal('5'), ge=0, le=15)
    daily_usd: Decimal = Field(default=Decimal('0.15'), ge=0, le=Decimal('0.50'))
    input_per_million: Decimal = Field(default=Decimal('0.25'), gt=0)
    output_per_million: Decimal = Field(default=Decimal('2'), gt=0)
    auto_publish: bool = True
    two_lanes: bool = False  # staged rollout; never enables itself on deployment
    practical_publications: int = Field(default=1, ge=1, le=2)
    max_corrections: int = Field(default=1, ge=0, le=1)
    max_output_tokens: int = Field(default=6000, ge=1000, le=10000)

    @field_validator('monthly_usd', 'daily_usd', 'input_per_million', 'output_per_million')
    @classmethod
    def finite(cls, value):
        if not value.is_finite():
            raise ValueError('Tarifa no finita')
        return value

    @model_validator(mode='after')
    def tariff_floor(self):
        floors = {'gpt-5-mini': ('0.25', '2'), 'gpt-5.4-mini': ('0.75', '4.5'), 'gpt-5.4-nano': ('0.2', '1.25')}
        incoming, outgoing = map(Decimal, floors[self.model])
        if self.input_per_million < incoming or self.output_per_million < outgoing:
            raise ValueError('Las tarifas configuradas infravaloran este modelo')
        return self


def settings():
    return ResearchSettings(
        api_key=os.environ.get('OPENAI_API_KEY', ''), model=os.environ.get('RESEARCH_MODEL', 'gpt-5-mini'),
        at=os.environ.get('RESEARCH_AT', '22:30'),
        monthly_usd=os.environ.get('RESEARCH_MONTHLY_USD', '5'), daily_usd=os.environ.get('RESEARCH_DAILY_USD', '0.15'),
        input_per_million=os.environ.get('RESEARCH_INPUT_USD_PER_MILLION', '0.25'),
        output_per_million=os.environ.get('RESEARCH_OUTPUT_USD_PER_MILLION', '2'),
        auto_publish=os.environ.get('RESEARCH_AUTO_PUBLISH', 'true').lower() == 'true',
        two_lanes=os.environ.get('RESEARCH_TWO_LANES', 'false').lower() == 'true',
        practical_publications=os.environ.get('RESEARCH_PRACTICAL_PUBLICATIONS', '1'))


def due(now: datetime, config: ResearchSettings):
    local = now.astimezone(MADRID)
    return local.date() if local.time() >= config.at else None
