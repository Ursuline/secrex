from dataclasses import dataclass, asdict
from typing import List, Optional
#import driver

@dataclass
class StabilityResult:
    end_date: str
    passive_gains: Optional[float] = None
    results_data: Optional[List] = None
    metrics: Optional[dict] = None

    def to_dict(self):
        """Return the dataclass as a dictionary"""
        return asdict(self)