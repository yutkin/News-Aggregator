import pandas as pd
from nltk.corpus import stopwords
from stop_words import get_stop_words
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
from functools import lru_cache
from pymystem3 import Mystem; mystem = Mystem()
import numpy as np
import datetime
from sklearn.cluster import KMeans, MiniBatchKMeans
import time

# Normalization functions
from nltk.corpus import stopwords
from stop_words import get_stop_words
en_sw = get_stop_words('en')
ru_sw = get_stop_words('ru')
STOP_WORDS = set(en_sw) | set(ru_sw)
STOP_WORDS = STOP_WORDS | set(stopwords.words('russian')) | set(stopwords.words('english'))
STOP_WORDS = STOP_WORDS | set(['лента', 'новость', 'риа', 'тасс',
                               'редакция', 'газета', 'корра', 'daily',
                               'village', 'интерфакс', 'reuters'])

class Pipeline(object):
    def __init__(self, *args):
        self.transformations = args
    def __call__(self, x):
        res = x
        for f in self.transformations:
            res = f(res)
        return res

def remove_ria(text):
    prefix = text[:50]
    ria = 'РИА Новости'
    if ria in prefix:
        text = text[text.find(ria)+len(ria)+1:]
    return text

def remove_tass(text):
    prefix = text[:100]
    return text[max(0, prefix.find('/.')+1):]

def get_lower(text):
    return str(text).lower().strip()

def remove_punctuation(text):
    return ''.join([c if c.isalpha() or c in ['-',"'"] else ' ' for c in text])

@lru_cache(maxsize=None)
def get_word_normal_form(word):
    return ''.join(mystem.lemmatize(word)).strip().replace('ё', 'е').strip('-')

def lemmatize_words(text):
    res = []
    for word in text.split():
        norm_form = get_word_normal_form(word)
        if len(norm_form) > 2 and norm_form not in STOP_WORDS:
            res.append(norm_form)
    return ' '.join(res)

TEXT_PIPELINE = Pipeline(remove_tass, remove_ria, get_lower, remove_punctuation, lemmatize_words)

