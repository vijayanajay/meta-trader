from praxis_engine import ConfigService, Orchestrator, Config

# Load the configuration
config_service = ConfigService("config.ini")
config: Config = config_service.load_config()

# Create an orchestrator
orchestrator = Orchestrator(config)

# Run a backtest for a single stock
stock_to_backtest = "RELIANCE.NS"  # Example stock
trades = orchestrator.run_backtest(
    stock=stock_to_backtest,
    start_date=config.data.start_date,
    end_date=config.data.end_date,
)

# Print the trades
for trade in trades:
    print(trade)
