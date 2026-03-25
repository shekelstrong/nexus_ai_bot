from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User, SubscriptionTier, Generation
from keyboards.inline import profile_menu, back_to_menu_kb
from config import TEXTS, SUBSCRIPTION_TIERS

router = Router(name="profile_router")

async def _send_profile_msg(bot, chat_id, user_id, session: AsyncSession, old_message: Message = None):
    res = await session.execute(select(User).where(User.telegram_id == user_id))
    user = res.scalar_one_or_none()

    if not user:
        if old_message:
            await bot.send_message(chat_id, "Пользователь не найден")
        return

    # Расчет времени до сброса для FREE тарифа
    now = datetime.utcnow()
    next_midnight = datetime(now.year, now.month, now.day) + timedelta(days=1)
    time_left = next_midnight - now
    hours, remainder = divmod(time_left.total_seconds(), 3600)
    minutes, _ = divmod(remainder, 60)
    
    # Формирование текста
    text = f"👤 <b>Профиль</b>\nID: <code>{user.telegram_id}</code>\n\n"
    
    if user.subscription_tier == SubscriptionTier.FREE.value:
        free_limit = SUBSCRIPTION_TIERS["FREE"]["tokens"]
        text += f"🪙 <b>Токены:</b> {user.tokens_balance}/{free_limit} (ежедневный лимит)\n"
        text += f"⏳ <b>Сброс через:</b> {int(hours)}ч {int(minutes)}м\n"
    else:
        text += f"🪙 <b>Токены:</b> {user.tokens_balance}\n"
        
    text += f"🎬 <b>Видео-генерации:</b> {user.video_generations_balance}\n"
    text += f"💎 <b>Тариф:</b> {user.subscription_tier}\n"
    
    if user.subscription_expires_at:
        text += f"⏳ <b>Подписка до:</b> {user.subscription_expires_at.strftime('%d.%m.%Y %H:%M')}\n"
    else:
        text += f"⏳ <b>Подписка до:</b> —\n"
        
    text += (
        f"\n🎁 <b>Реф. баланс:</b> {user.referral_balance:.2f}₽\n"
        f"🔗 <b>Ваш рефкод:</b> <code>{user.referral_code}</code>\n\n"
        f"Нажмите «История», чтобы посмотреть генерации."
    )

    # Аккуратная отправка или редактирование сообщения (чтобы не плодить новые)
    if old_message:
        try:
            if old_message.photo or old_message.video or old_message.document:
                await old_message.delete()
                await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=profile_menu())
            else:
                await old_message.edit_text(text=text, parse_mode="HTML", reply_markup=profile_menu())
        except Exception:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=profile_menu())
    else:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=profile_menu())

@router.callback_query(F.data.in_(["profile", "my_profile"]))
async def show_profile_cb(cb: CallbackQuery, session: AsyncSession):
    """Обработчик для inline-кнопки Профиль"""
    await _send_profile_msg(cb.bot, cb.message.chat.id, cb.from_user.id, session, cb.message)
    await cb.answer()

@router.message(Command("account"))
async def cmd_account(message: Message, session: AsyncSession):
    """Обработчик команды /account из меню"""
    await _send_profile_msg(message.bot, message.chat.id, message.from_user.id, session)

# --- ОБРАБОТЧИК ДЛЯ КНОПКИ "ИСТОРИЯ" С ПОДКЛЮЧЕНИЕМ К БД ---
@router.callback_query(F.data == "history")
async def show_history_cb(cb: CallbackQuery, session: AsyncSession):
    """Обработчик для inline-кнопки История (показывает 5 последних генераций)"""
    
    # Получаем внутренний ID пользователя из БД
    res = await session.execute(select(User.id).where(User.telegram_id == cb.from_user.id))
    user_id = res.scalar_one_or_none()

    if not user_id:
        await cb.answer("Пользователь не найден в базе", show_alert=True)
        return

    # Запрашиваем последние 5 генераций из таблицы Generation
    gens_res = await session.execute(
        select(Generation)
        .where(Generation.user_id == user_id)
        .order_by(Generation.created_at.desc())
        .limit(5)
    )
    generations = gens_res.scalars().all()

    if not generations:
        text = "📊 <b>История генераций</b>\n\nУ вас пока нет истории генераций. Попробуйте создать что-нибудь!"
    else:
        text = "📊 <b>Последние 5 запросов:</b>\n\n"
        for i, gen in enumerate(generations, 1):
            # Обрезаем длинный промпт, чтобы сообщение не было гигантским
            short_prompt = gen.prompt[:50] + "..." if len(gen.prompt) > 50 else gen.prompt
            
            # Эмодзи статуса (берем из GenerationStatus)
            status_emoji = "✅" if gen.status == "COMPLETED" else "❌" if gen.status == "FAILED" else "⏳"
            
            # Форматируем дату (например: 26.03 14:30)
            date_str = gen.created_at.strftime('%d.%m %H:%M')
            
            text += f"{i}. {status_emoji} <b>{gen.model_name}</b> ({date_str})\n"
            text += f"📝 <i>{short_prompt}</i>\n"
            text += f"💎 Стоимость: {gen.cost} токенов\n\n"

    try:
        if cb.message.photo or cb.message.video or cb.message.document:
            await cb.message.delete()
            await cb.message.answer(text, parse_mode="HTML", reply_markup=back_to_menu_kb())
        else:
            await cb.message.edit_text(text, parse_mode="HTML", reply_markup=back_to_menu_kb())
    except Exception:
        await cb.message.answer(text, parse_mode="HTML", reply_markup=back_to_menu_kb())
    
    await cb.answer()