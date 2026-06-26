from pydantic import BaseModel, Field


class ResellerProvisionRequest(BaseModel):
    telegram_id: int
    telegram_username: str | None = None
    pasar_username: str | None = Field(default=None, min_length=3, max_length=32)
    initial_balance_toman: int = Field(default=0, ge=0)
    price_per_gb_toman: int | None = Field(default=None, ge=0)
    debt_limit_toman: int | None = Field(default=None, ge=0)
    pasar_role_id: int | None = Field(default=None, ge=1)
    note: str | None = None


class ResellerResponse(BaseModel):
    id: int
    telegram_id: int
    telegram_username: str | None
    pasar_admin_id: int | None
    pasar_username: str
    pasar_role_id: int
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
