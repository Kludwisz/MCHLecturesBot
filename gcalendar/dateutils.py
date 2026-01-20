import arrow

DAY_NAMES = {
    1: 'Monday',
    2: 'Tuesday',
    3: 'Wednesday',
    4: 'Thursday',
    5: 'Friday',
    6: 'Saturday',
    7: 'Sunday'
}

MONTH_NAMES = {
    1: 'January',
    2: 'February',
    3: 'March',
    4: 'April',
    5: 'May',
    6: 'June',
    7: 'July',
    8: 'August',
    9: 'September',
    10: 'October',
    11: 'November',
    12: 'December'
}


def daystring(timepoint: arrow.Arrow) -> str:
    return timepoint.date().isoformat()


def day_name(timepoint: arrow.Arrow) -> str:
    return DAY_NAMES[timepoint.isoweekday()]


def day_name_short(timepoint: arrow.Arrow) -> str:
    return day_name(timepoint)[:3]


def month_name(timepoint: arrow.Arrow) -> str:
    return MONTH_NAMES[timepoint.date().month]


def month_name_short(timepoint: arrow.Arrow) -> str:
    return month_name(timepoint)[:3]
