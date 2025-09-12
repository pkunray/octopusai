## OctopusAI
OctopusAI contains many AI agents. For example, an APR workflow.

## Setup

1. **Set your OpenAI API key**:

```bash
   export OPENAI_API_KEY='your-openai-api-key'
```

## Commands

To view all available commands, run:
```bash
   uv run -m octopusai.cli --help
```

To run an APR on a sepcific PR using hierarchical multi-agent mode:
```bash
   uv run -m octopusai.cli run bug {Repo in owner/repo format} {PR ID} {feature-branch} -m hierarchical
   # examle:
   uv run -m octopusai.cli run bug pkunray/pr-based-eval-quixbugs 15 feat-breadth-first-search -m hierarchical
```