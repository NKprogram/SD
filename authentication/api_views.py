# authentication/api_views.py

from pydoc import visiblename
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q
from django.views import View
from django.db import models
from django.conf import settings
from django.http import HttpResponse, JsonResponse, Http404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from .models import Post, Profile, Comment, Notification
from django import forms
from .models import PostForm
import markdown
from django.templatetags.static import static
from django.core.files.base import ContentFile
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from rest_framework import viewsets, status, mixins, generics
from .models import Profile, Post, Comment
from .serializers import ProfileSerializer, CommentSerializer, PostSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.authentication import BasicAuthentication
from django.db import connection
from django.urls import reverse

from drf_yasg.utils import swagger_auto_schema

##### START OF APIs #####

class CustomProfilePagination(PageNumberPagination):
    page_size = 10  # Default page size
    page_size_query_param = 'size'

    def get_paginated_response(self, data):
        return Response({
            'type': 'authors',
            'items': data,
        })

class ProfileViewSet(mixins.UpdateModelMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    pagination_class = CustomProfilePagination
    authentication_classes = [BasicAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    @swagger_auto_schema(responses={200: ProfileSerializer(many=True)})
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(request_body=ProfileSerializer)
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            'type': 'author',
            'id': request.build_absolute_uri(reverse('profile', kwargs={'username': instance.user.username})),
            'host': f"{request.scheme}://{request.get_host()}/",
            'displayName': instance.displayName,
            'url': request.build_absolute_uri(reverse('profile', kwargs={'username': instance.user.username})),
            'github': instance.github,
            'profileImage': request.build_absolute_uri(instance.pfp),
        })


