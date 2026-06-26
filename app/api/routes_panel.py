from html import escape

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


def h(value: object) -> str:
    return escape(str(value)) if value is not None else ''


def toman(value: int | None) -> str:
    return f'{value or 0:,} تومان'


def gb(value: int | None) -> str:
    if not value:
        return '0 GB'
    return f'{value / (1024 ** 3):,.2f} GB'


def status_badge(status_value: str) -> str:
    klass = {
        'active': 'ok',
        'limited': 'warn',
        'disabled': 'danger',
        'pending': 'muted',
    }.get(status_value, 'muted')
    return f'<span class="badge {klass}">{h(status_value)}</span>'


def page(title: str, body: str) -> HTMLResponse:
    html = f"""
<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{h(title)}</title>
  <style>
    :root {{
      --bg:#07111f; --bg2:#0d1728; --card:#111c2f; --card2:#162238;
      --line:#24344d; --text:#eef5ff; --muted:#94a3b8; --brand:#38bdf8;
      --brand2:#2563eb; --green:#22c55e; --yellow:#f59e0b; --red:#ef4444;
      --shadow:0 24px 60px rgba(0,0,0,.28); --radius:22px;
    }}
    * {{ box-sizing:border-box; }}
    html {{ scroll-behavior:smooth; }}
    body {{ margin:0; background:radial-gradient(circle at top right,#143252 0,#07111f 38%,#050914 100%); color:var(--text); font-family:Tahoma,Arial,sans-serif; }}
    a {{ color:inherit; text-decoration:none; }}
    .layout {{ display:grid; grid-template-columns:260px 1fr; min-height:100vh; }}
    .sidebar {{ position:sticky; top:0; height:100vh; padding:24px; background:rgba(6,13,24,.78); border-left:1px solid var(--line); backdrop-filter:blur(18px); }}
    .brand {{ display:flex; gap:12px; align-items:center; margin-bottom:28px; }}
    .logo {{ width:46px; height:46px; border-radius:16px; display:grid; place-items:center; background:linear-gradient(135deg,var(--brand),var(--brand2)); font-weight:900; box-shadow:0 14px 35px rgba(56,189,248,.25); }}
    .brand h1 {{ margin:0; font-size:18px; }}
    .brand p {{ margin:4px 0 0; color:var(--muted); font-size:12px; }}
    .nav a {{ display:flex; align-items:center; justify-content:space-between; padding:13px 14px; border:1px solid transparent; color:#cbd5e1; border-radius:15px; margin:8px 0; background:rgba(255,255,255,.025); }}
    .nav a:hover {{ border-color:var(--line); background:rgba(56,189,248,.08); color:white; }}
    .main {{ padding:28px; max-width:1500px; width:100%; }}
    .hero {{ display:flex; justify-content:space-between; gap:16px; align-items:center; background:linear-gradient(135deg,rgba(37,99,235,.35),rgba(56,189,248,.12)); border:1px solid rgba(125,211,252,.25); border-radius:var(--radius); padding:24px; box-shadow:var(--shadow); margin-bottom:18px; }}
    .hero h2 {{ margin:0 0 8px; font-size:26px; }}
    .hero p {{ margin:0; color:#dbeafe; line-height:1.9; }}
    .quick-actions {{ display:flex; gap:10px; flex-wrap:wrap; }}
    .btn, button {{ display:inline-flex; align-items:center; justify-content:center; gap:8px; border:0; border-radius:14px; padding:11px 16px; background:linear-gradient(135deg,var(--brand2),#1d4ed8); color:white; cursor:pointer; font-weight:700; box-shadow:0 12px 28px rgba(37,99,235,.24); }}
    .btn.secondary {{ background:#1f2937; box-shadow:none; border:1px solid var(--line); }}
    .btn.danger, button.danger {{ background:linear-gradient(135deg,#dc2626,#991b1b); }}
    .btn.green, button.green {{ background:linear-gradient(135deg,#16a34a,#15803d); }}
    .stats {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin:18px 0; }}
    .stat {{ background:rgba(17,28,47,.82); border:1px solid var(--line); border-radius:20px; padding:18px; box-shadow:0 14px 35px rgba(0,0,0,.18); }}
    .stat span {{ display:block; color:var(--muted); font-size:12px; margin-bottom:10px; }}
    .stat strong {{ font-size:24px; }}
    .section {{ background:rgba(17,28,47,.82); border:1px solid var(--line); border-radius:var(--radius); padding:20px; margin:18px 0; box-shadow:0 18px 45px rgba(0,0,0,.2); }}
    .section-head {{ display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:16px; }}
    .section h3 {{ margin:0; font-size:19px; }}
    .hint {{ color:var(--muted); font-size:12px; line-height:1.8; }}
    .forms {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }}
    .form-card {{ background:rgba(2,6,23,.34); border:1px solid var(--line); border-radius:18px; padding:16px; }}
    .form-card h4 {{ margin:0 0 14px; }}
    .field-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }}
    label {{ display:block; color:#cbd5e1; font-size:12px; margin-bottom:6px; }}
    input, select, textarea {{ width:100%; min-height:42px; background:#07111f; color:var(--text); border:1px solid #334155; border-radius:13px; padding:10px 12px; outline:none; margin-bottom:12px; }}
    input:focus, select:focus {{ border-color:var(--brand); box-shadow:0 0 0 3px rgba(56,189,248,.12); }}
    .table-wrap {{ overflow:auto; border:1px solid var(--line); border-radius:18px; }}
    table {{ width:100%; border-collapse:collapse; min-width:760px; }}
    th {{ background:#0b1628; color:#bfdbfe; font-size:12px; }}
    th,td {{ border-bottom:1px solid var(--line); padding:12px; text-align:right; white-space:nowrap; }}
    tr:hover td {{ background:rgba(56,189,248,.035); }}
    .badge {{ display:inline-flex; align-items:center; justify-content:center; min-width:76px; padding:6px 10px; border-radius:999px; font-size:12px; border:1px solid transparent; }}
    .badge.ok {{ color:#bbf7d0; background:rgba(34,197,94,.12); border-color:rgba(34,197,94,.28); }}
    .badge.warn {{ color:#fde68a; background:rgba(245,158,11,.12); border-color:rgba(245,158,11,.28); }}
    .badge.danger {{ color:#fecaca; background:rgba(239,68,68,.12); border-color:rgba(239,68,68,.28); }}
    .badge.muted {{ color:#cbd5e1; background:rgba(148,163,184,.12); border-color:rgba(148,163,184,.22); }}
    .split-actions {{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; }}
    .mono {{ direction:ltr; unicode-bidi:plaintext; font-family:ui-monospace,SFMono-Regular,Consolas,monospace; }}
    @media (max-width: 980px) {{ .layout {{ grid-template-columns:1fr; }} .sidebar {{ position:relative; height:auto; }} .nav {{ display:grid; grid-template-columns:repeat(2,1fr); gap:8px; }} .stats {{ grid-template-columns:repeat(2,1fr); }} .forms {{ grid-template-columns:1fr; }} .hero {{ flex-direction:column; align-items:flex-start; }} }}
    @media (max-width: 560px) {{ body {{ font-size:14px; }} .main {{ padding:14px; }} .sidebar {{ padding:14px; }} .stats {{ grid-template-columns:1fr; }} .field-grid {{ grid-template-columns:1fr; }} .nav {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand"><div class="logo">BP</div><div><h1>BluePanel</h1><p>Reseller Management</p></div></div>
      <nav class="nav">
        <a href="#dashboard">داشبورد <span>⌁</span></a>
        <a href="#bot">تنظیمات ربات <span>🤖</span></a>
        <a href="#panels">پنل‌های پاسارگارد <span>🌐</span></a>
        <a href="#reseller-create">ساخت نماینده <span>➕</span></a>
        <a href="#wallet">کیف پول <span>💰</span></a>
        <a href="#tables">گزارش‌ها <span>📊</span></a>
      </nav>
    </aside>
    <main class="main">{body}</main>
  </div>
</body>
</html>
"""
    return HTMLResponse(html)


