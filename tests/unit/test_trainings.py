from datetime import date, timedelta

from bot.data_loaders.trainings import get_next_training_date, generate_upcoming_trainings, load_trainings


def test_get_next_training_date_same_week():
    # 2024-01-01 is Monday, next Friday is 2024-01-05
    monday = date(2024, 1, 1)
    result = get_next_training_date(4, monday)
    assert result == date(2024, 1, 5)


def test_get_next_training_date_next_week():
    # 2024-01-06 is Saturday, next Friday is 2024-01-12
    saturday = date(2024, 1, 6)
    result = get_next_training_date(4, saturday)
    assert result == date(2024, 1, 12)


def test_load_trainings_returns_list():
    trainings = load_trainings()
    assert isinstance(trainings, list)
    for t in trainings:
        assert t.enabled is True


def test_generate_upcoming_trainings_sorted():
    today = date(2024, 1, 1)
    trainings = generate_upcoming_trainings(days=14, from_date=today)
    assert len(trainings) > 0
    dates = [t["date"] for t in trainings]
    assert dates == sorted(dates)
