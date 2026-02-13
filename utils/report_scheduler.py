"""
Report Scheduler - AI报告定时生成任务
每天23:00为每个设备生成AI思维报告
"""
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import date, datetime, timedelta
from services.report_service import ReportService


class ReportScheduler:
    """报告定时调度器"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.report_service = ReportService()

    def generate_daily_reports(self):
        """
        为所有活跃设备生成当天报告

        逻辑：生成昨天的报告（23:00执行时，今天对话还未结束）
        """
        yesterday = (date.today() - timedelta(days=1)).isoformat()

        print(f"\n{'='*60}")
        print(f"[ReportScheduler] Starting daily report generation: {yesterday}")
        print(f"{'='*60}")

        try:
            # 获取所有活跃设备（最近7天有上线记录）
            devices = self.report_service.get_all_active_devices()

            if not devices:
                print("[ReportScheduler] No active devices found")
                return

            print(f"[ReportScheduler] Found {len(devices)} active device(s)")

            success_count = 0
            failed_count = 0
            total_chats = 0

            for device in devices:
                device_id = device['id']
                device_name = device['device_name']
                mac_address = device['mac_address']

                print(f"\n[ReportScheduler] Processing device: {device_name} ({mac_address})")

                # 生成报告
                result = self.report_service.generate_daily_report(mac_address, yesterday)

                if result['success']:
                    success_count += 1
                    chat_count = result.get('chat_count', 0)
                    total_chats += chat_count
                    status = "Already exists" if result.get('already_generated') else "Generated"
                    print(f"  ✅ {status} ({chat_count} chats)")
                else:
                    failed_count += 1
                    error = result.get('error', 'Unknown error')
                    print(f"  ❌ Failed: {error}")

            print(f"\n{'='*60}")
            print(f"[ReportScheduler] Completed:")
            print(f"  - Success: {success_count}/{len(devices)} devices")
            print(f"  - Failed: {failed_count}/{len(devices)} devices")
            print(f"  - Total chats: {total_chats}")
            print(f"{'='*60}\n")

        except Exception as e:
            print(f"[ReportScheduler] Error: {e}")
            import traceback
            traceback.print_exc()

    def start(self):
        """启动定时任务（每天23:00执行）"""
        # 每天23:00执行
        self.scheduler.add_job(
            self.generate_daily_reports,
            'cron',
            hour=23,
            minute=0,
            id='daily_report_generation',
            name='Generate daily AI reports for all devices',
            replace_existing=True
        )

        self.scheduler.start()
        print("[ReportScheduler] Started (scheduled for 23:00 daily)")

    def stop(self):
        """停止调度器"""
        self.scheduler.shutdown()
        print("[ReportScheduler] Stopped")

    def trigger_now(self):
        """手动触发（用于测试）"""
        print("[ReportScheduler] Manual trigger")
        self.generate_daily_reports()


# 全局调度器实例
_scheduler = None


def get_report_scheduler() -> ReportScheduler:
    """获取调度器单例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = ReportScheduler()
    return _scheduler
