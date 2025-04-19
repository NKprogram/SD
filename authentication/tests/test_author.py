from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from authentication.models import Profile
from rest_framework.response import Response

class AuthorAPITestCase(TestCase):
    def setUp(self):
        # Create a test user and profile
        self.user = User.objects.create_user(username='testuser', email='test@test.com', password='testpass')
        self.profile = Profile.objects.create(user=self.user, displayname="Test User", github="http://github.com/testuser")
        
        # Get a JWT for the test user
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
        # Initialize the APIClient
        self.client = APIClient()

    def test_list_authors(self):
        # Include the JWT in the Authorization header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Fetch the list of authors
        response = self.client.get(reverse('profile', kwargs={'username': self.user.username}))
        
        # Make sure the response is an HttpResponse object
        self.assertIsInstance(response, Response, "The response should be an instance of rest_framework.response.Response")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['type'], 'authors')
        # Assuming the response structure is a list under 'items'
        self.assertTrue('items' in response.data and len(response.data['items']) > 0)
        first_author = response.data['items'][0]
        self.assertEqual(first_author['type'], 'author')
        self.assertIn(self.user.username, first_author['id'])

    def test_retrieve_author_profile(self):
       # Include the JWT in the Authorization header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Fetch a specific author's profile
        response = self.client.get(reverse('profile', kwargs={'username': self.user.username}))
        
        # Make sure the response is an HttpResponse object
        self.assertIsInstance(response, Response, "The response should be an instance of rest_framework.response.Response")
        self.assertEqual(response.status_code, 200)
        # Ensure the response data matches the user's profile information
        self.assertEqual(response.data['displayName'], self.profile.displayName)
        self.assertEqual(response.data['github'], self.profile.github)
        self.assertIn(self.profile.profileImage.url, response.data['profileImage'])