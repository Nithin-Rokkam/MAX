# max_core/executor/browser_control.py
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
import time
import logging
from typing import Optional, List

LOG = logging.getLogger("browser_control")

class PlaywrightController:
    """
    Attach to a running Chrome (CDP) and perform DOM actions: search and click N-th result.
    Use connect_over_cdp to attach to http://127.0.0.1:9222

    Usage:
      ctrl = PlaywrightController(cdp_endpoint="http://127.0.0.1:9222")
      ok = ctrl.attach()
      ctrl.search_and_open(engine="google", query="geeksforgeeks", index=1, new_tab=False)
      ctrl.close()  # when done
    """

    def __init__(self, cdp_endpoint: str = "http://127.0.0.1:9222", timeout_ms: int = 8000):
        self.cdp_endpoint = cdp_endpoint
        self.timeout_ms = timeout_ms
        self._pw = None
        self._browser = None
        self._attached = False

    def attach(self) -> bool:
        try:
            self._pw = sync_playwright().start()
            # Connect to existing Chrome over CDP
            self._browser = self._pw.chromium.connect_over_cdp(self.cdp_endpoint, timeout=self.timeout_ms)
            self._attached = True
            return True
        except Exception as e:
            LOG.exception("Playwright attach failed: %s", e)
            self._attached = False
            # Ensure cleanup
            try:
                if self._pw:
                    self._pw.stop()
            except Exception:
                pass
            return False

    def close(self):
        try:
            if self._browser:
                try:
                    self._browser.close()
                except Exception:
                    pass
            if self._pw:
                try:
                    self._pw.stop()
                except Exception:
                    pass
        finally:
            self._pw = None
            self._browser = None
            self._attached = False

    def _get_pages(self) -> List:
        """
        Return a flat list of pages from all contexts.
        """
        pages = []
        if not self._attached or not self._browser:
            return pages
        try:
            for ctx in self._browser.contexts:
                try:
                    pages.extend(list(ctx.pages))
                except Exception:
                    continue
        except Exception:
            # older versions: browser.contexts might be callable
            try:
                for ctx in self._browser.contexts():
                    pages.extend(list(ctx.pages()))
            except Exception:
                pass
        return pages

    def _choose_page(self, prefer_contains: Optional[str] = None):
        """
        Try to choose a sensible page:
         - If prefer_contains is given, prefer a page whose URL or title contains that string.
         - Otherwise return the active/first page.
        """
        pages = self._get_pages()
        if not pages:
            return None
        if prefer_contains:
            pref = prefer_contains.lower()
            for p in pages:
                try:
                    u = (p.url or "").lower()
                    t = (p.title() or "").lower()
                except Exception:
                    u = ""
                    t = ""
                if pref in u or pref in t:
                    return p
        # fallback: return the first page
        return pages[0]

    def _ensure_page(self, prefer_contains: Optional[str] = None, new_tab: bool = False):
        """
        Return a page object to operate on. If new_tab True, create a new page in the first context.
        """
        if not self._attached or not self._browser:
            return None

        pages = self._get_pages()
        if new_tab:
            # create a new page in the first available context (or a new context)
            try:
                ctx = None
                # Handle both property and method access for contexts
                try:
                    contexts = self._browser.contexts
                    if hasattr(contexts, '__call__'):
                        contexts = contexts()
                    if contexts:
                        ctx = contexts[0]
                    else:
                        ctx = self._browser.new_context()
                except Exception:
                    ctx = self._browser.new_context()
                page = ctx.new_page()
                return page
            except Exception as e:
                LOG.warning(f"Failed to create new page: {e}")
                pass

        page = self._choose_page(prefer_contains=prefer_contains)
        return page

    def search_and_open(self, engine: Optional[str], query: str, index: int = 1, new_tab: bool = False) -> dict:
        """
        High-level function:
         - engine: "youtube" or "google" or None (None => google)
         - query: search query text
         - index: 1-based index of result to click
         - new_tab: whether to open in a new tab (creates a new page)
        Returns dict with keys 'done' and 'message'
        """
        if not self._attached:
            return {"done": False, "message": "Playwright not attached."}

        engine = (engine or "google").lower()
        try:
            # Choose a page to operate on
            prefer = None
            if engine == "youtube":
                prefer = "youtube"
            elif engine == "google":
                prefer = "google"
            page = self._ensure_page(prefer_contains=prefer, new_tab=new_tab)
            if page is None:
                return {"done": False, "message": "No browser page available to control."}

            if engine == "youtube":
                return self._search_and_open_youtube(page, query, index)
            else:
                return self._search_and_open_google(page, query, index)
        except Exception as e:
            LOG.exception("search_and_open failed: %s", e)
            return {"done": False, "message": f"Playwright search_and_open failed: {e}"}

    def _search_and_open_youtube(self, page, query: str, index: int):
        try:
            # If page is not yet navigated to Youtube, navigate there first
            if "youtube.com" not in (page.url or ""):
                page.goto(f"https://www.youtube.com/results?search_query={query}", timeout=self.timeout_ms)
            else:
                # use youtube search box
                try:
                    # focus and search using DOM if possible
                    page.fill('input#search', query)
                    page.keyboard.press("Enter")
                except Exception:
                    page.goto(f"https://www.youtube.com/results?search_query={query}", timeout=self.timeout_ms)

            # Wait for video links to appear
            # video title links use 'a#video-title' in many layouts
            page.wait_for_selector("a#video-title, ytd-video-renderer a#video-title", timeout=self.timeout_ms)
            # Collect candidates
            anchors = page.query_selector_all("a#video-title, ytd-video-renderer a#video-title")
            if not anchors:
                # fallback: look for links with /watch
                anchors = [a for a in page.query_selector_all("a[href]") if "/watch?" in (a.get_attribute("href") or "")]
            if not anchors:
                return {"done": False, "message": "Couldn't find video anchors on YouTube results."}

            idx = max(1, index) - 1
            if idx >= len(anchors):
                return {"done": False, "message": f"There are only {len(anchors)} videos; can't open item #{index}."}

            anchors[idx].click()
            return {"done": True, "message": f"Opened YouTube video #{index}."}
        except PWTimeoutError:
            return {"done": False, "message": "Timed out waiting for YouTube results."}
        except Exception as e:
            LOG.exception("YouTube open failed: %s", e)
            return {"done": False, "message": f"YouTube open failed: {e}"}

    def _search_and_open_google(self, page, query: str, index: int):
        try:
            # If current page is not google, navigate to google search url
            if "google.com" not in (page.url or ""):
                page.goto(f"https://www.google.com/search?q={query}", timeout=self.timeout_ms)
            else:
                # update address bar
                try:
                    page.fill('input[name="q"]', query)
                    page.keyboard.press("Enter")
                except Exception:
                    page.goto(f"https://www.google.com/search?q={query}", timeout=self.timeout_ms)

            # Wait for results
            page.wait_for_selector("div#search a", timeout=self.timeout_ms)

            # Prefer modern container 'div.yuRUbf a' then 'div.g a'
            anchors = page.query_selector_all("div.yuRUbf a[href]")
            if not anchors:
                anchors = page.query_selector_all("div.g a[href]")
            if not anchors:
                # fallback to any external anchors in search container
                anchors = [a for a in page.query_selector_all("div#search a[href]") if a.get_attribute("href") and a.get_attribute("href").startswith("http")]

            if not anchors:
                return {"done": False, "message": "Couldn't find any search result links on the page."}

            idx = max(1, index) - 1
            if idx >= len(anchors):
                return {"done": False, "message": f"There are only {len(anchors)} links; can't open item #{index}."}

            anchors[idx].click()
            return {"done": True, "message": f"Opened search result #{index}."}
        except PWTimeoutError:
            return {"done": False, "message": "Timed out waiting for Google results."}
        except Exception as e:
            LOG.exception("Google open failed: %s", e)
            return {"done": False, "message": f"Google open failed: {e}"}
