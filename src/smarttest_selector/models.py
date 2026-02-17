from dataclasses import dataclass, field
from typing import List


@dataclass
class TestCase:
    id: str
    title: str
    description: str = ""
    module: str = ""
    tags: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)

    def searchable_text(self) -> str:
        parts = [
            self.id,
            self.title,
            self.description,
            self.module,
            " ".join(self.tags),
            " ".join(self.steps),
        ]
        return " ".join(p for p in parts if p).lower()
