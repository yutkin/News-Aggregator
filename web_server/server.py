from flask import Flask, render_template, session, request,\
    redirect, url_for, Response, stream_with_context, jsonify
import datetime
import time
import news_getter
from analysis import Analizer
from threading import Timer
from pprint import pprint

app = Flask(__name__)
UPDATE_RATE = 60
HOURS_INIT = -12

# Redirecting to main page form root
@app.route('/')
def index():
    return redirect(
        url_for('get_content', aggregator='Kmeans', topic_count=5))

# Get aggregated topic from <aggregator>, return HTML
@app.route('/<aggregator>/<int:topic_count>')
def get_content(aggregator, topic_count=5):
    data, _ = analizer.get_data()
    if aggregator in data:
        groups = data[aggregator]
    else:
        return redirect(
            url_for('get_content', aggregator='Kmeans', topic_count=5))

    if len(groups) < topic_count:
        return redirect(
            url_for('get_content', aggregator=aggregator,
                topic_count=len(groups)))

    groups = groups[:topic_count]
    return render_template('main.html', aggregator=aggregator,
        count=analizer.count, groups=groups)

# For ajax
@app.route('/api/<aggregator>/<int:offset>')
def api_get_content(aggregator, offset=5):
    data, _ = analizer.get_data()
    if aggregator in data:
        groups = data[aggregator]
    else:
        response = jsonify(message="Invalid aggregator: " + aggregator)
        response.status_code = 404
        return response

    if len(groups) < offset + 5:
        response = jsonify(message="Topic number too large")
        response.status_code = 404
        return response
        
    groups = groups[offset:offset + 5]

    return jsonify({'data': render_template('view.html', groups=groups)})

@app.template_filter('min')
def reverse_filter(s):
    return min(s)

# Updating thread
def update_data(interval):
    Timer(interval, update_data, [interval]).start()
    global analizer
    print("UPDATING DATA...")
    # Getting all news since until_time
    _, until_time = analizer.get_data()
    news_list = news_getter.get_news(until_time, debug=False)
    
    print("NEW NEWS:", len(news_list))
    print(*[(x['title'], x['url'], x['date']) for x in news_list], sep='\n')

    if len(news_list):
        # Appending data if any exists
        analizer.append_data(news_list)
        data = analizer.get_data()[0]
        print_output(data)

def print_output(data):
    # Printing topics for debug
    for aggr, groups in data.items():
        print('.............', aggr, '.............')
        for i, group in enumerate(groups[:7]):
            print("Topic", i)
            for news in group:
                print(news['title'], news['url'])    

if __name__ == "__main__":
    # Getting init news for the last HOURS_INIT from all parsers
    until_time = datetime.datetime.now() + datetime.timedelta(hours=HOURS_INIT)
    news_list = news_getter.get_news(until_time, debug=False)
    print("News downloaded on init: ", len(news_list))
    analizer = Analizer(news_list)
    data, last_date = analizer.get_data()

    print_output(data)
    
    # Starting updating thread
    Timer(UPDATE_RATE, update_data, [UPDATE_RATE]).start()
    # Starting server
    app.run(debug=True, threaded=True, use_reloader=False)