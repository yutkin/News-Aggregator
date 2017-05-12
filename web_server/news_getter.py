from parsers import Gazeta, Tass, Lenta, Vedomosti, Novaya, Meduza
import logging
import time

def get_news(until_time, debug=False):
    if debug:
        print("Starting parsing...")
        logging.basicConfig(level=logging.DEBUG,
                            format='[PID %(process)d %(asctime)s] %(message)s',
                            datefmt='%d/%m/%Y %H:%M:%S')
        logging.getLogger('requests').setLevel(logging.CRITICAL)
        start = time.time()

    thrs = 16
    parsers_ = [
        Gazeta(threads=thrs),
        # Tass(threads=thrs),
        Meduza(threads=thrs),
        Lenta(threads=thrs),
        Vedomosti(threads=thrs),
        Novaya(threads=4)
    ]
    news_list = []
    for parser in parsers_:
        if debug: print(parser.id)
        news_list += parser.get_news(until_time=until_time, topic_filter=['newspaper'])
    if debug: print('Time of parsing ' + str(time.time() - start))
    return news_list