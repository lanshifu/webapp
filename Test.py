import requests
from bs4 import BeautifulSoup

def get_html_data():
    # get 请求
    response = requests.get('https://meiriyiwen.com/random')

    soup = BeautifulSoup(response.content, "html5lib")
    article = soup.find("div", id='article_show')
    article_title = article.h1.string
    print('article_title=%s' % article_title)
    article_author = article.find('p', class_="article_author").string
    print('article_author=%s' % article.find('p', class_="article_author").string)
    article_contents = article.find('div', class_="article_text").find_all('p')
    article_content = ''
    for content in article_contents:
        article_content = article_content + str(content)
        print('article_content=%s' % article_content)

get_html_data()