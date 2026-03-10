import sys
import types
from unittest import TestCase
from unittest.mock import patch


if 'openai' not in sys.modules:
    fake_openai = types.ModuleType('openai')

    class DummyOpenAI:
        def __init__(self, *args, **kwargs):
            pass

    fake_openai.OpenAI = DummyOpenAI
    sys.modules['openai'] = fake_openai

from home.ai.TaskAgent import AgentExecutionReport, TaskAgent, TaskExecutionResult
from home.ai.AiApi import AiType


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
        self.assertEqual(report.execution_results[0].display_text, 'formatted content')
        self.assertEqual(final_text, 'final answer')
        self.assertEqual(mock_decompose.call_count, 2)
        self.assertEqual(mock_execute_plan.call_count, 2)
        self.assertEqual(mock_summarize.call_count, 2)
