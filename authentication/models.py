from email.policy import default
from django.db import models
from django.contrib.auth.models import User
import requests
from datetime import datetime
from django import forms
from django.urls import reverse
from django.db.models.signals import post_save
from django.dispatch import receiver


class Node(models.Model):
    name = models.CharField(max_length=100, unique=True)
    host_url = models.URLField(unique=True)
    is_active = models.BooleanField(
        default=True, help_text="Status to enable/disable node interaction")
    username = models.CharField(
        max_length=100, null=True, blank=True, help_text="Username for the node")
    password = models.CharField(
        max_length=100, null=True, blank=True, help_text="Password for the node")

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Set default to empty string
    displayName = models.CharField(max_length=100, blank=True, default='')
    # Set default to empty string
    bio = models.TextField(blank=True, default='')
    # Set default to empty string
    github = models.URLField(blank=True, default='')
    # Set default to empty string
    profileImage = models.URLField(blank=True, default='')
    following = models.ManyToManyField(
        'self', symmetrical=False, related_name='followers', blank=True)
    liked = models.ManyToManyField(
        'Post', related_name='liked_posts', blank=True)
    posts = models.ManyToManyField('Post', related_name='posts', blank=True)

    class Meta:
        ordering = ['id']

    def get_absolute_url(self):
        return reverse('profile-detail', args=[str(self.id)])

    def __str__(self):
        return self.user.username  # TESTING

    def get_friends(self):
        # Users that the current user follows and also follow the current user back
        users_i_follow = self.following.all()
        # Users that follow the current user back
        friends = users_i_follow.filter(following__id=self.id)

        return friends

    def get_github_activity(self):
        # Check if the GitHub URL is None
        if self.github is None:
            # If it is, return an error message or an empty list
            return {'error': 'No GitHub URL'}
        # Extract the username from the GitHub URL
        github_username = self.github.split('/')[-1]

        # Make a request to the GitHub API
        response = requests.get(
            f'https://api.github.com/users/{github_username}/events')

        # Check if the request was successful
        if response.status_code == 200:
            # Get the JSON data from the response
            events = response.json()

            # Reverse the list of events
            events.reverse()
            return events
        else:
            # If the request was not successful, return an error message
            return {'error': 'Could not get GitHub activity'}

    def create_posts_from_github_activity(self):
        # Get the GitHub activity
        github_activity = self.get_github_activity()

        # Check if there was an error
        if 'error' in github_activity:
            return github_activity
        # Loop through the GitHub activity
        for event in github_activity:
            # Create a new Post instance for each event
            if self.posts.filter(github_id=event['id']).exists() == False:
                created_at = datetime.strptime(
                    event['created_at'], "%Y-%m-%dT%H:%M:%SZ")
                formatted_date = created_at.strftime("%B %d, %Y")
                post = Post.objects.create(
                    user=self.user,
                    profile=self,
                    github_id=event['id'],
                    content=f"Github Event - {event['type']} in {event['repo']['name']} on {formatted_date}",
                )
                self.posts.add(post)

        # Save the user's profile
        self.save()

    def get_absolute_url(self):
        return reverse('profile', kwargs={'username': self.user.username})

    def __str__(self):
        return self.user.username


class Post(models.Model):

    VISIBILITY_CHOICES = [('public', 'Public'),
                          ('private', 'Private'), ('unlisted', 'Unlisted')]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # add profile as well and give it a default value
    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, null=True, blank=True)
    content = models.TextField()
    # image = models.ImageField(upload_to='posts',  blank=True)
    image = models.URLField(blank=True, null=True)
    liked = models.ManyToManyField(
        Profile, related_name='liked_by', blank=True)
    created = models.DateTimeField(auto_now_add=True)
    github_id = models.CharField(max_length=100, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True)
    likes = models.ManyToManyField(
        User, related_name='liked_posts', blank=True)
    visibility = models.CharField(
        max_length=10, choices=VISIBILITY_CHOICES, default='public')
    cm_toggle = models.BooleanField(default=False)  # CommonMark toggle
    content_markdown = models.TextField()
    image_type = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.content[:20]

    def num_likes(self):
        return self.liked.all().count()

    def get_absolute_url(self):
        return reverse('post-detail', args=[str(self.id)])

    class Meta:
        ordering = ('-created',)


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    likes = models.ManyToManyField(
        User, related_name='liked_comments', blank=True)
    cm_toggle_comment = models.BooleanField(
        default=False)  # CommonMark toggle for comments

    def __str__(self):
        return self.content[:20]

    def get_absolute_url(self):
        return reverse('comment-detail', args=[str(self.post.profile.id), str(self.post.id), str(self.id)])

    class Meta:
        ordering = ('-created',)


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['content', 'image', 'cm_toggle',]  # Added 'is_unlisted'


class Notification(models.Model):
    TYPE_CHOICES = (
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('follow', 'Follow Request'),
        ('accepted_follow', 'Accepted Follow Request'),
        ('github_activity', 'GitHub Activity'),
        ('post', 'New Post'),
    )
    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.CASCADE,
                               null=True, blank=True, related_name='sent_notifications')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    post = models.ForeignKey(
        'Post', on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        return f"{self.recipient.username} - {self.get_type_display()}"

    def notification_text(self):
        """
        Generates a custom notification text based on the notification type.
        This method can be extended to include more personalized text for each notification.
        """
        if self.type == 'like':
            return f"{self.sender.username} liked your post."
        elif self.type == 'comment':
            return f"{self.sender.username} commented on your post: '{self.post.content[:30]}...'"
        elif self.type == 'follow':
            return f"{self.sender.username} has started following you."
        elif self.type == 'github_activity':
            return "New activity on your GitHub!"
        elif self.type == 'post':
            return f"{self.sender.username} created a new post."
        else:
            return "You have a new notification."


class FollowRequest(models.Model):
    sender = models.ForeignKey(
        User, related_name='sent_follow_requests', on_delete=models.CASCADE)
    receiver = models.ForeignKey(
        User, related_name='received_follow_requests', on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('sender', 'receiver')

    def __str__(self):
        return f"From {self.sender.username} to {self.receiver.username}"