class Analizer():
    """ Class-wrapper for nlp data-processing """
    def __init__(self, news_list):
        # Loading saved models
        with open('./models/SVM_classifier.bin', 'rb') as pickle_file:
            self.SVM_clf = pickle.load(pickle_file)
        with open('./models/TFIDF_vectorizer.bin', 'rb') as pickle_file:
            self.TFIDF_load = pickle.load(pickle_file)
        with open('./models/LabelEncoder.bin', 'rb') as pickle_file:
            self.labels = pickle.load(pickle_file)
        # self.fast_text = fasttext.load_model('./models/fast_text.bin')
        # Convering input news to pd table
        self.data = self._data_to_pandas(news_list)
        # Saving most recent news date for updating data
        self.last_date = self.data.iloc[0].date
        self.count = self.data.shape[0]
        if self.count > 300:
            self.data = self.data[:300]
        # Classifying news w/ ALL classifiers
        self._classify(self.data)
        # Aggregating with ALL aggregators
        self.agrs_conf = {
            'Graphs': {'coeff': 0.5},
            'Kmeans': {'coeff': 0.5, 'clusters': self.count//5}
        }
        aggregators = self._aggregate(self.data, self.agrs_conf)
        self._form_output(self.data, aggregators)

    def get_data(self):
        return self.output, self.last_date

    def append_data(self, news_list):
        if not news_list:
            return
        # Cleaning and classifying new data
        new_data = self._data_to_pandas(news_list)
        self._classify(new_data)
        # Adding new data to existing data
        self.data = pd.concat([new_data, self.data])
        # Sorting just to be sure
        self.data.sort_values('date', inplace=True, ascending=False)
        # Saving most recent news date for next update
        self.last_date = self.data.iloc[0].date
        # Dropping all data older then 24 hours
        if self.count > 300:
            until_time = datetime.datetime.now() + datetime.timedelta(hours=-12)
            self.data = self.data[self.data.date >= until_time]
            self.count = self.data.shape[0]
        # Aggregate every time new data is coming
        aggregators = self._aggregate(self.data, self.agrs_conf)
        self._form_output(self.data, aggregators)

    def _form_output(self, data, aggregators):
        """ Creating a json output for each agregator """
        self.output = {}
        for aggr_name, groups in aggregators.items():
            self.output[aggr_name] = []
            for i, group in enumerate(groups):
                self.output[aggr_name].append([])
                for id_ in group:
                    self.output[aggr_name][i].append({
                        'media': data.iloc[id_].media,
                        'title': data.iloc[id_].title,
                        'url': data.iloc[id_].url,
                        'text': self._cut_text(data.iloc[id_].text),
                        'labels': {
                            'SVM': self._class_to_str(
                                data.iloc[id_]['SVM_class'])
                        },
                        'date': self._date_to_str(data.iloc[id_]['date'])
                    })

    def _data_to_pandas(self, news_list):
        # Converting data to pandas table
        data = pd.DataFrame(news_list)
        # Keepink only usable columns
        data = data[['media', 'url', 'title', 'text', 'topic', 'date']]
        # Sorting by date
        data.date = pd.to_datetime(data.date)
        data.sort_values('date', inplace=True, ascending=False)
        data.drop_duplicates(subset='url', inplace=True)
        # Appending text_norm, title_norm columns to data w/ normalized text
        self._norimalize(data)
        return data

    def _norimalize(self, data):
        data.title = data.title.apply(lambda x: x.strip())
        # Appending normalized text to table
        data['text_norm'] = data.text.apply(TEXT_PIPELINE)
        data['title_norm'] = data.title.apply(TEXT_PIPELINE)

    def _classify(self, data):
        self.classifiers_ids = ('SVM_class', 'fast_text_class')
        # Adding colomn with class for each classifier
        self._classify_SVM(data)
        # self._classify_fast_text(data)
        # Add new classifier here

    def _classify_SVM(self, data):
        # Adding 'SVM_class' column
        data['SVM_class'] = data.apply(
            lambda row:
                self.SVM_clf.predict(
                    self.TFIDF_load.transform(
                        [row['title_norm'] + ' ' + row['text_norm']]))[0],
            axis=1)

    def _classify_fast_text(self, data):
        # Adding 'fast_text_class' column
        data['fast_text_class'] = data.apply(
            lambda row:
                int(self.fast_text.predict(
                    [row['title_norm'] + ' ' + row['text_norm']])[0][0][9:]),
            axis=1)

    def _aggregate(self, data, params):
        """
            Creating dict of aggrs w/ groups:
            collecions of news ids (id in self.data)
        """
        aggregators = {
            'Graphs': self._aggregate_graphs(data,
                coeff=params['Graphs']['coeff']),
            'Kmeans': self._aggregate_Kmeans(data,
                coeff=params['Kmeans']['coeff'],
                clusters=params['Kmeans']['clusters'])
        }
        return aggregators

    def _aggregate_graphs(self, data, coeff, titles=False):
        TFIDF, tfidf_matrix = self._get_TFIDF(data,  True, titles)
        cosines = []
        for tfidf_news in tfidf_matrix:
            cosine = cosine_similarity(tfidf_news, tfidf_matrix)
            cosines.append(cosine.tolist()[0])
        
        COS_THRESHOLD = coeff
        themes = [ -1 for _ in range(len(cosines)) ]
        themes_ids = [ [] for _ in range(len(cosines)) ]
        curr_theme = -1
        for v, theme in enumerate(themes):
            if theme == -1:
                curr_theme += 1
                Q = []
                Q.append(v)
                themes[v] = curr_theme
                themes_ids[curr_theme].append(v)
                while Q:
                    curr_v = Q.pop(0)
                    for u, cos in enumerate(cosines[curr_v]):
                        if cos >= COS_THRESHOLD and themes[u] == -1:
                            themes[u] = curr_theme
                            themes_ids[curr_theme].append(u)
                            Q.append(u)
        return self._sort_groups(themes_ids)

    def _aggregate_Kmeans(self, data, coeff, clusters, titles=False):
        TFIDF, tfidf_matrix = self._get_TFIDF(data, True, titles)
        if self.count < clusters:
            clusters = self.count
        # kmeans = KMeans(n_clusters=clusters, random_state=42).fit(tfidf_matrix)
        kmeans = MiniBatchKMeans(n_clusters=clusters, batch_size=32, n_init=10, max_iter=100).fit(
            tfidf_matrix)
        clasters = kmeans.predict(tfidf_matrix)
        c_list = [ [] for i in range(clusters) ]
        for i, claster in enumerate(clasters):
            tfidf_news = tfidf_matrix[i]
            if cosine_similarity(tfidf_news,
                kmeans.cluster_centers_[claster].reshape(1, -1))[0][0] >= coeff:
                c_list[claster].append(i)
        return self._sort_groups(c_list)

    def _get_avg_time(self, group):
        avg = 0
        for n in group:
            avg += time.mktime(self.data.iloc[n]['date'].timetuple())
        return avg//len(group)

    def _sort_groups(self, groups):
        groups = filter(lambda x: len(x) > 1, groups)
        groups = sorted(groups, key=lambda x: self._get_avg_time(x), reverse=True)
        groups = list(map(lambda x: sorted(x,
            key=lambda y: self.data.iloc[y]['date'], reverse=True), groups))
        return groups

    def _get_TFIDF(self, data, loaded=True, titles=False):
        if titles:
            trainX = self.data['title_norm']
        else:
            trainX = self.data['title_norm'] + ' ' + self.data['text_norm']
        trainX = trainX.values
        if loaded:
            tfidf_vectorizer = self.TFIDF_load
        else:    
            tfidf_vectorizer = TfidfVectorizer(min_df=5,
                ngram_range=(1,2), lowercase=False).fit(trainX)
        
        tfidf_matrix = tfidf_vectorizer.transform(trainX)
        return tfidf_vectorizer, tfidf_matrix

    def _class_to_str(self, class_num):
        """ Converting number of predicted class to string """
        return self.labels.inverse_transform(class_num)

    def _cut_text(self, text):
        """ Returns first paragraph of text """
        ps = []
        for p in text.split('\n'):
            if p != '':
                if len(p) > 500:
                    ps.append(p[:500].strip() + '...')
                    return "\n".join(ps)
                else:
                    ps.append(p.strip())
                if len(ps) == 1:
                    return "\n".join(ps)
        return ''

    def _date_to_str(self, date):
        return date.strftime('%a %H:%M')
    