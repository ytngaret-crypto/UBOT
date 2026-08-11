import os

required = ["API_ID", "API_HASH", "SESSION_STRING", "OWNER_ID"]
missing = [x for x in required if not os.getenv(x)]
if missing:
    print("Missing:", ", ".join(missing))
else:
    print("Required environment variables are present.")
