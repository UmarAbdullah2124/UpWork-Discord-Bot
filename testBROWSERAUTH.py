from BrowserAuth import refresh_auth_tokens

cookies, token, auth_cookie = refresh_auth_tokens()

print("\n--- TOKEN (localStorage) ---")
print(token)

print("\n--- AUTH COOKIE ---")
print(auth_cookie)

print("\n--- TOTAL COOKIES ---")
print(len(cookies))