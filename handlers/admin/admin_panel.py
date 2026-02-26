import asyncio
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import User, Generation, Transaction, SubscriptionTier
from utils.logger import logger

router = Router(name="admin_router")

# --- FSM States ---
class AdminStates(StatesGroup):
    find_user = State()
    add_tokens_user = State()
    add_tokens_amount = State()
    ban_user = State()
    unban_user = State()
    broadcast_text = State()
    promo_code = State()
    promo_percent = State()
    promo_limit = State()


# --- Keyboards ---
def admin_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="🔍 Найти юзера", callback_data="admin_find_user"),
        ],
        [
            InlineKeyboardButton(text="💰 Начислить токены", callback_data="admin_add_tokens"),
        ],
        [
            InlineKeyboardButton(text="🚫 Бан", callback_data="admin_ban"),
            InlineKeyboardButton(text="✅ Разбан", callback_data="admin_unban"),
        ],
        [
            InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="🎫 Создать промокод", callback_data="admin_promo"),
        ],
        [
            InlineKeyboardButton(text="❌ Закрыть", callback_data="admin_close"),
        ]
    ])


def cancel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_cancel")]
    ])


# --- Helpers ---
def is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.admin_ids_list


# --- Handlers ---

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        return

    await state.clear()
    await message.answer(
        "🔧 <b>Панель администратора</b>\n"
        "Выберите действие:",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_close")
async def close_panel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()


@router.callback_query(F.data == "admin_cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🔧 <b>Панель администратора</b>\nВыберите действие:",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML"
    )


# --- Statistics ---
@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery, session: AsyncSession):
    # Total users
    total_users_res = await session.execute(select(func.count(User.id)))
    total_users = total_users_res.scalar_one()

    # New today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    new_today_res = await session.execute(
        select(func.count(User.id)).where(User.created_at >= today_start)
    )
    new_today = new_today_res.scalar_one()

    # Active this week
    week_ago = datetime.utcnow() - timedelta(days=7)
    active_week_res = await session.execute(
        select(func.count(User.id)).where(User.last_activity >= week_ago)
    )
    active_week = active_week_res.scalar_one()

    # Total revenue
    revenue_res = await session.execute(
        select(func.sum(Transaction.amount)).where(Transaction.status == "SUCCESS")
    )
    total_revenue = revenue_res.scalar_one() or 0

    # Most popular model
    popular_model_res = await session.execute(
        select(Generation.model_name, func.count(Generation.id).label("cnt"))
        .group_by(Generation.model_name)
        .order_by(desc("cnt"))
        .limit(1)
    )
    popular = popular_model_res.first()
    popular_model = f"{popular[0]} ({popular[1]})" if popular else "—"

    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Пользователи: <b>{total_users}</b>\n"
        f"🆕 За сегодня: <b>{new_today}</b>\n"
        f"🔥 Активные (7д): <b>{active_week}</b>\n\n"
        f"💰 Выручка: <b>{total_revenue} ₽</b>\n"
        f"🎨 Топ модель: <code>{popular_model}</code>"
    )
    
    await callback.message.edit_text(text, reply_markup=admin_menu_kb(), parse_mode="HTML")


# --- Find User ---
@router.callback_query(F.data == "admin_find_user")
async def start_find_user(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.find_user)
    await callback.message.edit_text(
        "Введите Telegram ID или Username пользователя:",
        reply_markup=cancel_kb()
    )


@router.message(AdminStates.find_user)
async def process_find_user(message: Message, session: AsyncSession, state: FSMContext):
    query_val = message.text.strip().replace("@", "")
    
    stmt = select(User)
    if query_val.isdigit():
        stmt = stmt.where(User.telegram_id == int(query_val))
    else:
        stmt = stmt.where(User.username == query_val)

    res = await session.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        await message.answer("❌ Пользователь не найден.", reply_markup=admin_menu_kb())
        await state.clear()
        return

    # User info logic (simplified)
    gen_count = await session.scalar(select(func.count(Generation.id)).where(Generation.user_id == user.id))
    
    text = (
        f"👤 <b>Инфо о пользователе</b>\n"
        f"ID: <code>{user.telegram_id}</code>\n"
        f"Username: @{user.username}\n"
        f"Баланс: <b>{user.tokens_balance}</b>\n"
        f"Тариф: <b>{user.subscription_tier}</b>\n"
        f"Генераций: <b>{gen_count}</b>\n"
        f"Бан: {'🔴 ДА' if user.is_banned else '🟢 НЕТ'}"
    )
    await message.answer(text, reply_markup=admin_menu_kb(), parse_mode="HTML")
    await state.clear()


