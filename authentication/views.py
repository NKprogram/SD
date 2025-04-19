import profile
from django.db.models import Q
from math import e
from operator import is_
from django.views import View
from django.db import models
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Post, Profile, Comment
from django import forms
from .models import PostForm
from commonmark import commonmark
import markdown
import base64
from django.core.files.base import ContentFile
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger



class ProfileView(View):
    def get(self, request, *args, **kwargs):
        profiles = list(Profile.objects.values())
        return JsonResponse(profiles, safe=False)


@login_required
def follow(request):
    user_id = request.POST.get('user_id')
    # Accessing the profile directly
    target_user = get_object_or_404(User, id=user_id).profile
    current_user_profile = request.user.profile

    if target_user in current_user_profile.following.all():
        current_user_profile.following.remove(target_user)
        is_followed = False
    else:
        current_user_profile.following.add(target_user)
        is_followed = True

    return JsonResponse({'is_followed': is_followed})


def home(request):
    if request.user.is_authenticated:
        # find the user profile from profile model
        user_profile = Profile.objects.get(user=request.user)
        user_profile.create_posts_from_github_activity()

        # get all User instances that the current user is following
        following_users = [
            profile.user for profile in user_profile.following.all()]
        # get all posts by the users followed by the current user
        posts_following = Post.objects.filter(user__in=following_users)
        # get the user's own posts
        posts_own = Post.objects.filter(user=request.user)
        # combine and order the posts
        posts = Post.objects.all().order_by('-created')

        for post in posts:
            if post.cm_toggle:
                post.content = markdown.markdown(post.content_markdown)
                post.save()
        if request.user.is_authenticated:
            friend_ids = list(request.user.profile.get_friends().values_list('id', flat=True))
        else:
            friend_ids = []

        # get all other users in the database excluding the current user
        users = Profile.objects.all().exclude(user=request.user)
        followers = user_profile.followers.count()
        following = user_profile.following.count()
        return render(request, "index.html", {'user_profile': user_profile,
                                              'posts_length': len(posts),
                                              'all_user_length': len(users),
                                              'posts': posts, 'is_authenticated': True,
                                              'all_users': users,
                                              'following_users': following_users,
                                              'posts_following': posts_following,
                                              'followers': followers,
                                              'following': following,
                                              })
    return render(request, "index.html")


@login_required
def profilepage(request, username):
    user_profile = get_object_or_404(Profile, user__username=username)
    username = user_profile.user.username
    email = user_profile.user.email
    pfp = user_profile.pfp
    bio = user_profile.bio
    github = user_profile.github
    posts = Post.objects.filter(user=user_profile.user).order_by('-created')
    followers = user_profile.followers.count()
    following = user_profile.following.count()
    friends = user_profile.get_friends()

    context = {
        'profile': user_profile,
        'email': email,
        'username': username,
        'pfp': pfp,
        'bio': bio,
        'github': github,
        'posts': posts,
        'posts_length': len(posts),
        'followers': followers,
        'following': following,
        'friends': friends,  # Add the friends to the context
        'friends_length': len(friends),  # Add the number of friends to the context
    }
    return render(request, "profilepage.html", context)


# @login_required
# def create_post(request):
#     if request.method == 'POST':
#         # get the post content and image from the form
#         post_content_markdown = request.POST.get('content')
#         cm_toggle = 'cm_toggle' in request.POST
#         post_content_html = markdown.markdown(post_content_markdown) if cm_toggle else post_content_markdown
#         image = request.FILES.get('image')
#         # get the user profile
#         user_profile = Profile.objects.get(user=request.user)
#         # create the post
#         Post.objects.create(content=post_content_html, content_markdown = post_content_markdown,
#                             cm_toggle=cm_toggle, image=image,
#                             profile=user_profile, user = request.user
#                             )
#         # link the post to the user profile
#         user_profile.posts.add(Post.objects.last())
#         return redirect('home')

@login_required
def create_post(request):
    if request.method == 'POST':
        post_content_markdown = request.POST.get('content')
        cm_toggle = 'cm_toggle' in request.POST
        print(f'cm_toggle in create_post: {cm_toggle}')  # debug print
        post_content_html = markdown.markdown(post_content_markdown) if cm_toggle else post_content_markdown
        image = request.FILES.get('image')
        if image:
            image_data = image.read()  # read the image data
            # encode the image data to base64
            base64_image = base64.b64encode(image_data).decode('utf-8')

            image_type = image.content_type  # get the image's content type
            # image = ContentFile(base64.b64decode(base64_image), name=image.name)
            image = base64_image

        user_profile = Profile.objects.get(user=request.user)
        visibility = request.POST.get('visibility')
        post = Post.objects.create(visibility=visibility,content=post_content_html, content_markdown=post_content_markdown, 
                                   cm_toggle=cm_toggle, image=image, image_type=image_type, profile=user_profile, user=request.user)
        # print(f'post.cm_toggle after creation: {post.cm_toggle}')  # debug print
        # print(visibility)
        # get the user profile
        # create the post
        # Post.objects.create(visibility=visibility, content=post_content, image=image,
        #                     profile=user_profile, user=request.user)
        # link the post to the user profile
        user_profile.posts.add(Post.objects.last())
        return redirect('home')
    

@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user == post.user:
        post.delete()
    return redirect('home')

# @login_required
# def edit_post(request, post_id):
#     post = get_object_or_404(Post, id=post_id)  # Get the existing post by ID
#     if request.method == "POST":
#         form = PostForm(request.POST, request.FILES, instance=post)  # Notice the instance=post
#         if form.is_valid():
#             form.save()  # This updates the existing post
#             return redirect('home')  # Redirect to home URL
#     else:
#         form = PostForm(instance=post)  # Pre-populate the form with the post's current data
#     return render(request, 'edit_post.html', {'form': form, 'post': post})

