from bot.models import Training, Debtor, PollRecord, PaymentConfig, PaymentMethod


def test_training_defaults():
    t = Training(
        day_of_week=4,
        time="18:00",
        location="БНТУ",
        poll_create_days_before=2,
        reminder_days_before=1,
    )
    assert t.enabled is True


def test_training_full():
    t = Training(
        day_of_week=6,
        time="10:00",
        location="РГУОР",
        poll_create_days_before=2,
        reminder_days_before=1,
        enabled=False,
    )
    assert t.enabled is False
    assert t.day_of_week == 6


def test_debtor_creation():
    d = Debtor(name="Иван", balance=-1500.0)
    assert d.name == "Иван"
    assert d.balance == -1500.0


def test_poll_record_defaults():
    p = PollRecord(
        poll_id="abc123",
        message_id=42,
        date="01.01",
        time="18:00",
        location="БНТУ",
    )
    assert p.status == "active"
    assert p.thread_id is None


def test_payment_config_defaults():
    c = PaymentConfig()
    assert c.methods == []
    assert c.contact_name == "капитан"
    assert c.contact_user_id is None


def test_payment_method_creation():
    m = PaymentMethod(name="Сбер", details="+7 900 000 00 00")
    assert m.name == "Сбер"
    assert m.details == "+7 900 000 00 00"
