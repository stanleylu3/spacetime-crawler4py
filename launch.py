from configparser import ConfigParser
from argparse import ArgumentParser

from utils.server_registration import get_cache_server
from utils.config import Config
from crawler import Crawler


def main(config_file, restart):
    cparser = ConfigParser()
    cparser.read(config_file)
    config = Config(cparser)
    config.cache_server = get_cache_server(config, restart)
    crawler = Crawler(config, restart)
    crawler.start()

    # Generate report after crawling
    generate_report(config)

def generate_report(config):
    # Number of unique pages
    print(f"Number of unique pages found: {len(config.unique_pages)}")

    # Longest page
    longest_page_url = max(config.page_lengths, key=config.page_lengths.get)
    longest_page_length = config.page_lengths[longest_page_url]
    print(f"Longest page URL: {longest_page_url}, Length: {longest_page_length}")

    # 50 most common words
    common_words = config.word_frequencies.most_common(50)
    print("50 most common words:")
    for word, frequency in common_words:
        print(f"{word}: {frequency}")

    # Subdomains count
    print("Subdomains count:")
    for subdomain, count in sorted(config.subdomains.items()):
        print(f"{subdomain}: {count}")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--restart", action="store_true", default=False)
    parser.add_argument("--config_file", type=str, default="config.ini")
    args = parser.parse_args()
    main(args.config_file, args.restart)

