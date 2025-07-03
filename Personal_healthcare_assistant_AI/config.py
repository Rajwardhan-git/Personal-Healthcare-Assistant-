import secrets

SECRET_KEY = secrets.token_hex(16)
print(f"Generated SECRET_KEY: {SECRET_KEY}")