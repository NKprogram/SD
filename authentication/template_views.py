# authentication/template_views.py
import profile
from django.db.models import Q
from math import e
import requests
from operator import is_
from requests.auth import HTTPBasicAuth as HTTP

from django.views import View
from django.db import models
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, Http404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from .models import FollowRequest, Node, Post, Profile, Comment, Notification
from django import forms
from .models import PostForm
import markdown
from django.templatetags.static import static
from django.core.files.base import ContentFile
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from rest_framework import viewsets, status, mixins
from .models import Profile, Post, Comment
from .serializers import ProfileSerializer, CommentSerializer, PostSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import permissions
from rest_framework.pagination import PageNumberPagination
from django.urls import reverse


FREE_IMAGE_HOST_KEY = '6d207e02198a847aa98d0a2a901485a5'

CM_EMOJIS = {
    ':angry:': static('cm-emojis/angry.png'),
    ':bicycle:': static('cm-emojis/bicycle.png'),
    ':chef:': static('cm-emojis/chef.png'),
    ':deaf:': static('cm-emojis/deaf.png'),
    ':depression:': static('cm-emojis/depression.png'),
    ':devious:': static('cm-emojis/devious.png'),
    ':disgust:': static('cm-emojis/disgust.png'),
    ':fight:': static('cm-emojis/fight.png'),
    ':funny:': static('cm-emojis/funny.png'),
    ':goodbye:': static('cm-emojis/goodbye.png'),
    ':jojothinking:': static('cm-emojis/jojothinking.png'),
    ':looking:': static('cm-emojis/looking.png'),
    ':love:': static('cm-emojis/love.png'),
    ':mischievous:': static('cm-emojis/mischievous.png'),
    ':nerd:': static('cm-emojis/nerd.png'),
    ':pet:': static('cm-emojis/pet.gif'),
    ':pray:': static('cm-emojis/pray.png'),
    ':sad:': static('cm-emojis/sad.png'),
    ':shrug:': static('cm-emojis/shrug.png'),
    ':stare:': static('cm-emojis/stare.png'),
    ':sunglasses:': static('cm-emojis/sunglasses.gif'),
    ':swag:': static('cm-emojis/swag.png'),
    ':waiting:': static('cm-emojis/waiting.png'),
    ':walk:': static('cm-emojis/walk.gif'),
}
nodes = Node.objects.filter(is_active=True)


@login_required
def accept_follow_request(request, notification_id):
    notification = get_object_or_404(
        Notification, id=notification_id, recipient=request.user, type='follow')
    sender = notification.sender
    receiver = request.user

    # Add the sender to the receiver's followers
    receiver.profile.following.add(sender.profile)
    # Delete the notification
    notification.delete()

    return redirect('notifications_view')


@login_required
def deny_follow_request(request, notification_id):
    notification = get_object_or_404(
        Notification, id=notification_id, recipient=request.user, type='follow')
    # Simply delete the notification
    notification.delete()

    return redirect('notifications_view')


@login_required
def follow(request):
    user_id = request.POST.get('user_id')
    target_user = get_object_or_404(User, id=user_id)
    current_user = request.user

    # Check if a follow request already exists or if the current user is already following the target user
    if FollowRequest.objects.filter(sender=current_user, receiver=target_user).exists() or \
       current_user.profile.following.filter(id=target_user.profile.id).exists():
        return JsonResponse({'error': 'Follow request already sent or you are already following this user.'}, status=400)

    # Create a follow request
    FollowRequest.objects.create(sender=current_user, receiver=target_user)
    # Create a notification for the follow request
    Notification.objects.create(
        recipient=target_user,
        sender=current_user,
        type='follow',
        # You might want to add a reference to the FollowRequest object if you modify the Notification model to include it
    )

    return JsonResponse({'message': 'Follow request sent.'})


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
        friend_ids = list(
            request.user.profile.get_friends().values_list('id', flat=True))
        following_ids = list(
            request.user.profile.following.values_list('user__id', flat=True))
        # if request.user.is_authenticated:
        #     friend_ids = list(request.user.profile.get_friends().values_list('id', flat=True))
        # else:
        #     friend_ids = []

        # get all other users in the database excluding the current user
        users = Profile.objects.all().exclude(user=request.user)
        followers = user_profile.followers.count()
        following = user_profile.following.count()
        notifications = Notification.objects.filter(
            recipient=request.user).order_by('-created')
        unread_notifications_count = Notification.objects.filter(
            recipient=request.user, is_read=False).count()

        return render(request, "index.html", {'user_profile': user_profile,
                                              'posts_length': len(posts),
                                              'all_user_length': len(users),
                                              'posts': posts, 'is_authenticated': True,
                                              'all_users': users,
                                              'following_users': following_users,
                                              'posts_following': posts_following,
                                              'followers': followers,
                                              'following': following,
                                              'friend_ids': friend_ids,
                                              'cm_emojis': CM_EMOJIS,
                                              'following_ids': following_ids,
                                              'notifications': notifications,
                                              'unread_notifications_count': unread_notifications_count,
                                              'nodes': nodes,
                                              })
    return render(request, "index.html")


