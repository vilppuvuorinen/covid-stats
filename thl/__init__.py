import json
import pandas as pd
import requests
from datetime import date, timedelta
from requests import utils
from typing import Optional


_CACHE_FILE = '.cache-thl-covid19-v1.csv'
_DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:87.0) Gecko/20100101 Firefox/87.0'
utils.default_user_agent = lambda: _DEFAULT_USER_AGENT



def _sort_by_key(d):
    return [x[1] for x in sorted(d.items(), key=lambda item: item[0])]


def _sort_by_value(d):
    return [x[0] for x in sorted(d.items(), key=lambda item: item[1])]


def _load_cached() -> Optional[pd.DataFrame]:
    try:
        df = pd.read_csv(_CACHE_FILE, delimiter=';', parse_dates=True)
    except FileNotFoundError:
        return None

    if not isinstance(df, pd.DataFrame):
        return None

    date_col = df['date']
    if date_col is None:
        return None

    max_str = date_col.max()
    if not isinstance(max_str, str):
        return None

    max_date = date.fromisoformat(max_str)
    if max_date < date.today() - timedelta(days=1):
        return None

    print('Using cached data')
    df['date'] = pd.to_datetime(df['date']).dt.date
    return df


def load_daily_cases() -> Optional[pd.DataFrame]:
    """
    Fetch daily cases from THL covid19 API. The result is cached as a CSV file
    in the current working dir to avoid unnecessary traffic towards THL APIs.
    """
    existing_df = _load_cached()
    if existing_df is not None:
        return existing_df

    dimensions = json.loads(
         requests.get('https://sampo.thl.fi/pivot/prod/en/epirapo/covid19case/fact_epirapo_covid19case.dimensions.json')
            .text
            .split('\n', 1)[-1]
            .rsplit('\n', 1)[0]
            .rsplit('\n', 1)[0])


    areas = next(x for x in dimensions if x['label'] == 'Area')
    all_areas = next(x for x in areas['children'] if x['label'] == 'All areas')

    times = next(x for x in dimensions if x['label'] == 'Time')
    all_times = next(x for x in times['children'] if x['label'] == 'All times')
    weeks = [x for x in all_times['children'] if x['stage'] == 'week']

    full_df: Optional[pd.DataFrame] = None
    today_str = date.today().isoformat()

    for week in weeks:
        min_date = min([d['label'] for d in week['children']])
        if min_date >= today_str:
            break

        column = f"hcdmunicipality2020-{all_areas['sid']}"
        row = f"dateweek20200101-{week['sid']}"
        URL = f"https://sampo.thl.fi/pivot/prod/en/epirapo/covid19case/fact_epirapo_covid19case.json?row={row}&column={column}"

        dataset = json.loads(requests.get(URL).text)['dataset']

        [row, column] = dataset['dimension']['id']

        row_labels = [dataset['dimension'][row]['category']['label'][x] for x in _sort_by_value(dataset['dimension'][row]['category']['index'])]
        column_labels = [dataset['dimension'][column]['category']['label'][x] for x in _sort_by_value(dataset['dimension'][column]['category']['index'])]

        data = {}
        data['date'] = row_labels[:-1]

        value = dataset['value']
        is_list = type(value) == list

        for (i, column) in enumerate(column_labels):
            data[column] = []
            for (j, row) in enumerate(row_labels[:-1]):
                key = i + len(column_labels) * j
                if is_list:
                    if len(value) <= key:
                        data[column].append(0)
                    else:
                        data[column].append(value[key])
                else:
                    if str(key) in value:
                        data[column].append(value[str(key)])
                    else:
                        data[column].append(0)

        df = pd.DataFrame(data=data)
        if full_df is None:
            full_df = df
        else:
            full_df = full_df.append(df)

    if full_df is None:
        return None

    date_col = full_df['date']
    if date_col is None:
        return None

    full_df = full_df.loc[date_col <= (date.today() - timedelta(days=1)).isoformat()]

    full_df['date'] = pd.to_datetime(full_df['date']).dt.date

    if full_df is None:
        return None

    full_df.reset_index(drop=True, inplace=True)
    full_df.to_csv(_CACHE_FILE, sep=';', index=False)

    return full_df

