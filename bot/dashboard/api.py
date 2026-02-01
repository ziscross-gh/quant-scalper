"""
Dashboard API - FastAPI backend for web monitoring.

Provides REST endpoints for bot status, positions, trades, and P&L.
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import uvicorn
import logging

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Quant Scalping Bot Dashboard",
    description="Real-time monitoring and backtesting results",
    version="1.0.0",
)

# Setup templates
templates_dir = Path(__file__).parent.parent.parent / "templates"
templates_dir.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(templates_dir))


# ============================================================================
# Data Access Functions
# ============================================================================

def get_bot_status() -> Dict[str, Any]:
    """
    Get current bot status.

    In production, this would connect to the running bot process.
    For now, returns mock status.
    """
    return {
        "running": False,  # Would query from bot
        "mode": "paper",
        "symbol": "MES",
        "position": 0,
        "position_type": "FLAT",
        "daily_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "trades_today": 0,
        "current_zscore": None,
        "last_update": datetime.utcnow().isoformat(),
    }


def get_positions() -> List[Dict[str, Any]]:
    """Get current positions."""
    return [
        {
            "symbol": "MES",
            "quantity": 0,
            "entry_price": 0.0,
            "current_price": 0.0,
            "unrealized_pnl": 0.0,
            "entry_time": None,
        }
    ]


def get_trades(
    limit: int = 50,
    symbol: Optional[str] = None,
    days_back: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Get trade history from database.

    Args:
        limit: Maximum trades to return
        symbol: Filter by symbol (optional)
        days_back: Only trades from last N days (optional)

    Returns:
        List of trade dictionaries
    """
    db_path = "data/trades.db"
    if not Path(db_path).exists():
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM trades WHERE 1=1"
    params = []

    if symbol:
        query += " AND symbol = ?"
        params.append(symbol)

    if days_back:
        cutoff = (datetime.utcnow() - timedelta(days=days_back)).isoformat()
        query += " AND timestamp >= ?"
        params.append(cutoff)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)

    trades = []
    for row in cursor.fetchall():
        trades.append({
            "id": row["id"],
            "timestamp": row["timestamp"],
            "symbol": row["symbol"],
            "action": row["action"],
            "quantity": row["quantity"],
            "price": row["price"],
            "pnl": row["pnl"],
            "zscore": row["zscore"],
            "exit_reason": row.get("exit_reason"),
        })

    conn.close()
    return trades


def get_pnl_metrics(
    period: str = "daily",
) -> Dict[str, Any]:
    """
    Get P&L metrics for a period.

    Args:
        period: "daily", "weekly", "monthly", or "all"

    Returns:
        P&L summary dict
    """
    trades = get_trades(limit=1000, days_back=None)

    if not trades:
        return {
            "period": period,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "max_profit": 0.0,
            "max_drawdown": 0.0,
            "profit_factor": 0.0,
        }

    # Filter by period
    now = datetime.utcnow()
    if period == "daily":
        cutoff = now - timedelta(days=1)
    elif period == "weekly":
        cutoff = now - timedelta(days=7)
    elif period == "monthly":
        cutoff = now - timedelta(days=30)
    else:
        cutoff = datetime.min

    filtered_trades = [
        t for t in trades
        if datetime.fromisoformat(t["timestamp"]) >= cutoff
    ]

    # Calculate metrics
    winning = [t for t in filtered_trades if (t["pnl"] or 0) >= 0]
    losing = [t for t in filtered_trades if (t["pnl"] or 0) < 0]

    total_pnl = sum(t["pnl"] or 0 for t in filtered_trades)
    wins = sum(t["pnl"] or 0 for t in winning)
    losses = abs(sum(t["pnl"] or 0 for t in losing))

    max_profit = total_pnl
    max_drawdown = 0.0

    if wins > 0:
        profit_factor = wins / losses if losses > 0 else 0.0
    else:
        profit_factor = 0.0

    return {
        "period": period,
        "total_trades": len(filtered_trades),
        "winning_trades": len(winning),
        "losing_trades": len(losing),
        "win_rate": (len(winning) / len(filtered_trades) * 100) if filtered_trades else 0.0,
        "total_pnl": total_pnl,
        "max_profit": max_profit,
        "max_drawdown": max_drawdown,
        "profit_factor": profit_factor,
    }


