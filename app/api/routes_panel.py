from fastapi import APIRouter, Depends, Form, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import WalletTransactionType
from app.db.session import get_session
from app.schemas import BotConfigUpdate, PasarGuardPanelCreate, ResellerProvisionRequest
from app.services.panel_service import create_panel, get_bot_config, list_panels, telegram_delete_webhook, telegram_get_me, telegram_set_webhook, update_bot_config
from app.services.reseller_service import adjust_wallet, get_reseller_by_id, list_resellers, provision_reseller
from app.services.usage_monitor import run_usage_monitor_once

router = APIRouter(tags=['panel'])


def check_key(key: str | None) -> None:
    if not settings.api_secret_key or key != settings.api_secret_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid panel key')


def page(title: str, body: str) -> HTMLResponse:
    html = f"""
<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ font-family: Tahoma, Arial, sans-serif; background:#0f172a; color:#e5e7eb; margin:0; padding:24px; }}
    .wrap {{ max-width:1200px; margin:0 auto; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:16px; }}
    .card {{ background:#111827; border:1px solid #334155; border-radius:16px; padding:18px; box-shadow:0 10px 30px #0003; }}
    input, select, textarea {{ width:100%; box-sizing:border-box; background:#020617; color:#e5e7eb; border:1px solid #475569; border-radius:10px; padding:10px; margin:6px 0 12px; }}
    button {{ background:#2563eb; color:white; border:0; border-radius:10px; padding:10px 16px; cursor:pointer; }}
    table {{ width:100%; border-collapse:collapse; font-size:13px; }}
    th,td {{ border-bottom:1px solid #334155; padding:8px; text-align:right; }}
    a {{ color:#93c5fd; }}
    .muted {{ color:#94a3b8; font-size:13px; }}
    .danger {{ background:#991b1b; }}
  </style>
</head>
<body><div class="wrap"><h1>{title}</h1>{body}</div></body></html>
"""
    return HTMLResponse(html)


@router.get('/panel', response_class=HTMLResponse)
async def admin_panel(key: str | None = Query(default=None), session: AsyncSession = Depends(get_session)):
    check_key(key)
    resellers = await list_resellers(session)
    panels = await list_panels(session)
    bot_config = await get_bot_config(session)
    reseller_rows = ''.join(
        f'<tr><td>{r.id}</td><td>{r.telegram_id}</td><td>{r.pasar_username}</td><td>{r.status}</td><td>{r.balance_toman:,}</td><td>{r.price_per_gb_toman:,}</td><td>{r.panel_id or "-"}</td></tr>'
        for r in resellers
    ) or '<tr><td colspan="7">نماینده‌ای ثبت نشده است</td></tr>'
    panel_options = ''.join(f'<option value="{p.id}">{p.name} - {p.base_url}</option>' for p in panels)
    panel_rows = ''.join(
        f'<tr><td>{p.id}</td><td>{p.name}</td><td>{p.base_url}</td><td>{p.dashboard_url or "-"}</td><td>{p.default_role_id}</td><td>{"active" if p.is_active else "off"}</td></tr>'
        for p in panels
    ) or '<tr><td colspan="6">پنل پاسارگارد ثبت نشده است</td></tr>'
    bot_status = 'configured' if bot_config.bot_token else 'not configured'
    body = f"""
<div class="grid">
  <div class="card">
    <h2>تنظیمات ربات تلگرام</h2>
    <p class="muted">وضعیت توکن: {bot_status} | یوزرنیم: {bot_config.bot_username or '-'}</p>
    <form method="post" action="/panel/bot?key={key}">
      <label>Bot Token</label><input name="bot_token" placeholder="توکن ربات">
      <label>Webhook URL</label><input name="webhook_url" value="{bot_config.webhook_url or ''}" placeholder="https://domain.com/telegram/webhook/SECRET">
      <label>Webhook Secret</label><input name="webhook_secret" value="{bot_config.webhook_secret or ''}">
      <button>ذخیره تنظیمات ربات</button>
    </form>
    <form method="post" action="/panel/bot/set-webhook?key={key}"><button>Set Webhook</button></form><br>
    <form method="post" action="/panel/bot/delete-webhook?key={key}"><button class="danger">Delete Webhook</button></form>
  </div>

  <div class="card">
    <h2>افزودن پنل PasarGuard</h2>
    <form method="post" action="/panel/pasarguard-panels?key={key}">
      <label>نام پنل</label><input name="name" required>
      <label>Base URL</label><input name="base_url" placeholder="https://panel.example.com" required>
      <label>Dashboard URL</label><input name="dashboard_url" placeholder="https://panel.example.com/dashboard/">
      <label>Admin Username</label><input name="admin_username" required>
      <label>Admin Secret</label><input name="admin_secret" required>
      <label>Default Role ID</label><input name="default_role_id" type="number" value="0">
      <button>ثبت پنل</button>
    </form>
  </div>

  <div class="card">
    <h2>ساخت نماینده</h2>
    <form method="post" action="/panel/resellers/provision?key={key}">
      <label>Telegram ID</label><input name="telegram_id" type="number" required>
      <label>Telegram Username</label><input name="telegram_username">
      <label>PasarGuard Username</label><input name="pasar_username">
      <label>انتخاب پنل PasarGuard</label><select name="panel_id"><option value="">پیش‌فرض</option>{panel_options}</select>
      <label>شارژ اولیه تومان</label><input name="initial_balance_toman" type="number" value="0">
      <label>قیمت هر گیگ تومان</label><input name="price_per_gb_toman" type="number" value="{settings.default_price_per_gb_toman}">
      <label>سقف بدهی تومان</label><input name="debt_limit_toman" type="number" value="{settings.default_debt_limit_toman}">
      <button>ساخت اپراتور نماینده</button>
    </form>
  </div>

  <div class="card">
    <h2>شارژ کیف پول</h2>
    <form method="post" action="/panel/wallet?key={key}">
      <label>Reseller ID</label><input name="reseller_id" type="number" required>
      <label>مبلغ تومان</label><input name="amount_toman" type="number" required>
      <label>توضیح</label><input name="description">
      <button>اعمال تراکنش</button>
    </form>
    <form method="post" action="/panel/usage/run-once?key={key}"><button>اجرای مانیتور مصرف</button></form>
  </div>
</div>

<div class="card"><h2>نماینده‌ها</h2><table><tr><th>ID</th><th>Telegram ID</th><th>Username</th><th>Status</th><th>Balance</th><th>Price/GB</th><th>Panel</th></tr>{reseller_rows}</table></div>
<div class="card"><h2>پنل‌های پاسارگارد</h2><table><tr><th>ID</th><th>Name</th><th>Base URL</th><th>Dashboard</th><th>Role</th><th>Status</th></tr>{panel_rows}</table></div>
"""
    return page('BluePanel Management', body)


