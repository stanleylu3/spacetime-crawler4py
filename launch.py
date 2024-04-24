from configparser import ConfigParser
from argparse import ArgumentParser

from utils.server_registration import get_cache_server
from utils.config import Config
from crawler import Crawler
from scraper import unique_pages, page_lengths, word_frequencies, subdomains


def main(config_file, restart):
    cparser = ConfigParser()
    cparser.read(config_file)
    config = Config(cparser)
    config.cache_server = get_cache_server(config, restart)
    crawler = Crawler(config, restart)
    crawler.start()

    # Generate report after crawling
    generate_report(unique_pages, page_lengths, word_frequencies, subdomains)


def generate_report(unique_pages, page_lengths, word_frequencies, subdomains):
    # if not unique_pages:
    #     print("No pages were crawled.")
    #     return

    # Number of unique pages
    print(f"Number of unique pages found: {len(unique_pages)}")

    # Longest page
    longest_page_url = max(page_lengths, key=page_lengths.get)
    longest_page_length = page_lengths[longest_page_url]
    print(f"Longest page URL: {longest_page_url}, Length: {longest_page_length}")

    # 50 most common words
    common_words = word_frequencies.most_common(50)
    print("50 most common words:")
    for word, frequency in common_words:
        print(f"{word}: {frequency}")

    # Subdomains count
    print("Subdomains count:")
    for subdomain, count in sorted(subdomains.items()):
        print(f"{subdomain}: {count}")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--restart", action="store_true", default=False)
    parser.add_argument("--config_file", type=str, default="config.ini")
    args = parser.parse_args()
    main(args.config_file, args.restart)
