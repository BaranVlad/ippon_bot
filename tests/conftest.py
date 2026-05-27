import os

# Ensure a dummy bot token is present so that bot.config can be imported
# in tests without a real secrets file.
os.environ.setdefault("BOT_TOKEN", "fake-test-token")
