from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime
import json

@dataclass
class BugReport:
    """Structured bug report"""
    title: str
    description: str
    steps_to_reproduce: List[str]
    expected_behavior: str
    actual_behavior: str
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    environment: Dict[str, str] = field(default_factory=dict)
    affected_version: Optional[str] = None
    severity: str = "medium"  # low, medium, high, critical
    reporter: Optional[str] = None
    reported_date: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        # Handle datetime conversion
        if 'reported_date' in data and data['reported_date']:
            if isinstance(data['reported_date'], str):
                data['reported_date'] = datetime.fromisoformat(data['reported_date'])
        
        return cls(**data)

    @classmethod
    def from_json_file(cls, filepath: str):
        """Load from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result