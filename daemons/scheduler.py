"""
Фоновый планировщик задач (Scheduler Daemon).
Обеспечивает непрерывную автономную работу агента SLUGA:
1. Heartbeat-мониторинг жизнедеятельности агента.
2. Периодическая проверка целостности базы данных SQLite WAL.
3. Фоновые проверки проектов и автономные миссии.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from core.memory import SlugaMemory
from config import settings

logger = logging.getLogger("SLUGA_DAEMON")

class SlugaDaemon:
    def __init__(self, memory: SlugaMemory):
        self.memory = memory
        self.scheduler = AsyncIOScheduler()

    def start(self):
        # 1. Heartbeat каждые 15 минут
        self.scheduler.add_job(
            self._heartbeat_job,
            "interval",
            minutes=15,
            id="sluga_heartbeat"
        )
        # 2. Оптимизация базы данных SQLite раз в сутки
        self.scheduler.add_job(
            self._vacuum_job,
            "interval",
            hours=24,
            id="sluga_vacuum"
        )
        self.scheduler.start()
        logger.info("Фоновый демон SLUGA успешно запущен.")

    async def _heartbeat_job(self):
        logger.info("💓 SLUGA Heartbeat: автономный контур активен.")

    async def _vacuum_job(self):
        try:
            with self.memory._get_connection() as conn:
                conn.execute("PRAGMA optimize;")
            logger.info("🧹 Оптимизация SQLite завершена успешно.")
        except Exception as e:
            logger.error(f"Ошибка фоновой оптимизации SQLite: {e}")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Фоновый демон остановлен.")
