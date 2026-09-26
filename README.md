# Ai Nexus Pro

Symbiotic AI agent nexus — orchestrated intelligence with security, memory, and chaos engineering.

![Language](https://img.shields.io/badge/Language-Python-blue)
![Status](https://img.shields.io/badge/Status-Active-success)
![License](https://img.shields.io/badge/License-MIT-green)

## 🚀 Overview

Welcome to the **Ai Nexus Pro** repository. This project is built to deliver a robust and scalable solution tailored to modern development standards.

## ✨ Features

- **High Performance:** Optimized for speed and efficiency.
- **Scalable Architecture:** Designed to grow with your needs.
- **Clean Codebase:** Follows best practices and industry standards.
- **Secure by Default:** Engineered with security in mind.

## 🛠️ Prerequisites

Ensure you have the following installed in your environment before proceeding:
- Appropriate runtime/compiler for `Python`
- Standard development tools

## 📦 Installation

Follow standard installation steps for `Python` to set up the project locally:

1. Clone the repository:
   ```bash
   git clone https://github.com/Shivay00001/ai-nexus-pro.git
   ```
2. Navigate to the project directory:
   ```bash
   cd ai-nexus-pro
   ```
3. Create a virtual environment and install:
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -e .
   ```
4. Initialize the database:
   ```bash
   python -m goatclaw.cli init
   ```

## 🔑 Configuration (environment variables)

GOATCLAW never ships with API keys and never simulates LLM output.

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | LLM provider: OpenAI (default provider) |
| `ANTHROPIC_API_KEY` | LLM provider: Anthropic |
| `DEEPSEEK_API_KEY` | LLM provider: DeepSeek |
| `KIMI_API_KEY` / `MOONSHOT_API_KEY` | LLM provider: Kimi/Moonshot |
| `NVIDIA_API_KEY` | LLM provider: NVIDIA |
| `GOATCLAW_LLM_PROVIDER` | Select provider: `openai`, `anthropic`, `deepseek`, `kimi`, `nvidia` |
| `GOATCLAW_LLM_MODEL` | Override the model name (default `gpt-4`) |
| `SERPER_API_KEY` | Web search: Serper.dev (preferred) |
| `TAVILY_API_KEY` | Web search: Tavily |
| `DATABASE_URL` | Database URL (default: local `sqlite+aiosqlite` file) |
| `REDIS_URL` | Task queue / broker (optional; in-memory fallback when absent) |

Outbound HTTP uses `aiohttp` with `trust_env=True`, so standard
`HTTP(S)_PROXY` variables are honored for search and LLM calls.

## ⚠️ Honest degradation (no keys, no fakes)

Without an LLM API key the system does **not** invent results:

- Code generation / review / refactor / test generation, document
  analysis, data analysis, and LLM planning return an explicit
  `degraded` result naming the missing key (e.g. set `OPENAI_API_KEY`)
  instead of simulated output.
- Web search tries Serper → Tavily → free DuckDuckGo Instant Answer.
  If no provider returns results, the result is `degraded` with
  `"Web search unavailable: set SERPER_API_KEY or TAVILY_API_KEY"` --
  never placeholder `example.com` links.
- `python -m goatclaw.cli run "<goal>"` without a key prints
  `[DEGRADED]` with the reason instead of pretending to succeed.
- The demo (`python -m goatclaw.cli demo`) runs 4/4 with zero keys
  using only real no-LLM capabilities: live web search, sandboxed file
  write, and local data transform/clean.

## 💻 Usage

Run the project using standard execution commands for `Python`. Ensure all environment variables and configurations are set prior to execution.

```bash
python -m goatclaw.cli init     # create tables, seed demo user
python -m goatclaw.cli demo     # no-key demo: real search + file + data ops
python -m goatclaw.cli run "Research vector databases"
pytest                          # full test suite
```

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the issues page.

## 📝 License

This project is licensed under standard terms.
