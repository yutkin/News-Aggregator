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
    end_date = 2017
    begin_date = 2016
    while True:
        url_to_fetch = ("https://query.nytimes.com/svc/add/v1/sitesearch.json?q=cultural&end_date="
            + str(end_date) + "0101&begin_date="+ str(begin_date) +"0101&page="
            + str(curr_offset) + '&facet=true')
        curr_offset += 1
        try:
            response = requests.get(url_to_fetch)
            if response.status_code != requests.codes.ok:
                raise Exception()
            news_list = json.loads(response.text)['response']['docs']
        except Exception as err:
            if begin_date <= 2003:
                sync_flag.value = 0
                break
            else:
                end_date -= 1
                begin_date -= 1
                curr_offset = 1
            logging.debug("ERROR " + str(err) + ' ' + url_to_fetch)

        for news in news_list:
            try:
                Q.put([news['web_url'], news['headline']['main'], news['pub_date']])
                url_counter += 1
                if url_counter % 1000 == 0:
                    logging.debug('total downloaded %d urls' % url_counter)
            except Exception:
                continue

def fetch_news(Q, sync_flag):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    news_storage = []
    pid = current_process().pid

    while sync_flag.value == 1 or not Q.empty():
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
                paragraphs = html.find_all('p', 'story-body-text story-content')
                if not paragraphs:
                    paragraphs = html.find_all('p', attrs={'itemprop': 'articleBody'})
                text = ' '.join([p.get_text() for p in paragraphs])
                title = url[1]
                time = url[2]
            except Exception as err:
                logging.debug("ERROR " + str(err) + ' ' + url[0])
                continue
            news_storage.append({'title': title, 'url': url[0], 'text': text, 'time': time})
            logging.debug('%s' % url[0])

    logging.debug('Stopped, writing to _%d.csv' % pid)
    pd.DataFrame(news_storage).to_csv('../data/NY/NY_%d_1.csv' % pid,
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