from django.urls import include, path
from .template_views import accept_follow_request, deny_follow_request, home, signin, signout, signup, create_post, profilepage, update_profile, like_post, post_detail, delete_post, add_comment, delete_comment, user_search, follow, edit_post, all_users, like_comment, notifications_view, mark_all_notifications_as_read, get_unread_notifications_count
from authentication.template_views import notifications_view
from authentication.api_views import RegisterView
from authentication.api_views import ProfileViewSet

urlpatterns = [
    path('api/', include('authentication.api')),
    # path('', home, name='home'),
    # path('signin/', signin, name='signin'),
    # path('signout/', signout, name='logout'),
    # path('signup/', signup, name='signup'),
    # path('create_post/', create_post, name='create_post'),
    # path('p/<str:username>/', profilepage, name='profile'),
    # path('update_profile/', update_profile, name='update_profile'),
    # path('like_post/<int:post_id>/', like_post, name='like_post'),
    # path('post/<int:post_id>/', post_detail, name='post_detail'),
    # path('post/<int:post_id>/delete/', delete_post, name='delete_post'),
    # path('add_comment/<int:post_id>/', add_comment, name='add_comment'),
    path('', home, name='home'),
    path('signin/', signin, name='signin'),
    path('signout/', signout, name='logout'),
    path('signup/', signup, name='signup'),
    path('create_post/', create_post, name='create_post'),
    path('p/<str:username>/', profilepage, name='profile'),
    path('update_profile/', update_profile, name='update_profile'),
    path('like_post/<int:post_id>/', like_post, name='like_post'),
    path('post/<int:post_id>/', post_detail, name='post_detail'),
    path('post/<int:post_id>/delete/', delete_post, name='delete_post'),
    path('add_comment/<int:post_id>/', add_comment, name='add_comment'),
    path('comment/<int:comment_id>/delete/',
         delete_comment, name='delete_comment'),
    path('search/', user_search, name='user_search'),  # testing search
    path('follow/', follow, name='follow'),
    path('edit_post/<int:post_id>/', edit_post, name='edit_post'),
    path('authors/', all_users, name='all_users'),
    path('notifications/', notifications_view, name='notifications'),
    path('like_comment/<int:comment_id>/', like_comment, name='like_comment'),
    path('notifications/', notifications_view, name='notifications'),
    path('notifications/mark-all-as-read/', mark_all_notifications_as_read,
         name='mark-all-notifications-as-read'),
    path('notifications/unread-count/', get_unread_notifications_count,
         name='unread-notifications-count'),

    path('accept-follow-request/<int:notification_id>/',
         accept_follow_request, name='accept_follow_request'),
    path('deny-follow-request/<int:notification_id>/',
         deny_follow_request, name='deny_follow_request'),

    path('profile/<str:username>/', ProfileViewSet.as_view(
        {'get': 'retrieve', 'put': 'update'}), name='profile-detail'),
]