class FollowersViewSet(viewsets.GenericViewSet):
    serializer_class = ProfileSerializer
    authentication_classes = [BasicAuthentication]
    permission_classes = [IsAuthenticated, ]

    def list(self, request, author_id=None):
        author = get_object_or_404(Profile, id=author_id)
        followers = author.followers.all()
        serializer = self.get_serializer(followers, many=True)
        return Response({
            'type': 'followers',
            'items': serializer.data,
        })

    def retrieve(self, request, author_id=None, foreign_author_id=None):
        author = get_object_or_404(Profile, id=author_id)
        foreign_author = get_object_or_404(Profile, id=foreign_author_id)
        if foreign_author not in author.followers.all():
            raise Http404
        serializer = self.get_serializer(foreign_author)
        return Response(serializer.data)

    def create(self, request, author_id=None, foreign_author_id=None):
        author = get_object_or_404(Profile, id=author_id)
        foreign_author = get_object_or_404(Profile, id=foreign_author_id)
        author.followers.add(foreign_author)
        return Response(status=status.HTTP_200_OK)

    def destroy(self, request, author_id=None, foreign_author_id=None):
        author = get_object_or_404(Profile, id=author_id)
        foreign_author = get_object_or_404(Profile, id=foreign_author_id)
        author.followers.remove(foreign_author)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated] 

    # DELETE method for posts
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check if the authenticated user is the author of the post
        if request.user.profile != instance.profile:
            return Response({"error": "You are not authorized to delete this post"}, status=status.HTTP_403_FORBIDDEN)

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class CommentsViewSet(viewsets.GenericViewSet):
    serializer_class = CommentSerializer
    authentication_classes = [BasicAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    def list(self, request, author_id=None, post_id=None):
        post = get_object_or_404(Post, id=post_id, profile__id=author_id)
        comments = post.comments.all()
        serializer = self.get_serializer(comments, many=True)
        return Response({
            'type': 'comments',
            'page': 1,
            'size': len(comments),
            'post': request.build_absolute_uri(post.get_absolute_url()),
            'id': request.build_absolute_uri(reverse('comments-list', args=[author_id, post_id])),
            'comments': serializer.data,
        })

    def retrieve(self, request, author_id=None, post_id=None, pk=None):
        comment = get_object_or_404(
            Comment, id=pk, post__id=post_id, post__profile__id=author_id)
        serializer = self.get_serializer(comment)
        return Response(serializer.data)

    def create(self, request, author_id=None, post_id=None):
        post = get_object_or_404(Post, id=post_id, profile__id=author_id)
        # create a copy of the data to avoid modifying the original data
        comment_data = request.data.copy()
        comment_data['post'] = post.id
        comment_data['author'] = request.user.profile.id
        serializer = self.get_serializer(data=comment_data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LikedPostsView(generics.ListAPIView):
    serializer_class = PostSerializer

    def get_queryset(self):
        user_id = self.kwargs['author_id']
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT post_id FROM authentication_post_likes
                WHERE user_id = %s
            """, [user_id])
            post_ids = [row[0] for row in cursor.fetchall()]
        return Post.objects.filter(id__in=post_ids, visibility='public')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = PostSerializer(
            queryset, many=True, context={'request': request})
        user_id = self.kwargs['author_id']
        profile = get_object_or_404(Profile, user__id=user_id)
        profile_serializer = ProfileSerializer(
            profile, context={'request': request})
        return Response({
            "type": "liked",
            "items": [
                {
                    "summary": f"{profile.user.username} Likes your post",
                    "type": "Like",
                    "author": profile_serializer.data,
                    "object": serializer.context['request'].build_absolute_uri(reverse('post-detail', args=[post['id']]))
                } for post in serializer.data
            ]
        })

##### END OF APIs #####

## Swagger API Documentation

class RegisterView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email')
        user = User.objects.create_user(
            username=username, password=password, email=email, is_active=False)
        user.save()
        profile = Profile.objects.create(user=user)
        profile.save()
        return Response(status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = (permissions.AllowAny, )

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)

        if user is None:
            return Response({'error': 'Invalid username or password'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_200_OK)


##### END OF APIs #####


class InboxView(APIView):
    authentication_classes = [BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, author_id):
        # Assuming 'author_id' corresponds to a Profile ID
        profile = get_object_or_404(Profile, id=author_id)

        # Fetch posts from followed users
        followed_users_profiles = profile.following.all()
        posts = Post.objects.filter(
            profile__in=followed_users_profiles).order_by('-created')

        # Serialize posts
        serialized_posts = PostSerializer(
            posts, many=True, context={'request': request}).data

        # Construct the inbox items list, simulating the structure you've provided
        inbox_items = []
        for post in serialized_posts:
            post_data = {
                "type": "post",
                # Example title from post content
                "title": post.get('content'),
                "id": request.build_absolute_uri(reverse('post-detail', args=[post['id']])),
                # Adjust based on your model/needs
                "source": post.get('source', ''),
                # Adjust based on your model/needs
                "origin": post.get('origin', ''),
                # Short description from content
                "description": post.get('content'),
                "contentType": "text/markdown" if post["cm_toggle"] else "text/plain",
                "content": post['content'],
                "author": {
                    # Assuming author info is part of serialized post data
                    "type": "author",
                    "id": post['profile']['id'],
                    "host": post['profile']['host'],
                    "displayName": post['profile']['displayName'],
                    "url": post['profile']['url'],
                    "github": post['profile']['github'],
                    "profileImage": post['profile']['profileImage']
                },
                # Assuming comments are included in post serialization
                "comments": post['comments'],
                "published": post['created'],
                "visibility": post['visibility']
            }
            inbox_items.append(post_data)

        return Response({
            "type": "inbox",
            "author": author_id,
            "items":
                inbox_items
        })

    def post(self, request, author_id):
        # Here, you'll handle POST requests to add items to the inbox.
        # Since the inbox doesn't contain items directly, you might be creating Posts, Comments, or altering Follow relationships.
        # Implement logic based on the 'type' in the request data to update the respective models.

        return Response({"message": "POST to inbox not implemented."}, status=status.HTTP_501_NOT_IMPLEMENTED)

    def delete(self, request, author_id):
        # Clearing the inbox would involve removing or marking notifications as read.
        # Actual deletion might not be desired as it could remove records of likes, comments, etc.

        # Example: Mark notifications as read for the given author
        Notification.objects.filter(
            recipient__profile__id=author_id).update(is_read=True)

        return Response({"message": "Inbox cleared (notifications marked as read)."}, status=status.HTTP_204_NO_CONTENT)
