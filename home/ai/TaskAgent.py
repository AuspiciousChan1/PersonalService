import json
import subprocess
import io
import contextlib
import re
from dataclasses import dataclass, field
from typing import Any, Optional
from django.utils import timezone
from home.ai.AiApi import AiApiFactory, AiType
from home.ai.CodeReviewer import CodeReviewer
from home.ai import Constants
from home.models import TaskRun, TaskOutput


FAILURE_MARKERS = (
    "error",
    "failed",
    "exception",
    "not found",
    "timed out",
    "blocked by codereviewer",
    "unknown tool",
    "auto-recovery failed",
    "failure recovery failed",
)
SUCCESS_STATUSES = {"success", "recovered", "fallback_answered"}
FAILURE_STATUSES = {"failed", "fallback_unresolved"}


@dataclass
class LlmFallbackResult:
    attempted: bool
    can_replace_execution: bool
    original_error: str
    answer: str = ""
    raw_response: str = ""


@dataclass
class TaskExecutionResult:
    task_id: Any
    tool: str
    description: str
    status: str
    content: str
    display_text: str
    error_message: str = ""
    recovery_attempts: int = 0
    used_llm_fallback: bool = False
    fallback: Optional[LlmFallbackResult] = None
    metadata: dict = field(default_factory=dict)

    def to_log_string(self) -> str:
        return f"Task {self.task_id} ({self.tool}): {self.display_text}"

    def __str__(self) -> str:
        return self.display_text


@dataclass
class AgentExecutionReport:
    user_query: str
    plan: dict
    execution_results: list[TaskExecutionResult]
    final_report: str
    task_run_id: Optional[int] = None


def _run_python_sandbox(code):
    """
    模拟 Python 沙箱执行
    """
    print(f"  [Python] 执行 code: {code}...")

    output_buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(output_buffer):
            exec(code, {"__builtins__": __builtins__}, {})
        result = output_buffer.getvalue()
        return result.strip() if result else "Code executed successfully (no output)"
    except Exception as e:
        return f"Error executing code: {str(e)}"