def get_backtest_runs(limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent backtest runs."""
    db_path = "data/backtest_trades.db"
    if not Path(db_path).exists():
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, timestamp, total_trades, total_pnl, win_rate,
               max_drawdown, profit_factor, sharpe_ratio, parameters
        FROM backtest_runs
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    runs = []
    for row in cursor.fetchall():
        runs.append({
            "id": row["id"],
            "timestamp": row["timestamp"],
            "total_trades": row["total_trades"],
            "total_pnl": row["total_pnl"],
            "win_rate": row["win_rate"],
            "max_drawdown": row["max_drawdown"],
            "profit_factor": row["profit_factor"],
            "sharpe_ratio": row["sharpe_ratio"],
            "parameters": row["parameters"],
        })

    conn.close()
    return runs


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve dashboard HTML."""
    # Simple HTML dashboard
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quant Scalping Bot - Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            margin-bottom: 30px;
            text-align: center;
        }
        .header h1 {
            color: #38bdf8;
            font-size: 2rem;
            margin-bottom: 10px;
        }
        .header .status {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            background: #22c55e;
            font-weight: bold;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: #1e293b;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #334155;
        }
        .card h2 {
            color: #94a3b8;
            font-size: 1rem;
            margin-bottom: 15px;
        }
        .metric {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }
        .metric-label {
            color: #94a3b8;
        }
        .metric-value {
            font-weight: bold;
            font-size: 1.1rem;
        }
        .positive { color: #22c55e; }
        .negative { color: #ef4444; }
        .full-width {
            grid-column: 1 / -1;
        }
        .table-container {
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #334155;
        }
        th {
            color: #94a3b8;
            font-weight: 600;
        }
        tr:hover {
            background: #334155;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #94a3b8;
        }
        .refresh {
            text-align: center;
            margin-bottom: 20px;
        }
        button {
            background: #38bdf8;
            color: #0f172a;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: bold;
        }
        button:hover {
            background: #0ea5e9;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Quant Scalping Bot</h1>
            <span class="status">🟢 Dashboard Ready</span>
        </div>

        <div class="refresh">
            <button onclick="loadData()">🔄 Refresh Data</button>
        </div>

        <div class="grid">
            <!-- Bot Status -->
            <div class="card">
                <h2>📊 Bot Status</h2>
                <div class="metric">
                    <span class="metric-label">Running:</span>
                    <span class="metric-value" id="status-running">Loading...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Mode:</span>
                    <span class="metric-value" id="status-mode">Loading...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Symbol:</span>
                    <span class="metric-value" id="status-symbol">Loading...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Position:</span>
                    <span class="metric-value" id="status-position">Loading...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Current Z-Score:</span>
                    <span class="metric-value" id="status-zscore">Loading...</span>
                </div>
            </div>

            <!-- Today's P&L -->
            <div class="card">
                <h2>💰 Today's P&L</h2>
                <div class="metric">
                    <span class="metric-label">Net P&L:</span>
                    <span class="metric-value" id="pnl-net">Loading...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Trades:</span>
                    <span class="metric-value" id="pnl-trades">Loading...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Win Rate:</span>
                    <span class="metric-value" id="pnl-winrate">Loading...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Max Profit:</span>
                    <span class="metric-value" id="pnl-max-profit">Loading...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Max Drawdown:</span>
                    <span class="metric-value" id="pnl-max-dd">Loading...</span>
                </div>
            </div>

            <!-- Risk Status -->
            <div class="card">
                <h2>🛡️ Risk Status</h2>
                <div class="metric">
                    <span class="metric-label">Daily Limit:</span>
                    <span class="metric-value">$500</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Used Today:</span>
                    <span class="metric-value" id="risk-used">Loading...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Circuit Breaker:</span>
                    <span class="metric-value" id="risk-cb">Normal</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Position Duration:</span>
                    <span class="metric-value">0h 0m</span>
                </div>
            </div>

            <!-- Weekly P&L -->
            <div class="card">
                <h2>📈 Weekly P&L</h2>
                <div class="metric">
                    <span class="metric-label">Net P&L:</span>
                    <span class="metric-value" id="weekly-pnl">Loading...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Trades:</span>
                    <span class="metric-value" id="weekly-trades">Loading...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Win Rate:</span>
                    <span class="metric-value" id="weekly-winrate">Loading...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Profit Factor:</span>
                    <span class="metric-value" id="weekly-pf">Loading...</span>
                </div>
            </div>
        </div>

        <!-- Recent Trades -->
        <div class="card full-width">
            <h2>📋 Recent Trades</h2>
            <div class="table-container">
                <table id="trades-table">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Symbol</th>
                            <th>Action</th>
                            <th>Quantity</th>
                            <th>Price</th>
                            <th>P&L</th>
                            <th>Z-Score</th>
                        </tr>
                    </thead>
                    <tbody id="trades-body">
                        <tr>
                            <td colspan="7" class="loading">Loading trades...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Backtest Results -->
        <div class="card full-width">
            <h2>🧪 Backtest Results</h2>
            <div class="table-container">
                <table id="backtest-table">
                    <thead>
                        <tr>
                            <th>Run #</th>
                            <th>Time</th>
                            <th>Trades</th>
                            <th>Win Rate</th>
                            <th>Total P&L</th>
                            <th>PF</th>
                            <th>Sharpe</th>
                        </tr>
                    </thead>
                    <tbody id="backtest-body">
                        <tr>
                            <td colspan="7" class="loading">Loading backtests...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        async function loadData() {
            try {
                // Load status
                const statusRes = await fetch('/api/status');
                const status = await statusRes.json();
                document.getElementById('status-running').textContent = status.running ? '🟢 Yes' : '🔴 No';
                document.getElementById('status-mode').textContent = status.mode.toUpperCase();
                document.getElementById('status-symbol').textContent = status.symbol;
                document.getElementById('status-position').textContent = status.position_type;
                document.getElementById('status-zscore').textContent = status.current_zscore || 'Warming up...';

                // Load P&L
                const pnlRes = await fetch('/api/pnl/daily');
                const pnl = await pnlRes.json();
                document.getElementById('pnl-net').textContent = '$' + pnl.total_pnl.toFixed(2);
                document.getElementById('pnl-net').className = 'metric-value ' + (pnl.total_pnl >= 0 ? 'positive' : 'negative');
                document.getElementById('pnl-trades').textContent = pnl.total_trades;
                document.getElementById('pnl-winrate').textContent = pnl.win_rate.toFixed(1) + '%';
                document.getElementById('pnl-max-profit').textContent = '$' + pnl.max_profit.toFixed(2);
                document.getElementById('pnl-max-dd').textContent = '$' + pnl.max_drawdown.toFixed(2);

                document.getElementById('risk-used').textContent = '$' + Math.abs(Math.min(0, pnl.total_pnl)).toFixed(2);

                // Load weekly
                const weeklyRes = await fetch('/api/pnl/weekly');
                const weekly = await weeklyRes.json();
                document.getElementById('weekly-pnl').textContent = '$' + weekly.total_pnl.toFixed(2);
                document.getElementById('weekly-pnl').className = 'metric-value ' + (weekly.total_pnl >= 0 ? 'positive' : 'negative');
                document.getElementById('weekly-trades').textContent = weekly.total_trades;
                document.getElementById('weekly-winrate').textContent = weekly.win_rate.toFixed(1) + '%';
                document.getElementById('weekly-pf').textContent = weekly.profit_factor.toFixed(2);

                // Load trades
                const tradesRes = await fetch('/api/trades?limit=10');
                const trades = await tradesRes.json();
                const tradesBody = document.getElementById('trades-body');
                if (trades.length === 0) {
                    tradesBody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#94a3b8;">No trades yet</td></tr>';
                } else {
                    tradesBody.innerHTML = trades.map(t => `
                        <tr>
                            <td>${t.timestamp.substring(0, 16)}</td>
                            <td>${t.symbol}</td>
                            <td>${t.action}</td>
                            <td>${t.quantity}</td>
                            <td>$${t.price.toFixed(2)}</td>
                            <td class="${t.pnl >= 0 ? 'positive' : 'negative'}">$${t.pnl ? t.pnl.toFixed(2) : '0.00'}</td>
                            <td>${t.zscore ? t.zscore.toFixed(2) : '-'}</td>
                        </tr>
                    `).join('');
                }

                // Load backtests
                const btRes = await fetch('/api/backtests?limit=10');
                const backtests = await btRes.json();
                const btBody = document.getElementById('backtest-body');
                if (backtests.length === 0) {
                    btBody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#94a3b8;">No backtests yet</td></tr>';
                } else {
                    btBody.innerHTML = backtests.map(bt => `
                        <tr>
                            <td>#${bt.id}</td>
                            <td>${bt.timestamp.substring(0, 16)}</td>
                            <td>${bt.total_trades}</td>
                            <td>${bt.win_rate.toFixed(1)}%</td>
                            <td class="${bt.total_pnl >= 0 ? 'positive' : 'negative'}">$${bt.total_pnl.toFixed(2)}</td>
                            <td>${bt.profit_factor.toFixed(2)}</td>
                            <td>${bt.sharpe_ratio.toFixed(2)}</td>
                        </tr>
                    `).join('');
                }

            } catch (error) {
                console.error('Error loading data:', error);
                alert('Error loading dashboard data');
            }
        }

        // Auto-refresh every 30 seconds
        setInterval(loadData, 30000);

        // Initial load
        loadData();
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html)


@app.get("/api/status")
async def api_status():
    """Get bot status."""
    return get_bot_status()


@app.get("/api/positions")
async def api_positions():
    """Get current positions."""
    return get_positions()


@app.get("/api/trades")
async def api_trades(
    limit: int = 50,
    symbol: Optional[str] = None,
    days_back: Optional[int] = None,
):
    """
    Get trade history.

    Query params:
        limit: Max trades to return (default: 50)
        symbol: Filter by symbol
        days_back: Only trades from last N days
    """
    return get_trades(limit=limit, symbol=symbol, days_back=days_back)


@app.get("/api/pnl/{period}")
async def api_pnl(period: str = "daily"):
    """
    Get P&L metrics.

    Path params:
        period: "daily", "weekly", "monthly", or "all"
    """
    if period not in ["daily", "weekly", "monthly", "all"]:
        raise HTTPException(status_code=400, detail="Invalid period")

    return get_pnl_metrics(period=period)


@app.get("/api/backtests")
async def api_backtests(limit: int = 20):
    """
    Get backtest runs.

    Query params:
        limit: Max runs to return (default: 20)
    """
    return get_backtest_runs(limit=limit)


# ============================================================================
# Run Server
# ============================================================================

def run_dashboard(host: str = "127.0.0.1", port: int = 8000):
    """
    Run the dashboard server.

    Args:
        host: Host to bind to
        port: Port to listen on
    """
    logger.info(f"Starting dashboard on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_dashboard()