@login_required
def profilepage(request, username):
    try:
        # Try to fetch the profile locally first
        user_profile = Profile.objects.get(user__username=username)
    except Profile.DoesNotExist:
        # Profile not found locally, try fetching from remote nodes
        user_profile = None
        for node in Node.objects.filter(is_active=True):
            try:
                # Assuming username is sufficient to identify the user
                url = f"{node.host_url}api/authors/{username}"
                print(f"Fetching profile from {url}")
                response = requests.get(
                    url, auth=HTTP(node.username, node.password))
                if response.status_code == 200:
                    # Assuming the response contains the profile data in a compatible format
                    profile_data = response.json()
                    # Since the profile is remote, adjust your context accordingly
                    # This might involve setting flags to conditionally display data or messages in the template
                    user_profile = profile_data
                    break
            except requests.RequestException:
                continue
    if not user_profile:
        # If the profile is neither local nor found in any remote node
        raise Http404("Profile not found")
    if isinstance(user_profile, dict):
        print('Remote profile data:', user_profile)
        # Handle rendering for a remote user profile
        context = {
            # Adapt this according to the structure of your remote profile data
            'profile': user_profile,
            'email': user_profile.get('email', ''),
            'username': user_profile.get('username', ''),
            'posts': user_profile.get('posts', []),
            'posts_length': len(user_profile.get('posts', [])),
            'followers': user_profile.get('followers', 0),
            'following': user_profile.get('following', 0),
            'friends': [],
            'friends_length': 0,
            'cm_emojis': CM_EMOJIS,
            'friend_ids': [],
            'nodes': nodes,
            'is_remote': True,  # You can use this flag to conditionally render parts of your template
        }
        return render(request, "profilepage.html", context)
    else:
        print('Local profile data:', user_profile)
        # Handle rendering for a local user profile
        posts = Post.objects.filter(
            user=user_profile.user).order_by('-created')
        followers = user_profile.followers.count()
        following = user_profile.following.count()
        friends = user_profile.get_friends()
        friend_ids = [friend.user.id for friend in friends]

        context = {
            'profile': user_profile,
            'email': user_profile.user.email,
            'username': username,
            'profileImage': user_profile.profileImage,
            'bio': user_profile.bio,
            'github': user_profile.github,
            'posts': posts,
            'posts_length': len(posts),
            'followers': followers,
            'following': following,
            'friends': friends,
            'friends_length': len(friends),
            'cm_emojis': CM_EMOJIS,
            'friend_ids': friend_ids,
            'nodes': nodes,
            'is_remote': False,
        }
        return render(request, "profilepage.html", context)


def are_friends(user1, user2):
    return user1.profile.following.filter(id=user2.profile.id).exists() and user2.profile.following.filter(id=user1.profile.id).exists()


@login_required
def create_post(request):
    if request.method == 'POST':
        post_content_markdown = request.POST.get('content')
        cm_toggle = 'cm_toggle' in request.POST
        post_content_html = markdown.markdown(
            post_content_markdown) if cm_toggle else post_content_markdown
        image = request.FILES.get('image')
        image_url = None  # Default value for image URL

        if image:
            # Assumes an existing function to upload images
            image_url = upload_image(image)
            if image_url is None:
                return JsonResponse({'error': 'Failed to upload image'}, status=400)

        visibility = request.POST.get('visibility')

        # Create the post
        post = Post.objects.create(
            user=request.user,
            profile=request.user.profile,
            content=post_content_html,
            content_markdown=post_content_markdown,
            cm_toggle=cm_toggle,
            image=image_url,
            visibility=visibility,
        )

        # Skip notification creation for "unlisted" posts
        if post.visibility == 'unlisted':
            return redirect('home')

        # For public or private posts, decide who should receive a notification
        if post.visibility in ['public', 'private']:
            potential_recipients = set(
                request.user.profile.followers.all() | request.user.profile.get_friends())

            for profile in potential_recipients:
                # For private posts, ensure the recipient is a friend
                if post.visibility == 'private' and not are_friends(request.user, profile.user):
                    continue  # Skip non-friends for private posts

                # Create notification for eligible recipients, excluding the post's author
                if profile.user != request.user:
                    Notification.objects.create(
                        recipient=profile.user,
                        sender=request.user,
                        type='post',
                        post=post
                    )

        return redirect('home')


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user == post.user:
        post.delete()
    return redirect('home')


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    # Check if the current user is the author of the post
    if request.user.profile != post.profile:
        # If not, dont allow the user to edit the post
        return JsonResponse({'error': 'You are not authorized to edit this post'}, status=403)

    if request.method == 'POST':
        post_content_markdown = request.POST.get('content')
        cm_toggle = 'cm_toggle' in request.POST
        post_content_html = markdown.markdown(
            post_content_markdown) if cm_toggle else post_content_markdown
        post.content = post_content_html
        post.content_markdown = post_content_markdown
        post.cm_toggle = cm_toggle
        post.image = request.FILES.get('image')

        if post.image:
            # Upload the image to host api and get the URL of the uploaded image
            image_url = upload_image(post.image)
            if image_url is None:
                return JsonResponse({'error': 'Failed to upload image'}, status=400)
            post.image = image_url

        post.save()
        return redirect('home')
    form = PostForm(instance=post)
    return render(request, 'edit_post.html', {'form': form, 'post': post, 'nodes': nodes, })


