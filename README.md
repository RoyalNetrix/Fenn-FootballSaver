# Football (data saver) for Fenn

The same scores plugin as [Fenn-Football](https://github.com/RoyalNetrix/Fenn-Football), made to use as little data as possible. Use this one or the regular one, not both.

## What it does

- Wide tile: the live match, your favourite team's match, or the first fixture of the day. Team codes keep it short, e.g. `RMA v BAR`.
- Pill: pulses while a La Liga or Champions League match is live.
- Page (click the tile): league chips (PL, La Liga, Serie A, Bundesliga, Ligue 1, UCL), an optional favourite-team box and the list of today's matches with kick-off times in your local time. A line under the controls says when the data was last updated, and the refresh button forces an update.

## How it differs from Football

It is the same plugin with a much quieter refresh schedule. The tile, page, leagues and team codes work the same way.

| | Football | Football (data saver) |
|---|---|---|
| Live scores | any league, every 60 seconds while a match is live | **La Liga and UCL only**, every 60 seconds while a match is on |
| Other leagues | refreshed every 5 minutes all day | one check about 2h15 after kick-off, for the final result |
| Between matches | checks every 5 minutes | sleeps until 2 minutes before the next kick-off (6 hours at most) |
| Saved results | no | yes, in `cache.json`, so restarts and league switches don't download again |
| Data (rough estimate, not measured) | about 25 MB a day | about 1 MB a month in the quiet leagues, about 30 MB a month with La Liga selected all season |
| Plugin id and settings | `football` | `footballsaver` (its own settings) |

**What you give up:** in the leagues without live updates, a match in progress shows "In play" instead of a score, and the final score only appears after full time.

**Which to pick:** this one on a limited data plan, or if you only care about La Liga and the Champions League live. The regular one if you want live scores in every league. Install one, not both.

## How it saves data

It does not poll on a timer. It only asks for data when something can have changed, and only for the league you have selected.

- **La Liga and the Champions League** get live updates (every 60 seconds), but only while a match is on. It starts 2 minutes before kick-off and stops when the last match is over. Between matches it sleeps until the next kick-off.
- **Every other league** gets no live updates. It checks once, about 2 hours 15 minutes after kick-off, to pick up the final result. If the match isn't finished yet it retries every 10 minutes.
- **Nothing pending:** it only looks for new fixtures every 6 hours.
- **Final results are saved** in `cache.json`, so restarting Fenn or switching leagues doesn't download them again.
- Responses are requested gzip-compressed, which shrinks them a lot.

Rough estimate, not measured: a few KB a day in the quiet leagues, and a few MB on a La Liga matchday if you leave La Liga selected.

## Install

1. Copy this folder to `%APPDATA%\Fenn\plugins\footballsaver\` so that `plugin.toml` and `main.py` sit directly inside it.
2. In Fenn, open **Settings** and turn on **Plugin dev mode**. The tile appears within a few seconds, with no restart. (Without dev mode, restart Fenn.)
3. New tiles are added after the built-in ones, possibly on the second page. Use the pencil in the grid to move or resize it.

Requires Fenn with plugin support.

## Requirements

Python 3.8+ (Fenn can set it up for you, or use your own). No extra packages, no API key.

## Network and privacy

- `site.api.espn.com`: ESPN's public scoreboard JSON for the selected league. Nothing about you is sent.
- This is an unofficial, undocumented endpoint. It can change or stop working without notice.

## Settings and data

- League and favourite team are saved in `%APPDATA%\Fenn\plugin-data\footballsaver\config.json`, and the saved results in `cache.json` next to it.
- Favourite team is a substring match, e.g. `madrid`. With one set, the tile follows that team's matches.
- Constants at the top of `main.py` change the schedule: `LIVE_LEAGUES` (which leagues get live updates), `LIVE_EVERY`, `LEAD`, `MATCH_LEN`. `LEAGUES` lists the competitions by ESPN code. More live leagues mean more data.

## Limitations

- It shows the matches the scoreboard returns for the current day, not a full season schedule.
- In leagues without live updates, a match in progress shows "In play" instead of a score, and the final score appears after full time.
- Only the selected league is tracked, so switching to another league may trigger one update.
- A match that ESPN leaves unfinished more than 4 hours after kick-off (postponed, for example) is ignored rather than polled forever.

## Troubleshooting

- **Tile says "Stopped":** hover it to see the error and the last lines of the plugin's output.
- **Nothing happens:** Fenn can set up Python for you. If that didn't work, make sure `python --version` works in a new PowerShell window, or install Python from python.org and tick "Add python.exe to PATH".
- **Full log:** the logs of the last ten Fenn runs are in `%APPDATA%\Fenn\logs`.
- **Plugins are programs.** They run with the same rights as Fenn. Read the code (one short file) before installing any plugin.

## Credits and license

Scores come from ESPN's public scoreboard feed, which is not an official API. Not affiliated with or endorsed by ESPN.

MIT. See `LICENSE`.

## Files

- `plugin.toml`: the plugin manifest.
- `main.py`: the whole plugin.
- `LICENSE`, `.gitignore`.
