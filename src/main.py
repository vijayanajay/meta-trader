"""
Main entry point for the Self-Improving Quant Engine.
"""
# NOTE: This is a temporary, simplified main for Epic 1 & 2 validation.
# It will be replaced by the full orchestrator in a future task.
from services import (
    ConfigService,
    DataService,
    Backtester,
    ReportGenerator,
    StrategyEngine,
)
from core.models import StrategyDefinition, Indicator


def main() -> None:
    """
    Runs a simple, single backtest of a dynamically generated strategy.
    """
    print("--- Running Dynamic Strategy Backtest (Task 5.1 Validation) ---")
    config_service = ConfigService()
    config = config_service.load_config()

    data_service = DataService(data_dir=config.app.data_dir)
    strategy_engine = StrategyEngine()
    backtester = Backtester()
    report_generator = ReportGenerator()

    # For now, we test the first ticker only
    if not config.app.tickers:
        print("FATAL: No tickers specified in config.ini")
        return
    ticker = config.app.tickers[0]
    print(f"Fetching data for {ticker}...")
    train_data, _ = data_service.get_data(ticker)

    # Define a sample dynamic strategy (EMA Crossover)
    strategy_def = StrategyDefinition(
        strategy_name="EMA_Crossover_Dynamic",
        indicators=[
            Indicator(name="ema_fast", function="ema", params={"length": 10}),
            Indicator(name="ema_slow", function="ema", params={"length": 30}),
        ],
        buy_condition="ema_fast > ema_slow",
        sell_condition="ema_fast < ema_slow",
    )
    print(f"Processing strategy: {strategy_def.strategy_name}...")

    dynamic_strategy_class = strategy_engine.process(train_data, strategy_def)

    print("Running backtest on dynamically generated strategy...")
    stats, trades = backtester.run(train_data, dynamic_strategy_class)

    report = report_generator.generate(stats, trades, strategy_def)

    print("\n--- Dynamic Strategy Performance Report ---")
    print(f"Sharpe Ratio: {report.sharpe_ratio:.2f}")
    print(f"Total Trades: {report.trade_summary.total_trades}")
    print("--- Run Finished ---")


if __name__ == "__main__":
    main()
