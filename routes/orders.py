# ruff: noqa: B008

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from core.security import exigir_perfil, get_current_user
from models.usuario import PerfilEnum, Usuario

router = APIRouter(prefix="/orders", tags=["orders"])


class OrderItem(BaseModel):
    id: int
    code: str
    customer: str
    total: float
    status: Literal["pending", "paid", "shipped", "cancelled"]


class OrderCreateRequest(BaseModel):
    code: str
    customer: str
    total: float
    status: Literal["pending", "paid", "shipped", "cancelled"] = "pending"


ORDERS_DB = [
    OrderItem(
        id=1, code="ORD-1001", customer="Maria Souza", total=320.0, status="paid"
    ),
    OrderItem(
        id=2, code="ORD-1002", customer="João Lima", total=580.5, status="pending"
    ),
    OrderItem(
        id=3, code="ORD-1003", customer="Empresa X", total=980.0, status="shipped"
    ),
]


@router.get("", response_model=list[OrderItem])
def list_orders(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    status: str | None = None,
    usuario_atual: Usuario = Depends(get_current_user),
):
    items = ORDERS_DB
    if status:
        items = [order for order in items if order.status == status]
    return items[(page - 1) * limit : page * limit]


@router.get("/{order_id}", response_model=OrderItem)
def get_order(order_id: int, usuario_atual: Usuario = Depends(get_current_user)):
    for order in ORDERS_DB:
        if order.id == order_id:
            return order
    raise HTTPException(status_code=404, detail="Order not found")


@router.post("", response_model=OrderItem, status_code=201)
def create_order(
    payload: OrderCreateRequest,
    usuario_atual: Usuario = Depends(
        exigir_perfil(PerfilEnum.admin, PerfilEnum.gestor)
    ),
):
    new_order = OrderItem(
        id=max((order.id for order in ORDERS_DB), default=0) + 1,
        code=payload.code,
        customer=payload.customer,
        total=payload.total,
        status=payload.status,
    )
    ORDERS_DB.append(new_order)
    return new_order
