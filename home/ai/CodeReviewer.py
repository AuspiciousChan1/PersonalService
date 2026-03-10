from home.ai.AiApi import AiType


class CodeReviewer:
    DANGEROUS_KEYWORDS = ["rm -rf", "mkfs", "dd ", ":(){:|:&};:", "> /dev/sda", "mv /", "chmod -R 777 /"]

    @staticmethod
    def safe_check(command: str) -> tuple[bool, str]:
        """
        Performs a safety check on the command.
        Returns (is_safe, reason).
        """
        # 1. Static Keyword Analysis
        for keyword in CodeReviewer.DANGEROUS_KEYWORDS:
            if keyword in command:
                return False, f"Detected dangerous keyword: '{keyword}'"

        # 2. (Optional) LLM-based Semantic Analysis
        # If the command is complex, we could ask the LLM.
        # For now, we'll stick to a basic heuristic:
        # If it contains 'sudo', it requires manual approval (simulated here as unsafe for auto-execution)
        if "sudo" in command:
             return False, "Command requires 'sudo' privileges, which is restricted."

        return True, "Passed safety check"

    @staticmethod
    def review_and_approve(command: str, ai_type: AiType = AiType.DEEPSEEK) -> bool:
        """
        Uses LLM to review the command for potential side effects if static check passes but it looks suspicious.
        For this implementation, we will trust the static check + a prompt to the LLM.
        """
        is_safe, reason = CodeReviewer.safe_check(command)
        if not is_safe:
            print(f"[CodeReview] Blocked: {reason}")
            return False

        # Double check with LLM for intent
        api = AiApiFactory.get(ai_type)
        prompt = f"""
        You are a security auditor. A user wants to execute the following shell command on their local machine:
        Command: `{command}`
        
        Is this command safe to execute? It should not delete system files, format drives, or exfiltrate data.
        Reply with strictly "YES" or "NO".
        """
        # We use think=False for speed
        response = api.query(prompt, system_prompt="You are a strict security auditor.", think=False)
        
        if "YES" in response.upper():
            return True
        else:
            print(f"[CodeReview] LLM Blocked: {response}")
            return False
