import json
import subprocess
import io
import contextlib
import re
from home.ai.AiApi import AiApiFactory, AiType
from home.ai.CodeReviewer import CodeReviewer
from home.ai import Constants


def _run_python_sandbox(code):
    """
    模拟 Python 沙箱执行
    """
    print(f"  [Python] 执行 code: {code[:1000]}...")

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

    # 使用 CodeReviewer 进行安全审查
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
            timeout=60  # 增加超时时间
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Shell command failed with error:\n{e.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "Shell command timed out."
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"


class TaskAgent:
    def __init__(self, ai_type: AiType = AiType.DEEPSEEK, max_depth=3):
        self.ai_type = ai_type
        self.max_depth = max_depth
        self.results_cache = {}

    def call_deepseek(self, prompt, system_prompt=Constants.SYSTEM_PROMPT_PLANNER, think=True):
        instance = AiApiFactory.get(self.ai_type)
        return instance.query(query=prompt, system_prompt=system_prompt, think=think)

    def decompose(self, request_text, current_depth=1):
        if current_depth > self.max_depth:
            print(f"达到最大深度 {self.max_depth}，停止拆解。")
            return {"plan": []}

        print(f"层级 {current_depth}: 正在拆解任务 -> {request_text[:30]}...")
        llm_response = self.call_deepseek(request_text, system_prompt=Constants.SYSTEM_PROMPT_PLANNER, think=True)

        try:
            start_index = llm_response.index("{")
            end_index = llm_response.rindex("}") + 1
            plan_json_str = llm_response[start_index:end_index]
            plan = json.loads(plan_json_str)
            return plan
        except (json.JSONDecodeError, ValueError):
            print("LLM 返回格式错误，尝试二次修正...")
            return {"plan": []}

    def _handle_failure(self, task, error_msg, current_depth):
        """
        智能错误处理：
        1. 简单错误 -> 修复代码
        2. 环境/依赖错误 -> 生成补救计划 (Re-planning)
        """
        print(f"  [Failure Handler] 任务失败，正在分析原因并制定对策... 错误: {error_msg[:100]}...")

        if current_depth > self.max_depth + 2:  # 防止无限递归修复
            return f"Failure recovery failed: Max depth exceeded. Original error: {error_msg}"

        task_desc = task.get('description')
        original_code = task.get('code')
        tool = task.get('tool')

        prompt = f"""
        The following task failed during execution:
        Task Description: {task_desc}
        Tool Used: {tool}
        Original Code/Command:
        ```
        {original_code}
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

        # 尝试解析 JSON 补救计划
        if "```json" in response:
            try:
                start = response.index("```json") + 7
                end = response.rindex("```")
                plan_str = response[start:end].strip()
                recovery_plan = json.loads(plan_str)

                print(
                    f"  [Failure Handler] 识别为环境/复杂问题，执行补救计划 ({len(recovery_plan.get('plan', []))} 步)...")
                # 递归执行补救计划
                recovery_results = self.execute_plan(recovery_plan, current_depth + 1)

                if isinstance(recovery_results, list):
                    return "; ".join(recovery_results)
                return recovery_results

            except Exception as e:
                print(f"  [Failure Handler] 解析补救计划失败: {e}")

        # 尝试解析修复后的代码
        code_match = re.search(r"```(?:code|python|bash)?\n(.*?)```", response, re.DOTALL)
        if code_match:
            fixed_code = code_match.group(1).strip()
            print(f"  [Failure Handler] 识别为代码错误，尝试执行修复后的代码...")

            if tool == "Python_Script":
                return _run_python_sandbox(fixed_code)
            elif tool == "Shell_Command":
                return _run_shell_command(fixed_code, self.ai_type)

        return f"Auto-recovery failed. Original error: {error_msg}"

    def execute_plan(self, plan, current_depth=1):
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

            result = None
            if tool == "Decompose_Required":
                sub_plan = self.decompose(desc, current_depth=current_depth + 1)
                sub_results = self.execute_plan(sub_plan, current_depth=current_depth + 1)
                result = "; ".join(sub_results) if isinstance(sub_results, list) else sub_results

            elif tool == "Python_Script":
                result = _run_python_sandbox(code)
            elif tool == "Shell_Command":
                result = _run_shell_command(code, self.ai_type)
            elif tool == "DeepSeek_LLM":
                result = self.call_deepseek(desc, system_prompt="你是一个专业助手，请根据要求完成任务。", think=True)
            else:
                result = f"Unknown tool: {tool}"

            # 失败检测与智能恢复
            if isinstance(result, str) and (
                    "Error" in result or "failed" in result or "Exception" in result or "not found" in result):
                if tool in ["Python_Script", "Shell_Command"]:
                    result = self._handle_failure(task, result, current_depth)

            self.results_cache[task_id] = result
            execution_results.append(f"Task {task_id} ({tool}): {result}")

        return execution_results

    def summarize(self, user_query, execution_results):
        """
        根据任务执行结果生成最终回复
        """
        print("\n[总结] 正在生成最终报告...")

        if not execution_results:
            return "No tasks were executed."

        if isinstance(execution_results, str):
            context = execution_results
        else:
            context = "\n".join(execution_results)

        prompt = f"""
        User Request: {user_query}

        Execution Results of Sub-tasks:
        {context}

        Please provide a comprehensive summary and final answer to the user's request based on the execution results above.
        If the request was to perform an action, confirm whether it was successful.
        """

        return self.call_deepseek(prompt, system_prompt="You are a helpful assistant summarizing task results.",
                                  think=True)


if __name__ == '__main__':
    agent = TaskAgent(ai_type=AiType.DEEPSEEK)
    # user_query = "分析一下目前的行情趋势并给我建议"
    user_query = "删除邮箱AuspiciousChan@qq.com的中所有Apple Developer发送的邮件。"
    initial_plan = agent.decompose(user_query)
    results = agent.execute_plan(initial_plan)

    final_report = agent.summarize(user_query, results)
    print(f"\n--- Final Report ---\n{final_report}")
