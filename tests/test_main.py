import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main


def test_import_does_not_run_the_workflow(tmp_path):
    script = (
        "import main; "
        "assert callable(main.fetch_binance); "
        "assert callable(main.fetch_hyperliqued); "
        "assert callable(main.fetch_kraken)"
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
    assert "Fetching perpetual symbol list" not in result.stdout


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


def test_binance_workflow_fetches_both_quotes_and_writes_intersection(monkeypatch, tmp_path):
    output = tmp_path / "markets.txt"
    fetch_results = {
        "USDC": ["BTCUSDC", "ETHUSDC", "SOLUSDC"],
        "USDT": ["ETHUSDT", "BTCUSDT", "XRPUSDT"],
    }

    def fetch_historical_data(quote):
        return fetch_results[quote]

    written_files = []

    def write_to_file(symbol_list, filename, quote, fetched_at=None):
        written_files.append((filename, quote, symbol_list, fetched_at))
        with output.open("w", encoding="utf-8") as file:
            for symbol in sorted(symbol_list):
                if symbol.endswith(quote):
                    file.write(f"spot:{symbol[:-len(quote)]}/{quote}\n")

    monkeypatch.setattr(main, "fetch_historical_data", fetch_historical_data)
    monkeypatch.setattr(main, "write_to_file", write_to_file)
    monkeypatch.setattr(main, "BINANCE_FILE", str(output))

    main.fetch_binance()

    assert len(written_files) == 3
    assert written_files[0][1:3] == ("USDC", fetch_results["USDC"])
    assert written_files[1][1:3] == ("USDT", fetch_results["USDT"])
    assert written_files[2][1] == "USDT"
    assert set(written_files[2][2]) == {"BTCUSDT", "ETHUSDT"}


def test_hyperliquid_perps_include_active_swaps_only(monkeypatch):
    markets = [
        {"symbol": "BTC/USDC:USDC", "active": True},
        {"symbol": "OLD/USDC:USDC", "active": False},
    ]

    class FakeHyperliquid:
        def __init__(self, params):
            assert params == {"verbose": False}

        def fetch_swap_markets(self):
            return markets

        def load_markets(self, reload):
            raise TypeError("spot metadata contains a token index without a token")

    monkeypatch.setattr(main.ccxt, "hyperliquid", FakeHyperliquid)

    assert main.fetch_hyperliqued() == ["BTC/USDC:USDC"]


def test_kraken_market_list_keeps_active_quote_spot_markets(monkeypatch):
    markets = {
        "BTC/USDC": {
            "id": "XBTUSDC",
            "symbol": "BTC/USDC",
            "spot": True,
            "active": True,
            "quote": "USDC",
        },
        "OLD/USDC": {
            "id": "OLDUSDC",
            "symbol": "OLD/USDC",
            "spot": True,
            "active": False,
            "quote": "USDC",
        },
        "BTC/USD": {
            "id": "XXBTZUSD",
            "symbol": "BTC/USD",
            "spot": True,
            "active": True,
            "quote": "USD",
        },
        "BTC/USDC:USDC": {
            "id": "BTCUSDC",
            "symbol": "BTC/USDC:USDC",
            "spot": False,
            "active": True,
            "quote": "USDC",
        },
        "中/USDC": {
            "id": "CNUSDC",
            "symbol": "中/USDC",
            "spot": True,
            "active": True,
            "quote": "USDC",
        },
    }

    class FakeKraken:
        def __init__(self, params):
            assert params == {"verbose": False}

        def load_markets(self, reload):
            assert reload is False
            return markets

    monkeypatch.setattr(main.ccxt, "kraken", FakeKraken)

    assert main.fetch_historical_data(
        exchange=main.Exchange.kraken,
        market_type=main.Market_Type.spot,
        quote="USDC",
    ) == ["BTC/USDC"]


def test_write_kraken_spots_outputs_sorted_normalized_symbols(tmp_path):
    output = tmp_path / "kraken.txt"

    main.write_kraken_spots(
        ["SUPER/USDC", "ETH/USDC", "BTC/USDC", "中/USDC"],
        filename=output,
        fetched_at="fixture timestamp",
    )

    assert output.read_text(encoding="utf-8") == (
        "# Fetched: fixture timestamp\n"
        "spot:BTC/USDC\n"
        "spot:ETH/USDC\n"
        "spot:SUPER/USDC\n"
    )


def test_kraken_workflow_fetches_usdc_and_writes_timestamped_file(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(main, "format_fetched_at", lambda: "fixture timestamp")
    monkeypatch.setattr(
        main,
        "fetch_historical_data",
        lambda **kwargs: calls.append(kwargs) or ["BTC/USDC"],
    )
    monkeypatch.setattr(
        main,
        "write_kraken_spots",
        lambda symbols, filename, fetched_at: calls.append(
            (symbols, filename, fetched_at)
        ),
    )
    monkeypatch.setattr(main, "KRAKEN_FILE", str(tmp_path / "kraken.txt"))

    assert main.fetch_kraken(reload=True) is None
    assert calls == [
        {
            "exchange": main.Exchange.kraken,
            "market_type": main.Market_Type.spot,
            "quote": "USDC",
            "reload": True,
        },
        (["BTC/USDC"], str(tmp_path / "kraken.txt"), "fixture timestamp"),
    ]


def test_write_hyperliquid_perps_preserves_normalized_symbols(tmp_path):
    output = tmp_path / "hyperliquid.txt"

    main.write_hyperliquid_perps(
        ["ETH/USDC:USDC", "BTC/USDC:USDC"],
        filename=output,
        fetched_at="fixture timestamp",
    )

    assert output.read_text(encoding="utf-8") == (
        "# Fetched: fixture timestamp\n"
        "perp:BTC/USDC\n"
        "perp:ETH/USDC\n"
    )


def test_cli_dispatches_to_selected_exchange(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "fetch_binance", lambda: calls.append("binance"))
    monkeypatch.setattr(main, "fetch_hyperliqued", lambda: calls.append("hyperliquid") or [])
    monkeypatch.setattr(main, "fetch_kraken", lambda: calls.append("kraken"))
    monkeypatch.setattr(main, "write_hyperliquid_perps", lambda *args, **kwargs: None)

    assert main.main(["-d", "binance"]) is None
    assert calls == ["binance"]

    calls.clear()
    assert main.main(["-d", "hyperliquid"]) is None
    assert calls == ["hyperliquid"]

    calls.clear()
    assert main.main(["-d", "kraken"]) is None
    assert calls == ["kraken"]


def test_cli_rejects_unsupported_exchange():
    import pytest

    with pytest.raises(SystemExit) as error:
        main.main(["-d", "coinbase"])

    assert error.value.code == 2


def test_cli_requires_a_supported_exchange():
    import pytest

    with pytest.raises(SystemExit) as error:
        main.main([])

    assert error.value.code == 2


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
