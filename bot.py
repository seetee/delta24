"""Delta Chat bot: "/s TE23A" in a group posts that schedule as a picture."""

import hmac
import logging
import os
import re
import secrets
import time

from deltachat_rpc_client import Bot, DeltaChat, Rpc, events
from deltachat_rpc_client.const import ChatType

from skola24 import fetch_schedule  # change this import to fetch schedules another way

USAGE = "Skriv /s ID för dagens schema, /s ID -w för veckan eller /s ID -w42 för vecka 42."
SECONDS_BETWEEN_REQUESTS = 5  # per person
SECONDS_BETWEEN_ANY_REQUESTS = 2  # for everyone together, to spare the VPS and Skola24
MAX_AGE_SECONDS = 60  # requests that waited longer than this are dropped
KEEP_MESSAGES_SECONDS = "3600"  # group messages the bot receives are deleted after this
OWNER_KEY = "ui.owner"  # the owner's contact id, kept in the bot's own profile

hooks = events.HookCollection()
last_request = {}
claim_code = secrets.token_hex(8)  # new at every start, only shown in the log


def parse(text):
    """Return (id, week, whole_week) from the text after /s, or None if invalid."""
    match = re.fullmatch(r"\s*(.+?)(\s+-w(\d{1,2})?)?\s*", text)
    if not match:
        return None
    id, whole_week, week = match.group(1), match.group(2) is not None, match.group(3)
    if not re.fullmatch(r"[\w -]{1,20}", id) or id.startswith("-"):
        return None
    digits = re.sub(r"[ -]", "", id)
    if digits.isdigit() and len(digits) in (10, 12):  # personnummer: never look up pupils
        return None
    if week is not None and not 1 <= int(week) <= 53:
        return None
    return id, int(week) if week else None, whole_week


@hooks.on(events.NewMessage(command="/claim"))
def claim_ownership(event):
    """Whoever sends the code from the log in a 1:1 chat becomes the bot's owner."""
    message = event.message_snapshot
    account = message.chat.account
    if account.get_config(OWNER_KEY):
        return
    if message.chat.get_basic_snapshot().chat_type != ChatType.SINGLE:
        return
    if not hmac.compare_digest(event.payload.strip(), claim_code):
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

    if time.time() - message.received_timestamp > MAX_AGE_SECONDS:
        return
    now = time.monotonic()
    if now - last_request.get(message.from_id, -SECONDS_BETWEEN_REQUESTS) < SECONDS_BETWEEN_REQUESTS:
        return
    if now - last_request.get(None, -SECONDS_BETWEEN_ANY_REQUESTS) < SECONDS_BETWEEN_ANY_REQUESTS:
        return
    last_request[message.from_id] = last_request[None] = now

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
    try:
        chat.send_message(text=id, file=picture)
    finally:
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
        account.set_config("delete_device_after", KEEP_MESSAGES_SECONDS)
        account.set_config("mdns_enabled", "0")  # no read receipts for other people's messages
        if not account.get_config(OWNER_KEY):
            logging.info("Invite link for the bot: %s", account.get_qr_code())
            logging.info("No owner yet. To become owner, send the bot this in a 1:1 chat: /claim %s", claim_code)
        Bot(account, hooks).run_forever()


if __name__ == "__main__":
    main()
