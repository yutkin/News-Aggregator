import urllib
import urllib.request
import re
from datetime import datetime
from bs4 import BeautifulSoup
from pprint import pprint
from BaseParser import BaseParser       

class RIA(BaseParser):
    """docstring for RIA"""
    def __init__(self):
        super(RIA, self).__init__(
            'RIA', 'https://ria.ru',
            'https://ria.ru/archive/more.html')
    
    def get_news(self, start_time=datetime.now(),
                until_time=datetime(2004, 1, 2),
                news_count=None, topic_filter=None):
        last_time = start_time
        last_news_ID = ''
        done = False
        count_ = 0 
        while not done:
            params = {'id': 0, 'date': self._time_to_str(last_time)}
            for news in self.parse_page(params):
                if ((news_count is not None and count_ > news_count) or
                    (until_time is not None and last_time < until_time)):
                    done = True
                    print("END OF PARSING " + str(start_time)
                          + " -- " + str(last_time))
                    break
                if (news is None): continue
                if (topic_filter is None or news['topic'] in topic_filter):
                    last_time = news['date']
                    if last_news_ID == news['url']:
                        continue
                    last_news_ID = news['url']
                    count_ += 1
                    yield news
            # print('--------------------------------------------------\
                   # END OF PAGE\
                   # --------------------------------------------------')

    def parse_page(self, params):
        params_str = urllib.parse.urlencode(params)
        request_url = self.api_url + '?' + params_str
        html = self._get_html(request_url)
        if html is None:
            yield None
        for item in html.find_all('div', 'b-list__item'):
            try:
                title = item.a.find('span', 'b-list__item-title').text
                url = item.a['href'] 
                date = (item.find('div', 'b-list__item-time').text
                        + ' ' + item.find('div', 'b-list__item-date').text)
                popularity = item.find('span', 'b-statistic__item m-views').text
                text = self.get_news_text(self.root_url + url)
                topic = re.match(r'^\/([A-z0-9]+)\/', url).group(1)
                if text is None:
                    continue
                news = {
                    'site_id': self.id,
                    'title': title,
                    'url': self.root_url + url,
                    'date': self._str_to_time(date),
                    'topic': topic,
                    'text': text,
                    'popularity': popularity,
                    'tags': ''   
                }
                yield news
            except Exception as e:
                print(e)
                yield None

    def get_news_text(self, news_url):
        html = self._get_html(news_url)
        if html is None:
            return None
        text_element = html.find('div', 'b-article__body')
        if text_element is None:
            return None
        for div in text_element.find_all('div'): 
            div.decompose()
        return text_element.text

    def _time_to_str(self, time):
        return time.strftime('%Y%m%dT%H%M%S')

    def _str_to_time(self, time_str):
        return datetime.strptime(time_str, '%H:%M %d.%m.%Y')

def main():
    parser = RIA()
    for news in parser.get_news():
        print(news['title'], news['popularity'])
        # pass

if __name__ == '__main__':
    main()