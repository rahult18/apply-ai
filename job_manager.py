from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class Event:
    timestamp: datetime
    data: str

class EventStore:
    def __init__(self):
        self._events: Dict[str, List[Event]] = {}
    
    def add_event(self, run_id: str, data: str):
        if run_id not in self._events:
            self._events[run_id] = []
        
        self._events[run_id].append(Event(
            timestamp=datetime.now(),
            data=data
        ))
    
    def get_events(self, run_id: str) -> List[Event]:
        return self._events.get(run_id, [])