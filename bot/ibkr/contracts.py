"""
IBKR Contract Definitions

Standard contracts for trading, with helper functions for common instruments.
"""
from ibapi.contract import Contract
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class InstrumentConfig:
    """Configuration for a trading instrument"""
    symbol: str
    exchange: str
    sec_type: str
    expiry: str
    multiplier: float
    tick_size: float
    tick_value: float
    currency: str = "USD"


def create_mes_contract(expiry: str) -> Contract:
    """
    Create a Micro E-mini S&P 500 futures contract.

    Args:
        expiry: Expiry in YYYYMM format (e.g., "202503")

    Returns:
        Contract object for MES
    """
    contract = Contract()
    contract.symbol = "MES"
    contract.secType = "FUT"
    contract.exchange = "CME"
    contract.currency = "USD"
    contract.lastTradeDateOrContractMonth = expiry

    return contract


def create_contract_from_config(config: InstrumentConfig) -> Contract:
    """
    Create a contract from an InstrumentConfig.

    Args:
        config: Instrument configuration

    Returns:
        Contract object
    """
    contract = Contract()
    contract.symbol = config.symbol
    contract.secType = config.sec_type
    contract.exchange = config.exchange
    contract.currency = config.currency
    contract.lastTradeDateOrContractMonth = config.expiry

    return contract


# Common instruments
def create_sp500_contract() -> Contract:
    """Create SPY (SPDR S&P 500 ETF) contract for testing"""
    contract = Contract()
    contract.symbol = "SPY"
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"

    return contract


def get_all_contracts() -> List[Contract]:
    """Get a list of all supported contracts"""
    return [
        create_sp500_contract(),
    ]


# Contract validation
def validate_contract(contract: Contract) -> bool:
    """
    Validate that a contract has required fields.

    Args:
        contract: Contract to validate

    Returns:
        True if valid, False otherwise
    """
    required_fields = ['symbol', 'secType', 'exchange', 'currency']
    for field in required_fields:
        if not getattr(contract, field, None):
            return False

    return True


if __name__ == "__main__":
    # Test creating contracts
    print("Testing contract creation...")

    # MES contract
    mes = create_mes_contract("202503")
    print(f"\nMES Contract: {mes.symbol}")
    print(f"  Type: {mes.secType}")
    print(f"  Exchange: {mes.exchange}")
    print(f"  Expiry: {mes.lastTradeDateOrContractMonth}")
    print(f"  Valid: {validate_contract(mes)}")

    # SPY contract
    spy = create_sp500_contract()
    print(f"\nSPY Contract: {spy.symbol}")
    print(f"  Type: {spy.secType}")
    print(f"  Exchange: {spy.exchange}")
    print(f"  Valid: {validate_contract(spy)}")

    print("\n✅ Contract module OK")
