"""
Main entry point for the Self-Improving Quant Engine.
"""
# NOTE: This is a temporary, simplified main for Epic 1 validation.
# It will be replaced by the full orchestrator in Epic 2.
from services import ConfigService, DataService, Backtester, ReportGenerator
from core.strategy import SmaCross
from core.models import StrategyDefinition


def main() -> None:
    """
    Runs a simple, single backtest of the baseline strategy.
    """
    print("--- Running Baseline Backtest (Epic 1 Validation) ---")
    config_service = ConfigService()
    config = config_service.load_config()

    data_service = DataService(data_dir=config.app.data_dir)
    backtester = Backtester()
    report_generator = ReportGenerator()

    # For now, we test the first ticker only
    if not config.app.tickers:
        print("FATAL: No tickers specified in config.ini")
        return
    ticker = config.app.tickers[0]
    print(f"Fetching data for {ticker}...")
    train_data, _ = data_service.get_data(ticker)

    print("Running backtest on baseline SMA Crossover strategy...")
    stats, trades = backtester.run(train_data, SmaCross)

    # Create a dummy strategy definition for the report
    baseline_def = StrategyDefinition(
        strategy_name="SMA_Crossover_Baseline",
        indicators=[],
        buy_condition="SMA50 > SMA200",
        sell_condition="SMA50 < SMA200",
    )

    report = report_generator.generate(stats, trades, baseline_def)

    print("\n--- Baseline Performance Report ---")
    print(f"Sharpe Ratio: {report.sharpe_ratio:.2f}")
    print(f"Total Trades: {report.trade_summary.total_trades}")
    print("--- Run Finished ---")


if __name__ == "__main__":
    main()
