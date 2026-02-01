#!/bin/bash
# Test individual bot components

echo "🧪 Testing Trading Bot Components"
echo "=================================="

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
fi

# Test 1: Configuration
echo ""
echo "Test 1: Configuration Loading"
echo "-------------------------------"
python3 -c "
import sys
sys.path.insert(0, '.')
from bot.config import Config
try:
    config = Config.load('config/config.yaml.example')
    print('✅ Config loaded')
    print(f'   Lookback period: {config.strategy.lookback_period}')
    print(f'   Max daily loss: ${config.risk.max_daily_loss}')
    print(f'   IBKR paper mode: {config.ibkr.paper}')
except Exception as e:
    print(f'❌ Error: {e}')
    sys.exit(1)
" || exit 1

# Test 2: Signal Generation
echo ""
echo "Test 2: Signal Generation"
echo "-------------------------"
python3 -m bot.core.signals || exit 1

# Test 3: Database
echo ""
echo "Test 3: Database Persistence"
echo "----------------------------"
python3 -m bot.persistence.database || exit 1

# Test 4: Circuit Breaker
echo ""
echo "Test 4: Circuit Breaker"
echo "-----------------------"
python3 -m bot.risk.circuit_breaker || exit 1

# Test 5: Contracts
echo ""
echo "Test 5: IBKR Contracts"
echo "----------------------"
python3 -c "
import sys
sys.path.insert(0, '.')
from bot.ibkr import create_mes_contract, create_sp500_contract

mes = create_mes_contract('202503')
print(f'✅ MES contract created: {mes.symbol}')
print(f'   Exchange: {mes.exchange}')
print(f'   Expiry: {mes.lastTradeDateOrContractMonth}')

spy = create_sp500_contract()
print(f'✅ SPY contract created: {spy.symbol}')
print(f'   Exchange: {spy.exchange}')
" || exit 1

echo ""
echo "=================================="
echo "✅ All component tests passed!"
echo ""
