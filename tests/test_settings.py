import pytest
from pydantic import ValidationError

from fcrn_dispatcher.settings import Settings

VALID_ENV = {
    "DATABASE_URL": "postgresql://postgres:dev@localhost:5432/postgres",
    "FCRN_CAPACITY_W": "1000000",
    "BATTERY_MAX_POWER_W": "1340000",
    "BATTERY_ENERGY_WH": "2000000",
    "BATTERY_INITIAL_SOC": "0.5",
}


def settings_from(env: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> Settings:
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    return Settings(_env_file=None)


def test_a_valid_env_loads(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = settings_from(VALID_ENV, monkeypatch)

    assert settings.database_url == VALID_ENV["DATABASE_URL"]
    assert settings.fcrn_capacity_w == 1_000_000.0
    assert settings.battery_max_power_w == 1_340_000.0
    assert settings.battery_energy_wh == 2_000_000.0
    assert settings.battery_initial_soc == 0.5


def test_soc_above_one_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValidationError, match="battery_initial_soc"):
        settings_from({**VALID_ENV, "BATTERY_INITIAL_SOC": "1.5"}, monkeypatch)


def test_max_power_below_capacity_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValidationError, match="at least FCRN_CAPACITY_W"):
        settings_from({**VALID_ENV, "BATTERY_MAX_POWER_W": "999999"}, monkeypatch)
