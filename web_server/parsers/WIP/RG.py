import csv
import requests
from multiprocessing import Process, Queue, Value, Lock, current_process
import queue
from datetime import datetime, timedelta
import signal
import logging
import time
import pandas as pd
import datetime
import json
from bs4 import BeautifulSoup

NUM_JOBS = 32

def _time_to_str(time):
    return time.strftime('%d.%m.%Y_%H:%M')

def _str_to_time(time_str):
    return datetime.datetime.strptime(time_str, '%Y%m%d%H%M')

def url_fetcher(Q, sync_flag):
    curr_offset = 1
    url_counter = 0
    while True:
        url_to_fetch = "https://rg.ru/api/search/"
        curr_offset += 1
        try:
            response = requests.post(url_to_fetch, data=json.dumps(payload), headers=headers)
            if response.status_code != requests.codes.ok:
                raise Exception()
            news_list = json.loads(response.text)['items']
        except Exception as err:
            sync_flag.value = 0
            logging.debug("ERROR " + str(err) + ' ' + url_to_fetch)
            break

        for news in news_list:
            news_url = 'https://rg.ru' + news['uri']
            Q.put([news_url, news['link_title'], news['datetime']])
            url_counter += 1
            if url_counter % 1000 == 0:
                logging.debug('total downloaded %d urls' % url_counter)

def fetch_news(Q, sync_flag):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    news_storage = []
    pid = current_process().pid

    while sync_flag.value == 1:
        try:
            url = Q.get_nowait()
        except queue.Empty:
            continue

        try:
            response = requests.get(url[0])
        except Exception as e:
            continue
        
        if response.status_code == requests.codes.ok:
            html = BeautifulSoup(response.text, 'lxml')
            try:
                paragraphs = (html.find('div', 'b-material-wrapper__text'))
                paragraphs = paragraphs.find_all('p')
                text = ' '.join([p.text for p in paragraphs])
                title = url[1]
                time = _str_to_time(url[2])
            except Exception as err:
                logging.debug("ERROR " + str(err) + ' ' + url[0])
                continue
            news_storage.append({'title': title, 'url': url[0], 'text': text, 'time': time})
            logging.debug('%s' % url[0])

    logging.debug('Stopped, writing to /data/rg/rg_%d_1.csv' % pid)
    pd.DataFrame(news_storage).to_csv('./data/rg/rg_%d_1.csv' % pid,
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
        logging.debug('Start stoping threads')
        for worker in workers:
            worker.join()
        logging.debug('End of threads')

if __name__ == '__main__':
    main()