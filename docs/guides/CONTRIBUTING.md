# Contributing to Hyperliquid Multi-Agent System

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## 🚀 Quick Start

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/yourusername/hyperliquid-multi-agent.git
   cd hyperliquid-multi-agent
   ```
3. **Set up the development environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 📋 Development Guidelines

### Code Style

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Write docstrings for all public functions and classes
- Keep functions focused and single-purpose

### Testing

- Write tests for all new features
- Ensure all tests pass before submitting PR:
  ```bash
  pytest tests/ -v
  ```
- Aim for >80% code coverage

### Commit Messages

Use clear, descriptive commit messages:
```
feat: Add new caching strategy for candle data
fix: Resolve circuit breaker timeout issue
docs: Update architecture documentation
test: Add tests for orchestrator routing
```

## 🔒 Security

**NEVER commit:**
- API keys or credentials
- `.env` files (use `.env.example` with placeholders)
- Private keys or certificates
- Personal information

**Before committing:**
```bash
# Check for exposed secrets
grep -r "sk-ant-api" --include="*.py" --include="*.json" .
# Should return no results from source files
```

## 🧪 Testing Your Changes

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test file
pytest tests/agents/test_orchestrator_agent.py -v

# Run linting
flake8 agents/ core/ skills/
```

## 📝 Pull Request Process

1. **Update documentation** if you've changed APIs or added features
2. **Add tests** for new functionality
3. **Run the full test suite** and ensure all tests pass
4. **Update README.md** if needed
5. **Create your Pull Request** with a clear description:
   - What problem does it solve?
   - What approach did you take?
   - Any breaking changes?
   - Screenshots (if applicable)

### PR Checklist

- [ ] Tests pass locally
- [ ] Code follows project style guidelines
- [ ] Documentation updated
- [ ] No credentials or secrets exposed
- [ ] Commit messages are clear
- [ ] PR description explains changes

## 🐛 Reporting Bugs

Use GitHub Issues to report bugs. Include:
- **Description** of the issue
- **Steps to reproduce**
- **Expected behavior**
- **Actual behavior**
- **Environment** (OS, Python version, etc.)
- **Error messages** or logs

## 💡 Feature Requests

We welcome feature requests! Please:
- Check existing issues first
- Explain the use case
- Describe the proposed solution
- Discuss alternatives you've considered

## 🎯 Areas for Contribution

We especially welcome contributions in:
- **Additional Agents** - New specialized agents for specific tasks
- **Skills** - New data collection or processing skills
- **Testing** - Improving test coverage
- **Documentation** - Tutorials, guides, examples
- **Performance** - Optimization improvements
- **Error Handling** - Better error recovery strategies

## 📚 Resources

- [Architecture Documentation](docs/architecture/ARCHITECTURE.md)
- [Setup Guide](docs/setup/QUICKSTART.md)
- [Development Plan](docs/development/DEVELOPMENT_PLAN.md)
- [Hyperliquid API Docs](https://hyperliquid.gitbook.io/hyperliquid-docs/)
- [Anthropic Claude Docs](https://docs.anthropic.com/)

## 🤝 Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Assume good intentions

## 📞 Getting Help

- **GitHub Issues** - For bugs and feature requests
- **GitHub Discussions** - For questions and general discussion
- **Documentation** - Check the [docs/](docs/) directory first

## 🙏 Thank You!

Every contribution, no matter how small, is valuable and appreciated!
