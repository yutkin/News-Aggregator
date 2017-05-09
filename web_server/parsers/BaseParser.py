import requests
import re
import json
import datetime
from bs4 import BeautifulSoup
import requests
from multiprocessing import Process, Array, Queue, Value, Lock, current_process, cpu_count
import logging
import signal
import queue
import time

class BaseParser():
    """docstring for BaseParser"""
    def __init__(self, id, root_url, api_url, until_time, threads):
        self.id = id
        self.root_url = root_url # url for news
        self.api_url = api_url # url for pages
        self.until_time_default = until_time
        self.threads = threads

    def _request(self, url):
        response = requests.get(url)
        if response.status_code != requests.codes.ok:
            response.raise_for_status()
        return response

    def _get_content(self, url, type_='html'):
        response = self._request(url)
        if type_ == 'html':
            return BeautifulSoup(response.text, 'lxml')
        elif type_ == 'json':
            return response.json()
        else:
            raise Exception()

    def get_news(self, start_time=None, until_time=None,
                news_count=None, topic_filter=None):
        """ The main process of a parser """
        t_start = time.time()
        threads = self.threads
        self._check_args(start_time, until_time, news_count,
            topic_filter, threads)
        # Some parsers do not have start time, so need to check
        if not start_time:
            start_time = datetime.datetime.now()
        if not until_time:
            until_time = self.until_time_default

        Q_urls = Queue(0) # Queue, contains news urls and for deeper parsing 
        Q_out = Queue(0) # Queue, contains news outputs
        sync_flag = Value('i', 1) # Flag for stoping processes

        workers = []
        # Proceses for getting news by url 
        for _ in range(threads):
            workers.append(Process(target=self._process_news,
                args=(Q_urls, Q_out, sync_flag, topic_filter)))
            workers[-1].start()

        out = []

        try:
            # Parsing pages with urls ("Лента новостей")
            self.parse_pages(Q_urls, Q_out, sync_flag, start_time, 
                until_time, news_count, topic_filter)
            # Clearing output queue while processes still working
            # Probably significantly slowing down other workers, need to fix it
            self._listen_queue(workers, Q_out, out)
        except KeyboardInterrupt:
            sync_flag.value = 2 # Immediate stop, without clearing Q_urls
            logging.warning('Stopping parsing...')
            # But we still need to clear the out queue
            try:
                self._listen_queue(workers, Q_out, out)
            except KeyboardInterrupt:
                # If something goes wrong -- just kill everybody
                logging.warning('Hard stopping parsing on join...')
                Q_out.cancel_join_thread()
                for worker in workers:
                    worker.terminate()

        # Waiting for processes to stop
        for i, worker in enumerate(workers):
            worker.join()
            logging.debug("END OF THREAD " + str(i))

        logging.debug('END OF PARSING, TIME ' + str(time.time() - t_start))
        return sorted(out, key=lambda x: x['date'], reverse=True)

    def _listen_queue(self, workers, Q_out, out):
        while ([ p.is_alive() for p in workers ].count(True) > 0
            or not Q_out.empty()):
            try:
                news = Q_out.get_nowait()
                out += news
            except queue.Empty:
                continue

    def parse_pages(self, Q_urls, Q_out, sync_flag, 
            start_time=datetime.datetime.now(), until_time=None,
            news_count=None, topic_filter=None):
        """ Process for getting urls from pages """
        # signal.signal(signal.SIGINT, signal.SIG_IGN)
        self.curr_date = start_time
        url_counter = 0
        while sync_flag.value == 1:
            if self.curr_date == start_time:
                url_to_fetch = self._page_url()
            else:
                url_to_fetch = self._next_page_url()

            try:
                content = self._get_content(url_to_fetch, type_=self.page_type)
            except Exception as err:
                logging.error('Error: ' + str(err) + ' ' + url_to_fetch)
                if self._handle_page_conn_error():
                    sync_flag.value = 0
                    break
                else:
                    continue

            _err = None
            try:
                news_list = self._get_news_list(content)
            except Exception as err:
                _err = err

            if _err or not news_list:
                sync_flag.value = 0
                logging.error('Error: couldn\'t find content ' + url_to_fetch
                   + ' ' + str(_err))
                break
            
            logging.debug('PROCESSING PAGE ' + url_to_fetch)

            for news in news_list:
                try:
                    # Url always first, date always second in params
                    news_params = self._get_news_params_in_page(news)
                    url = news_params[0]
                    self.curr_date = news_params[1]
                    if ((news_count is not None and url_counter >= news_count) or
                        (until_time is not None and self.curr_date <= until_time)):
                        time.sleep(1)
                        sync_flag.value = 0
                        logging.debug('END ON ' + str(self.curr_date))
                        break

                    Q_urls.put_nowait(news_params)
                    url_counter += 1
                    if url_counter % 1000 == 0:
                        logging.warning('total downloaded %d urls' % url_counter)
                except Exception as e:
                    logging.error('Error: ' + str(e) + ' ' + url_to_fetch)

    def _process_news(self, Q_urls, Q_out, sync_flag, topic_filter):
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        process_data = []
        while ((sync_flag.value == 1 or not Q_urls.empty())
                and sync_flag.value != 2):

            try:
                news_params = Q_urls.get_nowait()
            except queue.Empty:
                continue

            try:
                news_out = self._parse_news(news_params)
                news_out['media'] = self.id
                if ('topic' in news_out.keys() and topic_filter 
                    and news_out['topic'] in topic_filter):
                    continue
                process_data.append(news_out)
                logging.debug('%s' % news_out['url'])
            except Exception as err:
                logging.error("ERROR " + str(err))
                continue
        Q_out.put(process_data) # Can be overloaded w/ a lot of threads

    def _handle_page_conn_error(self):
        """ Return True if end parsing, False -- go to the next page """
        return True

def main():
    pass

if __name__ == '__main__':
    main()