with open("scripts/smoke_test.py", "r") as f:
    lines = f.readlines()

with open("scripts/smoke_test.py", "w") as f:
    for line in lines:
        if '"app_env": settings.app_env,' in line:
            continue
        if '"runtime_mode": "DEVELOPMENT" if settings.is_development else "PRODUCTION",' in line:
            continue
        if '"telegram_token_source": settings.telegram_token_source,' in line:
            continue
        f.write(line)
