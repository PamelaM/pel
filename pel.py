import re
from collections import defaultdict
import requests
import fitz

SEPARATORS = ["Players", "Location", "GM", "Sponsor", "Prize", "Period", "Scale", "Rules", "Description"]
pattern = re.compile("(Wednesday|Thursday|Friday|Saturday|Sunday)")

choices = defaultdict(set)


def import_pel_pdf():
    url = "https://cdn.ymaws.com/www.hmgs.org/resource/resmgr/historicon/pels/2024_historicon_pel_5-25-24.pdf"
    response = requests.get(url)
    with open('pel.pdf', 'wb') as f:
        f.write(response.content)

    doc = fitz.open("pel.pdf")
    with open("pel2.txt", "w") as f:
        for page in doc:
            f.write(page.get_text())


def read_choices():
    with open("pel.choices") as f:
        for line in f.read().splitlines():
            event_id, who = line.split("::", 1)
            print(event_id, who)
            choices[event_id].add(who)


class Event:
    def __init__(self, lines):
        try:
            self.separators = SEPARATORS[::]
            self.text = " ".join(lines[1:])
            self.event_id, self.name = lines[0].split(None, 1)
            self.name = f"{self.name}{self.next()}".strip()
            pieces = pattern.split(self.name)
            self.name = ''.join(pieces[:-2])
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
            event_slot = self.event_id.split(":")[0].strip()
            for idx, c in enumerate("WTFSZ"):
                event_slot = event_slot.replace(c, str(idx))
            self.event_slot = event_slot
            event_number = self.event_id.split(":")[-1].strip()
            self.pam = "PMAYBE" if "pam" in choices.get(event_number, []) else ""
            self.conall = "CMAYBE" if "conall" in choices.get(event_number, []) else ""
            self.megan = "MMAYBE" if "megan" in choices.get(event_number, []) else ""
        except:
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

    def as_table_row(self):
        name = self.name.replace("ThemeGame", "Theme Game")
        name = name.replace("—", " — ")
        name = " ".join(name.split(None))
        name = name.replace("— Theme Game", "<br/><em>— Theme Game</em>")
        desc_len = 300
        other_cols = [self.pam,
                      self.megan,
                      self.conall,
                      ]
        row = [
            "<br/>".join([self.event_slot, self.event_id, self.day, self.hour]),
            name,
            self.length,
            self.players,
            self.location.replace(":", "<br/>"),
            self.GM.replace(" & ", " &<br/>"),
            self.period,
            self.scale,
            self.rules,
            self.description,  # -- [:desc_len] + " ..." if len(self.description) > (desc_len+3) else self.description,
            self.sponsor,
            self.prize,
        ]
        row = [
            f"<td>{v}</td>"
            for v in row
        ]
        row = "".join(row)
        return f"<tr>{row}</tr>"


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

    slots = set()
    for d in "WTFSZ":
        for n in range(9, 25):
            slots.add(f"{d}{n:02}")

    for line in read_pel_lines():
        line = line.strip()
        start = line.split(":", 1)[0]
        if len(start) == 3 and start in slots and event_lines:
            yield event_lines
            event_lines = []
        event_lines.append(line)
    if event_lines:
        yield event_lines


periods = defaultdict(int)


def pel_text_to_events():
    for event_lines in read_pel_event_lines():
        e = Event(event_lines)
        if 0 and not (e.pam or e.megan or e.conall):
            if "SciFi" in e.period:
                continue
            if "Science" in e.period:
                continue
            if "Fantasy" in e.period:
                continue
            if "Future" in e.period:
                continue
            if "Ancients" in e.period:
                continue
            if "WORLD of TANKS" in e.rules:
                continue
            if "Myth" in e.period:
                continue
            if "Modern" in e.period:
                continue
        periods[e.period] += 1
        yield e


def write_pel_html():
    with open("pel.template") as f:
        html_template = f.read()

    first_col_names = ["Pam", "Megan", "Conall", ]
    column_names = [
        "ID/Time", "Name", "Length", "Players", "Location",
        "GM", "Period", "Scale", "Rules", "Description", "Sponsor", "Prize",
    ]
    table_header = "".join(
        f"<th>{v}</th>"
        for v in column_names
    )
    html_text = html_template.replace("{{ table_header }}", table_header)

    column_toggles = [
        f'<a class="toggle-vis" data-column="{idx}">{v}</a>'
        for idx, v in enumerate(column_names)
    ]
    column_toggles = " - ".join(column_toggles)
    html_text = html_text.replace("{{ column_toggles }}", column_toggles)

    table_rows = [
        e.as_table_row()
        for e in pel_text_to_events()
    ]
    table_rows = "\n".join(table_rows)
    html_text = html_text.replace("{{ table_rows }}", table_rows)

    hidden_cols = ["Megan", "Conall", "Location", 'Sponsor', 'Prize']
    column_defs = [
        f'visible: {str(bool(col not in hidden_cols)).lower()}, targets: {idx}'
        for idx, col in enumerate(column_names)
    ]
    column_defs = "\n".join("{" + cd + "}," for cd in column_defs).rstrip(",")
    html_text = html_text.replace("{{ column_defs }}", column_defs)

    with open("pel.html", "w") as f:
        f.write(html_text)


if __name__ == "__main__":
    import sys
    if "import" in sys.argv:
        import_pel_pdf()
    read_choices()
    write_pel_html()

    for n, p in sorted([(n, p) for p, n in periods.items()], reverse=True):
        print(f"{n:3}  {p}")

