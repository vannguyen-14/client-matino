from sqlalchemy import event, inspect, Table
from sqlalchemy.sql import Select
from datetime import datetime, timedelta, timezone

# Myanmar timezone offset
MYANMAR_TZ = timezone(timedelta(hours=6, minutes=30))

# Giờ launch theo server (đã ở Myanmar)
# ⚠️ Không thêm tzinfo để tránh mismatch
LAUNCH_START = datetime(2025, 10, 22, 17, 0, 0)  # naive datetime

def apply_launch_filter(SessionClass, target_models: dict):
    @event.listens_for(SessionClass.sync_session_class, "do_orm_execute")
    def _add_launch_filter(execute_state):
        if not execute_state.is_select:
            return

        statement = execute_state.statement
        if not isinstance(statement, Select):
            return

        froms = statement.get_final_froms()

        for model, field_name in target_models.items():
            insp = inspect(model)
            local_table = insp.local_table
            table_names = [t.name for t in froms if hasattr(t, "name")]

            if local_table.name in table_names:
                field = getattr(model, field_name)
                execute_state.statement = statement.where(field >= LAUNCH_START)
