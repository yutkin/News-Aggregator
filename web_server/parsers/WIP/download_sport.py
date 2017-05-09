import csv
import requests
from multiprocessing import Process, Queue, Value, Lock, current_process
import queue
from datetime import datetime, timedelta
import signal
import logging
import time
import pandas as pd

from bs4 import BeautifulSoup

NUM_JOBS = 16

def url_fetcher(Q, sync_flag):
    curr_page = 2
    url_counter = 0
    while True:
        url_to_fetch = 'http://www.sport-express.ru/news/page' + str(curr_page) + '/'
        try:
            response = requests.get(url_to_fetch)
            if response.status_code != requests.codes.ok:
                raise Exception()
        except Exception:
            sync_flag.value = 0
            break

        html_tree = BeautifulSoup(response.text, 'lxml')
        news_list = html_tree.find_all('div', 'recent_item')
        for news in news_list:
            news_url = news.find('a', 'fs_20')['href']
            Q.put(news_url)

            url_counter += 1
            if url_counter % 1000 == 0:
                logging.debug('total downloaded %d urls' % url_counter)
        curr_page += 1

def fetch_news(Q, sync_flag):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    news_storage = []
    pid = current_process().pid

    while sync_flag.value == 1:
        try:
            url = Q.get_nowait()
        except queue.Empty:
            continue

        response = requests.get(url)
        if response.status_code == requests.codes.ok:
            html = BeautifulSoup(response.text, 'lxml')
            try:
                paragraphs = html.find('div', 'article_text').find_all('p')
                text = ' '.join([p.get_text() for p in paragraphs])
                topic = html.find('div',
                    'fs_13').find('a')['href']
                title = html.find('h1', 'trebuchet').get_text()
            except Exception:
                continue
            news_storage.append({'title': title, 'url': url, 'text': text,
                                 'topic': topic})
            logging.debug('%s' % url)

    # logging.debug('Stopped, writing to news_sport_%d.csv' % pid)
    pd.DataFrame(news_storage).to_csv('./data/sport/news_sport_%d.csv' % pid,
        encoding='utf-8', index=None)

def main():
    logging.basicConfig(level=logging.DEBUG,
                        format='[PID %(process)d %(asctime)s] %(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S')
    logging.getLogger('requests').setLevel(logging.CRITICAL)

    Q = Queue()
    sync_flag = Value('i', 1)

    workers = []
    for _ in range(NUM_JOBS):
        workers.append(Process(target=fetch_news, args=(Q, sync_flag)))
        workers[-1].start()

    try:
        url_fetcher(Q, sync_flag)
    except KeyboardInterrupt:
        sync_flag.value = 0
    finally:
        for worker in workers:
            worker.join()

if __name__ == '__main__':
    main()