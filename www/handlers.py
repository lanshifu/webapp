#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from apis import APIValueError,APIError
from aiohttp import web
__author__ = 'Michael Liao'

' url handlers '

import re, time, json, logging, hashlib, base64, asyncio
from coroweb import get, post
from models import User, Comment, Blog, next_id
from config import configs
from apis import Page
from apis import APIPermissionError
from apis import HttpResult
import markdown2
COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret

def user2cookie(user, max_age):
    '''
    Generate cookie str by user.
    '''
    # build cookie string by: id-expires-sha1
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)

def text2html(text):
    lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
    return ''.join(lines)

@get('/')
def index(request):
    summary = '内容太长。。。'
    blogs = [
        Blog(id='1', name='Test Blog', summary=summary, created_at=time.time()-120),
        Blog(id='2', name='Something New', summary=summary, created_at=time.time()-3600),
        Blog(id='3', name='Learn Swift', summary=summary, created_at=time.time()-7200)
    ]
    return {
        '__template__': 'blogs.html',
        'blogs': blogs
    }

@get('/register')
def register():
    return {
        '__template__': 'register.html'
    }

@get('/login')
def signin():
    return {
        '__template__': 'login.html'
    }

@get('/blog/{id}')
async def get_blog(id):
    blog = await Blog.find(id)
    comments = await Comment.findAll('blog_id=?', [id], orderBy='created_at desc')
    for c in comments:
        c.html_content = text2html(c.content)
    blog.html_content = markdown2.markdown(blog.content)
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'comments': comments
    }

@get('/manage/blogs')
def manage_blogs(*, page='1'):
    return {
        '__template__': 'manage_blogs.html',
        'page_index': get_page_index(page)
    }

@get('/manage/blogs/create')
def manage_create_blog():
    return {
        '__template__': 'manage_blog_edit.html',
        'id': '',
        'action': '/api/blogs'
    }


# @get('/login')
# def signout(request):
#     referer = request.headers.get('Referer')
#     r = web.HTTPFound(referer or '/')
#     r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
#     logging.info('user login.')
#     return r

#########################################################  api   ####################################################



# 查询用户列表接口
@get('/api/users')
async def api_get_users():
    users = await User.findAll()
    for u in users:
        # u.passwd = '******'
        pass
    # return dict(users=users)
    return dict(result = HttpResult(users))

# 登录接口
@post('/api/login')
async def authenticate(*, email, passwd):
    if not email:
        return dict(result=HttpResult('',10,'Invalid email'))
        # raise APIValueError('email', 'Invalid email.')
    if not passwd:
        return dict(result=HttpResult('', 10, 'Invalid password'))
        # raise APIValueError('passwd', 'Invalid password.')
    users = await User.findAll('email=?', [email])
    if len(users) == 0:
        return dict(result=HttpResult('', 10, 'Email not exist'))
        # raise APIValueError('email', 'Email not exist.')
    user = users[0]
    # check passwd:
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    print('old ='+user.passwd +" new ="+sha1.hexdigest())
    if user.passwd != sha1.hexdigest():
    # if user.passwd != passwd:
        raise APIValueError('passwd', 'Invalid password.')
    # authenticate ok, set cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

# 注册接口：邮箱、密码
@post('/api/register')
async def api_register_user(*, email, name, passwd):
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')
    users = await User.findAll('email=?', [email])
    if len(users) > 0:
        return dict(result=HttpResult('', 10, 'Email is already in use'))
        # raise APIError('register:failed', 'email', 'Email is already in use.')
    uid = next_id()
    sha1_passwd = '%s:%s' % (uid, passwd)
    # user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
    user = User(id=uid, name=name.strip(), email=email, passwd=passwd, image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
    await user.save()
    # make session cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r



def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p

def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()

@get('/api/blogs')
async def api_blogs(*, page='1'):
    page_index = get_page_index(page)
    num = await Blog.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, blogs=())
    blogs = await Blog.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, blogs=blogs)

@get('/api/blogs/{id}')
async def api_get_blog(*, id):
    blog = await Blog.find(id)
    if not blog:
        return  dict(result=HttpResult(''))
    return blog

@post('/api/blogs')
async def api_create_blog(request, *,id, name, summary, content):
    # check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    blog = Blog(user_id=id, user_name=id, user_image='', name=name.strip(), summary=summary.strip(), content=content.strip())
    await blog.save()
    return blog

