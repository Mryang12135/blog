from django.shortcuts import render,HttpResponse,redirect,reverse
from django.http import JsonResponse
from app01 import myforms
from app01 import models
from django.contrib import auth
import random
from io import BytesIO
from PIL import Image,ImageDraw,ImageFont
from django.contrib.auth.decorators import login_required
from utils.mypage import Pagination
from django.utils.safestring import mark_safe
import json
from django.db.models import F
from django.db import transaction
from bs4 import BeautifulSoup
# Create your views here.
def register(request):
    #产生一个空对象
    form_obj = myforms.MyRegFrom()
    if request.method == 'POST':
        black_dic = {'code': 1000, 'msg': ''}
        #校验数据
        form_obj = myforms.MyRegFrom(request.POST)
        if form_obj.is_valid():
            clean_data = form_obj.cleaned_data
            clean_data.pop('confirm_password')
            file_obj = request.FILES.get('avatar')
            blog = models.Blog.objects.create()
            print(blog.id)
            #判断用户是否上传对象
            if file_obj:
                clean_data['avatar'] = file_obj
            user = models.UserInfo.objects.create_user(**clean_data)
            user.blog = blog
            user.save()
            black_dic['url'] = 'http://127.0.0.1:8009/'
        else:
            black_dic['code'] = 2000
            black_dic['msg'] = form_obj.errors
        return JsonResponse(black_dic)
    return render(request,'register.html',locals())
# @load_backend
def login(request):
    if request.method == 'POST':
        back_dic = {'code':1000,'msg':''}
        username = request.POST.get('username')
        password = request.POST.get('password')
        code = request.POST.get('code')
        #校验验证码是否正确
        if request.session.get('code').upper() == code.upper():
            #校验用户名密码是否正确
            user_obj = auth.authenticate(username=username,password=password)
            if user_obj:
                #保存登录状态
                auth.login(request,user_obj)
                back_dic['url'] = 'http://127.0.0.1:8009/'
            else:
                back_dic['code'] = 2000
                back_dic['msg'] = '用户名或密码错误'
        else:
            back_dic['code'] = 3000
            back_dic['msg'] = '验证码错误'
        return JsonResponse(back_dic)
    return render(request,'login.html')
#随机验证码
def get_random():
    return random.randint(0,255),random.randint(0,255),random.randint(0,255)
#图片验证码
def get_code(request):
    img_obj=Image.new('RGB',(310,35),get_random())
    img_draw = ImageDraw.Draw(img_obj)#画笔对象
    img_font = ImageFont.truetype('static/font/222.ttf',30)
    code = ''
    for i in range(5):
        random_upper = chr(random.randint(65,90))
        random_lower = chr(random.randint(97,122))
        random_int = str(random.randint(0,9))
        temp = random.choice([random_upper,random_lower,random_int])
        img_draw.text((i*45+45,0),temp,get_random(),img_font)
        code += temp
    print(code)
    request.session['code']= code
    io_obj = BytesIO()
    img_obj.save(io_obj,'png')
    return HttpResponse(io_obj.getvalue())
#首页
def home(request):
    article_list = models.Article.objects.all()
    page_obj = Pagination(current_page=request.GET.get('page',1),all_count=article_list.count())
    page_queryset = article_list[page_obj.start:page_obj.end]
    return render(request,'home.html',locals())
@login_required()
def logout(request):
    #删除用户session数据
    auth.logout(request)
    return redirect('http://127.0.0.1:8009/')
