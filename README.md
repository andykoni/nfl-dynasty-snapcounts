# NFL Dynasty Snap Dashboard

This is the automated version of the dashboard for four MFL dynasty leagues.

## What it does
- Pulls the current roster from each MFL league using the MFL export API.
- Uses the DynastyProcess/nflreadpy player-ID crosswalk to connect MFL IDs to PFR IDs.
- Pulls NFL game-level snap counts from nflverse/PFR.
- Shows offense snap %, IDP defense snap %, special teams snaps, weekly history, 3-week average and season average.
- Consolidates duplicate ownership across leagues into one row.
- Keeps current MFL roster status per league (Active/IR/Taxi).
- Runs automatically from GitHub Actions on Tuesday at 09:00, 12:00 and 15:00 UTC, with a manual Run workflow option.

## Annual change
At the start of a new season, edit only `config.json` with the new season and league URLs. The GitHub Pages URL does not need to change.

## Important
The updater must be run by GitHub Actions because the local ChatGPT runtime cannot reach MFL/nflverse directly. The included `data.json` is only a preview until the first successful GitHub Action run.
