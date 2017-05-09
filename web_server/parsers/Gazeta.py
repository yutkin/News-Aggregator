import requests
from datetime import datetime, timedelta
import logging
import datetime
from bs4 import BeautifulSoup
from .BaseParser import BaseParser
from multiprocessing import cpu_count

class Gazeta(BaseParser):

    def __init__(self, threads=cpu_count()*2-1):
        super(Gazeta, self).__init__(
            'GAZETA', 'https://www.gazeta.ru',
            'https://www.gazeta.ru/news/?p=page&d=', None, threads)

        self.page_type = 'html'

    def _check_args(self, start_time, until_time,
                news_count, topic_filter, threads):
        pass

    def _get_news_list(self, content):
        """ Getting list of news from page content """
        return content.find_all('article',
            attrs={"itemprop": "itemListElement"})

    def _get_news_params_in_page(self, news):
        news_url = self.root_url + news.find('a',
                attrs={"itemprop": 'mainEntityOfPage url'})['href']
        timestamp = int(news.find('meta',
            attrs={"itemprop": "position"})['content'])
        news_date = datetime.datetime.fromtimestamp(timestamp)
        return news_url, news_date

    def _page_url(self):
        # Example: https://www.gazeta.ru/news/?p=page&d=09.04.2017_12:44
        return self.api_url + self._time_to_str(self.curr_date)

    def _next_page_url(self):
        return self._page_url()

    def _parse_news(self, news_params):
        """ Getting full news params by direct url """
        html = self._get_content(news_params[0])
        date = news_params[1]
        paragraphs = (html.find('div', attrs={"itemprop": "articleBody"})
            or html.find('div', 'article_text'))
        paragraphs = paragraphs.find_all('p')
        text = '\n'.join([p.get_text() for p in paragraphs])
        topic = html.find('div', 'b-navbar-main').find('div',
            'item active').find('a').text
        try:
            tag = html.find('div', 'news_theme') or html.find('div', 'border_up_red')
            tag = tag.find('a').text
        except Exception as e:
            tag = None
        title = html.find('h1', 'article-text-header') or html.find('h1', 'txtclear')
        title = title.get_text()
        news_out = {'title': title, 'url': news_params[0], 'text': text, 
            'topic': topic, 'tag': tag, 'date': date}
        return news_out

    def _time_to_str(self, time):
        return time.strftime('%d.%m.%Y_%H:%M')