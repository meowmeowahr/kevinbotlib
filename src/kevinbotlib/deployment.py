import datetime
import json
import os.path
import pathlib
from dataclasses import dataclass
from typing import TypedDict


class GitManifestData(TypedDict):
    branch: str | None
    tag: str | None
    commit: str | None

@dataclass
class Manifest:
    deploytool: str
    timestamp: datetime.datetime
    git: GitManifestData
    robot: str

class ManifestParser:
    def __init__(self, path: pathlib.Path | str | None = None):
        if not path:
            path = pathlib.Path(os.path.join(os.getcwd(), "deploy", "manifest.json"))
        else:
            path = pathlib.Path(path)
        self._path = path
        self._manifest: Manifest | None = None

        # attempt to load
        with open(path, "r") as f:
            data = f.read()
        self._manifest = Manifest(**json.loads(data))

    @property
    def path(self):
        return self._path

    @property
    def manifest(self):
        return self._manifest