@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    user = request.user
    if user in post.likes.all():
        post.likes.remove(user)
        user_likes = False
    else:
        post.likes.add(user)
        user_likes = True
        # Create a notification for a new like, excluding self-likes
        if post.user != user:
            Notification.objects.create(
                recipient=post.user,
                sender=user,
                type='like',
                post=post
            )
    return JsonResponse({'like_count': post.likes.count(), 'user_likes': user_likes})


@login_required
def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    # If the post is private, ensure the viewer is a friend of the post owner or the owner themselves
    if post.visibility == 'private':
        if not are_friends(request.user, post.user) and request.user != post.user:
            # Respond with an error if the user does not have permission to view the post
            return JsonResponse({'error': 'You do not have permission to view this post'}, status=403)

    # For public and unlisted posts, or if the viewer is authorized, display the post
    comments = Comment.objects.filter(post=post)

    # Convert Markdown content to HTML if the CommonMark toggle is enabled
    # This assumes your application supports Markdown and you wish to render it
    if post.cm_toggle:
        post.content = markdown.markdown(post.content_markdown)

    # Render the post detail page with the post and its comments
    return render(request, 'post_detail.html', {
        'post': post,
        'comments': comments,
        'nodes': nodes,
        'cm_emojis': CM_EMOJIS,
    })


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    comment_content = request.POST.get('content')
    cm_toggle_comment = 'cm_toggle_comment' in request.POST
    comment_content_html = markdown.markdown(
        comment_content) if cm_toggle_comment else comment_content

    Comment.objects.create(user=request.user, post=post,
                           content=comment_content_html, cm_toggle_comment=cm_toggle_comment)
    # Create a notification for the new comment, excluding self-comments
    if post.user != request.user:
        Notification.objects.create(
            recipient=post.user,
            sender=request.user,
            type='comment',
            post=post
        )
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
        displayName = request.POST.get('displayName')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        bio = request.POST.get('bio')
        github = request.POST.get('github')
        profileImage = request.POST.get('profileImage')
        profileImage = profileImage if profileImage else 'https://i.ibb.co/C7zzTBM/depositphotos-137014128-stock-illustration-user-profile-icon.webp'
        myuser = User.objects.create_user(
            username, email, password, is_active=False, is_staff=False)
        myprofile = Profile.objects.create(
            user=myuser, displayName=displayName, bio=bio, github=github, profileImage=profileImage)

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
        profile.displayName = request.POST.get('displayName')
        profile.bio = request.POST.get('bio')
        profile.github = request.POST.get('github')
        profile.profileImage = request.POST.get('profileImage')

        user.save()
        profile.save()

        return redirect('profile', username=user.username)


