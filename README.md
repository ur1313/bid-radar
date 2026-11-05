# Bid Radar

Free, daily-updated list of open federal contract opportunities on SAM.gov that small businesses can bid on, with a paid Pro email digest.

- Live site: https://ur1313.github.io/bid-radar/
- Data: SAM.gov public Contract Opportunities CSV extract (no API key)
- Rebuild: `python3 build.py` (expects CSV at `/tmp/sam-opps.csv` or set `SAM_CSV`; auto-downloads if missing)
- Publish: `./deploy.sh`

Pro: $49/mo weekday digest filtered by NAICS + set-aside + state. Wire a Stripe Payment Link into `PRO_URL` before rebuild.
