from sqlalchemy import select, update, insert, desc
from sqlalchemy.ext.asyncio import AsyncSession
# Импортируем Transaction вместо Payment
from database.models import Base, User, Transaction, Generation, TransactionStatus
from database.session import engine, async_session_maker
import logging

class Database:
    def __init__(self):
        self.engine = engine
        self.session_maker = async_session_maker

    async def connect(self):
        """Создает таблицы, если их нет"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logging.info("Database connected & tables created.")

    async def add_user(self, telegram_id: int, username: str = None, first_name: str = None, last_name: str = None, referrer_id: int = None):
        async with self.session_maker() as session:
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()

            if not user:
                user = User(
                    telegram_id=telegram_id, 
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    referrer_id=referrer_id,
                    referral_code=str(telegram_id) # Простейший рефкод
                )
                session.add(user)
                await session.commit()
                return True
            return False

    async def get_user(self, telegram_id: int):
        async with self.session_maker() as session:
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            return result.scalar_one_or_none()

    async def update_balance(self, telegram_id: int, amount: int):
        """Начисляет (или списывает, если amount < 0) токены"""
        async with self.session_maker() as session:
            await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(tokens_balance=User.tokens_balance + amount)
            )
            await session.commit()

    async def update_balance_rub(self, telegram_id: int, amount: int):
        """Начисляет рубли (реферальные)"""
        async with self.session_maker() as session:
            await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(referral_balance=User.referral_balance + amount)
            )
            await session.commit()

    async def add_payment(self, telegram_id: int, amount: float, tariff_name: str):
        """Создает запись о платеже (Транзакцию)"""
        async with self.session_maker() as session:
            # Сначала находим internal id юзера по telegram_id
            res = await session.execute(select(User.id).where(User.telegram_id == telegram_id))
            user_id = res.scalar_one_or_none()
            
            if user_id:
                # Используем модель Transaction
                txn = Transaction(
                    user_id=user_id,
                    amount=amount,
                    currency="RUB",
                    type="DEPOSIT", # Тип транзакции
                    status=TransactionStatus.SUCCESS,
                    payment_system="PLATEGA",
                    extra_data={"description": tariff_name}
                )
                session.add(txn)
                await session.commit()

    async def get_referrers_chain(self, telegram_id: int, max_depth: int = 3) -> list[int]:
        """Возвращает список ID рефереров вверх по цепочке (для начисления бонусов)"""
        chain = []
        current_id = telegram_id
        
        async with self.session_maker() as session:
            for _ in range(max_depth):
                # Ищем текущего юзера
                res = await session.execute(select(User.referrer_id).where(User.telegram_id == current_id))
                referrer_id = res.scalar_one_or_none()
                
                if referrer_id:
                    # Нам нужен telegram_id реферера для отправки сообщения, 
                    # но в таблице referrer_id - это FK на id (int).
                    # Нужно получить telegram_id этого юзера.
                    ref_user_res = await session.execute(select(User.telegram_id).where(User.id == referrer_id))
                    ref_tg_id = ref_user_res.scalar_one_or_none()
                    
                    if ref_tg_id:
                        chain.append(ref_tg_id)
                        current_id = ref_tg_id # Ищем дальше по telegram_id (или нужно переделать на внутренние ID)
                    else:
                        break
                else:
                    break
        return chain

# ЭКСПОРТИРУЕМ ЭКЗЕМПЛЯР КЛАССА
db = Database()