def user_search(request):
    query = request.GET.get('q', '')
    page = request.GET.get('page', 1)
    combined_list = []

    if query:
        # Fetch local users matching the query
        local_users = Profile.objects.filter(
            user__username__icontains=query, user__is_active=True).exclude(user=request.user)
        # add extra fields to the local users
        combined_list.extend(list(local_users.values(
            'user__id', 'user__username', 'user__email', 'profileImage').annotate(is_remote=models.Value(False, models.BooleanField()))))

        # Attempt to fetch remote users
        for node in Node.objects.filter(is_active=True):
            try:
                response = requests.get(
                    f"{node.host_url}/api/authors", auth=(node.username, node.password))
                if response.status_code == 200:
                    remote_authors = response.json().get('items', [])
                    for author in remote_authors:
                        if query.lower() in author.get('displayName', '').lower():
                            combined_list.append({
                                'user__id': author['id'],
                                'user__username': author.get('displayName', 'Unknown'),
                                'is_remote': True,
                                'user__database_id': author['database_id'],
                                'user__email': '',  # Placeholder, as remote authors might not have an email
                                'profileImage': author.get('profileImage', ''),
                            })
            except requests.RequestException as e:
                print(f"Error fetching data from {node.host_url}: {e}")

    # Handle pagination
    paginator = Paginator(combined_list, 10)
    try:
        users = paginator.page(page)
    except PageNotAnInteger:
        users = paginator.page(1)
    except EmptyPage:
        users = paginator.page(paginator.num_pages)

    # Get following ids for the current user
    if request.user.is_authenticated:
        following_ids = request.user.profile.following.values_list(
            'user__id', flat=True)
    else:
        following_ids = []

    return render(request, 'search.html', {
        'all_users': users,
        'following_ids': following_ids,
    })


def all_users(request):
    local_users_list = Profile.objects.filter(
        user__is_active=True
    ).exclude(user=request.user).values(
        'user__id', 'user__username', 'user__email', 'profileImage'
    )

    # Start with local users converted to a list of dictionaries
    combined_list = list(local_users_list)

    for node in Node.objects.filter(is_active=True):
        try:
            response = requests.get(
                f"{node.host_url}/api/authors",
                auth=HTTP(node.username, node.password)
            )
            print(f"CODE:{response.status_code}, Fetching data from {node.host_url}/api/authors")
            print(response.json())
            if response.status_code == 200:
                external_authors_data = response.json()
                # Assuming the structure you provided, navigate to the "items"
                print('\nextauthors: ', external_authors_data['items'])
                for author in external_authors_data['items']:
                    # Map external author data to match the local user structure
                    mapped_author = {}
                    # if author['displayName']:
                    mapped_author = {
                        # or a suitable placeholder
                        'user__id': author['id'],
                        'user__username': author['displayName'],
                        'user__email': '',  # Placeholder, as external authors might not have an email
                        # Adjust based on actual keys
                        'profileImage': author['profileImage'] if author['profileImage'] else '',
                        'user__database_id': author['database_id'],
                        'is_remote': True,
                    }
                    combined_list.append(mapped_author)
                    print(f'Added {mapped_author["user__username"]} from {node.host_url}')
        except requests.RequestException as e:
            print(f"Error fetching data from {node.host_url}: {e}")
    paginator = Paginator(combined_list, 10)  # Show 10 users per page
    page = request.GET.get('page')

    try:
        users = paginator.page(page)
    except PageNotAnInteger:
        users = paginator.page(1)
    except EmptyPage:
        users = paginator.page(paginator.num_pages)

    following_ids = request.user.profile.following.values_list('id', flat=True)

    return render(request, 'authors.html', {
        'users': users,
        'page_obj': users,
        'following_ids': following_ids,
    })


def upload_image(image_file):
    # Save the image file temporarily
    file_path = default_storage.save(
        'tmp/' + image_file.name, ContentFile(image_file.read()))

    # Prepare request parameters and files
    # Replace with actual API key management
    data = {'key': FREE_IMAGE_HOST_KEY, 'format': 'json'}
    files = {'source': open(file_path, 'rb')}

    # Send POST request
    try:
        response = requests.post(
            'https://freeimage.host/api/1/upload', data=data, files=files)
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('status_code') == 200 and response_data.get('status_txt') == 'OK':
                image_url = response_data.get('image', {}).get('url')
                return image_url
            else:
                # Handle API error
                return None
        else:
            # Handle HTTP error
            return None
    finally:
        files['source'].close()
        default_storage.delete(file_path)  # Delete the temporary file


@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(
        recipient=request.user, is_read=False).order_by('-created')
    return render(request, "notifications.html", {'notifications': notifications})


@login_required
def like_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    user = request.user
    if user in comment.likes.all():
        comment.likes.remove(user)
        liked = False
    else:
        comment.likes.add(user)
        liked = True
    return JsonResponse({'liked': liked, 'likes_count': comment.likes.count()})


@login_required
def unlike_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    user = request.user
    if user in comment.likes.all():
        comment.likes.remove(user)
    return redirect('wherever_you_want_to_redirect')


@login_required
def mark_all_notifications_as_read(request):
    # Update all notifications where the current user is the recipient to be marked as read
    Notification.objects.filter(
        recipient=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})


@login_required
def get_unread_notifications_count(request):
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({'count': count})

# pass in the list of all nodes with their link username and password to fetch data from them
