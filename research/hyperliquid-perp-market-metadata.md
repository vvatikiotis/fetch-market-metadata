# Hyperliquid perpetual market metadata

- Hyperliquid exposes public perpetual metadata through `POST https://api.hyperliquid.xyz/info` with `{"type":"meta"}` or `{"type":"metaAndAssetCtxs"}`. CCXT can fetch this with `ccxt.hyperliquid().load_markets()`.
- Select perpetuals using CCXT normalized fields `market["swap"] and market["active"]`. Hyperliquid delisted universe entries have `isDelisted: true`, mapped by CCXT to inactive.
- Keep CCXT's normalized symbol, e.g. `BTC/USDC:USDC`. The settlement suffix distinguishes a perp from spot `BTC/USDC`.
- A natural output format alongside this repo's `spot:` lines is `swap:BTC/USDC:USDC`.

Sources: [Hyperliquid perpetual API](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals), [CCXT Hyperliquid adapter](https://raw.githubusercontent.com/ccxt/ccxt/master/python/ccxt/hyperliquid.py).