@router.post('/panel/bot')
async def panel_bot_save(key: str | None = Query(default=None), bot_token: str | None = Form(default=None), webhook_url: str | None = Form(default=None), webhook_secret: str | None = Form(default=None), session: AsyncSession = Depends(get_session)):
    check_key(key)
    data = BotConfigUpdate(bot_token=bot_token or None, webhook_url=webhook_url or None, webhook_secret=webhook_secret or None)
    config = await update_bot_config(session, data)
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
        raise HTTPException(status_code=400, detail='Bot token and webhook URL required')
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


@router.post('/panel/resellers/provision')
async def panel_provision_reseller(key: str | None = Query(default=None), telegram_id: int = Form(...), telegram_username: str | None = Form(default=None), pasar_username: str | None = Form(default=None), panel_id: str | None = Form(default=None), initial_balance_toman: int = Form(0), price_per_gb_toman: int = Form(5000), debt_limit_toman: int = Form(50000), session: AsyncSession = Depends(get_session)):
    check_key(key)
    await provision_reseller(session, ResellerProvisionRequest(telegram_id=telegram_id, telegram_username=telegram_username or None, pasar_username=pasar_username or None, panel_id=int(panel_id) if panel_id else None, initial_balance_toman=initial_balance_toman, price_per_gb_toman=price_per_gb_toman, debt_limit_toman=debt_limit_toman))
    return RedirectResponse(f'/panel?key={key}', status_code=303)


@router.post('/panel/wallet')
async def panel_wallet(key: str | None = Query(default=None), reseller_id: int = Form(...), amount_toman: int = Form(...), description: str | None = Form(default=None), session: AsyncSession = Depends(get_session)):
    check_key(key)
    reseller = await get_reseller_by_id(session, reseller_id)
    if not reseller:
        raise HTTPException(status_code=404, detail='Reseller not found')
    tx_type = WalletTransactionType.manual_credit if amount_toman >= 0 else WalletTransactionType.manual_debit
    await adjust_wallet(session, reseller, amount_toman, tx_type, description)
    return RedirectResponse(f'/panel?key={key}', status_code=303)


@router.post('/panel/usage/run-once')
async def panel_usage_run(key: str | None = Query(default=None), session: AsyncSession = Depends(get_session)):
    check_key(key)
    await run_usage_monitor_once(session)
    return RedirectResponse(f'/panel?key={key}', status_code=303)
