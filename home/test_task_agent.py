import json
import sys
import types
from unittest.mock import patch

from django.test import TestCase


if 'openai' not in sys.modules:
    fake_openai = types.ModuleType('openai')

    class DummyOpenAI:
        def __init__(self, *args, **kwargs):
            pass

    fake_openai.OpenAI = DummyOpenAI
    sys.modules['openai'] = fake_openai

from home.ai.TaskAgent import AgentExecutionReport, TaskAgent, TaskExecutionResult
from home.ai.AiApi import AiType
from home.models import TaskOutput, TaskRun


class TaskAgentFailureFallbackTests(TestCase):
    def setUp(self):
        self.agent = TaskAgent(ai_type=AiType.DEEPSEEK, max_recovery_attempts=2)
        self.python_task = {
            'task_id': 1,
            'tool': 'Python_Script',
            'description': 'Run a script that currently fails',
            'code': "raise Exception('boom')",
        }

    @patch('home.ai.TaskAgent._run_python_sandbox')
    def test_successful_auto_recovery_does_not_use_llm_fallback(self, mock_run_python_sandbox):
        mock_run_python_sandbox.side_effect = [
            'Error executing code: boom',
            'fixed successfully',
            'Error executing code: boom',
            'fixed successfully',
        ]

        with patch.object(
            self.agent,
            'call_deepseek',
            return_value="```code\nprint('fixed successfully')\n```",
        ) as mock_call_deepseek:
            results = self.agent.execute_plan({'plan': [self.python_task]})
            structured_results = self.agent.execute_plan({'plan': [self.python_task]}, return_structured=True)

        self.assertEqual(len(results), 1)
        self.assertIn('fixed successfully', results[0])
        self.assertNotIn('LLM fallback answer instead', results[0])
        self.assertEqual(mock_call_deepseek.call_count, 2)

        self.assertEqual(len(structured_results), 1)
        result = structured_results[0]
        self.assertIsInstance(result, TaskExecutionResult)
        self.assertEqual(result.status, 'recovered')
        self.assertFalse(result.used_llm_fallback)
        self.assertEqual(result.recovery_attempts, 1)
        self.assertEqual(result.display_text, 'fixed successfully')

    @patch('home.ai.TaskAgent._run_python_sandbox')
    def test_failed_recovery_falls_back_to_llm_answer(self, mock_run_python_sandbox):
        mock_run_python_sandbox.side_effect = [
            'Error executing code: boom',
            'Error executing code: still broken',
            'Error executing code: broken again',
            'Error executing code: boom',
            'Error executing code: still broken',
            'Error executing code: broken again',
        ]

        with patch.object(
            self.agent,
            'call_deepseek',
            side_effect=[
                "```code\nraise Exception('still broken')\n```",
                "```code\nraise Exception('broken again')\n```",
                'CAN_RESOLVE_WITH_LLM: yes\n这里是直接询问大模型后的替代方案',
                "```code\nraise Exception('still broken')\n```",
                "```code\nraise Exception('broken again')\n```",
                'CAN_RESOLVE_WITH_LLM: yes\n这里是直接询问大模型后的替代方案',
            ],
        ) as mock_call_deepseek:
            results = self.agent.execute_plan({'plan': [self.python_task]})
            structured_results = self.agent.execute_plan({'plan': [self.python_task]}, return_structured=True)

        self.assertEqual(len(results), 1)
        self.assertIn('LLM fallback answer instead', results[0])
        self.assertIn('这里是直接询问大模型后的替代方案', results[0])
        self.assertEqual(mock_call_deepseek.call_count, 6)

        result = structured_results[0]
        self.assertEqual(result.status, 'fallback_answered')
        self.assertTrue(result.used_llm_fallback)
        self.assertEqual(result.recovery_attempts, 2)
        self.assertIsNotNone(result.fallback)
        self.assertTrue(result.fallback.can_replace_execution)
        self.assertEqual(result.content, '这里是直接询问大模型后的替代方案')

    @patch('home.ai.TaskAgent._run_python_sandbox')
    def test_failed_recovery_reports_when_llm_cannot_replace_execution(self, mock_run_python_sandbox):
        mock_run_python_sandbox.side_effect = [
            'Error executing code: boom',
            'Error executing code: still broken',
            'Error executing code: broken again',
        ]

        with patch.object(
            self.agent,
            'call_deepseek',
            side_effect=[
                "```code\nraise Exception('still broken')\n```",
                "```code\nraise Exception('broken again')\n```",
                'CAN_RESOLVE_WITH_LLM: no\n这个任务仍然需要真实执行环境。',
            ],
        ):
            results = self.agent.execute_plan({'plan': [self.python_task]}, return_structured=True)

        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result.status, 'fallback_unresolved')
        self.assertTrue(result.used_llm_fallback)
        self.assertIn('LLM fallback could not safely replace execution', result.display_text)
        self.assertIn('这个任务仍然需要真实执行环境', result.display_text)
        self.assertFalse(result.fallback.can_replace_execution)

    def test_summarize_accepts_structured_results(self):
        execution_results = [
            TaskExecutionResult(
                task_id=1,
                tool='Python_Script',
                description='desc',
                status='success',
                content='done',
                display_text='done',
            )
        ]

        with patch.object(self.agent, 'call_deepseek', return_value='summary') as mock_call_deepseek:
            summary = self.agent.summarize('do something', execution_results)

        self.assertEqual(summary, 'summary')
        self.assertIn('Task 1 (Python_Script): done', mock_call_deepseek.call_args.args[0])

    def test_execute_task_result_keeps_string_interface_compatible(self):
        structured_result = TaskExecutionResult(
            task_id=1,
            tool='DeepSeek_LLM',
            description='answer',
            status='success',
            content='raw content',
            display_text='formatted content',
        )

        with patch.object(self.agent, 'decompose', return_value={'plan': []}) as mock_decompose, \
                patch.object(self.agent, 'execute_plan', return_value=[structured_result]) as mock_execute_plan, \
                patch.object(self.agent, 'summarize', return_value='final answer') as mock_summarize:
            report = self.agent.execute_task_result('hello')
            final_text = self.agent.execute_task('hello')

        self.assertIsInstance(report, AgentExecutionReport)
        self.assertEqual(report.final_report, 'final answer')
        self.assertIsNotNone(report.task_run_id)
        self.assertEqual(report.execution_results[0].display_text, 'formatted content')
        self.assertEqual(final_text, 'final answer')
        self.assertEqual(mock_decompose.call_count, 2)
        self.assertEqual(mock_execute_plan.call_count, 2)
        self.assertEqual(mock_summarize.call_count, 2)

    @patch('home.ai.TaskAgent._run_python_sandbox', return_value='script ok')
    def test_execute_task_result_persists_feishu_source_context(self, mock_run_python_sandbox):
        plan_response = json.dumps({
            'plan': [
                {
                    'task_id': 1,
                    'tool': 'Python_Script',
                    'description': 'run script',
                    'code': "print('ok')",
                }
            ]
        }, ensure_ascii=False)
        run_context = {
            'source_type': 'feishu',
            'message_id': 'om_feishu_1',
            'chat_id': 'oc_chat_1',
            'chat_type': 'p2p',
            'sender_open_id': 'ou_sender_1',
            'mentions': [],
        }

        with patch.object(
                self.agent,
                'call_deepseek',
                side_effect=[plan_response, 'final summary'],
        ):
            report = self.agent.execute_task_result('test query', run_context=run_context)

        task_run = TaskRun.objects.get(pk=report.task_run_id)
        self.assertEqual(task_run.source_type, 'feishu')
        self.assertEqual(task_run.source_message_id, 'om_feishu_1')
        self.assertEqual(task_run.source_chat_id, 'oc_chat_1')
        self.assertEqual(task_run.source_sender_open_id, 'ou_sender_1')
        self.assertEqual(task_run.source_metadata['chat_type'], 'p2p')
        mock_run_python_sandbox.assert_called_once_with("print('ok')")

    @patch('home.ai.TaskAgent._run_python_sandbox', return_value='script ok')
    def test_execute_task_result_persists_run_and_outputs(self, mock_run_python_sandbox):
        plan_response = json.dumps({
            'plan': [
                {
                    'task_id': 1,
                    'tool': 'Python_Script',
                    'description': 'run script',
                    'code': "print('ok')",
                }
            ]
        }, ensure_ascii=False)

        with patch.object(
                self.agent,
                'call_deepseek',
                side_effect=[plan_response, 'final summary'],
        ):
            report = self.agent.execute_task_result('test query')

        self.assertEqual(report.final_report, 'final summary')
        self.assertEqual(TaskRun.objects.count(), 1)
        task_run = TaskRun.objects.get()
        self.assertEqual(task_run.user_query, 'test query')
        self.assertEqual(task_run.status, 'success')
        self.assertEqual(task_run.initial_plan['plan'][0]['description'], 'run script')
        self.assertEqual(task_run.final_report, 'final summary')
        self.assertIsNotNone(task_run.finished_at)

        outputs = list(TaskOutput.objects.filter(task_run=task_run).order_by('sequence'))
        self.assertEqual(len(outputs), 3)
        self.assertEqual(outputs[0].stage, 'planning')
        self.assertEqual(outputs[1].stage, 'execution')
        self.assertEqual(outputs[1].status, 'success')
        self.assertEqual(outputs[1].input_code, "print('ok')")
        self.assertEqual(outputs[2].stage, 'summary')
        self.assertEqual(outputs[2].content, 'final summary')
        mock_run_python_sandbox.assert_called_once_with("print('ok')")

    @patch('home.ai.TaskAgent._run_python_sandbox')
    def test_fallback_answer_is_persisted_to_database(self, mock_run_python_sandbox):
        mock_run_python_sandbox.side_effect = [
            'Error executing code: boom',
            'Error executing code: still broken',
            'Error executing code: broken again',
        ]
        plan_response = json.dumps({
            'plan': [
                {
                    'task_id': 1,
                    'tool': 'Python_Script',
                    'description': 'run script',
                    'code': "raise Exception('boom')",
                }
            ]
        }, ensure_ascii=False)

        with patch.object(
                self.agent,
                'call_deepseek',
                side_effect=[
                    plan_response,
                    "```code\nraise Exception('still broken')\n```",
                    "```code\nraise Exception('broken again')\n```",
                    'CAN_RESOLVE_WITH_LLM: yes\n这里是数据库里的兜底答案',
                    'final summary',
                ],
        ):
            self.agent.execute_task_result('test fallback')

        task_run = TaskRun.objects.get(user_query='test fallback')
        execution_output = TaskOutput.objects.get(task_run=task_run, stage='execution')
        self.assertEqual(execution_output.status, 'fallback_answered')
        self.assertTrue(execution_output.used_llm_fallback)
        self.assertTrue(execution_output.fallback_can_replace_execution)
        self.assertEqual(execution_output.fallback_answer, '这里是数据库里的兜底答案')
        self.assertIn('LLM fallback answer instead', execution_output.display_text)
        self.assertEqual(task_run.status, 'success')
