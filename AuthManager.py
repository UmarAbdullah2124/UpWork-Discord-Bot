import json
import time
import os
import logging
from seleniumbase import Driver

logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self, session_file="session_data.json"):
        self.session_file = session_file
        self.refresh_interval = 2 * 3600 # 2 Hours for Guest mode

    def should_refresh(self):
        if not os.path.exists(self.session_file): return True
        # Refresh if file is older than interval or if manually triggered
        return (time.time() - os.path.getmtime(self.session_file)) > self.refresh_interval

    def refresh_tokens(self):
        logger.info("🛡️ [Phase 5] Bypassing Cloudflare via SeleniumBase...")
        # uc=True enables Undetected Chromedriver
        # headless=True is cleaner, but if 403s persist, set to False once
        driver = Driver(uc=True, headless=True) 
        try:
            # 1. Open Upwork Search to trigger Cloudflare challenge
            driver.uc_open_with_reconnect("https://www.upwork.com/nx/search/jobs/", 20)
            
            # 2. Wait for the bypass to complete (15s is usually safe)
            time.sleep(15)
            
            # 3. Capture the REAL User-Agent the browser is using
            user_agent = driver.execute_script("return navigator.userAgent")
            cookies = driver.get_cookies()
            
            # 4. Try to grab the Auth Token from local storage or cookies
            token = driver.execute_script("return localStorage.getItem('oauth2_global_token')")
            if not token:
                for c in cookies:
                    if c["name"] == "UniversalSearchNuxt_vt":
                        token = c["value"]
                        break
            
            if cookies:
                logger.info(f"✅ Session Captured. UA: {user_agent[:50]}...")
                data = {
                    "token": token or "", 
                    "cookies": cookies, 
                    "user_agent": user_agent, # Saved for the Scraper
                    "timestamp": time.time()
                }
                with open(self.session_file, 'w') as f:
                    json.dump(data, f)
                return True
            
            logger.error("❌ Failed to capture cookies.")
            return False
        except Exception as e:
            logger.error(f"❌ Selenium Error: {e}")
            return False
        finally:
            driver.quit()

    def get_session(self):
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, 'r') as f: return json.load(f)
            except: return None
        return None
