#handlers.py

import asyncio, time, hashlib, json, logging, re
from aiohttp import web

from werkzeug import get, post, put, delete

from models import User, Blog, Comment, next_id
from apis import APIError, APIValueError, APIResourceNotFoundError
from config import configs
from models import next_id

COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret
MAX_BLOGS = 5

def user2cookie(user, max_age):
    expires = str(int(time.time()+max_age))
    s = hashlib.sha1(('%s-%s-%s-%s' % (user.id, user.password, expires, _COOKIE_KEY)).encode('utf-8'))
    L = [user.id, expires, s.hexdigest()]
    return '-'.join(L)
    
async def cookie2user(cookie_str):
    if not cookie_str:
        return None
    try:
        l = cookie_str.split('-')
        if len(l) != 3:
            return None
        uid, expires, sha_1 = l
        if time.time() > int(expires):
            return None
        user = await User.find(uid)
        if user:
            if sha_1 == hashlib.sha1(('%s-%s-%s-%s' % (user.id, user.password, expires, _COOKIE_KEY)).encode('utf-8')).hexdigest():
                user.password = '******'
                return user
        else:
            logging.info('invalid sha1')
            return None
    except Exception as e:
        logging.info(e)
        return None
    
@get('/hello/{name}')
def hello(name):
    return '<h1>Hello, %s.</h1>' % name
    
@get('/')
async def index(request):
    logging.info('call "/"')
    admin = await User.findAll('admin=?', 1)
    admin_id = admin[0].id
    blogs = await Blog.findAll('user_id=?', admin_id, size=3, orderBy='created_at DESC')
    return {
        '__template__': 'blogs.html',
        'blogs': blogs
    }

@get('/manage/users')
async def get_users(request):
    users = await User.findAll(orderBy='created_at desc')
    return {
        '__template__': 'users.html',
        'users': users
    }

@get('/manage/users/{id}')
async def delete_user(request, *, id):
    user = await User.find(id)
    if user:
        await user.remove()
    users = await User.findAll(orderBy='created_at desc')
    return {
        '__template__': 'users.html',
        'users': users
    }

@get('/user/{id}')
async def get_user(request, *, id):
    if id == '2333':
        return await index(request)
    user = await User.find(id)
    return {
        '__template__': 'user.html',
        'user': user
    }

@get('/blog/{id}')
async def get_blog(request, *, id):
    blog = await Blog.find(id)
    comments = await Comment.findAll('blog_id=?', id)
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'comments': comments
    }
    
@get('/manage/comments')
def get_comments(request):
    return {
        '__template__': 'comments.html',
    }
    
@get('/manage/api/comments')
async def get_api_comments(request):
    blogs = await Blog.findAll(orderBy='created_at desc')
    comments = await Comment.findAll(orderBy='created_at desc')
    commentsByBlog = []
    for blog in blogs:
        temp = [c for c in comments if c.blog_id == blog.id]
        if len(temp) > 0:
            for comment in temp:
                comment.blog_name = blog.name
                comment.blog_count = len(temp)
        else:
            temp.append({
                'blog_name': blog.name,
                'blog_count': 0,
                'blog_id': blog.id
            })
        commentsByBlog.append(temp)# difference with the append wethod in r
    return {
        'commentsByBlog': commentsByBlog
    }
    
@post('/api/comment')
async def api_post_comment(request, *, content, blog_id):
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    new_comment = Comment(
        id = next_id(),
        blog_id = blog_id,
        user_id = request.__user__.id if(request.__user__) else '2333',
        user_name = request.__user__.name if(request.__user__) else 'Gast',
        user_image = request.__user__.image if(request.__user__) else 'about: blank',
        content = content
    )
    await new_comment.save()
    return {
        'content': new_comment.content
    }

@delete('/manage/api/comment/{id}')
async def delete_api_comment(request, *, id):
    comment = await Comment.find(id);
    await comment.remove()
    return comment
    
@get('/blogs_list')
def get_blogs(request):
    return {
        '__template__': 'blogs_list.html'
    }
    
