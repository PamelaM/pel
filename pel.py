import re
from collections import defaultdict
import requests
import json
import fitz
from string import Template

SEPARATORS = ["Players", "Location", "GM", "Sponsor", "Prize", "Period", "Scale", "Rules", "Description"]
pattern = re.compile("(Wednesday|Thursday|Friday|Saturday|Sunday)")

TIME_SLOTS = set()
for d in "WTFSZ":
    for n in range(9, 25):
        TIME_SLOTS.add(f"{d}{n:02}")


def import_pel_pdf():
    url = "https://cdn.ymaws.com/www.hmgs.org/resource/resmgr/historicon/pels/2024_historicon_pel_5-25-24.pdf"
    response = requests.get(url)
    with open('pel.pdf', 'wb') as f:
        f.write(response.content)

    doc = fitz.open("pel.pdf")
    with open("pel2.txt", "w") as f:
        for page in doc:
            f.write(page.get_text())


class Event:
    def clean_name(self, name):
        name = name.replace("ThemeGame", "Theme Game")
        name = name.replace("—", " — ")
        name = " ".join(name.split(None))
        return name

    def __init__(self, lines):
        try:
            self.separators = SEPARATORS[::]
            self.text = " ".join(lines[1:])
            self.event_id, self.name = lines[0].split(None, 1)
            self.name = f"{self.name}{self.next()}".strip()
            pieces = pattern.split(self.name)
            self.name = self.clean_name(''.join(pieces[:-2]))
            self.day, extra = pieces[-2:]
            extra = extra.strip(",").strip()
            hour, length = extra.rsplit(",", 1)
            self.hour = hour.strip(",").strip().replace(":00:00", ":00")
            self.length = length.strip()
            self.players = self.next()
            self.location = self.next()
            self.GM = self.next()
            self.sponsor = self.next()
            self.prize = self.next()
            self.period = self.next()
            self.scale = self.next()
            self.rules = self.next()
            self.description = self.next()
            time_slot = event_slot = self.event_id.split(":")[0].strip()
            for idx, c in enumerate("WTFSZ"):
                event_slot = event_slot.replace(c, str(idx))
            self.event_slot = event_slot
            self.safe_event_id = self.event_id.replace(":", '-').strip()
            start_hour = int(time_slot[1:])
            day_letter = time_slot[0]
            duration = round(float(self.length.split(None)[0]) + 0.5)
            self.time_slots = [
                f"{day_letter}{(start_hour + idx):02d}"
                for idx in range(duration)
            ]
            self.conflicts = set()
        except Exception:
            print(len(lines), lines[0], self.text)
            raise

    def next(self):
        if not self.separators:
            val = self.text.strip()
        else:
            sep = self.separators.pop(0)
            value, self.text = self.text.split(f" {sep}: ")
            val = value.strip(",").strip()
        return "" if val == "NONE" else val

    def as_dict(self):
        return dict(
            event_id=self.safe_event_id,
            name=self.name,
            day=self.day,
            hour=self.hour,
            length=self.length,
            players=self.players,
            location=self.location,
            GM=self.GM,
            sponsor=self.sponsor,
            prize=self.prize,
            period=self.period,
            scale=self.scale,
            rules=self.rules,
            description=self.description,
            time_slots=self.time_slots,
            conflicts=sorted(self.conflicts),
        )


def read_pel_lines():
    with open("pel2.txt") as f:
        pel_text = f.read()

    pages = [
        page.split("P a g e", 1)[-1].split("\n", 1)[-1].strip()
        for page in pel_text.split("HISTORICON® 2024")
    ]
    for page in pages:
        yield from page.splitlines()


def read_pel_event_lines():
    event_lines = []

    for line in read_pel_lines():
        line = line.strip()
        start = line.split(":", 1)[0]
        if len(start) == 3 and start in TIME_SLOTS and event_lines:
            yield event_lines
            event_lines = []
        event_lines.append(line)
    if event_lines:
        yield event_lines


periods = defaultdict(int)


def pel_text_to_events():
    for event_lines in read_pel_event_lines():
        e = Event(event_lines)
        periods[e.period] += 1
        yield e


def event_to_table_row(evt):
    data = [
        f"<input type='checkbox' class='chk' id='chk-state-{evt.safe_event_id}'/>",
        "<br/>".join([evt.event_slot, evt.event_id, evt.day, evt.hour]),
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
        "GM", "Period", "Scale", "Rules", "Description", "Sponsor", "Prize",
        "hidden-selected", "hidden-conflicts"
    ]

    ctx['table_header'] = "".join(f"<th>{v}</th>" for v in column_names)

    hidden_cols = ["Location", 'Sponsor', 'Prize', 'hidden-selected', 'hidden-conflicts']
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

    # -- Events
    events = list(pel_text_to_events())
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


def test():
    events = list(pel_text_to_events())
    edict = {e.event_id: e for e in events}
    conflicts = {e.event_id: False for e in events}
    time_slots = defaultdict(list)
    for e in events:
        for s in e.time_slots:
            time_slots[s].append(e)

    selected_evts = [edict['T09:447']]

    for evt in selected_evts:
        for s in evt.time_slots:
            for e in time_slots[s]:
                conflicts[e.event_id] = True
    for evt in selected_evts:
        conflicts[evt.event_id] = False

    evt_conflicts = [
        (evt_id, edict[evt_id])
        for evt_id, is_conflict in sorted(conflicts.items())
        if is_conflict
    ]
    for _, e in sorted(evt_conflicts):
        print(e.event_id, e.time_slots)


if __name__ == "__main__":
    import sys
    if "import" in sys.argv:
        import_pel_pdf()
    write_pel_html()
