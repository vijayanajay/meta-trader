"""
Main entry point for the Self-Improving Quant Engine.
"""
from src.core import Orchestrator, Config
from src.services import (
    ConfigService,
    StateManager,
    DataService,
    StrategyEngine,
    Backtester,
    ReportGenerator,
    LLMService,
)


def main() -> None:
    """
    Main function to initialize and run the application.
    """
    print("--- Self-Improving Quant Engine ---")
    print("Initializing services...")

    # 1. Load Configuration
    config_service = ConfigService()
    try:
        config: Config = config_service.load_config()
        print("Configuration loaded successfully.")
        # For brevity, let's not print the whole config object unless debugging
        # print(config)
    except FileNotFoundError as e:
        print(f"FATAL: Configuration file not found. {e}")
        return
    except Exception as e:
        print(f"FATAL: Error loading configuration. {e}")
        return


    # 2. Initialize Services based on the loaded configuration
    state_manager = StateManager(state_file_path=config.app.run_state_file)
    data_service = DataService(data_dir=config.app.data_dir)
    strategy_engine = StrategyEngine()
    backtester = Backtester()
    report_generator = ReportGenerator()

    # Simple logic to select the right API key based on the provider
    api_key = ""
    if config.llm.provider == "openrouter":
        api_key = config.llm.openrouter_api_key
    elif config.llm.provider == "openai":
        api_key = config.llm.openai_api_key

    llm_service = LLMService(
        provider=config.llm.provider,
        api_key=api_key,
        model=config.llm.openrouter_model if config.llm.provider == "openrouter" else config.llm.openai_model,
        base_url=config.llm.openrouter_base_url if config.llm.provider == "openrouter" else None,
    )

    # 3. Initialize Orchestrator
    orchestrator = Orchestrator(
        config=config,
        state_manager=state_manager,
        data_service=data_service,
        strategy_engine=strategy_engine,
        backtester=backtester,
        report_generator=report_generator,
        llm_service=llm_service,
    )

    # 4. Run the main loop
    print("\nStarting Orchestrator...")
    orchestrator.run()
    print("\n--- Run Finished ---")


if __name__ == "__main__":
    main()
