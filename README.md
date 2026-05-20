## What It Does

1. **Reads** the GitHub issue — title, body, comments
2. **Clones** the repository and searches the codebase intelligently
3. **Identifies** the exact buggy file, function, and lines
4. **Generates** a minimal code patch
5. **Runs** the full test suite in an isolated Docker sandbox
6. **Reflects** on failures and retries with a fundamentally different strategy (up to 3×)
7. **Opens** a Pull Request with a professional description