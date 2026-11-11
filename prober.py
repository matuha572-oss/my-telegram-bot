import os
import random
import asyncio
import concurrent.futures
from telethon import TelegramClient
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.types import InputPhoneContact
from telethon.errors import FloodWaitError

API_ID = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")
SESSIONS_DIR = os.getenv("SESSIONS_DIR", "sessions")

_pool = []
_idx = 0


def _load_sessions():
    if not os.path.isdir(SESSIONS_DIR):
        return []
    return [
        os.path.join(SESSIONS_DIR, f[:-8])
        for f in os.listdir(SESSIONS_DIR)
        if f.endswith(".session")
    ]


async def _get_client():
    global _pool, _idx
    if not _pool:
        _pool = _load_sessions()
    if not _pool:
        return None
    path = _pool[_idx % len(_pool)]
    _idx += 1
    client = TelegramClient(path, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        return None
    return client


async def tg_lookup(phone: str) -> dict:
    client = await _get_client()
    if not client:
        return {"error": "нет живых сессий (положи .session в sessions/)"}
    try:
        contact = InputPhoneContact(
            client_id=random.randint(1, 10**9),
            phone=phone,
            first_name="chk",
            last_name="chk",
        )
        res = await client(ImportContactsRequest([contact]))
        if res.users:
            u = res.users[0]
            out = {
                "exists": True,
                "id": u.id,
                "username": u.username,
                "name": f"{u.first_name or ''} {u.last_name or ''}".strip(),
            }
            await client(DeleteContactsRequest(id=[u.id]))
        else:
            out = {"exists": False}
        return out
    except FloodWaitError as e:
        return {"error": f"флуд, жди {e.seconds} сек"}
    except Exception as e:
        return {"error": str(e)}
    finally:
        await client.disconnect()


def tg_lookup_sync(phone: str) -> dict:
    def _run():
        return asyncio.run(tg_lookup(phone))
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(_run).result()
