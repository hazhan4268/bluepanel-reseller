from html import escape
from fastapi import APIRouter, Depends, Form, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_session
from app.schemas import BotConfigUpdate, PasarGuardPanelCreate
from app.services.panel_service import create_panel, get_bot_config, list_panels, telegram_delete_webhook, telegram_get_me, telegram_set_webhook, update_bot_config
from app.services.reseller_service import list_resellers
from app.services.usage_monitor import run_usage_monitor_once

router = APIRouter(tags=['panel'])
PANEL_VERSION = 'clean-master-v3'


def check_key(key: str | None) -> None:
    if not settings.api_secret_key or key != settings.api_secret_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid panel key')


def h(value: object) -> str:
    return escape(str(value)) if value is not None else ''


def badge(text: str, cls: str = 'gray') -> str:
    return f'<span class="badge {cls}">{h(text)}</span>'


def page(body: str) -> HTMLResponse:
    return HTMLResponse(f'''<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BluePanel Master</title><style>
body{{margin:0;background:#07111f;color:#edf6ff;font-family:Tahoma,Arial,sans-serif}}.wrap{{max-width:1180px;margin:0 auto;padding:24px}}.top,.card{{background:#101b2e;border:1px solid #263750;border-radius:20px;padding:18px;margin:16px 0}}.top{{display:flex;justify-content:space-between;gap:12px;align-items:center}}.ver{{direction:ltr;background:#07111f;border:1px solid #263750;border-radius:999px;padding:8px 12px;color:#93c5fd;font-size:12px}}.hint{{color:#94a3b8;font-size:13px;line-height:1.8}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}label{{display:block;color:#cbd5e1;font-size:12px;margin:10px 0 6px}}input{{width:100%;box-sizing:border-box;background:#07111f;color:#edf6ff;border:1px solid #334155;border-radius:12px;padding:11px}}button{{border:0;border-radius:12px;padding:11px 16px;background:#2563eb;color:white;font-weight:700;cursor:pointer;margin-top:12px}}button.green{{background:#16a34a}}button.red{{background:#dc2626}}.actions{{display:flex;gap:10px;flex-wrap:wrap}}.table{{overflow:auto;border:1px solid #263750;border-radius:16px}}table{{width:100%;min-width:760px;border-collapse:collapse}}th,td{{border-bottom:1px solid #263750;padding:11px;text-align:right;white-space:nowrap}}th{{background:#0b1628;color:#bfdbfe}}.mono{{direction:ltr;unicode-bidi:plaintext;font-family:Consolas,monospace}}.badge{{display:inline-flex;padding:6px 10px;border-radius:999px;background:#334155;color:#e2e8f0;font-size:12px}}.ok{{background:#14532d;color:#bbf7d0}}.warn{{background:#713f12;color:#fde68a}}.bad{{background:#7f1d1d;color:#fecaca}}@media(max-width:800px){{.grid,.top{{display:block}}.wrap{{padding:12px}}}}
</style></head><body><div class="wrap">{body}</div></body></html>''')


