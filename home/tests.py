# home/tests.py
#
# This file contains test cases for the home app. It is used to write and run tests to ensure
# that the app's code is working correctly.
from django.test import TestCase, Client
from .models import VisitorLog
from . import feishu_utils
import json
from unittest.mock import patch


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

    def test_post_json_request_returns_payload(self):
        """Test that JSON POST requests on home stay generic."""
        response = self.client.post(
            '/',
            data=json.dumps({'source': 'home', 'value': 1}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['code'], 200)
        self.assertEqual(data['params']['source'], 'home')
        self.assertEqual(data['params']['value'], 1)


class FeishuWebhookViewTestCase(TestCase):
    """Test cases for the dedicated Feishu webhook endpoint"""

    def setUp(self):
        self.client = Client()
        feishu_utils._clear_recent_message_ids()

    def _build_feishu_message_payload(self, message_id='om_test', text='hello'):
        return {
            'schema': '2.0',
            'header': {
                'app_id': 'cli_a9255c608ff95cef',
                'token': 'x6pyZiEINLzSiUCQKbvmEgl7hIp3ItUv',
                'event_type': 'im.message.receive_v1'
            },
            'event': {
                'message': {
                    'message_type': 'text',
                    'message_id': message_id,
                    'chat_type': 'p2p',
                    'content': json.dumps({'text': text})
                }
            }
        }

    @patch('home.feishu_utils._start_background_task')
    def test_process_feishu_event_dispatches_background_task(self, mock_start_background_task):
        payload = self._build_feishu_message_payload(text='please install requests')

        dispatched = feishu_utils.process_feishu_event(payload)

        self.assertTrue(dispatched)
        mock_start_background_task.assert_called_once_with('om_test', 'please install requests')

    @patch('home.feishu_utils._start_background_task')
    def test_duplicate_message_id_is_ignored(self, mock_start_background_task):
        payload = self._build_feishu_message_payload(message_id='om_dup', text='same message')

        first_dispatch = feishu_utils.process_feishu_event(payload)
        second_dispatch = feishu_utils.process_feishu_event(payload)

        self.assertTrue(first_dispatch)
        self.assertFalse(second_dispatch)
        mock_start_background_task.assert_called_once_with('om_dup', 'same message')

    @patch('home.feishu_utils._start_background_task')
    def test_old_message_id_is_evictable_after_100_entries(self, mock_start_background_task):
        first_payload = self._build_feishu_message_payload(message_id='om_oldest', text='first')
        self.assertTrue(feishu_utils.process_feishu_event(first_payload))

        for index in range(1, feishu_utils.MAX_RECENT_MESSAGE_IDS + 1):
            payload = self._build_feishu_message_payload(
                message_id=f'om_{index}',
                text=f'message {index}'
            )
            self.assertTrue(feishu_utils.process_feishu_event(payload))

        recycled_payload = self._build_feishu_message_payload(message_id='om_oldest', text='first again')
        self.assertTrue(feishu_utils.process_feishu_event(recycled_payload))
        self.assertEqual(mock_start_background_task.call_count, feishu_utils.MAX_RECENT_MESSAGE_IDS + 2)

    def test_get_request_reports_ready(self):
        response = self.client.get('/robot/feishu')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

        data = json.loads(response.content)
        self.assertEqual(data['msg'], 'Feishu webhook is ready')

        log = VisitorLog.objects.latest('timestamp')
        self.assertEqual(log.path, '/robot/feishu')
        self.assertEqual(log.method, 'GET')

    def test_url_verification_challenge(self):
        payload = {
            'schema': '2.0',
            'type': 'url_verification',
            'token': 'x6pyZiEINLzSiUCQKbvmEgl7hIp3ItUv',
            'challenge': 'challenge-value'
        }

        response = self.client.post(
            '/robot/feishu',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {'challenge': 'challenge-value'})

    def test_rejects_invalid_token(self):
        payload = {
            'schema': '2.0',
            'type': 'url_verification',
            'token': 'invalid-token',
            'challenge': 'challenge-value'
        }

        response = self.client.post(
            '/robot/feishu',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)

    @patch('home.views.process_feishu_event')
    def test_event_callback_uses_dedicated_endpoint(self, mock_process_feishu_event):
        payload = self._build_feishu_message_payload()

        response = self.client.post(
            '/robot/feishu',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['msg'], 'Event received successfully')
        mock_process_feishu_event.assert_called_once_with(payload)

    def test_rejects_non_json_post(self):
        response = self.client.post('/robot/feishu', data={'foo': 'bar'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)['msg'], 'Content-Type must be application/json')