#修改密码
@login_required()
def set_password(request):
    if request.is_ajax():
        back_dic = {'code':1000,'mag':''}
        if request.method=='POST':
            old_password = request.POST.get('old_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            #校验两次密码是否一致
            if new_password == confirm_password:
                #先校验旧密码
                is_right = request.user.check_password(old_password)
                if is_right:
                    request.user.set_password(new_password)
                    request.user.save()
                    back_dic['url'] = 'http://127.0.0.1:8009/'
                else:
                    back_dic['code'] = 2000
                    back_dic['mag'] = '原密码错误'
            else:
                back_dic['code'] = 3000
                back_dic['msg'] = '两次密码不一致'
            return JsonResponse(back_dic)
#侧边栏筛选功能
def site(request,username,**kwargs):
    user_obj = models.UserInfo.objects.filter(username=username).first()
    if not user_obj:
        return render(request, 'error.html')
    blog = user_obj.blog
    print(blog)
    article_list = models.Article.objects.filter(blog=blog)
    if kwargs:
        condition = kwargs.get('condition')
        param = kwargs.get('param')
        print(param)
        if condition == 'category':
            article_list = article_list.filter(category=param)
        elif condition == 'tag':
            article_list = article_list.filter(tags__pk=param)
        else:
            year, month = param.split('-')
            article_list = article_list.filter(create_time__year=year, create_time__month=month)
    return render(request, 'site.html', locals())

#文章
def article_detail(request,article_id,username):
    article_obj = models.Article.objects.filter(pk=article_id).first()
    comment_list = models.Comment.objects.filter(article=article_obj)
    return render(request,'article_detail.html',locals())

#评论
def comment(request):
    print(1)
    if request.is_ajax():
        print(23)
        if request.method == 'POST':
            back_dic = {'code':1000,'msg':''}
            article_id = request.POST.get('article_id')
            content = request.POST.get('content')
            parent_id = request.POST.get('parent_id')
            print(article_id,content,parent_id)
            with transaction.atomic():
                models.Article.objects.filter(pk=article_id).update(comment_num = F("comment_num") + 1)
                models.Comment.objects.create(user=request.user,article_id=article_id,content=content,parent_id=parent_id)
            back_dic['msg'] = '评论成功'
            return JsonResponse(back_dic)

#点赞点踩
def UpAndDown(request):

    if request.is_ajax():
        if request.method == 'POST':
            back_dic = {'code': 1000, 'msg': ''}
            # 判断当前用户是否登录
            if request.user.is_authenticated():
                article_id = request.POST.get('article_id')
                is_up = request.POST.get('is_up')
                is_up = json.loads(is_up)
                # 判断当前文章是否是当前用户自己写的
                article_obj = models.Article.objects.filter(pk=article_id).first()
                if not article_obj.blog.userinfo == request.user:
                    # 校验当前用户是否已经点过了
                    is_click = models.UpAndDown.objects.filter(user=request.user, article=article_obj)
                    if not is_click:
                        # 操作数据库 更新记录
                        # 判断用户是点了赞 还是点了踩 从而决定到底给哪个普通字段加一
                        if is_up:
                            models.Article.objects.filter(pk=article_id).update(up_num=F('up_num') + 1)
                            back_dic['msg'] = '点赞成功'
                        else:
                            models.Article.objects.filter(pk=article_id).update(down_num=F('down_num') + 1)
                            back_dic['msg'] = '点踩成功'
                        # 真正的操作 点赞点踩表
                        models.UpAndDown.objects.create(user=request.user, article=article_obj, is_up=is_up)
                    else:
                        back_dic['code'] = 1001
                        back_dic['msg'] = '已经点过了'
                else:
                    back_dic['code'] = 1002
                    back_dic['msg'] = '不能给自己点'
            else:
                back_dic['code'] = 1003
                back_dic['msg'] = mark_safe('请先<a href="/login/">登录</a>')
            return JsonResponse(back_dic)

@login_required
def backend(request):
    # 获取当前用户所有的文章
    article_list = models.Article.objects.filter(blog=request.user.blog)
    return render(request,'backend/backend.html',locals())

def add_article(request):
    if request.method == "POST":
        title = request.POST.get('title')
        content = request.POST.get('content')
        category_id = request.POST.get('category')
        tag_list = request.POST.getlist('tag')

        # 先生成一个对象
        soup = BeautifulSoup(content,'html.parser')
        tags = soup.find_all()  # tags 是所有的标签
        for tag in tags:
        #     # tag.name取到标签的名字
        #     print(tag.name)
            if tag.name == 'script':  # # 取出script标签，删除
                tag.decompose()
        # 文章简介
        # 先简单粗暴 截150个字符串
        # desc = content[0:150]
        # 先获取文章文本内容  再截取150个字符
        desc = soup.text[0:150]
        article_obj = models.Article.objects.create(title=title,desc=desc,content=str(soup),category_id=category_id,blog=request.user.blog)
        # 关系表是我们自己建的 没法使用add set等方法
        tag_article_list = []
        for i in tag_list:
            tag_article_list.append(models.Article2Tag(article=article_obj,tag_id=i))
        # 批量插入数据
        print(tag_article_list)
        models.Article2Tag.objects.bulk_create(tag_article_list)
        return redirect('/backend/')
    category_list = models.Category.objects.filter(blog=request.user.blog)
    tag_list = models.Tag.objects.filter(blog=request.user.blog)
    print(tag_list)
    print(request.user.blog)
    print(category_list)

    return render(request,'backend/add_article.html',locals())

import os
from blog import settings
def upload_img(request):
    if request.method == 'POST':
        back_dic = {'error': 0, 'message': ''}
        file_obj = request.FILES.get('imgFile')
        file_dir = os.path.join(settings.BASE_DIR, 'media', 'article_img')
        if not os.path.isdir(file_dir):
            os.mkdir(file_dir)  # 自动创建文件夹
        file_path = os.path.join(file_dir, file_obj.name)  # 拼接文件路径
        with open(file_path, 'wb') as f:
            for line in file_obj:
                f.write(line)

        back_dic['url'] = '/media/article_img/%s' % file_obj.name
        return JsonResponse(back_dic)

def great(request,username):
    user_obj = models.UserInfo.objects.filter(username=username).first()
    if not user_obj:
        return render(request, 'error.html')
    blog = user_obj.blog
    print(blog)
    article_list = models.Article.objects.filter(blog=blog)
    return render(request,'great.html',locals())

def tag(request):
    blog = request.user.blog
    if request.method == 'POST':
        back_dic = {'code': 1000, 'msg': ''}
        tag = request.POST.get('tag')
        tag = models.Tag.objects.create(name=tag,blog=blog)
        if tag:
            back_dic['url'] = 'http://127.0.0.1:8009/add_article/'
        else:
            back_dic['code'] = 2000
            back_dic['mag'] = '创建失败'
        return JsonResponse(back_dic)
def category(request):
    blog = request.user.blog


    if request.method == 'POST':
        back_dic = {'code': 1000, 'msg': ''}
        category = request.POST.get('category')
        category = models.Category.objects.create(name=category,blog=blog)
        if category:
            back_dic['url'] = 'http://127.0.0.1:8009/add_article/'
        else:
            back_dic['code'] = 2000
            back_dic['mag'] = '创建失败'
        return JsonResponse(back_dic)