@get('/api/blogs_list')
async def get_blogs_list(request):
    admin = await User.findAll('admin=?', 1)
    admin_id = admin[0].id
    user_id = request.__user__.id if(request.__user__) else ''
    blogs = await Blog.findAll('user_id=?', [admin_id], orderBy='created_at DESC')
    pages_num = len(blogs) // MAX_BLOGS if(len(blogs)%MAX_BLOGS == 0) else (len(blogs) // MAX_BLOGS) + 1
    pages = list(range(pages_num+1))[1:]
    blogs_list = blogs[0:MAX_BLOGS]
    return {
        'blogs_list': blogs_list,
        'pages': pages,
        'max_blogs': MAX_BLOGS,
        'user_id': user_id,
        'pages_num': pages_num
    }
    
@post('/api/blogs_list')
async def post_blogs_list(request, *, page_index):
    admin = await User.findAll('admin=?', 1)
    admin_id = admin[0].id
    blogs = await Blog.findAll('user_id=?', [admin_id], orderBy='created_at DESC')
    index = (page_index-1) * MAX_BLOGS
    blogs_list = blogs[index: index+MAX_BLOGS]
    return {
        'blogs_list': blogs_list
    }

@delete('/manage/api/blogs_list/{id}')
async def delete_blog(request, *, id):
    blog = await Blog.findAll('id=? and user_id=?', args=(id, request.__user__.id))
    if blog:
        await blog[0].remove()
        return blog[0]
    else:
        raise APIValueError('Blog', 'Blog not found')


@get('/manage/blog_edit/{id}')
def get_blog_edit(request, *, id):
    if id == '0':
        blog_id = ''
    else:
        blog_id = id
    logging.info('[ID]: %s' % id)
    logging.info('call "/blog"')
    return {
    '__template__': 'blog_edit.html',
    'id': blog_id,
    'user': request.__user__ or ''
    }

@get('/api/blog/{id}')
async def api_get_blog(request, *, id):
    blog = await Blog.find(id)
    if(blog):
        return blog
    else:
        raise APIResourceNotFoundError('blog')

@post('/manage/api/blog')
async def api_post_blog(request, *, name, summary, content, id=None):
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    if id:
        blog = await Blog.find(id)
        blog.content = content
        blog.summary = summary
        blog.name = name
        await blog.update()
    else:
        blog = Blog(
            id = next_id(),
            name = name,
            summary = summary,
            content = content,
            user_id = request.__user__.id,
            user_name = request.__user__.name,
            user_image = request.__user__.image
        )
        await blog.save()
    return blog
    
@get('/api/users')
async def api_get_users(request):
    users = await User.findAll(orderBy='created_at desc')
    for u in users:
        u.password = '******'
    return {
        'users': users
    }

@get('/register')
def register(request):
    return {
        '__template__': 'register.html'
    }
    
@get('/signin')
def signin(request):
    return {
        '__template__': 'signin.html'
    }

@get('/signout')
def signout(request):
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
    logging.info('user is signed out')
    return r
    
_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_AUTH = re.compile(r'^[0-9a-f]{40}$')

@post('/api/users')
async def api_register_user(*, email, name, passwd):
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not name or not name.strip():
        raise APIValueError('name')
    if not passwd or not _RE_AUTH.match(passwd):
        raise APIValueError('password')
    users = await User.findAll('email=?', [email])
    if len(users) > 0:
        raise APIError('register:failed', 'email', 'Email is already in use')
    uid = next_id()
    sha1_passwd = '%s:%s' % (uid, passwd)
    user = User(id=uid, email=email, name=name, password=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')))
    await user.save()
    
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    r.content_type = 'application/json'
    user.password = '******'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r
    
@post('/api/authenticate')
async def authenticate(*, email, passwd):
    if not email:
        raise APIValueError('email', 'Invalid email.')
    if not passwd:
        raise APIValueError('password', 'Invalid password.')
    users = await User.findAll('email=?', [email])
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist.')
    user = users[0]
    sha1_pw = hashlib.sha1(('%s:%s' % (user.id, passwd)).encode('utf-8')).hexdigest()
    if sha1_pw != user.password:
        raise APIValueError('password', 'Invalid passsword.')
    
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    r.content_type = 'application/json'
    user.password = '******'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r