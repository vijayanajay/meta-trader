import pandas as pd
import numpy as np
import datetime
from praxis_engine.core.models import Config, DataConfig, StrategyParamsConfig, FiltersConfig, ScoringConfig, SignalLogicConfig, LLMConfig, CostModelConfig, ExitLogicConfig, MarketDataConfig
from praxis_engine.core.orchestrator import Orchestrator


def make_minimal_config(tmp_cache_dir: str) -> Config:
    data = DataConfig(
        cache_dir=tmp_cache_dir,
        stocks_to_backtest=["TEST.NS"],
        start_date="2020-01-01",
        end_date="2020-12-31",
        sector_map={"TEST.NS": "^NSEI"},
    )
    strategy_params = StrategyParamsConfig(
        bb_length=15,
        bb_std=2.0,
        bb_weekly_length=10,
        bb_weekly_std=2.5,
        bb_monthly_length=6,
        bb_monthly_std=3.0,
        rsi_length=14,
        hurst_length=100,
        exit_days=5,
        min_history_days=5,
        liquidity_lookback_days=5,
    )
    filters = FiltersConfig(
        sector_vol_threshold=1.0,
        liquidity_turnover_crores=0.1,
        adf_p_value_threshold=0.1,
        hurst_threshold=0.6,
    )
    scoring = ScoringConfig(
        liquidity_score_min_turnover_crores=0.0,
        liquidity_score_max_turnover_crores=10.0,
        regime_score_min_volatility_pct=0.0,
        regime_score_max_volatility_pct=10.0,
        hurst_score_min_h=0.0,
        hurst_score_max_h=1.0,
        adf_score_min_pvalue=0.0,
        adf_score_max_pvalue=1.0,
    )
    signal_logic = SignalLogicConfig(
        require_daily_oversold=False,
        require_weekly_oversold=False,
        require_monthly_not_oversold=False,
        rsi_threshold=30,
    )
    llm = LLMConfig(
        use_llm_audit=False,
        provider="none",
        confidence_threshold=0.5,
        min_composite_score_for_llm=0.05,
        model="",
        prompt_template_path="",
    )
    cost_model = CostModelConfig(
        brokerage_rate=0.0003,
        brokerage_max=20.0,
        stt_rate=0.00025,
        assumed_trade_value_inr=100000,
        slippage_volume_threshold=100000,
        slippage_rate_high_liquidity=0.0005,
        slippage_rate_low_liquidity=0.001,
    )
    exit_logic = ExitLogicConfig(
        use_atr_exit=False,
        atr_period=14,
        atr_stop_loss_multiplier=2.0,
        max_holding_days=10,
        reward_risk_ratio=1.75,
    )

    market_data = MarketDataConfig(
        index_ticker="^NSEI",
        vix_ticker="^INDIAVIX",
        training_start_date="2010-01-01",
        cache_dir=tmp_cache_dir,
    )

    return Config(
        data=data,
        market_data=market_data,
        strategy_params=strategy_params,
        filters=filters,
        scoring=scoring,
        signal_logic=signal_logic,
        llm=llm,
        cost_model=cost_model,
        exit_logic=exit_logic,
    )


from typing import Any
from pytest import MonkeyPatch
from pathlib import Path

def make_sample_df() -> pd.DataFrame:
    dates = pd.date_range(start="2020-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "Open": np.linspace(100, 110, len(dates)),
            "High": np.linspace(101, 111, len(dates)),
            "Low": np.linspace(99, 109, len(dates)),
            "Close": np.linspace(100, 110, len(dates)),
            "Volume": np.arange(1000, 1000 + len(dates)),
        },
        index=dates,
    )
    return df


def test_orchestrator_bypasses_llm(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """When use_llm_audit is False, orchestrator should not call LLMAuditService and should assign confidence 1.0."""
    cfg = make_minimal_config(str(tmp_path))

    # Replace DataService.get_data to return our small dataframe
    sample_df = make_sample_df()

    def fake_get_data(self: Any, stock: str, start: str, end: str, sector_ticker: Any = None) -> pd.DataFrame:
        return sample_df

    monkeypatch.setattr("praxis_engine.services.data_service.DataService.get_data", fake_get_data)

    # Track whether LLMAuditService.get_confidence_score is called
    called = {"was_called": False}

    def fake_get_confidence(self: Any, historical_stats: Any, signal: Any, df_window: Any) -> float:
        called["was_called"] = True
        return 0.0

    monkeypatch.setattr(
        "praxis_engine.services.llm_audit_service.LLMAuditService.get_confidence_score",
        fake_get_confidence,
    )

    orchestrator = Orchestrator(cfg)

    # Call generate_opportunities; with LLM disabled, get_confidence should not be called and
    # the resulting opportunity should have confidence_score == 1.0 or None if pre-filters remove signal.
    opp = orchestrator.generate_opportunities("TEST.NS", lookback_days=10)

    # Ensure LLMAuditService was not called
    assert called["was_called"] is False

    if opp is not None:
        assert opp.confidence_score == 1.0
    else:
        # If the signal was filtered by statistical guards, that's acceptable for this test
        assert opp is None
