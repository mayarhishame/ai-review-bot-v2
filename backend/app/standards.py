import yaml
from pydantic import BaseModel, ValidationError
from .errors import StandardsError


class Rule(BaseModel):
    id: str
    description: str
    severity: str = "warning"


class Standards(BaseModel):
    global_rules: list[Rule] = []
    languages: dict[str, list[Rule]] = {}
    ignore_paths: list[str] = []

    def rules_for(self, language: str) -> list[Rule]:
        return self.global_rules + self.languages.get(language, [])

    def is_ignored(self, path: str) -> bool:
        return any(p in path for p in self.ignore_paths)


def parse_standards(text: str) -> Standards:
    try:
        return Standards(**(yaml.safe_load(text) or {}))
    except (yaml.YAMLError, ValidationError, TypeError) as e:
        raise StandardsError(f"Invalid standards file: {e}") from e


def load_standards(path: str) -> Standards:
    try:
        with open(path, encoding="utf-8") as f:
            return parse_standards(f.read())
    except FileNotFoundError:
        return Standards()  # graceful default: review with no custom rules