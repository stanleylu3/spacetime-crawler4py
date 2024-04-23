import re
from urllib.parse import urlparse, urlunparse, urljoin
from bs4 import BeautifulSoup


# stores visited URLs and gurantees no duplicates
visited_urls = set()

# data structures to help generate report
page_lengths ={}

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
    global visited_urls
    if is_valid(resp.url):
        if resp.status != 200:
            print(f"error: {resp.error}")
        else:
            content = resp.raw_response.content
            if content:
                soup = BeautifulSoup(content, 'html.parser')

                # calculates text ratio whether there's a good amount of relevant text info.
                text_ratio = len(soup.get_text(strip=True)) / len(content)

                if text_ratio > 0.1:
                    # Check for redirection
                    if resp.url != url:
                        visited_urls.add(resp.url)
                    # Checking for infinite traps
                    if url in visited_urls:
                        return urls
                    visited_urls.add(url)
                    # Check for dead URLS
                    if len(content) == 0:
                        return urls
                    # Check for large files
                    if len(content) > 1000000:
                        return urls
                links = soup.find_all('a')
                for link in links:
                    href = link.get('href')
                    if href and is_valid(href):
                        # remove fragment from URL
                        parsed_url = urlparse(href)
                        cleaned_url = urlunparse(parsed_url._replace(fragment=''))
                        # makes sure the URL is absolute
                        absolute_url = urljoin(resp.url, cleaned_url)
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