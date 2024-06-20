from collections import defaultdict
import requests
import json
import fitz
from string import Template
import read_games
import read_warcollege


def import_pel_pdf():
    url = "https://cdn.ymaws.com/www.hmgs.org/resource/resmgr/historicon/pels/2024_historicon_pel_5-25-24.pdf"
    response = requests.get(url)
    with open('pel.pdf', 'wb') as f:
        f.write(response.content)

    doc = fitz.open("pel.pdf")
    with open("pel2.txt", "w") as f:
        for page in doc:
            f.write(page.get_text())


def event_to_table_row(evt):
    data = [
        f"<input type='checkbox' class='chk' id='chk-state-{evt.safe_event_id}'/>",
        "<br/>".join([evt.event_slot, evt.event_id, evt.day, evt.hour, evt.event_type, "FULL" if evt.is_full else "Available"]),
        evt.name.replace("— Theme Game", "<br/><em>— Theme Game</em>"),
        evt.length,
        evt.players,
        evt.location.replace(":", "<br/>"),
        evt.GM.replace(" & ", " &<br/>"),
        evt.period,
        evt.scale,
        evt.rules,
        evt.description,
        evt.sponsor,
        evt.prize,
        evt.bio,
        'PELNOTSELECTED',
        'PELNOCONFLICTS',
    ]
    cells = [f"<td>{v}</td>" for v in data]

    cells[-2] = cells[-2].replace("<td>", f"<td id='hidden-selected-{evt.safe_event_id}'>")
    cells[-1] = cells[-1].replace("<td>", f"<td id='hidden-conflicts-{evt.safe_event_id}'>")
    row = "".join(cells)
    return f"<tr id='evt-{evt.safe_event_id}'>{row}</tr>"


def create_context():
    ctx = {}

    column_names = [
        "", "ID/Time", "Name", "Length", "Players", "Location",
        "GM", "Period", "Scale", "Rules",
        "Description", "Sponsor", "Prize", "Bio",
        "hidden-selected", "hidden-conflicts"
    ]

    ctx['table_header'] = "".join(f"<th>{v}</th>" for v in column_names)

    hidden_cols = ["Location", 'Sponsor', 'Prize',
                   'Bio', 'hidden-selected', 'hidden-conflicts']
    ctx['hidden_selected_col_num'] = len(column_names) - 2
    ctx['hidden_conflicts_col_num'] = len(column_names) - 1

    def active_class(col_name):
        return "" if col_name in hidden_cols else "active"

    column_toggles = [
        f'<button type="button" class="btn btn-outline-secondary btn-sm toggle-vis {active_class(v)}" autocomplete="off" data-toggle="button" data-column="{idx}" aria-pressed="false">{v}</button>'
        for idx, v in enumerate(column_names[1:-2], 1)
    ]
    ctx['column_toggles'] = "\n".join(column_toggles)

    column_defs = [
        {
            'visible': bool(col not in hidden_cols),
            'targets': idx,
            'name_': 'checkbox' if idx == 0 else col,
            'searchable': idx != 0,
            'orderable': (idx == 0) or col.startswith('hidden-')
        }
        for idx, col in enumerate(column_names)
    ]

    ctx['column_defs'] = json.dumps(
        column_defs,
        sort_keys=True,
        indent=4,
    )

    # -- GameEvents
    game_events = list(read_games.pel_text_to_events())
    wc_events = list(read_warcollege.warcollege_text_to_events())
    events = game_events + wc_events
    time_slots = defaultdict(list)
    for e in events:
        for s in e.time_slots:
            time_slots[s].append(e)
    for evt in events:
        for s in evt.time_slots:
            for e in time_slots[s]:
                evt.conflicts.add(e.safe_event_id)

    edict = {e.safe_event_id: e.as_dict() for e in events}
    ctx['events'] = json.dumps(edict, sort_keys=True, indent=4)

    table_rows = [event_to_table_row(e) for e in events]
    ctx['table_rows'] = "\n".join(table_rows)
    return ctx


def write_pel_html():
    with open("pel.template") as f:
        html_template = Template(f.read())

    ctx = create_context()
    html_text = html_template.substitute(ctx)

    with open("pel.html", "w") as f:
        f.write(html_text)


if __name__ == "__main__":
    import sys
    if "import" in sys.argv:
        import_pel_pdf()
    write_pel_html()
