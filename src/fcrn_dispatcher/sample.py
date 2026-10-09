from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Sample:
    at: datetime
    frequency_hz: float
    commanded_w: float
    actual_w: float
    soc: float
