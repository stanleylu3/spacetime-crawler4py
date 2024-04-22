import re
import time
from urllib.parse import urlparse, urlunparse, urljoin
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    urls = []
    if is_valid(resp.url):
        if resp.status != 200:
            print(f"error: {resp.error}")
        else:
            content = resp.raw_response.content
            if content:
                soup = BeautifulSoup(content, 'html.parser')
                links = soup.find_all('a')
                for link in links:
                    href = link.get('href')
                    if href and is_valid(href):
                        # remove fragment from URL
                        parsed_url = urlparse(href)
                        cleaned_url = urlunparse(parsed_url._replace(fragment=''))
                        # makes sure the URL is absolute
                        absolute_url = urljoin(resp.url, cleaned_url)
                        #check for permission to crawl
                        if get_permission(absolute_url):
                            #get politeness delay
                            politeness_delay = get_politeness_delay(absolute_url)
                            #respect the politeness delay before moving on to the next url
                            time.sleep(politeness_delay)
                            urls.append(absolute_url)
    return urls

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        #uci websites to be crawled
        allowed_domains = [
            "ics.uci.edu",
            "cs.uci.edu",
            "informatics.uci.edu",
            "stat.uci.edu"
        ]
        parsed = urlparse(url)
        #if the website is not within the allowed domains, return false
        if parsed.netloc.endswith(tuple(allowed_domains)):
            if parsed.scheme not in set(["http", "https"]):
                return False
            return not re.match(
                r".*\.(css|js|bmp|gif|jpe?g|ico"
                + r"|png|tiff?|mid|mp2|mp3|mp4"
                + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
                + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
                + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
                + r"|epub|dll|cnf|tgz|sha1"
                + r"|thmx|mso|arff|rtf|jar|csv"
                + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())
        else:
            return False

    except TypeError:
        print ("TypeError for ", parsed)
        raise

def get_politeness_delay(url):
    #gets politeness delay from website's robots.txt file, if it DNE uses a default value
    #default value
    DEFAULT_CRAWL_DELAY = 0.5
    #get the robots file for the url
    try:
        robots_txt_url = urljoin(url, "/robots.txt")
        robot_parser = RobotFileParser()
        robot_parser.set_url(robots_txt_url)
        #parse the robots file
        robot_parser.read()
        #retrieve the crawl delay for user agent '*'
        crawl_delay = robot_parser.crawl_delay('*')
        if crawl_delay:
            return crawl_delay
        return DEFAULT_CRAWL_DELAY
    except Exception as e:
        print('Error retrieving crawl delay')
        return DEFAULT_CRAWL_DELAY

def get_permission(url):
    #checks robots.txt for permission to crawl
    try:
        robots_txt_url = urljoin(url, "/robots.txt")
        robot_parser = RobotFileParser()
        robot_parser.set_url(robots_txt_url)
        robot_parser.read()
        return robot_parser.can_fetch("*", url)
    except Exception as e:
        print(f"Error checking permission: {e}")
        return False