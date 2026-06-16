from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]
CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

CHROMA_PATH: Path = Path(os.getenv("CHROMA_PATH", "data/chroma"))
RUNS_PATH: Path = Path(os.getenv("RUNS_PATH", "data/runs"))
REPORTS_PATH: Path = Path(os.getenv("REPORTS_PATH", "data/reports"))
PROMPTS_PATH: Path = Path(os.getenv("PROMPTS_PATH", "data/prompts"))
REPLAYS_INBOX: Path = Path(os.getenv("REPLAYS_INBOX", "data/replays/inbox"))
LOGS_PATH: Path = Path(os.getenv("LOGS_PATH", "logs"))
REFLECTIONS_PATH: Path = Path(os.getenv("REFLECTIONS_PATH", "data/reflections"))
KNOWLEDGE_PATH: Path = Path(os.getenv("KNOWLEDGE_PATH", "data/knowledge"))

EVALUATOR_PASS_THRESHOLD: float = 0.7
EVALUATOR_CRITERIA_COUNT: int = 11
RUN_TIMEOUT_SECONDS: int = 120

# AI player sentinel value as documented in mgz — must not change silently
AI_PLAYER_SENTINEL: int = 0xFFFFFFFF
