from pathlib import Path

import toml
from pydantic import BaseModel, Field

DEPLOYFILE_PATH = Path("Deployfile.toml")


class DeployTarget(BaseModel):
    name: str
    python_version: str = Field(default="3.10")
    glibc_version: str = Field(default="2.36")
    arch: str = Field(default="x64")
    user: str
    host: str
    port: int = Field(default=22)

    @classmethod
    def from_dict(cls, data: dict) -> "DeployTarget":
        return cls(**data.get("target", {}))

    def to_dict(self) -> dict:
        return {"target": self.model_dump()}


def read_deployfile(path: Path = DEPLOYFILE_PATH) -> DeployTarget:
    if not path.exists():
        msg = f"Deployfile not found at {path}"
        raise FileNotFoundError(msg)
    data = toml.load(path)
    return DeployTarget.from_dict(data)


def write_deployfile(target: DeployTarget, path: Path = DEPLOYFILE_PATH) -> None:
    data = target.to_dict()
    with open(path, "w") as f:
        toml.dump(data, f)
