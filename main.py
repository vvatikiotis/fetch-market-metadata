from datetime import datetime
from enum import Enum

import ccxt

Market_Type = Enum("Market_Type", ["spot", "swaps_linear", "swaps_inverse", "futures"])
Exchange = Enum("Exchange", ["binance"])

FILE = "/Users/vatikiot/devel/Trading/data/binance_market_list"


def contains_chinese_characters(value):
    return any(
        0x3400 <= ord(character) <= 0x4DBF
        or 0x4E00 <= ord(character) <= 0x9FFF
        or 0xF900 <= ord(character) <= 0xFAFF
        for character in value
    )


def fetch_historical_data(
    exchange: Exchange = Exchange.binance,
    market_type: Market_Type = Market_Type.spot,
    symbols="all",
    quote: str = "USDC",
    verbose=False,
    reload=False,
):
    print(f"Fetching spot symbol list -- {quote}\n")

    params = {}
    if market_type == Market_Type.spot:
        params = {"verbose": verbose, "options": {"fetchMarkets": ["spot"]}}
    elif market_type == Market_Type.swaps_linear:
        params = {"verbose": verbose, "options": {"fetchMarkets": ["linear"]}}

    if exchange:
        _exchange = ccxt.binance(params)
    else:
        return "No exchange is set"

    markets = _exchange.load_markets(reload)

    # print(json.dumps(markets, indent=4))
    if symbols == "all":
        symbols = []
        if market_type == Market_Type.spot:
            symbols = [
                symbol["id"]
                for _, symbol in markets.items()
                if symbol["id"].endswith(quote)
                and symbol["info"]["status"] == "TRADING"
                and not contains_chinese_characters(symbol["id"])
            ]
        elif market_type == Market_Type.swaps_linear:
            # FIX like above
            symbols = [
                symbol.replace("/", "").split(":", 1)[0]
                for symbol in list(markets.keys())
                if not contains_chinese_characters(symbol)
            ]

    print(f"Fetched symbols:\n\n{symbols}\n")
    return symbols


def write_to_file(symbol_list, filename=FILE, quote="USDT", fetched_at=None):
    print(f"Writing to file {filename}\n\n{symbol_list}\n")

    symbol_list = [
        symbol for symbol in symbol_list if not contains_chinese_characters(symbol)
    ]

    excludes = [
        "USTCUSDT",
        "USTUSDT",
        "DOWNUSDT",
        "UPUSDT",
        "BEARUSDT",
        "BULLUSDT",
        "USDCUSDT",
        "USDPUSDT",
        "TUSDUSDT",
        "USDSBUSDT",
        "USDSUSDT",
        "BUSDUSDT",
        "PAXUSDT",
        "AEURUSDT",
        "EURIUSDT",
        "FTTUSDT",
        "BCCUSDT",
        "LUNAUSDT",
        "EURUSDT",
        "COCOSUSDT",
        "LUNCUSDT",
        "MULTIUSDT",
        "MOBUSDT",
        "TORNUSDT",
        "LOOMUSDT",
        "BETHUSDT",
        "AGIXUSDT",
        "GALUSDT",
        "NEBLUSDT",
        "EPXUSDT",
        "MCUSDT",
        "ANCUSDT",
        "ANYUSDT",
        "VGXUSDT",
        # "RNDRUSDT",
        "PLAUSDT",
        "FRONTUSDT",
        "RGTUSDT",
        "CVPUSDT",
        "POLYUSDT",
        "TRIBEUSDT",
        "TVKUSDT",
        "BONDUSDT",
        "KEEPUSDT",
        "MDXUSDT",
        "POLSUSDT",
        "NUUUSDT",
        "MIRUSDT",
        "BTGUSDT",
        "RAMPUSDT",
        "EPSUSDT",
        "AUTOUSDT",
        "XEMUSDT",
        "WTCUSDT",
        "SUSDUSDT",
        "DNTUSDT",
    ]

    # Symbols with UP/DOWN/BEAR/BULL... Binance symbols
    downs = [s for s in symbol_list if "DOWN" in s]
    ups = [s for s in symbol_list if "UP" in s and s != "JUPUSDT" and s != "SUPERUSDT"]

    bears = [s for s in symbol_list if "BEAR" in s]
    bulls = [s for s in symbol_list if "BULL" in s]

    symbol_list_sorted = sorted(symbol_list, key=str.lower)
    with open(filename, "w", encoding="utf-8") as file:
        if fetched_at is not None:
            file.write(f"# Fetched: {fetched_at}\n")
        for symbol in symbol_list_sorted:
            if (
                symbol not in excludes
                and symbol not in ups
                and symbol not in downs
                and symbol not in bears
                and symbol not in bulls
            ) and symbol.endswith(quote):
                file.write(f"spot:{symbol[:-len(quote)]}/{quote}\n")


def main():
    now = datetime.now().astimezone()
    utc_offset = now.strftime("%z")
    utc_offset = f"{utc_offset[:3]}:{utc_offset[3:]}" if utc_offset else ""
    fetched_at = now.strftime("%A, %B %d, %Y at %H:%M:%S %Z")
    fetched_at += f" (UTC{utc_offset})"

    quote = "USDC"
    symbol_list = fetch_historical_data(quote=quote)
    write_to_file(symbol_list=symbol_list, filename=f"{FILE}.{quote}", quote=quote)

    usdc_symbols = list(map(lambda x: x.removesuffix(quote), symbol_list))

    quote = "USDT"
    symbol_list = fetch_historical_data(quote=quote)
    write_to_file(symbol_list=symbol_list, filename=f"{FILE}.{quote}", quote=quote)

    usdt_symbols = list(map(lambda x: x.removesuffix(quote), symbol_list))

    common_symbols = set(usdt_symbols).intersection(set(usdc_symbols))
    final_list = list(map(lambda x: x + "USDT", common_symbols))
    write_to_file(
        symbol_list=final_list,
        filename=f"{FILE}",
        quote="USDT",
        fetched_at=fetched_at,
    )

    comment = """\n'm forced to trade USDC pairs due to MiCA.
However, Binance USDC timeseries quality is not as good as the USDT.
Note: Binance supports much less USDC pairs than USDT series.
So I fetch both sets and I do an intersection.
Result: I keep all USDT pairs that also have a USDC pair"""
    print(comment)


if __name__ == "__main__":
    main()
