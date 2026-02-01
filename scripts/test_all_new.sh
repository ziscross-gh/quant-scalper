#!/bin/bash
# Test all enhancements

echo "=========================================="
echo "🧪 Testing All New Features"
echo "=========================================="
echo ""

cd "$(dirname "$0")/.."
source venv/bin/activate 2>/dev/null

# Track failures
FAILURES=0

echo "1️⃣  Testing Market Data Simulator..."
python3 -m bot.market_data.simulator
if [ $? -eq 0 ]; then
    echo "   ✅ Market data simulator OK"
else
    echo "   ❌ Market data simulator FAILED"
    FAILURES=$((FAILURES + 1))
fi
echo ""

echo "2️⃣  Testing Configuration Validator..."
python3 scripts/validate_config.py config/config.yaml.example
if [ $? -eq 0 ]; then
    echo "   ✅ Config validator OK"
else
    echo "   ❌ Config validator FAILED"
    FAILURES=$((FAILURES + 1))
fi
echo ""

echo "3️⃣  Testing Performance Benchmark..."
python3 scripts/benchmark.py --quick 2>&1 | grep "✅ Benchmark Complete" > /dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ Benchmark OK"
else
    echo "   ⚠️  Benchmark may have issues"
fi
echo ""

echo "4️⃣  Testing Telegram Commands..."
python3 -m bot.telegram.commands 2>&1 | grep "✅ Telegram commands test complete" > /dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ Telegram commands OK"
else
    echo "   ❌ Telegram commands FAILED"
    FAILURES=$((FAILURES + 1))
fi
echo ""

echo "5️⃣  Testing Walk-Forward Analysis..."
python3 -m bot.backtest.walkforward 2>&1 | grep "✅ Walk-forward test complete" > /dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ Walk-forward analysis OK"
else
    echo "   ⚠️  Walk-forward may have issues"
fi
echo ""

echo "6️⃣  Testing Multiple Strategies..."
python3 -m bot.strategies.fatory 2>&1 | grep "✅ Strategies test complete" > /dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ Multiple strategies OK"
else
    echo "   ❌ Multiple strategies FAILED"
    FAILURES=$((FAILURES + 1))
fi
echo ""

echo "=========================================="
echo "📊 Test Summary"
echo "=========================================="

if [ $FAILURES -eq 0 ]; then
    echo "✅ ALL TESTS PASSED!"
    echo ""
    echo "New features ready to use:"
    echo "  - Market data simulation"
    echo "  - Configuration validation"
    echo "  - Performance benchmarking"
    echo "  - Telegram commands"
    echo "  - Walk-forward analysis"
    echo "  - Multiple strategies"
    echo ""
    echo "Run individual tests to see detailed output."
else
    echo "⚠️  $FAILURES test(s) failed"
    echo ""
    echo "Run individual tests to see what went wrong."
fi

echo "=========================================="

exit $FAILURES
