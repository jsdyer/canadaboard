# Canada Board

[Open Canada Board](https://coolcode.ca/canadaboard/) — six national economic indicators with observation periods, small charts, source definitions and explicit official release dates.

<!-- coolcode:guide -->
Read inflation, unemployment, the policy target, CAD/USD, the 10-year benchmark yield and annualized housing starts together without losing their different reference dates. Switch chart periods, inspect exact observations, pin cards locally and export CSV. Download the publisher-scheduled release calendar as all-day events. This is a dated source snapshot, not trading prices or forecasts.
<!-- /coolcode:guide -->

## Sources and meaning

- **Statistics Canada WDS**: v41690973 all-items Canada CPI (18-10-0004), v2062815 total-gender age15+ seasonally adjusted unemployment (14-10-0287), and v52300157 CMHC all-area housing starts at seasonally adjusted annual rates (34-10-0158). Metadata units, scalar, frequency and table IDs are validated. CPI annual inflation compares exactly the same month one year earlier and rounds the derived percentage to one decimal; missing months stay missing. Housing thousands are multiplied by1000, but the measure remains an annualized pace, not monthly completions.
- **Bank of Canada Valet**: V39079 policy target, FXUSDCAD daily indicative exchange rate, BD.CDN.10YR.DQ.YLD benchmark yield. The FX observation is inverted to show US dollars per Canadian dollar. This is not an executable exchange quote.
- **Calendars**: the official StatCan major-indicator JSON and explicitly captioned Bank of Canada policy-date tables. No recurring release dates are inferred. Housing, bond and FX calendars are not guessed. All-day ICS exports intentionally omit a release time.

Each indicator displays its actual latest observation period. `checked_at` is when sources were successfully retrieved, not an observation or publication date. Earlier observations can be revised; each capture represents a current vintage. Successful snapshots are retained in Git history. Charts scale independently and have exact tables; missing values interrupt lines. Adjacent-observation changes use percentage points for percentage series.

Official documentation: [WDS](https://www.statcan.gc.ca/en/developers/wds), [Valet](https://www.bankofcanada.ca/valet-api-how-to/), [StatCan calendar](https://www150.statcan.gc.ca/n1/dai-quo/cal2-eng.htm), [policy calendar](https://www.bankofcanada.ca/core-functions/monetary-policy/key-interest-rate/). Reproduced and reorganized independently; not endorsed by the publishers.

## Refresh, test and publish

No keys are needed. Pages source must be GitHub Actions. `pages.yml` refreshes weekdays at22:47UTC and on manual dispatch; pushes test and publish the saved snapshot. Any failed source fetch/validation prevents publication and retains the existing site. The independent watchdog should check `data/snapshot.json` → `checked_at` with a4-day allowance for weekends/holidays. A separate schedule guard covers the workflow.

```sh
python3 scripts/collect.py
node --test tests/*.test.mjs
python3 -m unittest discover -s tests -v
python3 scripts/build.py
python3 tests/browser_smoke.py
```

Only collection needs network; build/tests use saved data or isolated fixtures. Browser checks need `tests/browser-requirements.txt` and Chromium. Set `CHROMIUM_PATH` to an installed Chrome executable if needed. Publish only `dist/`.

## Expand or customize

Edit `config/series.json`: add a unique ID and an official `statcan` vector or `valet` series, display metadata, expected units/scalar, supported transformation (`level`, `yoy`, `reciprocal`) and source-related tool. The collector and cards derive coverage from this array; tests include an added seventh indicator. Verify vector metadata with `getSeriesInfoFromVector` before adding it. An optional `calendar_match` matches an explicit publisher title; leave blank if no verified schedule applies. Never invent a future date. `periods` controls monthly history, `valet_start` daily history.

After changes run tests and collect, commit and push. To refresh remotely use **Actions → Canada Board · Check and refresh → Run workflow**. Source and saved editions remain inspectable in Git. Root hub registration handles catalogue, Worker ID, sitemap, README, watchdog and audit integration.

## Privacy

Pins use `coolcode:canadaboard:pins` in local storage and persist on this device. The tool fetches only its same-origin snapshot. CSV/ICS exports are generated locally. Shared CoolCode metrics record aggregate opens, not pin choices. External official-source links leave the site only when opened.
