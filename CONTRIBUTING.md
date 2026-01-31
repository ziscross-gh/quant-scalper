# Contributing to Quant Scalper

Thank you for your interest in contributing! This bot is designed for educational purposes and systematic trading.

## Development Setup

1. Fork the repository
2. Clone your fork
3. Run setup: `./scripts/setup.sh`
4. Create a branch: `git checkout -b feature/your-feature`

## Code Style

### Python
- Follow PEP 8
- Use type hints where possible
- Add docstrings to public methods
- Run tests before committing: `pytest`

### Rust
- Follow Rust conventions (`cargo fmt`)
- Add tests for new functionality
- Run `cargo clippy` before committing

## Testing

### Unit Tests
```bash
pytest tests/unit/ -v
```

### Integration Tests (requires IB Gateway)
```bash
pytest tests/integration/ -v -m paper
```

### Rust Tests
```bash
cd rust && cargo test
```

## Pull Request Process

1. Update documentation if needed
2. Add tests for new features
3. Ensure all tests pass
4. Update CHANGELOG.md
5. Submit PR with clear description

## Areas for Contribution

### High Priority
- Additional risk management features
- Improved backtest engine
- Dashboard UI improvements
- Additional strategy implementations

### Medium Priority
- Performance optimizations
- Better error handling
- More comprehensive tests
- Documentation improvements

### Low Priority
- Additional alert channels (Discord, email)
- Multi-asset support
- Machine learning parameter optimization

## Safety First

When contributing:
- Never commit actual API keys or secrets
- Always default to paper trading in examples
- Add warnings for risky features
- Document all configuration changes

## Questions?

Open an issue for:
- Bug reports
- Feature requests
- Documentation improvements
- General questions

---

**Remember**: This is a trading bot. Any changes should prioritize safety and risk management over performance.
