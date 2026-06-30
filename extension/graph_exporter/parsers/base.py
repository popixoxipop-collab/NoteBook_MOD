from abc import ABC, abstractmethod
from pathlib import Path
from ..common import DependencyGraph


class BaseParser(ABC):
    EXTENSIONS: tuple[str, ...]

    def can_parse(self, path: Path) -> bool:
        return path.suffix in self.EXTENSIONS

    @abstractmethod
    def parse(self, path: Path) -> DependencyGraph:
        ...
