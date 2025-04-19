# authentication/api.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import ProfileViewSet, LoginView, FollowersViewSet, PostViewSet, CommentsViewSet, LikedPostsView, InboxView
router = DefaultRouter()
router.register(r'authors', ProfileViewSet)
router.register(r'authors/(?P<author_id>\d+)/posts', PostViewSet, basename='author-posts')
router.register(r'authors/(?P<author_id>\d+)/posts/(?P<post_id>\d+)/comments',
                CommentsViewSet, basename='comment')

followers_list = FollowersViewSet.as_view({
    'get': 'list',
})

followers_detail = FollowersViewSet.as_view({
    'get': 'retrieve',
    'delete': 'destroy',
    'put': 'create',
})

comments_list = CommentsViewSet.as_view({
    'get': 'list',
    'post': 'create',
})

comments_detail = CommentsViewSet.as_view({
    'get': 'retrieve',
})

urlpatterns = [
    path('', include(router.urls)),
    path('login/', LoginView.as_view(), name='login'),
    path('authors/<int:author_id>/followers/',
         followers_list, name='followers-list'),
    path('authors/<int:author_id>/followers/<int:foreign_author_id>/',
         followers_detail, name='followers-detail'),
    path('authors/<int:author_id>/posts/<int:post_id>/comments/',
         comments_list, name='comments-list'),
    path('authors/<int:author_id>/posts/<int:post_id>/comments/<int:pk>/',
         comments_detail, name='comments-detail',),
    path('authors/<int:author_id>/inbox/', InboxView.as_view(), name='inbox'),
    path('authors/<int:author_id>/liked/',
         LikedPostsView.as_view(), name='liked-posts-list'),

]
