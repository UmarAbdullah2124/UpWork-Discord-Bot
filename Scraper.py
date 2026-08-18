import requests
import time
import logging
from AuthManager import AuthManager

logger = logging.getLogger("Scraper")


class UpworkScraper:

    def __init__(self):

        self.auth = AuthManager()
        self.session = requests.Session()

        self.bearer_token = None
        self.cookies = {}
        self.user_agent = None

    def ensure_auth(self, force=False):

        if (
            force
            or self.auth.should_refresh()
            or not self.cookies
            or not self.user_agent
        ):

            if not self.auth.refresh_tokens():
                logger.error("❌ AuthManager failed to refresh session.")
                return False

            data = self.auth.get_session()

            if not data:
                return False

            self.bearer_token = data.get('token')

            self.cookies = {
                c['name']: c['value']
                for c in data['cookies']
            }

            self.user_agent = data.get('user_agent')

            self.session.headers.update({
                'user-agent': self.user_agent,
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9',
                'x-upwork-accept-language': 'en-US',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'origin': 'https://www.upwork.com'
            })

        return True

    def _safe_post(self, url, headers, json_payload, max_retries=3):

        for attempt in range(max_retries):

            try:

                if not self.ensure_auth():
                    return None

                current_headers = headers.copy()

                if self.bearer_token:
                    current_headers['authorization'] = f'Bearer {self.bearer_token}'

                current_headers['user-agent'] = self.user_agent

                r = self.session.post(
                    url,
                    headers=current_headers,
                    cookies=self.cookies,
                    json=json_payload,
                    timeout=15
                )

                if r.status_code == 403:

                    logger.warning(
                        "🚫 403 Forbidden: Cloudflare mismatch. Refreshing session..."
                    )

                    if self.ensure_auth(force=True):
                        continue

                    return None

                if r.status_code != 200:
                    logger.error(f"⚠️ API Error {r.status_code}: {r.text[:200]}")

                r.raise_for_status()

                return r.json()

            except Exception as e:

                logger.error(
                    f"🌐 Network Error (Attempt {attempt+1}): {str(e)}"
                )

                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return None

    def fetch_search(self, query, offset=0):

        url = "https://www.upwork.com/api/graphql/v1?alias=visitorJobSearch"

        headers = {
            'content-type': 'application/json',
            'referer': 'https://www.upwork.com/nx/search/jobs/',
        }

        payload = {
            "query": """
            query VisitorJobSearch($requestVariables: VisitorJobSearchV1Request!) {

              search {

                universalSearchNuxt {

                  visitorJobSearchV1(request: $requestVariables) {

                    paging {
                      total
                      offset
                      count
                    }

                    results {

                      id
                      title
                      description

                      ontologySkills {
                        uid
                        prefLabel
                      }

                      jobTile {

                        job {

                          id
                          ciphertext: cipherText

                          jobType
                          contractorTier
                          weeklyRetainerBudget
                          hourlyBudgetMax
                          hourlyBudgetMin
                          hourlyEngagementType
                          sourcingTimestamp
                          createTime
                          publishTime

                          hourlyEngagementDuration {
                            label
                            weeks
                          }

                          fixedPriceAmount {
                            isoCurrencyCode
                            amount
                          }

                          fixedPriceEngagementDuration {
                            label
                            weeks
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
            """,

            "variables": {
                "requestVariables": {
                    "userQuery": query,
                    "sort": "recency+desc",
                    "highlight": True,
                    "paging": {
                        "offset": offset,
                        "count": 50
                    }
                }
            }
        }

        data = self._safe_post(url, headers, payload)

        if not data:
            return []

        return (
            (data.get('data') or {})
            .get('search', {})
            .get('universalSearchNuxt', {})
            .get('visitorJobSearchV1', {})
            .get('results', [])
        )

    def fetch_details(self, ciphertext):

        url = "https://www.upwork.com/api/graphql/v1"

        headers = {
            'content-type': 'application/json',
            'referer': f'https://www.upwork.com/jobs/{ciphertext}',
        }

        payload = {
            "query": """
            query JobPubDetailsQuery($id: ID!) {

              jobPubDetails(id: $id) {

                opening {
                  description

                  clientActivity {
                    totalApplicants
                  }
                }

                buyer {

                  location {
                    country
                  }

                  stats {

                    totalCharges {
                      amount
                    }

                    totalJobsWithHires
                  }
                }
              }
            }
            """,

            "variables": {
                "id": ciphertext
            }
        }

        data = self._safe_post(url, headers, payload)

        if not data:
            return {}

        pub = (data.get('data') or {}).get('jobPubDetails') or {}

        opening = pub.get('opening') or {}

        buyer = pub.get('buyer') or {}

        stats = buyer.get('stats') or {}

        return {
            "description": opening.get('description'),

            "client": {
                "location": buyer.get('location', {}),
                "totalSpent": (
                    (stats.get('totalCharges') or {}).get('amount', 0)
                )
            },

            "stats": {
                "proposals": (
                    opening.get('clientActivity', {}).get(
                        'totalApplicants',
                        'N/A'
                    )
                )
            }
        }