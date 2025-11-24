from datetime import date, timedelta
import calendar
from typing import List, Optional

from corrida.models import CorridaTemplate, Corrida


def generate_occurrences(template: CorridaTemplate, until_date: Optional[date] = None) -> List[Corrida]:
    """
    Gera ocorrências (Corrida) a partir do template.
    Retorna a lista de Corrida criadas.
    """
    if not template.ativo:
        return []

    start = template.start_date or date.today()
    end = until_date or template.end_date or start

    generated = []

    if template.frequency == template.FREQ_DAILY:
        cur = start
        while cur <= end:
            c = Corrida.create_from_template(template, cur)
            generated.append(c)
            cur += timedelta(days=1)

    elif template.frequency == template.FREQ_WEEKLY:
        dow = template.days_of_week or [start.weekday()]  # 0=segunda
        cur = start
        while cur <= end:
            if cur.weekday() in dow:
                c = Corrida.create_from_template(template, cur)
                generated.append(c)
            cur += timedelta(days=1)

    elif template.frequency == template.FREQ_MONTHLY:
        cur = start
        while cur <= end:
            c = Corrida.create_from_template(template, cur)
            generated.append(c)
            # next month
            year = cur.year + (cur.month // 12)
            month = cur.month % 12 + 1
            day = min(cur.day, calendar.monthrange(year, month)[1])
            cur = date(year, month, day)

    return generated
