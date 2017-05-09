import requests
import datetime
import logging
import re
from bs4 import BeautifulSoup
from .BaseParser import BaseParser    
import time       
from multiprocessing import cpu_count

class Vedomosti(BaseParser):
    """docstring for Lenta"""
    def __init__(self, threads=cpu_count()*2-1):
        super(Vedomosti, self).__init__(
            'VED', 'http://www.vedomosti.ru',
            'http://www.vedomosti.ru/archive', datetime.datetime(2010, 1, 1),
            threads)
        self.page_type = 'html'
        
    def _check_args(self, start_time, until_time,
            news_count, topic_filter, threads):
        pass

    def _get_news_list(self, content):
        """ Getting list of news from page content """
        return content.find_all('div', 'b-article__left-inner whole_width')

    def _get_news_params_in_page(self, news):
        news_url =  news.find('div', 'b-article__title').find('a')['href']
        news_date = self._str_to_time(news.find('time')['datetime'])
        topic = re.match(r'\/([A-z0-9]+)\/', news_url).group(1)
        title = news.find('div', 'b-article__title').text
        return news_url, news_date, topic, title

    def _page_url(self):
        # Example:http://www.vedomosti.ru/archive/2017/02/01/
        return self.api_url + self._time_to_str(self.curr_date)

    def _next_page_url(self):    
        self.curr_date -= datetime.timedelta(days=1)
        return self._page_url()

    def _parse_news(self, news_params):
        """ Getting full news params by direct url """
        url = news_params[0]
        html = self._get_content(self.root_url + '/body' + url)
        date = news_params[1]
        topic = news_params[2]
        title = news_params[3]
        paragraphs = html.find_all('p')
        text = '\n'.join([p.get_text() for p in paragraphs])
        news_out = {'title': title, 'url': self.root_url + url, 'text': text, 
            'topic': topic, 'date': date}
        return news_out

    def _str_to_time(self, time_str):
        return datetime.datetime.strptime(time_str[:-6], '%Y-%m-%d %H:%M:%S')

    def _time_to_str(self, time):
        return time.strftime('/%Y/%m/%d/')