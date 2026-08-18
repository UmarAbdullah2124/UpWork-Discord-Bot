import time
from seleniumbase import Driver

# ----------------------------
# SESSION EXTRACTION (SELENIUMBASE UC MODE)
# ----------------------------
def refresh_auth_tokens():
    print("Launching selenium-based cloudscraper (SeleniumBase)...")
    
    # Use SeleniumBase with UC mode (Undetected Chromedriver)
    driver = Driver(
        uc=True, 
        headless=False, 
        window_size="1920,1080",
        agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
    )
    
    try:
        # Step 1: Navigate directly to the search page where tokens are generated
        print("Step 1: Navigating directly to search page...")
        # uc_open_with_reconnect helps bypass the initial Cloudflare wall
        driver.uc_open_with_reconnect("https://www.upwork.com/nx/search/jobs/", 20)
        
        print("Solving Cloudflare challenge if present...")
        driver.uc_gui_handle_captcha()
        
        print("Finalizing session and waiting for tokens (30 seconds)...")
        # Giving time for the page to fully load and cookies/localStorage to settle
        time.sleep(30)
        
        cookies = driver.get_cookies()
        
        # Discover all available localStorage keys to find the correct token
        ls_keys = driver.execute_script("return Object.keys(localStorage);")
        print(f"Found LocalStorage keys: {ls_keys}")
        
        # Priority 1: Check localStorage for common token keys
        token = driver.execute_script("""
            return localStorage.getItem('oauth2_access_token') ||
                   localStorage.getItem('oauth2_global_js_token') ||
                   localStorage.getItem('visitor_id');
        """)
        
        # Priority 2: Look for the specific 'UniversalSearchNuxt_vt' cookie 
        # (This matches the Bearer token in your main.py)
        auth_cookie = None
        for c in cookies:
            if c["name"] == "UniversalSearchNuxt_vt":
                auth_cookie = c
                break
        
        # Fallback for Visitor Sessions: If localStorage is empty, use the Nuxt_vt cookie
        if not token and auth_cookie:
            print(f"LocalStorage token empty. Using cookie '{auth_cookie['name']}' as Bearer token.")
            token = auth_cookie['value']
                
        return cookies, token, auth_cookie

    finally:
        driver.quit()
        print("Extraction complete (Browser closed).")

if __name__ == "__main__":
    # Test block
    c, t, a = refresh_auth_tokens()
    print(f"Token found: {t}")
