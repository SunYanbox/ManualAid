from collections import defaultdict
from statistics import mean


class ToolResultCollection:
    def __init__(self):
        self.consumes: dict[str, list[float]] = defaultdict(list)
        self.results: dict[str, list[tuple[dict, str]]] = defaultdict(list)

    def add(self, name: str, seconds: float, kwargs: dict, result: str):
        if name not in self.consumes:
            self.consumes[name] = []
        if name not in self.results:
            self.results[name] = []
        self.consumes[name].append(seconds)
        self.results[name].append((kwargs, result))

    def get_avg_consume(self, name: str) -> float:
        records = self.consumes.get(name, [])
        return mean(records) if records else 0.0

    def tools(self) -> list[str]:
        return list(self.consumes.keys())
