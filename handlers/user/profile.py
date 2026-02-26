from datetime import datetime, timedelta


from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession


from database.models import User, Generation, GenerationStatus
from keyboards.inline import main_menu
from utils.logger import logger
from model_config import MODEL_CATALOG


router = Router(name="profile_router")


HISTORY_PAGE_SIZE = 5


def _model_category(model_id: str) -> str:
    for category, families in MODEL_CATALOG.items():
        for fam_data in families.values():
            for m in fam_data.get("models", []):
                if m.get("id") == model_id:
                    return category
    return "unknown"


def _fmt_dt(dt):
    if not dt:
        return "—"
    return dt.strftime("%Y-%m-%d %H:%M")



@router.message(Command("profile"))
async def cmd_profile(message: Message, session: AsyncSession):
    res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = res.scalar_one_or_none()
    if not user:
        await message.answer("Сначала нажмите /start", reply_markup=main_menu())
        return


    text = (
        f"👤 <b>Профиль</b>\n"
        f"ID: <code>{user.telegram_id}</code>\n\n"
        f"🪙 Токены: <b>{user.tokens_balance}</b>\n"
        f"💎 Тариф: <b>{user.subscription_tier}</b>\n"
        f"⏳ Подписка до: <b>{_fmt_dt(user.subscription_expires_at)}</b>\n\n"
        f"🎁 Реф. баланс: <b>{user.referral_balance}</b>\n"
        f"🔗 Ваш рефкод: <code>{user.referral_code}</code>\n"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=main_menu())



@router.callback_query(F.data == "profile")
async def profile_cb(cb: CallbackQuery, session: AsyncSession):
    res = await session.execute(select(User).where(User.telegram_id == cb.from_user.id))
    user = res.scalar_one_or_none()
    if not user:
        await cb.message.edit_text("Сначала нажмите /start", reply_markup=main_menu())
        await cb.answer()
        return


    text = (
        f"👤 <b>Профиль</b>\n"
        f"ID: <code>{user.telegram_id}</code>\n\n"
        f"🪙 Токены: <b>{user.tokens_balance}</b>\n"
        f"💎 Тариф: <b>{user.subscription_tier}</b>\n"
        f"⏳ Подписка до: <b>{_fmt_dt(user.subscription_expires_at)}</b>\n\n"
        f"🎁 Реф. баланс: <b>{user.referral_balance}</b>\n"
        f"🔗 Ваш рефкод: <code>{user.referral_code}</code>\n\n"
        f"Нажмите «История», чтобы посмотреть генерации."
    )
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu())
    await cb.answer()



@router.callback_query(F.data == "history")
async def history_first(cb: CallbackQuery, session: AsyncSession):
    await _show_history(cb, session, page=0)



@router.callback_query(F.data.startswith("history_page_"))
async def history_page(cb: CallbackQuery, session: AsyncSession):
    page = int(cb.data.split("_")[-1])
    await _show_history(cb, session, page=page)



async def _show_history(cb: CallbackQuery, session: AsyncSession, page: int):
    res_user = await session.execute(select(User).where(User.telegram_id == cb.from_user.id))
    user = res_user.scalar_one_or_none()
    if not user:
        await cb.message.edit_text("Сначала нажмите /start", reply_markup=main_menu())
        await cb.answer()
        return


    offset = page * HISTORY_PAGE_SIZE


    total_res = await session.execute(
        select(func.count(Generation.id)).where(Generation.user_id == user.id)
    )
    total = total_res.scalar_one()


    gens_res = await session.execute(
        select(Generation)
        .where(Generation.user_id == user.id)
        .order_by(desc(Generation.created_at))
        .limit(HISTORY_PAGE_SIZE)
        .offset(offset)
    )
    gens = gens_res.scalars().all()


    if not gens:
        await cb.message.edit_text("📊 История пуста.", reply_markup=main_menu())
        await cb.answer()
        return


    lines = [f"📊 <b>История</b> (стр. {page+1})\n"]
    for g in gens:
        prompt_short = (g.prompt[:80] + "…") if len(g.prompt) > 80 else g.prompt
        category = _model_category(g.model_name)
        lines.append(
            f"• <b>{category}</b> | <code>{g.model_name}</code>\n"
            f"  {prompt_short}\n"
            f"  Статус: <b>{g.status}</b> | Стоимость: <b>{g.cost}</b>\n"
            f"  ID: <code>{g.id}</code> | {_fmt_dt(g.created_at)}\n"
        )


    nav = []
    if page > 0:
        nav.append(f"history_page_{page-1}")
    if offset + HISTORY_PAGE_SIZE < total:
        nav.append(f"history_page_{page+1}")


    text = "\n".join(lines)[:4096]
    if nav:
        text += "\n\nДля навигации:\n" + "\n".join([f"• /history {x.split('_')[-1]}" for x in nav])


    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu())
    await cb.answer()



@router.message(Command("history"))
async def history_cmd(message: Message, session: AsyncSession):
    # /history or /history 2
    parts = (message.text or "").split()
    page = 0
    if len(parts) > 1 and parts[1].isdigit():
        page = max(0, int(parts[1]) - 1)


    # имитируем callback
    class Dummy:
        from_user = message.from_user
        message = message
        async def answer(self, *args, **kwargs): ...
    dummy = Dummy()
    await _show_history(dummy, session, page=page)
