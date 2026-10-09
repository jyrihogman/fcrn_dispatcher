from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str
    fcrn_capacity_w: float = Field(gt=0)
    battery_max_power_w: float = Field(gt=0)
    battery_energy_wh: float = Field(gt=0)
    battery_initial_soc: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def max_power_covers_capacity(self) -> Self:
        if self.battery_max_power_w < self.fcrn_capacity_w:
            raise ValueError("BATTERY_MAX_POWER_W must be at least FCRN_CAPACITY_W")
        return self
