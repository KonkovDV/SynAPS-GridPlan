"""The registry memo lists rules and does not claim compliance."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_registry_memo_does_not_claim_inclusion() -> None:
    text = (ROOT / "docs" / "ru_software_registry.md").read_text(encoding="utf-8")
    assert "соответствие не заявляется" in text
    assert "Номера реестровой записи в репозитории нет" in text
    assert "16.11.2015 № 1236" in text
    assert "23.12.2024 № 1875" in text
    assert "https://reestr.digital.gov.ru/" in text
    assert "две доверенные операционные системы" in text
