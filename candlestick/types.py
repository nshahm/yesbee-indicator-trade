from dataclasses import dataclass
from typing import List, Callable

@dataclass
class Candle:
    date: str
    open: float
    high: float
    low: float
    close: float

CandlestickPattern = Callable[[List[Candle]], bool]
