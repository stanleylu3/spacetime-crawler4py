import re
from urllib.parse import urlparse, urlunparse, urljoin
from bs4 import BeautifulSoup
from collections import Counter
from simhash import Simhash
import nltk
from nltk.corpus import stopwords
from utils import get_logger
nltk.download('punkt')

# Download stopwords (if not already downloaded)
nltk.download('stopwords')

# Get the list of English stopwords
stop_words = set(stopwords.words('english'))

# stores visited URLs and guarantees no duplicates
visited_urls = set()

# data structures to help generate report
page_lengths = {}
word_frequencies = Counter()
subdomains = Counter()
unique_pages = set()

# dict of simhashes of URLs
simhash_dict = {}

logger = get_logger("CRAWLER")

min_word_length = 2

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return list(links)


def extract_next_links(url, resp):
    urls = []
    redirect_count = 0
    global visited_urls
    global simhash_dict
    if is_valid(resp.url):
        if resp.status != 200:
            print(f"error: {resp.error}")
        else:
            content = resp.raw_response.content
            if content:
                soup = BeautifulSoup(content, 'html.parser')
                # Tokenize the text
                words = nltk.word_tokenize(soup.get_text())
                # Filter out stopwords and non-alphabetic words
                words = [word.lower() for word in words if len(word) >= min_word_length and word.isalpha() and word.lower() not in stop_words]
                # Update word frequencies
                word_frequencies.update(words)

                # update page length
                page_lengths[url] = len(words)

                # update unique pages count
                parsed_url = urlparse(url)
                clean_url = urlunparse(parsed_url._replace(fragment=''))
                unique_pages.add(clean_url)

                # update subdomains count
                if parsed_url.netloc.endswith('ics.uci.edu'):
                    subdomain = parsed_url.netloc.split('.ics.uci.edu')[0]
                    subdomains[subdomain] += 1

                # calculates text ratio whether there's a good amount of relevant text info.
                text_ratio = len(soup.get_text(strip=True)) / len(content)

                if text_ratio > 0.1:
                    # Check for redirection
                    if resp.status >= 300 and resp.status < 400:
                        # Handle redirection
                        if 'Location' in resp.headers:
                            redirect_url = resp.headers['Location']
                            redirect_count+=1
                            if redirect_count > 30:
                                print("Exceeded maximum redirects. Skipping:", redirect_url)
                                return urls
                            # Checking for if redirected URL is already in visited URLs
                            if redirect_url in visited_urls:
                                return urls
                            # Add redirected URL to visited_urls
                            visited_urls.add(redirect_url)
                            url = redirect_url
                            redirect_count = 0

                    # Check for dead URLS and large files
                    if len(content) == 0 or len(content) > 5000000:
                        return urls

                links = soup.find_all(['a', 'link'])
                for link in links:
                    if link.name == 'a':
                        href = link.get('href')
                    elif link.name == 'link':
                        href = link.get('href')
                        rel = link.get('rel')
                        if rel and 'stylesheet' not in rel:
                            continue
                    if href:
                        # remove fragment from URL
                        parsed_href = urlparse(href)
                        cleaned_href = urlunparse(parsed_href._replace(fragment=''))
                        # makes sure the URL is absolute
                        absolute_url = urljoin(resp.url, cleaned_href)

                        # Remove query parameters from the URL
                        parsed_absolute_url = urlparse(absolute_url)
                        cleaned_absolute_url = parsed_absolute_url._replace(query='').geturl()
                        if is_valid(cleaned_absolute_url):
                            # checks for near duplicate
                            if is_near_duplicate(absolute_url, simhash_dict):
                                print(f"{absolute_url} is a near duplicate with path {parsed_href}")
                                continue
                            # URL appended after all checks
                            urls.append(cleaned_absolute_url)
    return urls


def is_valid(url):
    try:
        # uci websites to be crawled
        allowed_domains = [
            "ics.uci.edu",
            "cs.uci.edu",
            "informatics.uci.edu",
            "stat.uci.edu"
        ]
        parsed = urlparse(url)
        # if the website is not within the allowed domains, return false
        if parsed.netloc.endswith(tuple(allowed_domains)) and parsed.netloc != 'physics.uci.edu':
            if parsed.scheme not in set(["http", "https"]):
                return False

            # Trap checking for certain words in path and query
            query_bl = {"ical", "rev"}
            if any([(query in parsed.query) for query in query_bl]):
                return False

            path_blacklist = {"/events/", "/day/", "/week/", "/month/", "/list/", "?filter", "img"}
            if any([(path in parsed.path.lower()) for path in path_blacklist]):
                return False

            # Check if URL contains repeated words
            if len(parsed.path.split("/")) != len(set(parsed.path.split("/"))):
                return False

            # Checks if length of link is too long
            if len(url) > 200:
                return False

            # Trap checking for slideshows and datasheets
            if (re.search("[sS]li?de?s?[_-]?\d", url) != None or re.search("sheets?-?\d", url)):
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
        print("TypeError for ", parsed)
        raise


def is_near_duplicate(url, simhash_dict):
    # extract path with given url
    new_path = urlparse(url).path
    # extract query with given url
    new_query = urlparse(url).query
    # create a combined path
    combined_path = f"{new_path}?{new_query}"
    # create new simhash for path
    new_simhash = Simhash(combined_path)
    # adds new path to dictionary
    simhash_dict[combined_path] = new_simhash
    # checks current url simhash with existing simhash
    for existing_path, existing_simhash in simhash_dict.items():
        if combined_path == existing_path:
            continue
        # calculate Hamming distance between simhashes
        distance = new_simhash.distance(existing_simhash)
        # returns True if Hamming distance is 1 or less
        if distance <= 1:
            print(f"near duplicate detected, url: {url}")
            return True
    return False
def generate_report():
    # Number of unique pages
    logger.info("Number of unique pages found: %s", len(unique_pages))

    # Longest page
    if page_lengths:
        longest_page_url = max(page_lengths, key=page_lengths.get)
        longest_page_length = page_lengths[longest_page_url]
        logger.info("Longest page URL: %s, Length: %s", longest_page_url, longest_page_length)
    else:
        logger.info("No pages crawled yet.")

    # 50 most common words
    filtered_word_frequencies = {word: freq for word, freq in word_frequencies.items() if word not in stop_words}
    filtered_word_frequencies_counter = Counter(filtered_word_frequencies)
    common_words = filtered_word_frequencies_counter.most_common(50)
    logger.info("50 most common words:")
    for word, frequency in common_words:
        logger.info("%s: %s", word, frequency)

    # Subdomains count
    logger.info("Subdomains count:")
    for subdomain, count in sorted(subdomains.items()):
        logger.info("%s: %s", subdomain, count)

        # Count unique pages in each subdomain
        subdomain_pages = [page for page in unique_pages if
                           page.startswith("http://" + subdomain) or page.startswith("https://" + subdomain)]
        logger.info("   %s, %s", subdomain, len(subdomain_pages))