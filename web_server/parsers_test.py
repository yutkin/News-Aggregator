import logging
import datetime
from parsers import Gazeta, Tass, Lenta, Vedomosti, Novaya, Meduza

def main():
    logging.basicConfig(level=logging.DEBUG,
                        format='[PID %(process)d %(asctime)s] %(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S')
    logging.getLogger('requests').setLevel(logging.CRITICAL)

    parsers_ = [
        Meduza(threads=32)
    ]

    news_list = []

    for parser in parsers_:
        print(parser.id)
        news_list += parser.get_news(
            until_time=datetime.datetime(2017, 5, 12, 0, 0, 0))

    for news in news_list:
        print(news)
    print(len(news_list))

if __name__ == '__main__':
    main()