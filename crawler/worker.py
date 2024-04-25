import socket
from threading import Thread

from inspect import getsource
from urllib.error import URLError
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

from utils.download import download
from utils import get_logger
import scraper
import time


class Worker(Thread):
    permissions = {}
    crawl_delays = {}
    retry_attempts = 6
    retry_delay = 10

    def __init__(self, worker_id, config, frontier):
        self.logger = get_logger(f"Worker-{worker_id}", "Worker")
        self.config = config
        self.frontier = frontier
        # basic check for requests in scraper
        assert {getsource(scraper).find(req) for req in
                {"from requests import", "import requests"}} == {
                   -1}, "Do not use requests in scraper.py"
        assert {getsource(scraper).find(req) for req in
                {"from urllib.request import", "import urllib.request"}} == {
                   -1}, "Do not use urllib.request in scraper.py"
        super().__init__(daemon = True)

    def run(self):
        while True:
            tbd_url = self.frontier.get_tbd_url()
            if not tbd_url:
                self.logger.info(f"Number of domains crawled: {len(self.permissions)}")
                self.logger.info("Frontier is empty. Stopping Crawler.")
                break
            domain = self.get_domain(tbd_url)
            politeness_delay = self.get_politeness_delay(domain, tbd_url)
            permission = self.get_permission(domain, tbd_url)
            if permission:
                if politeness_delay:
                    time.sleep(politeness_delay)
                resp = self.download_with_retry(tbd_url)
                if resp:
                    if 600 <= resp.status < 700:
                        self.logger.info(f"Ignoring url {tbd_url}, status: {resp.status}")
                        continue
                    self.logger.info(
                        f"Downloaded {tbd_url}, status <{resp.status}> , "
                        f"using cache {self.config.cache_server}.")
                    scraped_urls = scraper.scraper(tbd_url, resp)
                    for scraped_url in scraped_urls:
                        self.frontier.add_url(scraped_url)
                    self.frontier.mark_url_complete(tbd_url)
                    time.sleep(self.config.time_delay)
                else:
                    self.logger.error(f"Failed to connect {tbd_url}")
            else:
                self.logger.warning(f"Permission denied for {domain}")

    def get_domain(self, url):
        return urlparse(url).netloc

    def get_politeness_delay(self, domain, url):
        if domain in self.crawl_delays:
            return self.crawl_delays[domain]
        else:
            try:
                robots_txt_url = f"{urlparse(url).scheme}://{domain}/robots.txt"
                robots_parser = RobotFileParser()
                robots_parser.set_url(robots_txt_url)
                robots_parser.read()
                crawl_delay = robots_parser.crawl_delay(self.config.user_agent)
                self.crawl_delays[domain] = crawl_delay if crawl_delay else 0
                return self.crawl_delays[domain]
            except Exception as e:
                self.logger.info(f"Error retrieving politeness delay: {e}")
                return 0

    def get_permission(self, domain, url):
        if domain in self.permissions:
            return self.permissions[domain]
        else:
            try:
                robots_txt_url = f"{urlparse(url).scheme}://{domain}/robots.txt"
                robots_parser = RobotFileParser()
                robots_parser.set_url(robots_txt_url)
                robots_parser.read()
                permission = robots_parser.can_fetch(self.config.user_agent, domain)
                self.logger.info(f"{domain} permission: {permission}")
                self.permissions[domain] = permission
                return permission
            except URLError as e:
                self.logger.warning(f"Connection failed {e}")
                return False
            except Exception as e:
                self.logger.info(f"Error retrieving permission: {e}")
                return False

    def download_with_retry(self, url):
        attempts = 0
        while attempts < self.retry_attempts:
            try:
                return download(url, self.config, self.logger)
            except (URLError, socket.timeout, ConnectionError, ConnectionRefusedError, TimeoutError) as e:
                self.logger.warning(f"Download Attempts {attempts + 1} failed: {e}")
                time.sleep(self.retry_delay)
                attempts += 1
        return None