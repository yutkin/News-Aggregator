import logging
import datetime
from parsers import Gazeta, Tass, Lenta, Vedomosti, Novaya

def main():
    logging.basicConfig(level=logging.DEBUG,
                        format='[PID %(process)d %(asctime)s] %(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S')
    logging.getLogger('requests').setLevel(logging.CRITICAL)

    parsers_ = [
        Gazeta(threads=4),
        Tass(threads=32),
        Lenta(threads=32),
        Vedomosti(threads=32),
        Novaya(threads=4)
    ]

    news_list = []

    for parser in parsers_:
        print(parser.id)
        news_list += parser.get_news(news_count=1,
            until_time=datetime.datetime(2017, 4, 21, 0, 0, 0))

    for news in news_list:
        print(news['media'], news['url'])
        for p in news['text'].split('\n'):
            if p != '':
                print(p)
                break
    print(len(news_list))

if __name__ == '__main__':
    main()