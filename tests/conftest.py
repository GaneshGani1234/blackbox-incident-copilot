"""Force offline mode for every test, before any app module is imported.

Even if a developer has a real .env with Hindsight and Groq keys, tests must never call them.
"""
import os

os.environ["MEMORY_BACKEND"] = "local"
os.environ["LLM_MODE"] = "mock"
