from django.test import TestCase, Client
from .models import VisitorLog
import json


class HomeViewTestCase(TestCase):
    """Test cases for the home view"""
    
    def setUp(self):
        """Set up test client"""
        self.client = Client()
    
    def test_get_request(self):
        """Test that GET requests work and return JSON"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        # Check response is JSON
        self.assertEqual(response['Content-Type'], 'application/json')
        data = json.loads(response.content)
        self.assertEqual(data['code'], 200)
        self.assertEqual(data['msg'], '成功')
        self.assertIn('params', data)
        
        # Check that visitor log was created
        log = VisitorLog.objects.latest('timestamp')
        self.assertEqual(log.method, 'GET')
        self.assertEqual(log.path, '/')
    
    def test_post_request(self):
        """Test that POST requests work without CSRF token and return JSON"""
        response = self.client.post('/', {})
        self.assertEqual(response.status_code, 200)
        
        # Check response is JSON
        self.assertEqual(response['Content-Type'], 'application/json')
        data = json.loads(response.content)
        self.assertEqual(data['code'], 200)
        self.assertEqual(data['msg'], '成功')
        
        # Check that visitor log was created
        log = VisitorLog.objects.latest('timestamp')
        self.assertEqual(log.method, 'POST')
        self.assertEqual(log.path, '/')
    
    def test_put_request(self):
        """Test that PUT requests work and return JSON"""
        response = self.client.put('/', {})
        self.assertEqual(response.status_code, 200)
        
        # Check response is JSON
        self.assertEqual(response['Content-Type'], 'application/json')
        data = json.loads(response.content)
        self.assertEqual(data['code'], 200)
        
        # Check that visitor log was created
        log = VisitorLog.objects.latest('timestamp')
        self.assertEqual(log.method, 'PUT')
        self.assertEqual(log.path, '/')
    
    def test_delete_request(self):
        """Test that DELETE requests work and return JSON"""
        response = self.client.delete('/')
        self.assertEqual(response.status_code, 200)
        
        # Check response is JSON
        self.assertEqual(response['Content-Type'], 'application/json')
        data = json.loads(response.content)
        self.assertEqual(data['code'], 200)
        
        # Check that visitor log was created
        log = VisitorLog.objects.latest('timestamp')
        self.assertEqual(log.method, 'DELETE')
        self.assertEqual(log.path, '/')
    
    def test_patch_request(self):
        """Test that PATCH requests work and return JSON"""
        response = self.client.patch('/', {})
        self.assertEqual(response.status_code, 200)
        
        # Check response is JSON
        self.assertEqual(response['Content-Type'], 'application/json')
        data = json.loads(response.content)
        self.assertEqual(data['code'], 200)
        
        # Check that visitor log was created
        log = VisitorLog.objects.latest('timestamp')
        self.assertEqual(log.method, 'PATCH')
        self.assertEqual(log.path, '/')
    
    def test_get_request_with_params(self):
        """Test that GET request parameters are captured in response"""
        response = self.client.get('/', {'name': 'test', 'value': '123'})
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(data['code'], 200)
        self.assertEqual(data['params']['name'], 'test')
        self.assertEqual(data['params']['value'], '123')
    
    def test_post_request_with_params(self):
        """Test that POST request parameters are captured in response"""
        response = self.client.post('/', {'key': 'value', 'data': 'test'})
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(data['code'], 200)
        self.assertEqual(data['params']['key'], 'value')
        self.assertEqual(data['params']['data'], 'test')