def _run_shell_command(command: str, ai_type: AiType) -> str:
    """
    执行经过审查的 Shell 命令
    """
    print(f"  [Shell] 准备执行: {command}")

    if not CodeReviewer.review_and_approve(command, ai_type):
        return "Command execution blocked by CodeReviewer."

    try:
        print(f"  [Shell] 正在执行...")
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Shell command failed with error:\n{e.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "Shell command timed out."
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"


class TaskAgent:
    def __init__(self, ai_type: AiType = AiType.DEEPSEEK, max_depth=4, max_recovery_attempts=5):
        self.ai_type = ai_type
        self.max_depth = max_depth
        self.max_recovery_attempts = max_recovery_attempts
        self.results_cache = {}
        self.current_run: Optional[TaskRun] = None
        self._output_sequence = 0

    def _next_output_sequence(self) -> int:
        self._output_sequence += 1
        return self._output_sequence

    def _persist_output(
            self,
            *,
            stage: str,
            status: str,
            content: str,
            display_text: str,
            depth: int = 1,
            task_id: Any = None,
            tool: Optional[str] = None,
            description: Optional[str] = None,
            input_code: Optional[str] = None,
            error_message: str = "",
            recovery_attempts: int = 0,
            used_llm_fallback: bool = False,
            fallback: Optional[LlmFallbackResult] = None,
            metadata: Optional[dict] = None,
    ) -> None:
        if not self.current_run:
            return

        TaskOutput.objects.create(
            task_run=self.current_run,
            sequence=self._next_output_sequence(),
            stage=stage,
            depth=depth,
            task_id=str(task_id) if task_id is not None else None,
            tool=tool,
            description=description,
            input_code=input_code,
            status=status,
            content=str(content),
            display_text=str(display_text),
            error_message=error_message,
            recovery_attempts=recovery_attempts,
            used_llm_fallback=used_llm_fallback,
            fallback_can_replace_execution=(fallback.can_replace_execution if fallback else None),
            fallback_answer=(fallback.answer if fallback else None),
            fallback_raw_response=(fallback.raw_response if fallback else None),
            metadata=metadata or {},
        )

    def _persist_task_result(self, task, result: TaskExecutionResult, depth: int, input_code: Optional[str] = None) -> None:
        self._persist_output(
            stage='execution',
            status=result.status,
            content=result.content,
            display_text=result.display_text,
            depth=depth,
            task_id=result.task_id,
            tool=result.tool,
            description=result.description,
            input_code=input_code if input_code is not None else task.get('code'),
            error_message=result.error_message,
            recovery_attempts=result.recovery_attempts,
            used_llm_fallback=result.used_llm_fallback,
            fallback=result.fallback,
            metadata=result.metadata,
        )

    def _resolve_run_status(self, execution_results: list[TaskExecutionResult]) -> str:
        if not execution_results:
            return 'success'
        return 'completed_with_failures' if any(result.status in FAILURE_STATUSES for result in execution_results) else 'success'

    def _build_task_run_source_fields(self, run_context: Optional[dict]) -> dict:
        run_context = run_context or {}
        return {
            'source_type': run_context.get('source_type'),
            'source_message_id': run_context.get('message_id'),
            'source_chat_id': run_context.get('chat_id'),
            'source_sender_open_id': run_context.get('sender_open_id'),
            'source_metadata': run_context,
        }

    def execute_task_result(self, user_query: str, run_context: Optional[dict] = None) -> AgentExecutionReport:
        self.results_cache = {}
        self._output_sequence = 0
        self.current_run = TaskRun.objects.create(
            user_query=user_query,
            ai_type=self.ai_type.name,
            status='running',
            **self._build_task_run_source_fields(run_context),
        )

        try:
            initial_plan = self.decompose(user_query)
            self.current_run.initial_plan = initial_plan
            self.current_run.save(update_fields=['initial_plan'])

            execution_results = self.execute_plan(initial_plan, return_structured=True)
            final_report = self.summarize(user_query, execution_results)

            self.current_run.status = self._resolve_run_status(execution_results)
            self.current_run.final_report = final_report
            self.current_run.error_message = ''
            self.current_run.finished_at = timezone.now()
            self.current_run.save(update_fields=['status', 'final_report', 'error_message', 'finished_at'])

            return AgentExecutionReport(
                user_query=user_query,
                plan=initial_plan,
                execution_results=execution_results,
                final_report=final_report,
                task_run_id=self.current_run.pk,
            )
        except Exception as exc:
            if self.current_run:
                self.current_run.status = 'failed'
                self.current_run.error_message = str(exc)
                self.current_run.finished_at = timezone.now()
                self.current_run.save(update_fields=['status', 'error_message', 'finished_at'])
            raise
        finally:
            self.current_run = None

    def execute_task(self, user_query: str, run_context: Optional[dict] = None) -> str:
        return self.execute_task_result(user_query, run_context=run_context).final_report

    def call_deepseek(self, prompt, system_prompt=Constants.SYSTEM_PROMPT_PLANNER, think=True):
        instance = AiApiFactory.get(self.ai_type)
        return instance.query(query=prompt, system_prompt=system_prompt, think=think)

    def decompose(self, request_text, current_depth=1):
        if current_depth > self.max_depth:
            print(f"达到最大深度 {self.max_depth}，停止拆解。")
            self._persist_output(
                stage='planning',
                status='failed',
                content='Max depth exceeded.',
                display_text='达到最大深度，停止拆解。',
                depth=current_depth,
                tool='DeepSeek_LLM',
                description=request_text,
                error_message='Max depth exceeded.',
                metadata={'current_depth': current_depth},
            )
            return {"plan": []}

        print(f"层级 {current_depth}: 正在拆解任务 -> {request_text}...")
        llm_response = self.call_deepseek(request_text, system_prompt=Constants.SYSTEM_PROMPT_PLANNER, think=True)

        try:
            start_index = llm_response.index("{")
            end_index = llm_response.rindex("}") + 1
            plan_json_str = llm_response[start_index:end_index]
            plan = json.loads(plan_json_str)
            self._persist_output(
                stage='planning',
                status='success',
                content=llm_response,
                display_text=json.dumps(plan, ensure_ascii=False),
                depth=current_depth,
                tool='DeepSeek_LLM',
                description=request_text,
                metadata={'current_depth': current_depth, 'parsed_plan': plan},
            )
            return plan
        except (json.JSONDecodeError, ValueError):
            print("LLM 返回格式错误，尝试二次修正...")
            self._persist_output(
                stage='planning',
                status='failed',
                content=llm_response,
                display_text=llm_response,
                depth=current_depth,
                tool='DeepSeek_LLM',
                description=request_text,
                error_message='LLM response is not valid JSON.',
                metadata={'current_depth': current_depth},
            )
            return {"plan": []}

    def _build_task_result(self, task, status, content, display_text=None, error_message="", recovery_attempts=0,
                           used_llm_fallback=False, fallback=None, metadata=None):
        return TaskExecutionResult(
            task_id=task.get('task_id'),
            tool=task.get('tool', ''),
            description=task.get('description', ''),
            status=status,
            content=str(content),
            display_text=display_text or str(content),
            error_message=error_message,
            recovery_attempts=recovery_attempts,
            used_llm_fallback=used_llm_fallback,
            fallback=fallback,
            metadata=metadata or {},
        )

    def _is_failure_result(self, result) -> bool:
        if isinstance(result, TaskExecutionResult):
            return result.status in FAILURE_STATUSES
        if isinstance(result, list):
            return any(self._is_failure_result(item) for item in result)
        if isinstance(result, str):
            lowered = result.lower()
            return any(marker in lowered for marker in FAILURE_MARKERS)
        return False

    def _stringify_results(self, results) -> str:
        if isinstance(results, TaskExecutionResult):
            return results.to_log_string()
        if isinstance(results, list):
            return "; ".join(self._stringify_results(item) for item in results)
        return str(results)

    def _extract_recovery_plan(self, response: str):
        if "```json" not in response:
            return None
        try:
            start = response.index("```json") + 7
            end = response.rindex("```")
            plan_str = response[start:end].strip()
            return json.loads(plan_str)
        except Exception as e:
            print(f"  [Failure Handler] 解析补救计划失败: {e}")
            return None

    def _extract_fixed_code(self, response: str):
        code_match = re.search(r"```(?:code|python|bash)?\n(.*?)```", response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        return None

    def _should_fallback_to_llm(self, task, error_msg) -> bool:
        if task.get('tool') == "DeepSeek_LLM":
            return False
        return bool(error_msg)

    def _request_llm_fallback(self, task, error_msg, recovery_attempts) -> TaskExecutionResult:
        prompt = f"""
        A task failed after {recovery_attempts} automated recovery attempt(s).

        Task Description: {task.get('description')}
        Tool Used: {task.get('tool')}
        Original Code/Command:
        ```
        {task.get('code')}
        ```
        Final Error Message:
        {error_msg}

        Decide whether this task can still be meaningfully addressed without actually executing code or shell commands.

        Rules:
        1. First line must be exactly one of:
           CAN_RESOLVE_WITH_LLM: yes
           CAN_RESOLVE_WITH_LLM: no
        2. If yes, provide the best possible direct answer, corrected script/command, or manual workaround.
        3. If the original task involved side effects or real execution, clearly state that execution did NOT happen and your answer is guidance only.
        4. If no, explain briefly why real execution is still required.
        """
        try:
            response = self.call_deepseek(
                prompt,
                system_prompt="You are a pragmatic fallback assistant who helps after tool execution fails.",
                think=True,
            )
        except Exception as e:
            fallback = LlmFallbackResult(
                attempted=True,
                can_replace_execution=False,
                original_error=error_msg,
                answer="",
                raw_response=str(e),
            )
            message = (
                f"Auto-recovery failed after {recovery_attempts} attempts. "
                f"LLM fallback request also failed: {e}. Original error: {error_msg}"
            )
            return self._build_task_result(
                task,
                status="fallback_unresolved",
                content=message,
                display_text=message,
                error_message=error_msg,
                recovery_attempts=recovery_attempts,
                used_llm_fallback=True,
                fallback=fallback,
            )

        cleaned_response = response.strip()
        first_line = cleaned_response.splitlines()[0].strip().lower() if cleaned_response else ""
        remaining = cleaned_response.split("\n", 1)[1].strip() if "\n" in cleaned_response else cleaned_response

        if first_line == "can_resolve_with_llm: yes":
            fallback = LlmFallbackResult(
                attempted=True,
                can_replace_execution=True,
                original_error=error_msg,
                answer=remaining,
                raw_response=cleaned_response,
            )
            message = (
                f"Execution failed after {recovery_attempts} recovery attempt(s). "
                f"Returned an LLM fallback answer instead; no real execution happened.\n{remaining}"
            )
            return self._build_task_result(
                task,
                status="fallback_answered",
                content=remaining,
                display_text=message,
                error_message=error_msg,
                recovery_attempts=recovery_attempts,
                used_llm_fallback=True,
                fallback=fallback,
            )

        llm_note = remaining if first_line == "can_resolve_with_llm: no" else cleaned_response
        fallback = LlmFallbackResult(
            attempted=True,
            can_replace_execution=False,
            original_error=error_msg,
            answer=llm_note,
            raw_response=cleaned_response,
        )
        message = (
            f"Auto-recovery failed after {recovery_attempts} attempts. "
            f"LLM fallback could not safely replace execution. Original error: {error_msg}\n{llm_note}"
        )
        return self._build_task_result(
            task,
            status="fallback_unresolved",
            content=llm_note,
            display_text=message,
            error_message=error_msg,
            recovery_attempts=recovery_attempts,
            used_llm_fallback=True,
            fallback=fallback,
        )

    def _handle_failure(self, task, error_msg, current_depth, attempt=1) -> TaskExecutionResult:
        print(f"  [Failure Handler] 任务失败，正在分析原因并制定对策... 尝试次数: {attempt}, 错误: {error_msg}...")

        if current_depth > self.max_depth + 2:
            capped_error = f"Failure recovery failed: Max depth exceeded. Original error: {error_msg}"
            if self._should_fallback_to_llm(task, capped_error):
                return self._request_llm_fallback(task, capped_error, max(1, attempt - 1))
            return self._build_task_result(task, status="failed", content=capped_error, display_text=capped_error,
                                           error_message=capped_error, recovery_attempts=max(0, attempt - 1))

        if attempt > self.max_recovery_attempts:
            if self._should_fallback_to_llm(task, error_msg):
                return self._request_llm_fallback(task, error_msg, self.max_recovery_attempts)
            message = f"Auto-recovery failed after {self.max_recovery_attempts} attempts. Original error: {error_msg}"
            return self._build_task_result(task, status="failed", content=message, display_text=message,
                                           error_message=error_msg, recovery_attempts=self.max_recovery_attempts)

        tool = task.get('tool')
        prompt = f"""
        The following task failed during execution:
        Task Description: {task.get('description')}
        Tool Used: {tool}
        Original Code/Command:
        ```
        {task.get('code')}
        ```
        Error Message:
        {error_msg}

        Analyze the error and decide the best course of action:

        OPTION 1: If it is a simple syntax error, logic error, or typo in the code:
        Provide the corrected code inside a code block.
        Format:
        ```code
        <corrected_code_content>
        ```

        OPTION 2: If the error is due to missing environment, missing dependencies (e.g., ModuleNotFoundError), or requires pre-requisite steps (e.g., installing a package, creating a directory):
        Provide a JSON plan to fix the environment and then retry the original task.
        Format:
        ```json
        {{
            "plan": [
                {{ "task_id": 1, "tool": "Shell_Command", "description": "Install missing library", "code": "pip install <library>" }},
                {{ "task_id": 2, "tool": "{tool}", "description": "Retry original task", "code": "<original_or_fixed_code>" }}
            ]
        }}
        ```

        Return ONLY the content in one of the specified formats.
        """
        response = self.call_deepseek(prompt, system_prompt="You are an expert troubleshooter.", think=True)

        recovery_plan = self._extract_recovery_plan(response)
        if recovery_plan:
            print(f"  [Failure Handler] 识别为环境/复杂问题，执行补救计划 ({len(recovery_plan.get('plan', []))} 步)...")
            recovery_results = self.execute_plan(recovery_plan, current_depth + 1, return_structured=True)
            recovery_summary = self._stringify_results(recovery_results)
            if not any(item.status in FAILURE_STATUSES for item in recovery_results):
                return self._build_task_result(
                    task,
                    status="recovered",
                    content=recovery_summary,
                    display_text=recovery_summary,
                    recovery_attempts=attempt,
                    metadata={"recovery_plan": recovery_plan, "recovery_statuses": [item.status for item in recovery_results]},
                )
            return self._handle_failure(task, recovery_summary, current_depth + 1, attempt + 1)

        fixed_code = self._extract_fixed_code(response)
        if fixed_code:
            print(f"  [Failure Handler] 识别为代码错误，尝试执行修复后的代码...")
            if tool == "Python_Script":
                retry_result = _run_python_sandbox(fixed_code)
            elif tool == "Shell_Command":
                retry_result = _run_shell_command(fixed_code, self.ai_type)
            else:
                retry_result = f"Unknown tool: {tool}"

            if not self._is_failure_result(retry_result):
                return self._build_task_result(
                    task,
                    status="recovered",
                    content=retry_result,
                    display_text=retry_result,
                    recovery_attempts=attempt,
                    metadata={"fixed_code": fixed_code},
                )
            return self._handle_failure(task, retry_result, current_depth + 1, attempt + 1)

        unusable_response_error = f"Auto-recovery response was unusable. Last known error: {error_msg}"
        return self._handle_failure(task, unusable_response_error, current_depth + 1, attempt + 1)

    def execute_plan(self, plan, current_depth=1, return_structured=False):
        tasks = plan.get("plan", [])
        if not tasks:
            return []

        sorted_tasks = sorted(tasks, key=lambda x: x.get('task_id', 0))
        execution_results = []

        for task in sorted_tasks:
            task_id = task.get('task_id')
            tool = task.get('tool')
            desc = task.get('description')
            code = task.get('code')
            print(f"\n[执行中] 任务 {task_id} (层级 {current_depth}): {desc}")

            if tool == "Decompose_Required":
                sub_plan = self.decompose(desc, current_depth=current_depth + 1)
                sub_results = self.execute_plan(sub_plan, current_depth=current_depth + 1, return_structured=True)
                summary = self._stringify_results(sub_results)
                status = "failed" if any(item.status in FAILURE_STATUSES for item in sub_results) else "success"
                result = self._build_task_result(
                    task,
                    status=status,
                    content=summary,
                    display_text=summary,
                    error_message=summary if status == "failed" else "",
                    metadata={"sub_result_statuses": [item.status for item in sub_results]},
                )
            elif tool == "Python_Script":
                raw_result = _run_python_sandbox(code)
                result = self._handle_failure(task, raw_result, current_depth) if self._is_failure_result(raw_result) else self._build_task_result(task, status="success", content=raw_result, display_text=raw_result)
            elif tool == "Shell_Command":
                raw_result = _run_shell_command(code, self.ai_type)
                result = self._handle_failure(task, raw_result, current_depth) if self._is_failure_result(raw_result) else self._build_task_result(task, status="success", content=raw_result, display_text=raw_result)
            elif tool == "DeepSeek_LLM":
                raw_result = self.call_deepseek(desc, system_prompt="你是一个专业助手，请根据要求完成任务。", think=True)
                result = self._build_task_result(task, status="success", content=raw_result, display_text=raw_result)
            else:
                message = f"Unknown tool: {tool}"
                result = self._build_task_result(task, status="failed", content=message, display_text=message, error_message=message)

            self.results_cache[task_id] = result
            self._persist_task_result(task, result, depth=current_depth, input_code=code)
            execution_results.append(result)

        return execution_results if return_structured else [item.to_log_string() for item in execution_results]

    def summarize(self, user_query, execution_results):
        """
        根据任务执行结果生成最终回复
        """
        print("\n[总结] 正在生成最终报告...")

        if not execution_results:
            final_report = "No tasks were executed."
            self._persist_output(
                stage='summary',
                status='success',
                content=final_report,
                display_text=final_report,
                tool='DeepSeek_LLM',
                description=user_query,
            )
            return final_report

        context = self._stringify_results(execution_results)

        prompt = f"""
        User Request: {user_query}

        Execution Results of Sub-tasks:
        {context}

        Please provide a comprehensive summary and final answer to the user's request based on the execution results above.
        If the request was to perform an action, confirm whether it was successful.
        """

        final_report = self.call_deepseek(
             prompt,
             system_prompt="You are a helpful assistant summarizing task results.",
             think=True,
         )
        self._persist_output(
            stage='summary',
            status='success',
            content=final_report,
            display_text=final_report,
            tool='DeepSeek_LLM',
            description=user_query,
            metadata={'execution_result_count': len(execution_results)},
        )
        return final_report


if __name__ == '__main__':
    agent = TaskAgent(ai_type=AiType.DEEPSEEK)
    # user_query = "分析一下目前的行情趋势并给我建议"
    user_query = "删除邮箱AuspiciousChan@qq.com的中所有Apple Developer发送的邮件。"
    final_report = agent.execute_task(user_query)
    print(f"\n--- Final Report ---\n{final_report}")
