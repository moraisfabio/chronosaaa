from app import app
from apscheduler.schedulers.background import BackgroundScheduler
from app.handlers.appointment_handlers import handle_send_reminders_for_tomorrow

scheduler = BackgroundScheduler()
scheduler.add_job(handle_send_reminders_for_tomorrow, 'cron', hour=7)  # Executa todos os dias às 7h
scheduler.start()

if __name__ == "__main__":
    app.run(port=5000)