from app.services.reminder import send_due_reminders


async def check_due_cards():
    await send_due_reminders()
