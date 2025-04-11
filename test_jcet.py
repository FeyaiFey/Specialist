from modules.crawler.jcetCrawler_t import JcetCrawler

if __name__ == "__main__":
    jcet_crawler = JcetCrawler()
    jcet_crawler.login()
    jcet_crawler.get_wip_data()


