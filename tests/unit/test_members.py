from bot.data_loaders import members as members_loader
from bot.data_loaders.members import get_member_name_by_id, is_member


def test_get_member_name_by_id_found(monkeypatch):
    monkeypatch.setattr(members_loader, "_members_cache", {"Иван": 123456789})
    assert get_member_name_by_id(123456789) == "Иван"


def test_get_member_name_by_id_not_found(monkeypatch):
    monkeypatch.setattr(members_loader, "_members_cache", {"Иван": 123456789})
    assert get_member_name_by_id(999) is None


def test_is_member_with_empty_cache(monkeypatch):
    """When no members.json exists, everyone is allowed."""
    monkeypatch.setattr(members_loader, "_members_cache", {})
    assert is_member(999) is True
