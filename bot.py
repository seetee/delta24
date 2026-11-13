"""Delta Chat bot: "/s TE23A" in a group posts that schedule as a picture."""

import logging
import os
import re
import time

from deltachat_rpc_client import Bot, DeltaChat, Rpc, events
from deltachat_rpc_client.const import ChatType

from skola24 import fetch_schedule  # change this import to fetch schedules another way

USAGE = "Skriv /s ID för dagens schema, /s ID -w för veckan eller /s ID -w42 för vecka 42."
SECONDS_BETWEEN_REQUESTS = 5
OWNER_KEY = "ui.owner"  # the owner's contact id, kept in the bot's own profile

hooks = events.HookCollection()
last_request = {}


def parse(text):
    """Return (id, week, whole_week) from the text after /s, or None if invalid."""
    match = re.fullmatch(r"\s*(.+?)(\s+-w(\d{1,2})?)?\s*", text)
    if not match:
        return None
    id, whole_week, week = match.group(1), match.group(2) is not None, match.group(3)
    if not re.fullmatch(r"[\w -]{1,20}", id) or id.startswith("-"):
        return None
    if re.fullmatch(r"(\d{6}|\d{8})[- ]?\d{4}", id):  # personnummer: never look up pupils
        return None
    if week is not None and not 1 <= int(week) <= 53:
        return None
    return id, int(week) if week else None, whole_week


@hooks.on(events.NewMessage())
def claim_ownership(event):
    """The first person to write to the bot in a 1:1 chat becomes its owner."""
    message = event.message_snapshot
    account = message.chat.account
    if account.get_config(OWNER_KEY):
        return
    if message.chat.get_basic_snapshot().chat_type != ChatType.SINGLE:
        return
    # Stored in the bot's profile, so no address has to be written in any file.
    account.set_config(OWNER_KEY, str(message.from_id))
    message.chat.send_text("Du är nu botens ägare. Jag svarar bara i grupper där du är med.")


@hooks.on(events.NewMessage(command="/s"))
def on_schedule_request(event):
    message = event.message_snapshot
    chat = message.chat
    if chat.get_basic_snapshot().chat_type != ChatType.GROUP:
        return
    owner = chat.account.get_config(OWNER_KEY)
    if not owner or int(owner) not in {contact.id for contact in chat.get_contacts()}:
        return

    now = time.monotonic()
    if now - last_request.get(message.from_id, -SECONDS_BETWEEN_REQUESTS) < SECONDS_BETWEEN_REQUESTS:
        return
    last_request[message.from_id] = now

    request = parse(event.payload)
    if not request:
        chat.send_text(USAGE)
        return
    id, week, whole_week = request
    try:
        picture = fetch_schedule(id, week, whole_week)
    except Exception:
        logging.exception("Could not fetch schedule for %s", id)
        chat.send_text(f"Hittade inget schema för {id}.")
        return
    chat.send_message(text=id, file=picture)
    os.remove(picture)


def main():
    logging.basicConfig(level=logging.INFO)
    with Rpc(accounts_dir=os.getenv("DATA", "data")) as rpc:
        deltachat = DeltaChat(rpc)
        accounts = deltachat.get_all_accounts()
        account = accounts[0] if accounts else deltachat.add_account()
        if not account.is_configured():
            account.set_config("bot", "1")
            account.set_config("displayname", "Schema")
            account.init_transports(os.getenv("RELAY_QR") or None)
        logging.info("Invite link for the bot: %s", account.get_qr_code())
        if not account.get_config(OWNER_KEY):
            logging.info("No owner yet: the first person to write to the bot in a 1:1 chat becomes owner.")
        Bot(account, hooks).run_forever()


if __name__ == "__main__":
    main()