# @login_required
# def edit_post(request, post_id):
#     post = get_object_or_404(Post, id=post_id)
#     if request.method == 'POST':
#         # get the post content and cm_toggle from the form
#         post_content_markdown = request.POST.get('content')
#         cm_toggle = 'cm_toggle' in request.POST
#         # convert the post content to HTML if cm_toggle is True
#         post_content_html = markdown.markdown(post_content_markdown) if cm_toggle else post_content_markdown
#         # update the post
#         post.content = post_content_html
#         post.content_markdown = post_content_markdown
#         post.cm_toggle = cm_toggle
#         post.image = request.FILES.get('image')
#         post.save()
#         return redirect('home')
#     form = PostForm(instance=post)
#     return render(request, 'edit_post.html', {'form': form, 'post': post})

@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == 'POST':
        post_content_markdown = request.POST.get('content')
        cm_toggle = 'cm_toggle' in request.POST
        # print(f'cm_toggle in edit_post: {cm_toggle}')  # debug print
        post_content_html = markdown.markdown(post_content_markdown) if cm_toggle else post_content_markdown
        post.content = post_content_html
        post.content_markdown = post_content_markdown
        post.cm_toggle = cm_toggle
        post.image = request.FILES.get('image')
        post.save()
        # print(f'post.cm_toggle after editing: {post.cm_toggle}')  # debug print
        return redirect('home')
    form = PostForm(instance=post)
    return render(request, 'edit_post.html', {'form': form, 'post': post})



# def edit_post(request, post_id):
#     post = get_object_or_404(Post, id=post_id)  # Get the existing post by ID
#     if request.method == "PUT":
#         form = PostForm(request.POST, request.FILES, instance=post)  # Notice the instance=post
#         if form.is_valid():
#             form.save()  # This updates the existing post
#             return redirect('home')  # Redirect to a new URL
#     else:
#         form = PostForm(instance=post)  # Pre-populate the form with the post's current data
#     return render(request, 'edit_post.html', {'post_id': post_id})

# @login_required
# def edit_post(request, post_id):
#     post = get_object_or_404(Post, id=post_id)
#     if request.method == 'POST':
#         form = PostForm(request.POST, request.FILES, instance=post)
#         if form.is_valid():
#             if request.user == post.user:
#                 form.save()
#                 return redirect('home')  # or wherever you want to redirect after editing
#     else:
#         form = PostForm(instance=post)
#     return render(request, 'edit_post.html', {'form': form})

@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user in post.likes.all():
        post.likes.remove(request.user)
        user_likes = False
    else:
        post.likes.add(request.user)
        user_likes = True
    return JsonResponse({'like_count': post.likes.count(), 'user_likes': user_likes})

@login_required
def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    comments = Comment.objects.filter(post=post)
    return render(request, 'post_detail.html', {'post': post, 'comments': comments})


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    comment_content = request.POST.get('content')
    Comment.objects.create(user=request.user, post=post,
                           content=comment_content)
    return redirect('post_detail', post_id=post.id)

@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if request.user == comment.user:
        comment.delete()
    return redirect('post_detail', post_id=comment.post.id)

def signin(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        authenticated_user = authenticate(username=username, password=password)
        if authenticated_user is not None:
            login(request, authenticated_user)
            messages.success(request, 'Logged In successfully')
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password')
            return redirect('home')
    return render(request, "signin.html")


def signout(request):
    if not request.user.is_authenticated:
        messages.error(request, 'You are not logged in')
        return redirect('home')
    else:
        logout(request)
        messages.success(request, 'Logged out successfully')
        return redirect('home')


def signup(request):
    if request.method == 'POST':
        displayname = request.POST.get('displayname')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        bio = request.POST.get('bio')
        github = request.POST.get('github')
        pfp = request.POST.get('pfp')
        myuser = User.objects.create_user(
            username, email, password, is_active=False, is_staff=False)
        myprofile = Profile.objects.create(
            user=myuser, displayname=displayname, bio=bio, github=github, pfp=pfp)
        myprofile.save()
        messages.success(request, 'Your account has been created successfully')
        return redirect('home')
    return render(request, "signup.html")

@login_required
def update_profile(request):
    if request.method == 'POST':
        user = request.user
        profile = user.profile

        user.email = request.POST.get('email')
        profile.displayname = request.POST.get('displayname')
        profile.bio = request.POST.get('bio')
        profile.github = request.POST.get('github')
        profile.pfp = request.POST.get('pfp')

        user.save()
        profile.save()

        return redirect('profile', username=user.username)

def user_search(request):
    current_user = request.user
    query = request.GET.get('q', '')
    if query:
        users = Profile.objects.filter(user__username__icontains=query).exclude(
            user=current_user)
        # Collect the IDs of users that the current user is following
        following_ids = current_user.profile.following.values_list(
            'user__id', flat=True)
    else:
        users = Profile.objects.none()
        following_ids = []

    return render(request, 'search.html', {
        'all_users': users,
        'all_user_length': users.count(),
        'following_ids': following_ids  # Add this line
    })

def all_users(request):
    all_users_list = Profile.objects.all().exclude(user=request.user)
    paginator = Paginator(all_users_list, 10)  # Show 10 users per page

    page = request.GET.get('page')
    try:
        users = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        users = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        users = paginator.page(paginator.num_pages)

    return render(request, 'authors.html', {'users': users, 'page_obj': users})  # Pass 'page_obj' to the context