# --- Add Tokens ---
@router.callback_query(F.data == "admin_add_tokens")
async def start_add_tokens(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.add_tokens_user)
    await callback.message.edit_text("Введите ID пользователя для начисления:", reply_markup=cancel_kb())


@router.message(AdminStates.add_tokens_user)
async def process_add_tokens_user(message: Message, session: AsyncSession, state: FSMContext):
    try:
        user_id = int(message.text)
        # Check existence
        user = await session.scalar(select(User).where(User.telegram_id == user_id))
        if not user:
            await message.answer("❌ Пользователь не найден. Попробуйте снова или нажмите отмену.", reply_markup=cancel_kb())
            return
            
        await state.update_data(target_id=user_id)
        await state.set_state(AdminStates.add_tokens_amount)
        await message.answer(f"Сколько токенов начислить пользователю {user_id}?", reply_markup=cancel_kb())
    except ValueError:
        await message.answer("❌ Введите числовой ID.", reply_markup=cancel_kb())


@router.message(AdminStates.add_tokens_amount)
async def process_add_tokens_amount(message: Message, session: AsyncSession, state: FSMContext):
    try:
        amount = int(message.text)
        data = await state.get_data()
        target_id = data['target_id']

        user = await session.scalar(select(User).where(User.telegram_id == target_id))
        if user:
            user.tokens_balance += amount
            await session.commit()
            await message.answer(f"✅ Успешно! Баланс {target_id} пополнен на {amount}.\nТекущий: {user.tokens_balance}", reply_markup=admin_menu_kb())
            
            # Notify user
            try:
                await message.bot.send_message(target_id, f"🎁 Администратор начислил вам {amount} токенов!")
            except:
                pass
        else:
            await message.answer("❌ Ошибка: пользователь пропал из базы.", reply_markup=admin_menu_kb())
            
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите целое число.", reply_markup=cancel_kb())


# --- Ban/Unban ---
@router.callback_query(F.data == "admin_ban")
async def start_ban(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.ban_user)
    await callback.message.edit_text("Введите ID пользователя для БАНА:", reply_markup=cancel_kb())

@router.message(AdminStates.ban_user)
async def process_ban(message: Message, session: AsyncSession, state: FSMContext):
    try:
        uid = int(message.text)
        user = await session.scalar(select(User).where(User.telegram_id == uid))
        if user:
            user.is_banned = True
            await session.commit()
            await message.answer(f"🚫 Пользователь {uid} забанен.", reply_markup=admin_menu_kb())
        else:
            await message.answer("❌ Не найден.", reply_markup=admin_menu_kb())
        await state.clear()
    except ValueError:
        await message.answer("ID должен быть числом.", reply_markup=cancel_kb())


@router.callback_query(F.data == "admin_unban")
async def start_unban(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.unban_user)
    await callback.message.edit_text("Введите ID пользователя для РАЗБАНА:", reply_markup=cancel_kb())

@router.message(AdminStates.unban_user)
async def process_unban(message: Message, session: AsyncSession, state: FSMContext):
    try:
        uid = int(message.text)
        user = await session.scalar(select(User).where(User.telegram_id == uid))
        if user:
            user.is_banned = False
            await session.commit()
            await message.answer(f"✅ Пользователь {uid} разбанен.", reply_markup=admin_menu_kb())
        else:
            await message.answer("❌ Не найден.", reply_markup=admin_menu_kb())
        await state.clear()
    except ValueError:
        await message.answer("ID должен быть числом.", reply_markup=cancel_kb())


# --- Broadcast ---
@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.broadcast_text)
    await callback.message.edit_text(
        "✍️ Введите текст рассылки (можно с HTML тегами) или перешлите сообщение:",
        reply_markup=cancel_kb()
    )

@router.message(AdminStates.broadcast_text)
async def process_broadcast(message: Message, session: AsyncSession, state: FSMContext):
    text = message.html_text if message.text else message.caption
    
    # Get users
    users_res = await session.execute(select(User.telegram_id).where(User.is_banned == False))
    users = users_res.scalars().all()
    
    await message.answer(f"🚀 Начинаю рассылку на {len(users)} чел...", reply_markup=admin_menu_kb())
    await state.clear()

    good, bad = 0, 0
    for uid in users:
        try:
            if message.text:
                await message.bot.send_message(uid, text, parse_mode="HTML")
            else:
                await message.copy_to(uid)
            good += 1
            await asyncio.sleep(0.05)
        except:
            bad += 1
            
    await message.answer(f"🏁 Рассылка завершена.\n✅ {good}\n❌ {bad}")