# delta24

A Delta Chat bot that posts Nösnäsgymnasiet's Skola24 schedule as a picture.

Write in a group where the bot and the owner are both members:

```
/s TE23A        today (on weekends: the coming Monday)
/s TE23A -w     current week
/s TE23A -w42   week 42
```

The ID is a class name or a teacher signature. Personnummer are refused.
The bot is silent in 1:1 chats and in groups the owner is not in.

## Run it

1. On a machine with Docker, download the compose file and start it.
   Docker fetches the rest of this repo by itself:

   ```
   curl -O https://raw.githubusercontent.com/seetee/delta24/main/docker-compose.yml
   docker compose up -d --build
   docker compose logs bot
   ```

   The log shows the bot's invite link and a one-time `/claim` code.

2. Open the invite link in Delta Chat and send the bot the `/claim ...`
   line from the log. You are now the bot's owner. The code changes at
   every start and stops working once the bot has an owner.
3. Add the bot to a group you are in.

Update: run `docker compose up -d --build` again.

The volume `data` holds the bot's profile and keys. If it is deleted, the
bot becomes a new contact, forgets its owner, and must be invited again.

## Good to know

- **Who can use it.** The bot answers in every group that contains its
  owner. Anyone who has both the owner and the bot as contacts can create
  such a group, so treat the bot as usable by everyone who has met it.
  It only hands out schedules that are public on the web anyway.
- **What it stores.** As a group member the bot receives every message in
  the group. It deletes them from its own storage after one hour and
  sends no read receipts.
- **Limits.** One request per person every 5 seconds and one per
  2 seconds in total; the rest are silently dropped.
- **Keep it patched.** Nothing updates by itself. About once a month:

  ```
  docker compose build --pull --no-cache && docker compose up -d
  ```

## Develop

```
uv run test_bot.py                  # check the command parser
uv run bot.py                       # run without Docker, profile in ./data
```

`docker compose build` always builds what is on GitHub. To build local
changes, set `context: .` in `docker-compose.yml` for the moment.

## Change how schedules are fetched

`bot.py` knows only one function: `fetch_schedule(id, week, whole_week)` in
`skola24.py`, which returns the path to a PNG. To use something else (for
example a headless browser), write a module with the same function and
change the import line in `bot.py`.

`skola24.py` uses the same undocumented API as Skola24's own viewer page.
It can change without notice.

## Licence

GNU Affero General Public License v3.0, see `LICENSE`.
