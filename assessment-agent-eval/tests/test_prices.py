"""The cost estimate uses the prices of the model that actually ran, so `--model` can
switch models within one config without the estimate going wrong."""

from pathlib import Path

import pytest
import yaml

import run_eval
from run_eval import model_prices

TABLE = {
    "model": "big",
    "prices": {
        "big": {"input_per_1m": 1.32, "output_per_1m": 3.96},
        "small": {"input_per_1m": 0.30, "output_per_1m": 1.20},
    },
}


def test_a_config_without_a_price_table_uses_its_flat_prices():
    config = {"model": "m", "price_input_per_1m": 2.0, "price_output_per_1m": 12.0}
    assert model_prices(config, "m") == (2.0, 12.0)


def test_the_price_table_gives_the_prices_of_the_model_asked_for():
    assert model_prices(TABLE, "big") == (1.32, 3.96)
    assert model_prices(TABLE, "small") == (0.30, 1.20)


def test_a_model_missing_from_the_price_table_is_refused_and_the_known_ones_named():
    with pytest.raises(ValueError, match="big, small"):
        model_prices(TABLE, "typo")


def test_the_deepseek_config_prices_both_models_and_runs_one_of_them():
    eval_dir = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((eval_dir / "config.deepseek.yaml").read_text(encoding="utf-8"))
    assert {"deepseek-flash", "deepseek-v4-pro"} <= set(config["prices"])
    assert config["model"] in config["prices"]


def test_a_live_run_with_a_bad_model_stops_before_any_call(monkeypatch, tmp_path):
    (tmp_path / "c.yaml").write_text(yaml.safe_dump({**TABLE, "provider": "mock"}), encoding="utf-8")
    monkeypatch.setattr(run_eval, "BASE", tmp_path)
    monkeypatch.setattr("sys.argv", ["run_eval.py", "--config", "c.yaml", "--model", "typo"])
    with pytest.raises(SystemExit, match="typo"):
        run_eval.main()
