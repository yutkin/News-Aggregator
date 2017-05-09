import requests
import datetime
import logging
import re
from bs4 import BeautifulSoup
from .BaseParser import BaseParser
import time            
from multiprocessing import cpu_count

class Novaya(BaseParser):
    """docstring for Novaya"""
    def __init__(self, threads=2):
        super(Novaya, self).__init__(
            'NOVAYA', 'https://www.novayagazeta.ru/news/',
            'https://content.novayagazeta.ru/news/', None, threads)
        self.news_per_page = 100
        self.page_type = 'json'
        self.offset = 0
    
    def _check_args(self, start_time, until_time,
            news_count, topic_filter, threads):
        if not start_time is None:
            raise Exception("Start time for Novaya is not implemented")
        if threads > 2:
            logging.debug("Novaya can block connections with a lot of processes")

    def _get_news_list(self, content):
        """ Getting list of news from page content """
        return content['items']

    def _get_news_params_in_page(self, news):
        news_url = news['code']
        news_date = self._str_to_time(news['dtime'])
        try:
            topic = news['rubric']['code']
        except Exception as e:
            topic = None
        title = news['title']
        popularity = news['views_count']
        return news_url, news_date, topic, title, popularity

    def _page_url(self):
        # Example: https://content.novayagazeta.ru/news?offset=0&limit=100
        return self.api_url + '?offset=%d&limit=%d' % (
            self.offset, self.news_per_page)
    
    def _next_page_url(self):
        self.offset += self.news_per_page
        return self._page_url()

    def _parse_news(self, news_params):
        """ Getting full news params by direct url """
        url = self.root_url + news_params[0]
        json_ = self._get_content(self.api_url + news_params[0], 'json')
        date = news_params[1]
        topic = news_params[2]
        title = news_params[3]
        text = BeautifulSoup(json_['body'], 'lxml')
        for div in text.find_all('div'): 
            div.decompose()
        text = text.get_text()
        popularity = news_params[4]
        try:
            tag = ','.join(list(
                map(lambda x: x['title'], json_['tags'])))
        except Exception:
            tag = None
        news_out = {'title': title, 'url': url, 'text': text, 
            'topic': topic, 'date': date, 'popularity': popularity, 'tag': tag}
        return news_out

    def _str_to_time(self, time_str):
        # 2017-01-31T18:59:00.000+03:00
        return datetime.datetime.strptime(time_str[:19], '%Y-%m-%dT%H:%M:%S')
