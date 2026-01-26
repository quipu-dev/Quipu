# Quipu Monorepo

This is the development repository for **Quipu**, the "Process Archaeology" toolkit for the AI era.

## Repository Structure

- `packages/`: All independent distribution packages.
  - `pyquipu`: The entry point meta-package.
  - `pyquipu-cli`: The command-line interface.
  - `pyquipu-engine`: The Phantom State engine.
  - ... (see [DEVELOPING.md](./DEVELOPING.md) for details)
- `scripts/`: Development and maintenance scripts, including the CD Release Manager.
- `.github/`: CI/CD workflow definitions.

## Getting Started

If you are a **user**, please install Quipu via PyPI:
```bash
pip install pyquipu
```

If you are a **contributor**, please read [DEVELOPING.md](./DEVELOPING.md) for environment setup and the bootstrap workflow.

## License
Apache-2.0