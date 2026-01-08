from django.test import TestCase, Client
from .models import VisitorLog


class HomeViewTestCase(TestCase):
    """Test cases for the home view"""
    
    def setUp(self):
        """Set up test client"""
        self.client = Client()
    
    def test_get_request(self):
        """Test that GET requests work"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        # Check that visitor log was created
        log = VisitorLog.objects.latest('timestamp')
        self.assertEqual(log.method, 'GET')
        self.assertEqual(log.path, '/')
    
    def test_post_request(self):
        """Test that POST requests work without CSRF token"""
        response = self.client.post('/', {})
        self.assertEqual(response.status_code, 200)
        
        # Check that visitor log was created
        log = VisitorLog.objects.latest('timestamp')
        self.assertEqual(log.method, 'POST')
        self.assertEqual(log.path, '/')
    
    def test_put_request(self):
        """Test that PUT requests work"""
        response = self.client.put('/', {})
        self.assertEqual(response.status_code, 200)
        
        # Check that visitor log was created
        log = VisitorLog.objects.latest('timestamp')
        self.assertEqual(log.method, 'PUT')
        self.assertEqual(log.path, '/')
    
    def test_delete_request(self):
        """Test that DELETE requests work"""
        response = self.client.delete('/')
        self.assertEqual(response.status_code, 200)
        
        # Check that visitor log was created
        log = VisitorLog.objects.latest('timestamp')
        self.assertEqual(log.method, 'DELETE')
        self.assertEqual(log.path, '/')
    
    def test_patch_request(self):
        """Test that PATCH requests work"""
        response = self.client.patch('/', {})
        self.assertEqual(response.status_code, 200)
        
        # Check that visitor log was created
        log = VisitorLog.objects.latest('timestamp')
        self.assertEqual(log.method, 'PATCH')
        self.assertEqual(log.path, '/')