@router.get('/panel', response_class=HTMLResponse)
async def panel(key: str | None = Query(default=None), session: AsyncSession = Depends(get_session)):
    check_key(key)
    bot = await get_bot_config(session)
    panels = await list_panels(session)
    resellers = await list_resellers(session)
    bot_badge = badge('Bot connected', 'ok') if bot.bot_token else badge('Bot not set', 'bad')
    hook_badge = badge('Webhook on', 'ok') if bot.webhook_enabled else badge('Webhook off', 'warn')
    panel_rows = ''.join(f'<tr><td>#{p.id}</td><td>{h(p.name)}</td><td class="mono">{h(p.base_url)}</td><td class="mono">{h(p.dashboard_url) or "-"}</td><td>{p.default_role_id}</td><td>{badge("active","ok") if p.is_active else badge("off","bad")}</td></tr>' for p in panels) or '<tr><td colspan="6">No PasarGuard connection.</td></tr>'
    reseller_rows = ''.join(f'<tr><td>#{r.id}</td><td>{r.telegram_id}</td><td>{h(r.telegram_username) or "-"}</td><td class="mono">{h(r.pasar_username)}</td><td>{badge(r.status,"ok" if r.status == "active" else "warn")}</td><td>{r.balance_toman:,}</td><td>{r.price_per_gb_toman:,}</td><td>{(r.last_total_usage_bytes or 0)/(1024**3):,.2f} GB</td><td>{r.panel_id or "-"}</td></tr>' for r in resellers) or '<tr><td colspan="9">No reseller yet. Creation is inside Telegram bot.</td></tr>'
    secret_value = h(bot.webhook_secret) if bot.webhook_secret else 'WEBHOOK_SECRET'
    body = f'''
<div class="top"><div><h1>BluePanel Master Panel</h1><p class="hint">Clean system panel. Reseller creation is only inside Telegram bot.</p></div><span class="ver">{PANEL_VERSION}</span></div>
<div class="grid"><div class="card"><h2>Telegram</h2><p>{bot_badge} {hook_badge}</p><form method="post" action="/panel/bot?key={h(key)}"><label>Bot credential</label><input class="mono" name="bot_token"><label>Webhook URL</label><input class="mono" name="webhook_url" value="{h(bot.webhook_url)}" placeholder="https://domain.com/telegram/webhook/{secret_value}"><label>Webhook key</label><input class="mono" name="webhook_secret" value="{secret_value}"><button>Save Telegram</button></form><div class="actions"><form method="post" action="/panel/bot/set-webhook?key={h(key)}"><button class="green">Set Webhook</button></form><form method="post" action="/panel/bot/delete-webhook?key={h(key)}"><button class="red">Delete Webhook</button></form></div></div>
<div class="card"><h2>PasarGuard</h2><p class="hint">Connect the real PasarGuard panel. Bot creates operators there.</p><form method="post" action="/panel/pasarguard-panels?key={h(key)}"><label>Name</label><input name="name" required><label>Base URL</label><input class="mono" name="base_url" required><label>Dashboard URL</label><input class="mono" name="dashboard_url"><label>Owner user</label><input name="admin_username" required><label>Owner key</label><input name="admin_secret" required><label>Default role ID</label><input name="default_role_id" type="number" value="0"><button>Save PasarGuard</button></form></div></div>
<div class="card"><h2>Usage monitor</h2><p class="hint">Reads usage and applies billing.</p><form method="post" action="/panel/usage/run-once?key={h(key)}"><button class="green">Run now</button></form></div>
<div class="card"><h2>Resellers</h2><p class="hint">Read-only report. No creation form here.</p><div class="table"><table><thead><tr><th>ID</th><th>Telegram ID</th><th>Telegram</th><th>PasarGuard user</th><th>Status</th><th>Balance</th><th>Price/GB</th><th>Usage</th><th>Panel</th></tr></thead><tbody>{reseller_rows}</tbody></table></div></div>
<div class="card"><h2>PasarGuard connections</h2><div class="table"><table><thead><tr><th>ID</th><th>Name</th><th>Base URL</th><th>Dashboard</th><th>Role ID</th><th>Status</th></tr></thead><tbody>{panel_rows}</tbody></table></div></div>
'''
    return page(body)


@router.post('/panel/bot')
async def panel_bot_save(key: str | None = Query(default=None), bot_token: str | None = Form(default=None), webhook_url: str | None = Form(default=None), webhook_secret: str | None = Form(default=None), session: AsyncSession = Depends(get_session)):
    check_key(key)
    config = await update_bot_config(session, BotConfigUpdate(bot_token=bot_token or None, webhook_url=webhook_url or None, webhook_secret=webhook_secret or None))
    if config.bot_token:
        try:
            me = await telegram_get_me(config.bot_token)
            config.bot_username = me.get('username')
            session.add(config)
            await session.commit()
        except Exception:
            pass
    return RedirectResponse(f'/panel?key={key}', status_code=303)


@router.post('/panel/bot/set-webhook')
async def panel_bot_set_webhook(key: str | None = Query(default=None), session: AsyncSession = Depends(get_session)):
    check_key(key)
    config = await get_bot_config(session)
    if not config.bot_token or not config.webhook_url:
        raise HTTPException(status_code=400, detail='Bot credential and webhook URL required')
    await telegram_set_webhook(config.bot_token, config.webhook_url, config.webhook_secret)
    config.webhook_enabled = True
    session.add(config)
    await session.commit()
    return RedirectResponse(f'/panel?key={key}', status_code=303)


@router.post('/panel/bot/delete-webhook')
async def panel_bot_delete_webhook(key: str | None = Query(default=None), session: AsyncSession = Depends(get_session)):
    check_key(key)
    config = await get_bot_config(session)
    if config.bot_token:
        await telegram_delete_webhook(config.bot_token)
    config.webhook_enabled = False
    session.add(config)
    await session.commit()
    return RedirectResponse(f'/panel?key={key}', status_code=303)


@router.post('/panel/pasarguard-panels')
async def panel_create_pasarguard(key: str | None = Query(default=None), name: str = Form(...), base_url: str = Form(...), dashboard_url: str | None = Form(default=None), admin_username: str = Form(...), admin_secret: str = Form(...), default_role_id: int = Form(0), session: AsyncSession = Depends(get_session)):
    check_key(key)
    await create_panel(session, PasarGuardPanelCreate(name=name, base_url=base_url, dashboard_url=dashboard_url or None, admin_username=admin_username, admin_secret=admin_secret, default_role_id=default_role_id))
    return RedirectResponse(f'/panel?key={key}', status_code=303)


@router.post('/panel/usage/run-once')
async def panel_usage_run(key: str | None = Query(default=None), session: AsyncSession = Depends(get_session)):
    check_key(key)
    await run_usage_monitor_once(session)
    return RedirectResponse(f'/panel?key={key}', status_code=303)
