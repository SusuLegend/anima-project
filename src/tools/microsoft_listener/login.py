# login.py
from msal import PublicClientApplication, SerializableTokenCache
import json
import os
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), '.env')
print("Loading .env from:", env_path)
load_dotenv(dotenv_path=env_path)

# ----------------- Azure App Credentials -----------------
AZURE_CLIENT_ID = os.environ.get("AZURE_APP_CLIENT_ID")
TENANT = "consumers"
SCOPES = ["User.Read","Mail.Read", "Calendars.Read", "Tasks.Read"]


def login():
    # Use a persistent token cache file for MSAL
    cache_path = os.path.join(os.path.dirname(__file__), "msal_token_cache.bin")
    token_cache = SerializableTokenCache()
    if os.path.exists(cache_path):
        token_cache.deserialize(open(cache_path, "r").read())
    app_msal = PublicClientApplication(
        AZURE_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT}",
        token_cache=token_cache
    )

    accounts = app_msal.get_accounts()
    if accounts:
        result = app_msal.acquire_token_silent(SCOPES, account=accounts[0])
    else:
        flow = app_msal.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            raise Exception("Failed to create device flow")
        # Output device code and message for app integration
        print("DEVICE_CODE:", flow["user_code"])
        print("AUTH_URL:", flow["verification_uri"])
        print("MESSAGE:", flow["message"])
        # Optionally, you can return these values from a function for API integration
        result = app_msal.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        raise Exception("Could not obtain access token")

    # Save token to file for later use
    with open("token.json", "w") as f:
        json.dump(result, f)
    # Save MSAL token cache for refresh
    with open(cache_path, "w") as f:
        f.write(token_cache.serialize())

    return result["access_token"]

if __name__ == "__main__":
    token = login()
    print("Login successful! Access token obtained.")
