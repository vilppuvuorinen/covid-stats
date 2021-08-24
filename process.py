import matplotlib.pyplot as plt
import mpld3
import os
import pandas as pd
from datetime import date
from mpld3 import plugins

from thl import load_daily_cases

_HTML = 'covid.html'


def _render_fig(ax) -> str:
    html = mpld3.fig_to_html(ax.get_figure(), template_type='general')
    plt.close(ax.get_figure())
    return html

def _daily_symptomatic_population(data: pd.DataFrame) -> str:
    df = data[['date', 'All areas']].rename(columns={'All areas': 'y'})
    df['y'] = df['y'].rolling(7*4).sum()
    df = df.loc[df['y'].notna()]

    ax = df.plot(
        x='date',
        y='y',
        xlabel='',
        ylabel='Symptomatic population',
        legend=False
    )

    return f"""
    <h2>Total symptomatic population</h2>
    <p><i>Assuming flat 4 week symptomatic period.</i></p>
    {_render_fig(ax)}
    """

def _daily_symptomatic_population_delta(data: pd.DataFrame) -> str:
    df = data[['date', 'All areas']].rename(columns={'All areas': 'y'})
    df['y'] = df['y'].rolling(7*4).sum().diff()
    df = df.loc[df['y'].notna()]

    ax = df.plot(
        x='date',
        y='y',
        xlabel='',
        ylabel='Symptomatic population delta',
        legend=False
    )

    return f"""
    <h2>Change in symptomatic population per day</h2>
    <p><i>Assuming a flat 4 week symptomatic period.</i></p>
    {_render_fig(ax)}
    """

def _daily_symptomatic_population_delta_percentage(data: pd.DataFrame) -> str:
    df = data[['date', 'All areas']].rename(columns={'All areas': 'y'})
    df['y_prev'] = df['y'].rolling(7*4).sum().shift(periods=1)
    df['y_diff'] = df['y'].rolling(7*4).sum().diff()
    df = df.loc[df['y_diff'].notna() & df['y_prev']]
    df['y'] = df['y_diff'].div(df['y_prev']).mul(100.0)
    df = df.loc[df['date'] > date.fromisoformat('2020-03-31')]

    ax = df.plot(
        x='date',
        y='y',
        xlabel='',
        ylabel='Symptomatic population delta %',
        legend=False
    )

    return f"""
    <h2>Relative change in symptomatic population per day</h2>
    <p><i>Assuming a flat 4 week symptomatic period.</i></p>
    {_render_fig(ax)}
    """

def _14d_deltas(data: pd.DataFrame) -> str:
    symptomatic_df = data.drop(columns=['date', 'All areas']).rolling(7*4).sum()

    two_periods_ago = symptomatic_df.iloc[-29]
    period_ago = symptomatic_df.iloc[-15]
    now = symptomatic_df.iloc[-1]

    this_period = now.sub(period_ago).div(period_ago).mul(100)
    this_period.name = 'delta'

    last_period = period_ago.sub(two_periods_ago).div(two_periods_ago).mul(100)

    pp_to_last_period = this_period.sub(last_period)
    pp_to_last_period.name = 'since last'

    relative_deltas = pd.concat([this_period, pp_to_last_period], axis=1).reset_index().sort_values(by='delta', ascending=False)

    table_rows = [f"""
    <tr>
    <td>{v['index']}</td>
    <td style="text-align:right">{'{:+.1f}'.format(v['delta'])}</td>
    <td style="text-align:right;color:{'red' if v['since last'] > 0 else 'green'}">
        {'{:+.2f}'.format(v['since last'])}
    </td>
    </tr>
    """
    for _, v in relative_deltas.iterrows()]

    return f"""
    <h2>14 day deltas</h2>
    <p>Relative change in symptomatic population in the past 14 days.</p>
    <table>
    <tr>
    <th>District</th>
    <th>Change (%)</th>
    <th>Difference to last period (pp)
    </tr>
    {"".join(table_rows)}
    </table>
    """

def _60d_deltas(data: pd.DataFrame) -> str:
    symptomatic_df = data.drop(columns=['date', 'All areas']).rolling(7*4).sum()

    two_periods_ago = symptomatic_df.iloc[-121]
    period_ago = symptomatic_df.iloc[-61]
    now = symptomatic_df.iloc[-1]

    this_period = now.sub(period_ago).div(period_ago).mul(100)
    this_period.name = 'delta'

    last_period = period_ago.sub(two_periods_ago).div(two_periods_ago).mul(100)

    pp_to_last_period = this_period.sub(last_period)
    pp_to_last_period.name = 'since last'

    relative_deltas = pd.concat([this_period, pp_to_last_period], axis=1).reset_index().sort_values(by='delta', ascending=False)

    table_rows = [f"""
    <tr>
    <td>{v['index']}</td>
    <td style="text-align:right">{'{:+.1f}'.format(v['delta'])}</td>
    <td style="text-align:right;color:{'red' if v['since last'] > 0 else 'green'}">
        {'{:+.2f}'.format(v['since last'])}
    </td>
    </tr>
    """
    for _, v in relative_deltas.iterrows()]

    return f"""
    <h2>60 day deltas</h2>
    <p>Relative change in symptomatic population in the past 60 days.</p>
    <table>
    <tr>
    <th>District</th>
    <th>Change (%)</th>
    <th>Difference to last period (pp)
    </tr>
    {"".join(table_rows)}
    </table>
    """

def process():
    data = load_daily_cases()
    if data is None:
        print('No data available')
        return

    data = data.iloc[:-3]

    if os.path.exists(_HTML):
        os.remove(_HTML)

    with open('public/index.html', 'a') as f:
        f.write(f"""
        <!doctype html>

        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>COVID stats with some assumptions</title>
        </head>
        <body>
        {_daily_symptomatic_population(data)}
        {_daily_symptomatic_population_delta(data)}
        {_daily_symptomatic_population_delta_percentage(data)}
        {_14d_deltas(data)}
        {_60d_deltas(data)}
        </body>
        </html>
        """)
if __name__ == "__main__":
    process()
