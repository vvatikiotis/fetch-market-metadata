import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main


def test_import_does_not_run_the_workflow(tmp_path):
    script = (
        "import main; "
        "assert callable(main.main); "
        "assert main.main.__name__ == 'main'"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Fetching spot symbol list" not in result.stdout


def test_market_list_keeps_active_quote_symbols_without_chinese_characters(monkeypatch):
    import copy

    markets = {
        "BTC/USDC": {
            "id": "BTCUSDC",
            "info": {"status": "TRADING"},
        },
        "ETH/USDC": {
            "id": "ETHUSDC",
            "info": {"status": "TRADING"},
        },
        "OLD/USDC": {
            "id": "OLDUSDC",
            "info": {"status": "BREAK"},
        },
        "CN/USDC": {
            "id": "中USDC",
            "info": {"status": "TRADING"},
        },
        "BTC/USDT": {
            "id": "BTCUSDT",
            "info": {"status": "TRADING"},
        },
    }

    class FakeBinance:
        def __init__(self, params):
            self.options = copy.deepcopy(params.get("options", {"fetchMarkets": ["spot"]}))

        def load_markets(self, reload):
            assert reload is False
            return markets

    monkeypatch.setattr(main.ccxt, "binance", FakeBinance)

    assert main.fetch_historical_data(quote="USDC") == ["BTCUSDC", "ETHUSDC"]


def test_main_writes_usdt_markets_for_the_usdc_intersection(monkeypatch, tmp_path):
    output = tmp_path / "markets.txt"
    fetch_results = {
        "USDC": ["BTCUSDC", "ETHUSDC", "SOLUSDC"],
        "USDT": ["ETHUSDT", "BTCUSDT", "XRPUSDT"],
    }

    def fetch_historical_data(quote):
        return fetch_results[quote]

    written_files = []

    actual_write_to_file = main.write_to_file

    def write_to_file(symbol_list, filename, quote, fetched_at=None):
        written_files.append((filename, quote, symbol_list, fetched_at))
        actual_write_to_file(
            symbol_list,
            filename=output,
            quote=quote,
            fetched_at=fetched_at,
        )

    monkeypatch.setattr(main, "fetch_historical_data", fetch_historical_data)
    monkeypatch.setattr(main, "write_to_file", write_to_file)
    monkeypatch.setattr(main, "FILE", str(output))

    main.main()

    assert len(written_files) == 3
    assert written_files[0][1:3] == ("USDC", fetch_results["USDC"])
    assert written_files[1][1:3] == ("USDT", fetch_results["USDT"])
    assert written_files[2][1] == "USDT"
    assert set(written_files[2][2]) == {"BTCUSDT", "ETHUSDT"}
    assert output.read_text(encoding="utf-8").splitlines()[1:] == [
        "spot:BTC/USDT",
        "spot:ETH/USDT",
    ]


def test_write_to_file_outputs_sorted_spot_markets(tmp_path):
    output = tmp_path / "markets.txt"

    main.write_to_file(
        ["ETHUSDT", "BTCUSDT", "DOWNUSDT", "中USDT"],
        filename=output,
        quote="USDT",
        fetched_at="fixture timestamp",
    )

    assert output.read_text(encoding="utf-8") == (
        "# Fetched: fixture timestamp\n"
        "spot:BTC/USDT\n"
        "spot:ETH/USDT\n"
    )
