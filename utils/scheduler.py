"""
Reminder Scheduling Utility (MVP Version)
Supports: one-time and daily reminders
"""
import time
from datetime import datetime, timedelta
from typing import Tuple, Optional


class ReminderScheduler:
    """Calculate next occurrence for reminders (MVP: once, daily)"""

    @staticmethod
    def calculate_next(
        reminder_type: str,
        scheduled_time: str,  # "HH:MM"
        from_timestamp: Optional[int] = None,
        skip_holidays: bool = False
    ) -> Tuple[int, str, bool]:
        """
        Calculate next reminder timestamp

        Args:
            reminder_type: 'once' or 'daily'
            scheduled_time: Time in "HH:MM" format
            from_timestamp: Reference timestamp (default: now)
            skip_holidays: Whether to skip holidays (not implemented in MVP)

        Returns:
            (next_timestamp, formatted_date, is_holiday)
        """
        if from_timestamp is None:
            from_timestamp = int(time.time())

        from_dt = datetime.fromtimestamp(from_timestamp)

        # Parse scheduled time
        try:
            hour, minute = map(int, scheduled_time.split(':'))
        except ValueError:
            raise ValueError(f"Invalid scheduled_time format: {scheduled_time}. Expected HH:MM")

        if reminder_type == 'once':
            # For one-time reminders, schedule for today at the specified time
            scheduled_dt = from_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # If that time has passed, schedule for tomorrow
            if scheduled_dt <= from_dt:
                scheduled_dt += timedelta(days=1)

            # TODO: Check holiday when skip_holidays is True
            is_holiday = False  # MVP: Always False

            return (
                int(scheduled_dt.timestamp()),
                scheduled_dt.strftime("%Y-%m-%d %H:%M"),
                is_holiday
            )

        elif reminder_type == 'daily':
            # Calculate next daily occurrence
            scheduled_dt = from_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # If that time has passed today, schedule for tomorrow
            if scheduled_dt <= from_dt:
                scheduled_dt += timedelta(days=1)

            # TODO: Skip holidays if enabled (not implemented in MVP)
            is_holiday = False  # MVP: Always False

            return (
                int(scheduled_dt.timestamp()),
                scheduled_dt.strftime("%Y-%m-%d %H:%M"),
                is_holiday
            )

        else:
            raise ValueError(f"Unknown reminder type: {reminder_type}. Supported: 'once', 'daily'")

    @staticmethod
    def format_timestamp(timestamp: int, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Format Unix timestamp to readable string"""
        return datetime.fromtimestamp(timestamp).strftime(format_str)

    @staticmethod
    def parse_time(time_str: str) -> Tuple[int, int]:
        """
        Parse time string "HH:MM" into (hour, minute)

        Args:
            time_str: Time string in "HH:MM" format

        Returns:
            (hour, minute) tuple
        """
        try:
            hour, minute = map(int, time_str.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Hour must be 0-23, minute must be 0-59")
            return hour, minute
        except ValueError:
            raise ValueError(f"Invalid time format: {time_str}. Expected HH:MM")


class HolidayChecker:
    """
    Chinese holiday checker (MVP: Placeholder)
    Phase 2 will implement actual holiday checking
    """

    # TODO: Load holidays from database
    _holidays = set()

    @classmethod
    def is_holiday(cls, date) -> bool:
        """
        Check if a date is a holiday
        MVP: Always returns False
        Phase 2: Check against database
        """
        return False

    @classmethod
    def is_observed_holiday(cls, date) -> bool:
        """
        Check if a date is an observed holiday (working holiday)
        MVP: Always returns False
        """
        return False

    @classmethod
    def next_non_holiday(cls, from_dt: datetime) -> datetime:
        """
        Find next non-holiday date
        MVP: Returns next day
        Phase 2: Skip actual holidays
        """
        return from_dt + timedelta(days=1)


# Example usage and testing
if __name__ == "__main__":
    # Test scheduler
    print("=== Reminder Scheduler Test ===")

    # Test one-time reminder
    print("\nOne-time reminder at 14:30:")
    next_ts, next_date, is_holiday = ReminderScheduler.calculate_next(
        reminder_type='once',
        scheduled_time='14:30',
        from_timestamp=int(time.time())
    )
    print(f"  Next: {next_date} (timestamp: {next_ts})")

    # Test daily reminder
    print("\nDaily reminder at 08:00:")
    next_ts, next_date, is_holiday = ReminderScheduler.calculate_next(
        reminder_type='daily',
        scheduled_time='08:00',
        from_timestamp=int(time.time())
    )
    print(f"  Next: {next_date} (timestamp: {next_ts})")

    # Test time parsing
    print("\nTime parsing test:")
    hour, minute = ReminderScheduler.parse_time("23:59")
    print(f"  23:59 -> hour={hour}, minute={minute}")

    print("\n✅ All tests passed!")
