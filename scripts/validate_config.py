#!/usr/bin/env python3
"""
Configuration Validator

Validates bot configuration before running.
"""
import sys
sys.path.insert(0, '.')

from bot.config import Config
import yaml


class ConfigValidator:
    """Validates bot configuration"""

    ERRORS = "ERROR"
    WARNINGS = "WARNING"
    INFO = "INFO"

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.issues = []

    def validate(self) -> bool:
        """Run all validations and return True if valid."""
        print("=" * 60)
        print("🔍 Configuration Validator")
        print("=" * 60)
        print()

        try:
            # Load config
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)

            # Run validations
            self._validate_structure(config_data)
            self._validate_strategy(config_data)
            self._validate_risk(config_data)
            self._validate_ibkr(config_data)
            self._validate_telegram(config_data)

            # Summary
            print()
            print("=" * 60)
            print("VALIDATION SUMMARY")
            print("=" * 60)

            errors = [i for i in self.issues if i[0] == self.ERRORS]
            warnings = [i for i in self.issues if i[0] == self.WARNINGS]
            info = [i for i in self.issues if i[0] == self.INFO]

            print(f"\n✅ {len(info)} informational messages")
            print(f"⚠️  {len(warnings)} warnings")
            print(f"❌ {len(errors)} errors\n")

            if errors:
                print("📋 Errors:")
                for _, message in errors:
                    print(f"   ❌ {message}")
                print()
                return False

            if warnings:
                print("⚠️  Warnings:")
                for _, message in warnings:
                    print(f"   ⚠️  {message}")
                print()

            print("✅ Configuration is valid!")
            return True

        except FileNotFoundError:
            print(f"❌ Error: Config file not found: {self.config_path}")
            return False
        except yaml.YAMLError as e:
            print(f"❌ Error: Invalid YAML: {e}")
            return False

    def _add_issue(self, level: str, message: str):
        """Add an issue to the list."""
        self.issues.append((level, message))

    def _validate_structure(self, config: dict):
        """Validate required sections exist."""
        required_sections = ['strategy', 'risk', 'ibkr', 'alerts']

        for section in required_sections:
            if section not in config:
                self._add_issue(self.ERRORS, f"Missing section: [{section}]")
            elif not isinstance(config[section], dict):
                self._add_issue(self.ERRORS, f"Section [{section}] should be a dictionary")

    def _validate_strategy(self, config: dict):
        """Validate strategy parameters."""
        if 'strategy' not in config:
            return

        strategy = config['strategy']

        # Lookback period
        lookback = strategy.get('lookback_period', 0)
        if lookback < 5:
            self._add_issue(self.WARNINGS,
                          f"Lookback period ({lookback}) is very low, recommend 15+")
        elif lookback > 50:
            self._add_issue(self.WARNINGS,
                          f"Lookback period ({lookback}) is very high, recommend 30 or less")

        # Z thresholds
        z_entry = strategy.get('z_threshold_entry', 0)
        z_exit = strategy.get('z_threshold_exit', 0)

        if z_entry <= z_exit:
            self._add_issue(self.ERRORS,
                          f"Z-Entry ({z_entry}) must be greater than Z-Exit ({z_exit})")

        if z_entry < 1.0:
            self._add_issue(self.WARNINGS,
                          f"Z-Entry ({z_entry}) is very low, will trigger often")
        elif z_entry > 3.0:
            self._add_issue(self.WARNINGS,
                          f"Z-Entry ({z_entry}) is very high, may miss opportunities")

        if z_exit < 0.1:
            self._add_issue(self.WARNINGS,
                          f"Z-Exit ({z_exit}) is very low, may exit too early")

    def _validate_risk(self, config: dict):
        """Validate risk parameters."""
        if 'risk' not in config:
            return

        risk = config['risk']

        # Position size
        max_pos = risk.get('max_position_size', 0)
        if max_pos < 1:
            self._add_issue(self.ERRORS,
                          f"Max position size ({max_pos}) must be at least 1")
        elif max_pos > 5:
            self._add_issue(self.WARNINGS,
                          f"Max position size ({max_pos}) is high for paper trading")

        # Stop loss / take profit
        sl = risk.get('stop_loss_dollars', 0)
        tp = risk.get('take_profit_dollars', 0)

        if sl < 0:
            self._add_issue(self.ERRORS,
                          f"Stop loss ({sl}) must be positive")

        if tp < 0:
            self._add_issue(self.ERRORS,
                          f"Take profit ({tp}) must be positive")

        if tp <= sl:
            self._add_issue(self.WARNINGS,
                          f"Take profit ({tp}) <= stop loss ({sl}), risking more than reward")

        risk_reward = tp / sl if sl > 0 else 0
        if risk_reward < 1.5:
            self._add_issue(self.WARNINGS,
                          f"Risk/Reward ratio ({risk_reward:.2f}) is low, recommend > 1.5")

        # Daily loss limit
        daily_loss = risk.get('max_daily_loss', 0)
        if daily_loss < 0:
            self._add_issue(self.ERRORS,
                          f"Daily loss limit ({daily_loss}) must be positive")
        elif daily_loss > 1000:
            self._add_issue(self.WARNINGS,
                          f"Daily loss limit (${daily_loss}) is high for paper trading")

        # Consecutive losses
        cons_losses = risk.get('max_consecutive_losses', 0)
        if cons_losses < 2:
            self._add_issue(self.WARNINGS,
                          f"Max consecutive losses ({cons_losses}) is low")
        elif cons_losses > 5:
            self._add_issue(self.WARNINGS,
                          f"Max consecutive losses ({cons_losses}) is high")

        # Position duration
        duration = risk.get('max_position_duration_hours', 0)
        if duration < 0.5:
            self._add_issue(self.WARNINGS,
                          f"Position duration ({duration}h) is very short")
        elif duration > 8:
            self._add_issue(self.WARNINGS,
                          f"Position duration ({duration}h) is very long")

    def _validate_ibkr(self, config: dict):
        """Validate IBKR configuration."""
        if 'ibkr' not in config:
            return

        ibkr = config['ibkr']

        # Account
        account = ibkr.get('account', '')
        if not account:
            self._add_issue(self.ERRORS,
                          "IBKR account ID is required")
        elif not account.startswith('DU'):
            self._add_issue(self.WARNINGS,
                          f"Account ID ({account}) doesn't look like paper account (should start with DU)")

        # Paper trading check
        paper = ibkr.get('paper', True)
        if not paper:
            self._add_issue(self.ERRORS,
                          "⚠️  LIVE TRADING MODE ENABLED! Set paper: true for safety!")

        # Port
        port = ibkr.get('port', 0)
        if port not in [4001, 4002]:
            self._add_issue(self.WARNINGS,
                          f"Port ({port}) is unusual (paper=4002, live=4001)")

        # Host
        host = ibkr.get('host', '')
        if not host:
            self._add_issue(self.INFO, "IBKR host not set, will use 127.0.0.1")

    def _validate_telegram(self, config: dict):
        """Validate Telegram configuration."""
        if 'alerts' not in config:
            return

        alerts = config.get('alerts', {})
        telegram = alerts.get('telegram', {})

        enabled = telegram.get('enabled', False)
        bot_token = telegram.get('bot_token', '')
        chat_id = telegram.get('chat_id', '')

        if enabled:
            if not bot_token or bot_token == 'YOUR_BOT_TOKEN':
                self._add_issue(self.ERRORS,
                              "Telegram enabled but bot_token not set")
            elif not bot_token.startswith('${'):
                # It's a static token, check format
                if not bot_token.startswith(('1234567890', '111')):
                    self._add_issue(self.WARNINGS,
                                  "Bot token format looks unusual")

            if not chat_id or chat_id == 'YOUR_CHAT_ID':
                self._add_issue(self.ERRORS,
                              "Telegram enabled but chat_id not set")
        else:
            self._add_issue(self.INFO, "Telegram alerts are disabled")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate bot configuration")
    parser.add_argument("config", help="Path to config file")
    parser.add_argument("--fix", action="store_true",
                       help="Attempt to fix issues (future feature)")

    args = parser.parse_args()

    validator = ConfigValidator(args.config)
    valid = validator.validate()

    sys.exit(0 if valid else 1)


if __name__ == "__main__":
    main()
