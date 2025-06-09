# Bug Detection Crew

Analyzes given GitHub repository for bugs, security vulnerabilities, and code quality issues.

## Workflow (Fixed)

```
Input: GitHub Repository URL
    ↓
Bug Detective Agent
    • Clones the repository
    • Scans for code files
    • Analyzes code for issues
    ↓
Report Compiler Agent
    • Organizes findings
    • Creates structured report
    ↓
Output: bug_report.md
```

## Run

1. **Run the analysis:**

   ```bash
   cd /src/fastslug && uv run bug_detection_crew.py
   ```

2. **Enter a GitHub repository URL when prompted:**

   ```
   Enter GitHub repository URL: https://github.com/user/repo
   ```

3. **Check the results:**
   - The analysis will run automatically
   - Results will be saved to `bug_report.md`

## Evaluations:

The expected outcome for this task was the identification of a logical error. The crew was executed three times, with varying results:

- **First Run:** The logical error was not detected. Instead, a performance issue was reported, which was unrelated to the intended target bug.
- **Second Run:** The agent encountered a problem while attempting to read the source code using the `FileReadTool`. Ultimately, it generated a general but irrelevant bug report. This behavior reflects CrewAI's design philosophy—capturing all possible errors throughout the process to maximize success rates. However, in this case, an early failure (fail-fast strategy) might have been a more effective approach.
- **Third Run:** The expected result was successfully achieved:

> ### Logical Error in `reverse_string` Function
>
> - **File:** `/var/folders/0k/j5165xfd4v17bf5lln5pjh0m0000gn/T/bug_scan_v7qye_e8/python/reverse_string.py`
> - **Line Number:** 2–5
> - **Description:** The `reverse_string` function fails to reverse the input string as intended. It appends each character in the original order, resulting in the same string being returned.
> - **Potential Impact:** The logical flaw prevents correct string reversal and leads to incorrect outputs in dependent functionalities.
> - **Code Snippet:**
>   ```python
>   def reverse_string(s):
>       reversed_s = ""
>       for i in range(len(s)):
>           reversed_s += s[i]
>       return reversed_s
>   ```
> - **Recommended Fix:**  
>   Modify the loop to iterate in reverse:
>   ```python
>   def reverse_string(s):
>       reversed_s = ""
>       for i in range(len(s)-1, -1, -1):
>           reversed_s += s[i]
>       return reversed_s
>   ```

In summary, the success rate for this task was **33%**, with only one out of three executions yielding the correct diagnosis.

## TODO

Create a Developer agent that, based on the bug report, creates a bug-fix branch, implements the code fix, and opens a pull request. (Github Operation Tools)
Create a QA agent that, tests the fix solution from the developer agent. (Computer use Tool)
