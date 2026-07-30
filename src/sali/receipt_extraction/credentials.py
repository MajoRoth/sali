"""Credential loading for the hosted receipt extractor."""

from __future__ import annotations

import os
from collections.abc import MutableMapping
from pathlib import Path

if __package__:
    from .configuration import ENV_FILE
    from .errors import HostedReceiptError
else:
    from configuration import ENV_FILE
    from errors import HostedReceiptError


class ApiKeyProvider:
    """Load the OpenAI API key from the process or a private env file."""

    def __init__(
        self,
        env_file: Path = ENV_FILE,
        environment: MutableMapping[str, str] | None = None,
    ) -> None:
        self._env_file = env_file
        self._environment = environment if environment is not None else os.environ

    def load(self) -> str:
        configured = self._environment.get("OPENAI_API_KEY", "").strip()
        if configured:
            return configured

        try:
            lines = self._env_file.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError as exc:
            raise HostedReceiptError("OPENAI_API_KEY is not configured") from exc
        except OSError as exc:
            raise HostedReceiptError("OPENAI_API_KEY could not be loaded") from exc

        for line in lines:
            api_key = self._parse_api_key(line)
            if api_key is None:
                continue
            if api_key:
                self._environment["OPENAI_API_KEY"] = api_key
                return api_key
            break

        raise HostedReceiptError("OPENAI_API_KEY is not configured")

    @staticmethod
    def _parse_api_key(line: str) -> str | None:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            return None

        name, value = stripped.split("=", 1)
        if name.strip() != "OPENAI_API_KEY":
            return None

        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            return value[1:-1]
        return value
