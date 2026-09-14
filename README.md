# NFL Dynasty Snap Dashboard

Live dashboard for four MFL dynasty teams.

## Automatic behaviour
- MFL API is the source of truth for current rosters.
- nflverse supplies weekly offensive, defensive and special-teams snaps.
- The scheduled GitHub Action runs three times each Tuesday.
- The main dashboard only displays players currently on the four rosters.
- Dropped/traded players therefore disappear on the next refresh.
- Historical NFL snap data is retained in `data.json` for the current-player trend view.
- New MFL league URLs can be changed in `config.json` next season; the website URL stays the same.

## Sources
MFL's export API supports current rosters by league/franchise. nflverse provides snap counts and cross-platform player IDs.