@router.get('/panel', response_class=HTMLResponse)
async def admin_panel(key: str | None = Query(default=None), session: AsyncSession = Depends(get_session)):
    check_key(key)
    resellers = await list_resellers(session)
    panels = await list_panels(session)
    bot_config = await get_bot_config(session)

    active_count = sum(1 for r in resellers if r.status == 'active')
    limited_count = sum(1 for r in resellers if r.status == 'limited')
    disabled_count = sum(1 for r in resellers if r.status == 'disabled')
    total_balance = sum(r.balance_toman for r in resellers)

    panel_options = ''.join(f'<option value="{p.id}">{h(p.name)} - {h(p.base_url)}</option>' for p in panels)
    reseller_rows = ''.join(
        f'<tr><td>#{r.id}</td><td>{r.telegram_id}</td><td>{h(r.telegram_username) or "-"}</td><td class="mono">{h(r.pasar_username)}</td><td>{status_badge(r.status)}</td><td>{toman(r.balance_toman)}</td><td>{toman(r.price_per_gb_toman)}</td><td>{gb(r.last_total_usage_bytes)}</td><td>{r.panel_id or "-"}</td></tr>'
        for r in resellers
    ) or '<tr><td colspan="9">هنوز نماینده‌ای ثبت نشده است.</td></tr>'
    panel_rows = ''.join(
        f'<tr><td>#{p.id}</td><td>{h(p.name)}</td><td class="mono">{h(p.base_url)}</td><td class="mono">{h(p.dashboard_url) or "-"}</td><td>{p.default_role_id}</td><td>{status_badge("active" if p.is_active else "disabled")}</td></tr>'
        for p in panels
    ) or '<tr><td colspan="6">هنوز پنل پاسارگارد ثبت نشده است.</td></tr>'

    bot_status = status_badge('active') if bot_config.bot_token else status_badge('disabled')
    webhook_status = status_badge('active') if bot_config.webhook_enabled else status_badge('pending')
    webhook_placeholder = f'https://your-domain.com/telegram/webhook/{h(bot_config.webhook_secret)}' if bot_config.webhook_secret else 'https://your-domain.com/telegram/webhook/SECRET'

    body = f"""
<section id="dashboard" class="hero">
  <div>
    <h2>پنل مدیریت بلوپنل</h2>
    <p>مدیریت نماینده‌ها، کیف پول، ربات تلگرام و اتصال چند پنل PasarGuard در یک صفحه مرتب.</p>
  </div>
  <div class="quick-actions">
    <a class="btn secondary" href="/health">Health</a>
    <a class="btn" href="#reseller-create">ساخت نماینده</a>
  </div>
</section>

<section class="stats">
  <div class="stat"><span>کل نماینده‌ها</span><strong>{len(resellers):,}</strong></div>
  <div class="stat"><span>نماینده فعال</span><strong>{active_count:,}</strong></div>
  <div class="stat"><span>محدود / غیرفعال</span><strong>{limited_count + disabled_count:,}</strong></div>
  <div class="stat"><span>موجودی کل</span><strong>{toman(total_balance)}</strong></div>
</section>

<section id="bot" class="section">
  <div class="section-head"><div><h3>تنظیمات ربات تلگرام</h3><div class="hint">توکن، وبهوک و وضعیت اتصال ربات از همین بخش مدیریت می‌شود.</div></div><div class="split-actions">{bot_status}{webhook_status}</div></div>
  <div class="forms">
    <div class="form-card">
      <h4>اطلاعات ربات</h4>
      <form method="post" action="/panel/bot?key={h(key)}">
        <div class="field-grid">
          <div><label>Bot Token</label><input name="bot_token" placeholder="توکن ربات را اینجا وارد کن"></div>
          <div><label>Bot Username</label><input value="{h(bot_config.bot_username) or '-'}" disabled></div>
        </div>
        <label>Webhook URL</label><input class="mono" name="webhook_url" value="{h(bot_config.webhook_url)}" placeholder="{webhook_placeholder}">
        <label>Webhook Secret</label><input class="mono" name="webhook_secret" value="{h(bot_config.webhook_secret)}">
        <button>ذخیره تنظیمات ربات</button>
      </form>
    </div>
    <div class="form-card">
      <h4>عملیات Webhook</h4>
      <p class="hint">بعد از ذخیره توکن و Webhook URL، روی Set Webhook بزن. اگر از polling استفاده می‌کنی، Delete Webhook را بزن.</p>
      <div class="split-actions">
        <form method="post" action="/panel/bot/set-webhook?key={h(key)}"><button class="green">Set Webhook</button></form>
        <form method="post" action="/panel/bot/delete-webhook?key={h(key)}"><button class="danger">Delete Webhook</button></form>
      </div>
    </div>
  </div>
</section>

<section id="panels" class="section">
  <div class="section-head"><div><h3>پنل‌های PasarGuard</h3><div class="hint">چند پنل مرکزی اضافه کن و نماینده را روی پنل دلخواه بساز.</div></div><span class="badge ok">{len(panels)} پنل</span></div>
  <div class="form-card">
    <form method="post" action="/panel/pasarguard-panels?key={h(key)}">
      <div class="field-grid">
        <div><label>نام پنل</label><input name="name" required placeholder="مثلا Germany Main"></div>
        <div><label>Base URL</label><input class="mono" name="base_url" placeholder="https://panel.example.com" required></div>
        <div><label>Dashboard URL</label><input class="mono" name="dashboard_url" placeholder="https://panel.example.com/dashboard/"></div>
        <div><label>Default Role ID</label><input name="default_role_id" type="number" value="0"></div>
        <div><label>Admin Username</label><input name="admin_username" required></div>
        <div><label>Admin Secret</label><input name="admin_secret" required></div>
      </div>
      <button>ثبت پنل پاسارگارد</button>
    </form>
  </div>
</section>

<section id="reseller-create" class="section">
  <div class="section-head"><div><h3>ساخت نماینده</h3><div class="hint">بعد از ثبت، برای نماینده داخل PasarGuard اپراتور ساخته می‌شود.</div></div></div>
  <div class="form-card">
    <form method="post" action="/panel/resellers/provision?key={h(key)}">
      <div class="field-grid">
        <div><label>Telegram ID</label><input name="telegram_id" type="number" required></div>
        <div><label>Telegram Username</label><input name="telegram_username" placeholder="بدون @"></div>
        <div><label>PasarGuard Username</label><input name="pasar_username" placeholder="خالی بماند خودکار ساخته می‌شود"></div>
        <div><label>انتخاب پنل PasarGuard</label><select name="panel_id"><option value="">پنل پیش‌فرض</option>{panel_options}</select></div>
        <div><label>شارژ اولیه</label><input name="initial_balance_toman" type="number" value="0"></div>
        <div><label>قیمت هر گیگ</label><input name="price_per_gb_toman" type="number" value="{settings.default_price_per_gb_toman}"></div>
        <div><label>سقف بدهی</label><input name="debt_limit_toman" type="number" value="{settings.default_debt_limit_toman}"></div>
      </div>
      <button>ساخت اپراتور نماینده</button>
    </form>
  </div>
</section>

<section id="wallet" class="section">
  <div class="section-head"><div><h3>کیف پول و مصرف</h3><div class="hint">شارژ دستی، کسر دستی و اجرای فوری مانیتور مصرف.</div></div></div>
  <div class="forms">
    <div class="form-card">
      <h4>تراکنش کیف پول</h4>
      <form method="post" action="/panel/wallet?key={h(key)}">
        <div class="field-grid">
          <div><label>Reseller ID</label><input name="reseller_id" type="number" required></div>
          <div><label>مبلغ تومان</label><input name="amount_toman" type="number" required placeholder="مثبت برای شارژ، منفی برای کسر"></div>
        </div>
        <label>توضیح</label><input name="description" placeholder="مثلا شارژ دستی کارت به کارت">
        <button>اعمال تراکنش</button>
      </form>
    </div>
    <div class="form-card">
      <h4>مانیتور مصرف</h4>
      <p class="hint">مصرف نماینده‌ها از پنل PasarGuard خوانده می‌شود و هزینه از کیف پولشان کم می‌شود.</p>
      <form method="post" action="/panel/usage/run-once?key={h(key)}"><button class="green">اجرای مانیتور مصرف</button></form>
    </div>
  </div>
</section>

<section id="tables" class="section">
  <div class="section-head"><div><h3>نماینده‌ها</h3><div class="hint">لیست نماینده‌های ثبت‌شده و وضعیت مالی/مصرف.</div></div></div>
  <div class="table-wrap"><table><thead><tr><th>ID</th><th>Telegram ID</th><th>Username</th><th>PasarGuard</th><th>Status</th><th>Balance</th><th>Price/GB</th><th>Usage</th><th>Panel</th></tr></thead><tbody>{reseller_rows}</tbody></table></div>
</section>

<section class="section">
  <div class="section-head"><div><h3>پنل‌های پاسارگارد</h3><div class="hint">اتصالات ثبت‌شده برای ساخت اپراتور و خواندن مصرف.</div></div></div>
  <div class="table-wrap"><table><thead><tr><th>ID</th><th>Name</th><th>Base URL</th><th>Dashboard</th><th>Role</th><th>Status</th></tr></thead><tbody>{panel_rows}</tbody></table></div>
</section>
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
