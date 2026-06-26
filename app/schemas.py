from pydantic import BaseModel, Field


class PasarGuardPanelCreate(BaseModel):
    name: str = Field(min_length=2, max_length=128)
    base_url: str = Field(min_length=8, max_length=255)
    dashboard_url: str | None = None
    admin_username: str = Field(min_length=1, max_length=128)
    admin_secret: str = Field(min_length=1)
    default_role_id: int = Field(default=0, ge=0)
    is_active: bool = True
    note: str | None = None


class PasarGuardPanelResponse(BaseModel):
    id: int
    name: str
    base_url: str
    dashboard_url: str | None
    admin_username: str
    default_role_id: int
    is_active: bool
    note: str | None

    class Config:
        from_attributes = True


class BotConfigUpdate(BaseModel):
    bot_token: str | None = None
    bot_username: str | None = None
    webhook_url: str | None = None
    webhook_secret: str | None = None
    webhook_enabled: bool | None = None


class BotConfigResponse(BaseModel):
    id: int
    bot_username: str | None
    webhook_url: str | None
    webhook_secret: str | None
    webhook_enabled: bool
    has_bot_token: bool = False

    class Config:
        from_attributes = True


class ResellerProvisionRequest(BaseModel):
    telegram_id: int
    telegram_username: str | None = None
    pasar_username: str | None = Field(default=None, min_length=3, max_length=32)
    initial_balance_toman: int = Field(default=0, ge=0)
    price_per_gb_toman: int | None = Field(default=None, ge=0)
    debt_limit_toman: int | None = Field(default=None, ge=0)
    pasar_role_id: int | None = Field(default=None, ge=1)
    panel_id: int | None = Field(default=None, ge=1)
    note: str | None = None


class ResellerResponse(BaseModel):
    id: int
    telegram_id: int
    telegram_username: str | None
    pasar_admin_id: int | None
    pasar_username: str
    pasar_role_id: int
    panel_id: int | None = None
    status: str
    balance_toman: int
    price_per_gb_toman: int
    debt_limit_toman: int
    last_total_usage_bytes: int
    panel_url: str | None = None

    class Config:
        from_attributes = True


class ProvisionResponse(BaseModel):
    reseller: ResellerResponse
    generated_panel_key: str
    panel_url: str | None


class WalletAdjustRequest(BaseModel):
    amount_toman: int
    description: str | None = None


class UsageRunResponse(BaseModel):
    checked: int
    charged: int
    restricted: int
    errors: list[str] = []


class MessageResponse(BaseModel):
    detail: str
