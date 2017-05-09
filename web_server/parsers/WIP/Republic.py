import urllib
import urllib.request
import json
from datetime import datetime
from pprint import pprint
from bs4 import BeautifulSoup
from BaseParser import BaseParser       

class Novaya(BaseParser):
    """docstring for Novaya"""
    def __init__(self):
        super(Novaya, self).__init__(
            'REPUBLIC', 'https://republic.ru/',
            'https://republic.ru/news')
        self.news_per_page = 100
    
    def get_news(self, start_time=datetime.now(), until_time=None,
                news_count=None, topic_filter=None):
        last_time = start_time
        done = False
        count_ = 0
        page = 1
        while not done:
            params = {'page': page}
            for news in self.parse_page(params):
                if ((news_count is not None and count_ < news_count) or
                    (until_time is not None and last_time < until_time) or
                    (news is None)):
                    done = False
                    break
                if (topic_filter is None or news['topic'] in topic_filter):
                    last_time = news['date']
                    count_ += 1
                    yield news
            page += 1
            # print('--------------------------------------------------\
                   # END OF PAGE\
                   # --------------------------------------------------')

    def parse_page(self, params):
        params_str = urllib.parse.urlencode(params)
        request_url = self.api_url + '?' + params_str
        data = self._get_json(request_url)
        if not data:
            return None
        for item in data.find_all('article', 'card'):
            try:
                title = item.find('h2', 'card__title').text
                url = item.find('a', 'card__link')['href']
                date = item.find('span', 'card__meta__datetime').text
                topic = item.find('span', 'card__label').text
                popularity = item.find('span', 'card__meta__count').text
                news_html = self._get_html(self.root_url + url)
                text = self.get_news_text(news_html)
                tag = self.get_news_tag(news_html)
                news = {
                    'title': title,
                    'url': self.root_url + url,
                    'date': self._str_to_time(date),
                    'topic': topic,
                    'text': text,
                    'popularity': None,
                    'tag': tag
                }
                yield news
            except Exception as e:
                print(e)

    def get_news_text(self, news_content):
        text_element = BeautifulSoup(news_content['body'], 'lxml')
        if text_element is None:
            return None
        for div in text_element.find_all('div'): 
            div.decompose()
        return text_element.text

    def get_news_tags(self, news_content):
        return list(
            map(lambda x: [x['code'], x['title']], news_content['tags']))

    # def _time_to_str(self, time):
    #     return time.strftime('%Y%m%dT%H%M%S')

    def _str_to_time(self, time_str):
        # 2017-01-31T18:59:00.000+03:00
        return datetime.strptime(time_str, '%d %mT%H:%M:%S')

def main():
    parser = Novaya()
    for news in parser.get_news():
        print(news['title'], news['topic'])
        # pass

if __name__ == '__main__':
    main()