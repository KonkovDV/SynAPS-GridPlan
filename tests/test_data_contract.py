"""The table-exchange notes stay a dictionary, not a second standard."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_table_exchange_does_not_invent_a_profile_or_stock() -> None:
    text = (ROOT / "docs" / "data-contract-v2.md").read_text(encoding="utf-8")
    section = text.split("## Табличный обмен", 1)
    assert len(section) == 2
    body = section[1]
    assert "Конкретный профиль CIM" in body
    assert "Чтеца CSV и XLSX в пакете нет" in body
    assert "pool_size" in body
    assert "не склад" in body
    assert "Пустое пересечение не круглосуточно" in body
    for field in (
        "Asset.voltage_level",
        "Asset.parent_asset_id",
        "Asset.coordinates",
        "Asset.failure_modes",
        "SparePart.warehouse_location",
        "SparePart.lead_time_min",
    ):
        assert field in body
