from rest_framework import serializers
from .models import Profile, Post, Comment
from django.urls import reverse


class ProfileSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()
    database_id = serializers.IntegerField(source='id')
    url = serializers.SerializerMethodField()
    host = serializers.SerializerMethodField()
    posts = serializers.SerializerMethodField()
    friends = serializers.SerializerMethodField()
    followers = serializers.SerializerMethodField()
    following = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['type', 'id', 'url', 'host',
                  'database_id',  'posts', 'friends', 'followers', 'following',
                  'displayName', 'github', 'profileImage']

    def get_type(self, obj):
        return 'author'

    def get_id(self, obj):
        request = self.context.get('request')
        # Ensure you have a username field or attribute in your Profile model or linked user
        username = obj.user.username
        return request.build_absolute_uri(reverse('profile', kwargs={'username': username}))

    def get_url(self, obj):
        request = self.context.get('request')
        username = obj.user.username
        return request.build_absolute_uri(reverse('profile', kwargs={'username': username}))

    def get_host(self, obj):
        request = self.context.get('request')
        # Get the scheme ('http' or 'https') and the host from the request
        scheme = request.scheme
        host = request.get_host()
        # Combine scheme, host, and add a trailing slash to form the full base URL
        return f"{scheme}://{host}/"

    def get_posts(self, obj):
        posts = Post.objects.filter(user=obj.user).order_by('-created')
        # Use SimplePostSerializer here to avoid recursion
        return SimplePostSerializer(posts, many=True, context=self.context).data

    def get_friends(self, obj):
        friends = obj.get_friends()
        return FriendSerializer(friends, many=True, context=self.context).data

    def get_followers(self, obj):
        return obj.followers.count()

    def get_following(self, obj):
        return obj.following.count()
    
    # def to_representation(self, instance):
    #     representation = super().to_representation(instance)
    #     representation['displayName'] = representation.pop('displayName')
    #     return representation


class CommentSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    author = ProfileSerializer(source='user.profile')
    comment = serializers.CharField(source='content')
    contentType = serializers.SerializerMethodField()
    published = serializers.DateTimeField(
        source='created', format="%Y-%m-%dT%H:%M:%S%z")
    id = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['type', 'author', 'comment',
                  'contentType', 'published', 'id']

    def get_type(self, obj):
        return 'comment'

    def get_contentType(self, obj):
        return 'text/markdown'  # according to eClass forum post - guaranteed to be markdown

    def get_id(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(obj.get_absolute_url())


class SimpleProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['id', 'displayName', 'profileImage']


class SimplePostSerializer(serializers.ModelSerializer):
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        # Add any other fields you need but omit 'profile'
        fields = ['id', 'content', 'comments']


class PostSerializer(serializers.ModelSerializer):
    profile = SimpleProfileSerializer(read_only=True)

    comments = CommentSerializer(
        many=True, read_only=True)  # Note the change here
    # have an field that generate a url for the author of the post like this
    # http://127.0.0.1:8000/api/author/author_id,
    # where author_id is the id of the author of the post

    class Meta:
        model = Post
        fields = '__all__'


class FriendSerializer(serializers.ModelSerializer):
    # Serialize friend information, adjust according to your model structure
    class Meta:
        model = Profile
        fields = ['user__username', 'displayName', 'pfp']
