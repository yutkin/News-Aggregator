import requests
import datetime
import logging
import re
from bs4 import BeautifulSoup
from .BaseParser import BaseParser
import time            
from multiprocessing import cpu_count

class Meduza(BaseParser):
    """docstring for Novaya"""
    def __init__(self, threads=2):
        super(Meduza, self).__init__(
            'MEDUZA', 'https://meduza.io/',
            'https://meduza.io/api/v3/', None, threads)
        self.news_per_page = 24
        self.page_type = 'json'
        self.page = 0
    
    def _check_args(self, start_time, until_time,
            news_count, topic_filter, threads):
        if not start_time is None:
            raise Exception("Start time for Meduza is not implemented")

    def _get_news_list(self, content):
        """ Getting list of news from page content """
        return content['documents'].items()

    def _get_news_params_in_page(self, news):
        news = news[1]
        if news['tag']['name'] != 'новости':
            return None
        news_url = news['url']
        news_date = self._str_to_time(news['published_at'])
        topic = None
        title = news['title']
        return news_url, news_date, topic, title

    def _page_url(self):
        return self.api_url + 'search?chrono=news&locale=ru&page=%d&per_page=%d' % (
            self.page, self.news_per_page)
    
    def _next_page_url(self):
        self.page += 1
        if self.page > 10:
            raise Exception("Meduza limit exeded")
        return self._page_url()

    def _parse_news(self, news_params):
        """ Getting full news params by direct url """
        url = self.root_url + news_params[0]
        json_ = self._get_content(self.api_url + news_params[0], 'json')
        date = news_params[1]
        title = news_params[3]
        paragraphs = BeautifulSoup(json_['root']['content']['body'], 'lxml').find_all('p')
        text = '\n'.join([p.get_text() for p in paragraphs])
        news_out = {'title': title, 'url': url, 'text': text, 'date': date}
        return news_out

    def _str_to_time(self, time_str):
        return datetime.datetime.fromtimestamp(int(time_str))
