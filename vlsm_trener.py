"""Trener VLSM IPv4 v3: jednoczesny edytor binarny i dziesiętny (Tkinter)."""
from __future__ import annotations

import ipaddress
import random
import re
import tkinter as tk
from tkinter import messagebox, ttk

from vlsm_core import (
    Answer, FIELD_NAMES, VLSMError, check_answers, format_ipv4,
    format_prefix, generate_solution, min_prefix_for_hosts, parse_base_network,
    parse_host_count, parse_ipv4, parse_prefix,
)

BG = "#f3f6fa"
WHITE = "#ffffff"
INK = "#172235"
MUTED = "#536273"
BLUE = "#174ea6"
BLUE_LIGHT = "#edf4ff"
GREEN = "#e0f5e7"
RED = "#ffe4e6"
BORDER = "#dbe3ee"

NUMBER_KEYS = ("hosts", "allocated", "capacity")
ADDRESS_STEPS = (
    ("mask", "1. Maska podsieci", "Dobierz maskę do liczby urządzeń"),
    ("network", "2. Adres sieci", "Adres = IP AND maska"),
    ("inverse_mask", "3. Negacja maski", "Zamień 0 na 1, a 1 na 0 (NOT)"),
    ("broadcast", "4. Broadcast", "Adres sieci OR negacja maski"),
    ("first", "5. Pierwszy host", "Adres sieci + 1"),
    ("last", "6. Ostatni host", "Broadcast − 1"),
)
EXERCISES = [
    ("192.168.10.0", 24, [60, 30, 14, 6]),
    ("10.20.0.0", 22, [220, 100, 60, 30, 12]),
    ("172.16.8.0", 23, [180, 90, 50, 20, 10]),
    ("192.168.50.0", 24, [110, 50, 25, 10]),
    ("10.30.16.0", 21, [400, 180, 80, 50, 20, 10]),
    ("172.18.4.0", 22, [190, 110, 70, 35, 15, 5]),
]


def _entry(parent, width: int, var: tk.StringVar | None = None,
           bg: str = WHITE, font_size: int = 10) -> tk.Entry:
    return tk.Entry(parent, textvariable=var, width=width, bg=bg, fg=INK,
                    insertbackground=INK, relief="solid", bd=1,
                    highlightthickness=1, highlightbackground=BORDER,
                    highlightcolor=BLUE, font=("Consolas", font_size))


def to_view(value: str, key: str, binary: bool) -> str:
    """Zachowana funkcja pomocnicza, np. do testów starszych wersji."""
    if not value.strip() or key in NUMBER_KEYS:
        return value
    try:
        return (format_prefix(parse_prefix(value), binary) if key == "mask"
                else format_ipv4(parse_ipv4(value), binary))
    except VLSMError:
        return value


class PairedAddress:
    """Jednoczesny edytor 4 oktetów BIN i całego adresu DEC.

    Zmiana w jednym zapisie jest odwzorowywana w drugim, gdy wartość jest
    kompletna. Niekompletne dane pozostają w aktywnym polu, bez ich zgadywania.
    Zmienna _source wskazuje, z której strony pobrać odpowiedź do walidacji.
    """

    def __init__(self, parent: tk.Widget, key: str, on_change,
                 decimal_var: tk.StringVar | None = None,
                 allow_inline_mask: bool = False) -> None:
        self.key = key
        self.on_change = on_change
        self.allow_inline_mask = allow_inline_mask
        self.decimal_var = decimal_var if decimal_var is not None else tk.StringVar()
        self.binary_vars = [tk.StringVar() for _ in range(4)]
        self.binary_entries = [_entry(parent, 10, var) for var in self.binary_vars]
        self.decimal_entry = _entry(parent, 19, self.decimal_var)
        self._source = "decimal"
        self._suspend = False
        self.decimal_var.trace_add("write", self._from_decimal)
        for var in self.binary_vars:
            var.trace_add("write", self._from_binary)
        if self.decimal_var.get():
            self._from_decimal(notify=False)

    def grid(self, row: int, binary_start: int = 1, decimal_col: int = 5) -> None:
        for i, entry in enumerate(self.binary_entries):
            entry.grid(row=row, column=binary_start + i, padx=3, pady=3,
                       ipady=4, sticky="ew")
        self.decimal_entry.grid(row=row, column=decimal_col, padx=(12, 4),
                                pady=3, ipady=4, sticky="ew")

    def _parsed_decimal(self, text: str) -> ipaddress.IPv4Address:
        if self.key == "mask":
            try:
                return ipaddress.IPv4Address(format_prefix(parse_prefix(text)))
            except VLSMError:
                # Błędna merytorycznie maska (np. 255.0.255.0) nadal
                # jest adresem IPv4; pokaż jej bity, aby można ją poprawić.
                return parse_ipv4(text)
        if self.allow_inline_mask and "/" in text:
            address, suffix = text.rsplit("/", 1)
            parse_prefix(suffix)
            return parse_ipv4(address)
        return parse_ipv4(text)

    def _from_decimal(self, *_args, notify: bool = True) -> None:
        if self._suspend:
            return
        self._source = "decimal"
        text = self.decimal_var.get().strip()
        try:
            parts = format_ipv4(self._parsed_decimal(text), True).split(".")
        except (VLSMError, ValueError):
            parts = [""] * 4
        self._suspend = True
        try:
            for variable, part in zip(self.binary_vars, parts):
                variable.set(part)
        finally:
            self._suspend = False
        if notify:
            self.on_change()

    def _from_binary(self, *_args) -> None:
        if self._suspend:
            return
        self._source = "binary"
        parts = [variable.get().strip() for variable in self.binary_vars]
        if all(re.fullmatch(r"[01]{8}", part) for part in parts):
            try:
                decimal = format_ipv4(parse_ipv4(".".join(parts)))
            except VLSMError:
                decimal = ""
        else:
            decimal = ""
        self._suspend = True
        try:
            self.decimal_var.set(decimal)
        finally:
            self._suspend = False
        self.on_change()

    def get(self) -> str:
        if self._source == "decimal":
            return self.decimal_var.get().strip()
        parts = [variable.get().strip() for variable in self.binary_vars]
        return ".".join(parts) if any(parts) else ""

    def put(self, raw: str) -> None:
        """Załaduj wartość dziesiętną lub binarną bez sygnalizacji edycji."""
        text = str(raw).strip()
        self._suspend = True
        try:
            if not text:
                decimal, parts, source = "", [""] * 4, "decimal"
            else:
                try:
                    parsed = self._parsed_decimal(text)
                    parts = format_ipv4(parsed, True).split(".")
                    decimal = (text if self.allow_inline_mask and "/" in text
                               else format_ipv4(parsed))
                    source = "decimal"
                except (VLSMError, ValueError):
                    split = text.split(".")
                    looks_binary = (len(split) == 4 and
                                    all(re.fullmatch(r"[01]{0,8}", p) for p in split))
                    if looks_binary:
                        decimal, parts, source = "", split, "binary"
                    else:
                        decimal, parts, source = text, [""] * 4, "decimal"
            self._source = source
            self.decimal_var.set(decimal)
            for variable, part in zip(self.binary_vars, parts):
                variable.set(part)
        finally:
            self._suspend = False
        self.set_color("unchecked")

    def set_color(self, status: str, expected_binary: str | None = None) -> None:
        if status == "good":
            binary_colors = [GREEN] * 4
            decimal_color = GREEN
        elif status == "unchecked":
            binary_colors = [WHITE] * 4
            decimal_color = WHITE
        else:
            binary_colors = [RED] * 4
            expected = expected_binary.split(".") if expected_binary else []
            parts = [variable.get().strip() for variable in self.binary_vars]
            if len(expected) == 4 and all(re.fullmatch(r"[01]{8}", p) for p in parts):
                differences = [got != wanted for got, wanted in zip(parts, expected)]
                if any(differences):
                    binary_colors = [RED if wrong else GREEN for wrong in differences]
            decimal_color = RED
        for entry, color in zip(self.binary_entries, binary_colors):
            entry.configure(bg=color)
        self.decimal_entry.configure(bg=decimal_color)


class SubnetRow:
    """Karta podsieci: obliczenia pionowo, BIN i DEC obok siebie."""

    def __init__(self, parent: tk.Widget, number: int, changed_callback):
        self.number = number
        self.on_change = changed_callback
        self.outer = tk.Frame(parent, bg=WHITE, highlightbackground=BORDER,
                              highlightthickness=1)
        self.outer.pack(fill="x", pady=(0, 10), padx=2)
        self.inputs: dict[str, tk.Entry] = {}
        self.pairs: dict[str, PairedAddress] = {}
        self.octets: dict[str, list[tk.Entry]] = {}
        self.decimals: dict[str, tk.Entry] = {}
        self.labels: dict[str, tk.Label] = {}
        self._create_content()
        self.info = tk.Label(self.outer, text="", anchor="w", justify="left",
                             bg=WHITE, fg=MUTED, wraplength=1150,
                             font=("Segoe UI", 9))
        self.info.pack(fill="x", padx=14, pady=(0, 8))

    def _number_entry(self, parent, key, width, bg=WHITE):
        var = tk.StringVar()
        entry = _entry(parent, width, var, bg)
        var.trace_add("write", lambda *_: self.on_change())
        self.inputs[key] = entry
        return entry

    def _create_content(self):
        top = tk.Frame(self.outer, bg=WHITE)
        top.pack(fill="x", padx=15, pady=(11, 6))
        tk.Label(top, text=f"PODSIEĆ {self.number}", bg=WHITE, fg=BLUE,
                 font=("Segoe UI", 12, "bold")).pack(side="left", padx=(0, 20))
        tk.Label(top, text="Wymagane urządzenia:", bg=WHITE, fg=INK,
                 font=("Segoe UI", 10)).pack(side="left")
        self._number_entry(top, "hosts", 10, "#f5f9ff").pack(
            side="left", padx=(9, 8), ipady=4)
        self.status = tk.Label(top, text="—", bg=WHITE, fg=MUTED,
                               font=("Segoe UI", 10, "bold"))
        self.status.pack(side="right", padx=4)

        table = tk.Frame(self.outer, bg=WHITE)
        table.pack(fill="x", padx=15, pady=(0, 8))
        tk.Label(table, text="Kolejne obliczenia", bg=WHITE, fg=MUTED,
                 font=("Segoe UI", 9, "bold"), anchor="w").grid(
                     row=0, column=0, sticky="w", padx=(2, 9), pady=(3, 6))
        for i in range(4):
            tk.Label(table, text=f"BIN · oktet {i + 1}", bg=WHITE, fg=MUTED,
                     font=("Segoe UI", 9, "bold")).grid(
                         row=0, column=i + 1, pady=(3, 6), padx=3)
        tk.Label(table, text="DEC · IPv4", bg=WHITE, fg=BLUE,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=5,
                                                    pady=(3, 6), padx=(12, 4))
        tk.Label(table, text="Działanie", bg=WHITE, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=6,
                                                    sticky="w", padx=(12, 2))
        for step, (key, title, explanation) in enumerate(ADDRESS_STEPS, 1):
            label = tk.Label(table, text=title, bg=WHITE, fg=INK,
                             font=("Segoe UI", 10, "bold"), anchor="w", width=24)
            label.grid(row=step, column=0, sticky="w", padx=(2, 8), pady=3)
            self.labels[key] = label
            pair = PairedAddress(table, key, self.on_change)
            pair.grid(step)
            self.pairs[key] = pair
            self.octets[key] = pair.binary_entries
            self.decimals[key] = pair.decimal_entry
            tk.Label(table, text=explanation, bg=WHITE, fg=MUTED,
                     font=("Segoe UI", 9), anchor="w").grid(
                         row=step, column=6, padx=(12, 4), sticky="w")

        footer = tk.Frame(self.outer, bg="#f8fafd")
        footer.pack(fill="x", padx=15, pady=(1, 8))
        for key, title, formula in (
            ("allocated", "7. Zajęte adresy (łącznie)", "2^(32 − CIDR), z siecią i broadcastem"),
            ("capacity", "8. Dostępne adresy hostów", "2^(32 − CIDR) − 2"),
        ):
            group = tk.Frame(footer, bg="#f8fafd")
            group.pack(side="left", padx=(7, 34), pady=8)
            label = tk.Label(group, text=title, bg="#f8fafd", fg=INK,
                             font=("Segoe UI", 9, "bold"))
            label.pack(side="left")
            self.labels[key] = label
            self._number_entry(group, key, 12).pack(side="left", padx=(8, 7), ipady=4)
            tk.Label(group, text=formula, bg="#f8fafd", fg=MUTED,
                     font=("Segoe UI", 8)).pack(side="left")

    def get(self, key: str) -> str:
        if key in self.pairs:
            return self.pairs[key].get()
        return self.inputs[key].get().strip()

    def put(self, key: str, value: str) -> None:
        if key in self.pairs:
            self.pairs[key].put(str(value))
        else:
            entry = self.inputs[key]
            entry.delete(0, "end")
            entry.insert(0, str(value))
        self.set_color(key, "unchecked")

    def answer(self) -> Answer:
        return Answer(**{key: self.get(key) for key in FIELD_NAMES})

    def set_color(self, key: str, status: str, expected: str | None = None):
        if key in self.pairs:
            self.pairs[key].set_color(status, expected)
        else:
            bg = "#f5f9ff" if key == "hosts" and status == "unchecked" else {
                "good": GREEN, "error": RED, "unchecked": WHITE
            }[status]
            self.inputs[key].configure(bg=bg)
        if key in self.labels:
            self.labels[key].configure(fg="#b42332" if status == "error" else INK)

    def clear_result(self):
        for key in FIELD_NAMES:
            self.set_color(key, "unchecked")
        self.status.configure(text="—", fg=MUTED)
        self.info.configure(text="", fg=MUTED)


class VLSMTrainer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Trener VLSM – IPv4 (wersja 3: BIN + DEC)")
        self.geometry("1520x900")
        self.minsize(1050, 650)
        self.configure(bg=BG)
        try:
            self.tk.call("tk", "scaling", 1.25)
        except tk.TclError:
            pass
        self.style = ttk.Style(self)
        if "vista" in self.style.theme_names():
            self.style.theme_use("vista")
        elif "clam" in self.style.theme_names():
            self.style.theme_use("clam")
        self.style.configure("Action.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 8))
        self.style.configure("Normal.TButton", font=("Segoe UI", 10), padding=(12, 7))
        self.style.configure("Option.TCheckbutton", background=BG, font=("Segoe UI", 10))

        self.strict_var = tk.BooleanVar(value=True)
        self.base_ip_var = tk.StringVar(value="192.168.10.0")
        self.base_mask_var = tk.StringVar(value="255.255.255.0")
        self.count_var = tk.StringVar(value="4")
        self.parent_note_var = tk.StringVar(value="")
        self.summary_var = tk.StringVar(value="Uzupełnij odpowiedzi i kliknij „Sprawdź”.")
        self.rows: list[SubnetRow] = []
        self._build_ui()
        self._create_rows(4, [60, 30, 14, 6])
        self.bind_all("<Control-Return>", lambda _e: self.check())
        self.after(100, self.update_parent_note)

    def _base_changed(self):
        self.update_parent_note()
        self.invalidate_result()

    def _build_ui(self):
        header = tk.Frame(self, bg="#183153")
        header.pack(fill="x")
        tk.Label(header, text="TRENER VLSM  |  IPv4", font=("Segoe UI", 20, "bold"),
                 fg=WHITE, bg="#183153").pack(anchor="w", padx=24, pady=(12, 2))
        tk.Label(header, text="Obliczenia pionowo · zapis binarny i dziesiętny jednocześnie",
                 font=("Segoe UI", 11), fg="#d8e8fb", bg="#183153").pack(
                     anchor="w", padx=24, pady=(0, 12))
        setup = tk.Frame(self, bg=BG)
        setup.pack(fill="x", padx=20, pady=(12, 6))
        base = tk.Frame(setup, bg=BG)
        base.pack(side="left", anchor="nw", padx=(0, 26))
        tk.Label(base, text="Sieć bazowa – oba zapisy", bg=BG, fg=INK,
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=0,
                    columnspan=6, sticky="w", pady=(0, 6))
        for i in range(4):
            tk.Label(base, text=f"BIN · oktet {i + 1}", bg=BG, fg=MUTED,
                     font=("Segoe UI", 8, "bold")).grid(row=1, column=i + 1,
                                                            padx=3, pady=(0, 3))
        tk.Label(base, text="DEC · IPv4", bg=BG, fg=BLUE,
                 font=("Segoe UI", 9, "bold")).grid(row=1, column=5,
                                                    padx=(12, 4), pady=(0, 3))
        for index, (key, text, variable, allow_cidr) in enumerate((
            ("network", "Adres sieci", self.base_ip_var, True),
            ("mask", "Maska sieci", self.base_mask_var, False),
        ), start=2):
            tk.Label(base, text=text, bg=BG, fg=INK,
                     font=("Segoe UI", 9, "bold"), anchor="w", width=15).grid(
                         row=index, column=0, sticky="w", padx=(0, 6))
            pair = PairedAddress(base, key, self._base_changed,
                                 decimal_var=variable, allow_inline_mask=allow_cidr)
            pair.grid(index)
            if key == "network":
                self.base_ip_pair = pair
                self.base_ip_entry = pair.decimal_entry
            else:
                self.base_mask_pair = pair
                self.base_mask_entry = pair.decimal_entry

        controls = tk.Frame(setup, bg=BG)
        controls.pack(side="left", anchor="nw", pady=(2, 0))
        tk.Label(controls, text="Liczba podsieci", bg=BG, fg=INK,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))
        actions = tk.Frame(controls, bg=BG)
        actions.pack(anchor="w")
        ttk.Spinbox(actions, textvariable=self.count_var, from_=1, to=50,
                    width=6, font=("Segoe UI", 10)).pack(side="left", ipady=4)
        ttk.Button(actions, text="Ustaw liczbę", command=self.resize_rows,
                   style="Normal.TButton").pack(side="left", padx=(8, 6))
        ttk.Button(controls, text="Losuj zadanie", command=self.random_exercise,
                   style="Normal.TButton").pack(anchor="w", pady=(8, 0))

        settings = tk.Frame(self, bg=BG)
        settings.pack(fill="x", padx=20, pady=(0, 7))
        self.parent_note = tk.Label(settings, textvariable=self.parent_note_var,
                                    bg=BG, fg=MUTED, font=("Segoe UI", 9))
        self.parent_note.pack(side="left", anchor="w")
        ttk.Checkbutton(settings, text="Wymagaj najmniejszej wystarczającej maski",
                        variable=self.strict_var, style="Option.TCheckbutton",
                        command=self.invalidate_result).pack(side="right", padx=(12, 0))

        self.hint = tk.Label(self, bg=BLUE_LIGHT, fg="#20446b", justify="left",
                             wraplength=1370, font=("Segoe UI", 9), anchor="w",
                             text="W każdym wierszu wpisuj BIN (po 8 bitów w czterech oktetach) albo DEC "
                                  "(cały adres). Drugi zapis uzupełni się automatycznie po wpisaniu "
                                  "poprawnej wartości. Niepełne dane nie są nadpisywane. "
                                  "Maskę DEC możesz również wpisać jako /26.")
        self.hint.pack(fill="x", padx=20, pady=(0, 10), ipady=9)

        worksheet = tk.Frame(self, bg=BG)
        worksheet.pack(fill="both", expand=True, padx=19, pady=(0, 8))
        self.canvas = tk.Canvas(worksheet, bg=BG, highlightthickness=0, bd=0)
        vscroll = ttk.Scrollbar(worksheet, orient="vertical", command=self.canvas.yview)
        hscroll = ttk.Scrollbar(worksheet, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vscroll.grid(row=0, column=1, sticky="ns")
        hscroll.grid(row=1, column=0, sticky="ew")
        worksheet.rowconfigure(0, weight=1)
        worksheet.columnconfigure(0, weight=1)
        self.table_body = tk.Frame(self.canvas, bg=BG)
        self.table_window = self.canvas.create_window((0, 0), window=self.table_body,
                                                     anchor="nw")
        self.table_body.bind("<Configure>", lambda _e: self._update_scroll())
        self.canvas.bind("<Configure>", lambda _e: self._update_scroll())
        self.bind_all("<MouseWheel>", self._on_scroll, add="+")
        self.bind_all("<Shift-MouseWheel>", self._on_horizontal_scroll, add="+")
        self.rows_frame = tk.Frame(self.table_body, bg=BG)
        self.rows_frame.pack(fill="x")

        bottom = tk.Frame(self, bg=BG)
        bottom.pack(fill="x", padx=20, pady=(4, 15))
        tk.Label(bottom, textvariable=self.summary_var, bg=BG, fg=INK,
                 font=("Segoe UI", 10, "bold"), anchor="w", justify="left",
                 wraplength=810).pack(side="left", fill="x", expand=True, padx=(0, 12))
        ttk.Button(bottom, text="Wyczyść odpowiedzi", command=self.clear_answers,
                   style="Normal.TButton").pack(side="right", padx=(8, 0))
        ttk.Button(bottom, text="Pokaż rozwiązanie", command=self.show_solution,
                   style="Normal.TButton").pack(side="right", padx=(8, 0))
        ttk.Button(bottom, text="Sprawdź (Ctrl+Enter)", command=self.check,
                   style="Action.TButton").pack(side="right")

    def _update_scroll(self):
        if not hasattr(self, "canvas"):
            return
        required = max(self.canvas.winfo_width(), self.table_body.winfo_reqwidth())
        if int(float(self.canvas.itemcget(self.table_window, "width") or 0)) != required:
            self.canvas.itemconfigure(self.table_window, width=required)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        for row in self.rows:
            row.info.configure(wraplength=max(660, self.canvas.winfo_width() - 60))

    def _on_scroll(self, event):
        if self._within_canvas(event.widget):
            self.canvas.yview_scroll(-int(event.delta / 120), "units")

    def _on_horizontal_scroll(self, event):
        if self._within_canvas(event.widget):
            self.canvas.xview_scroll(-int(event.delta / 120), "units")

    def _within_canvas(self, widget):
        current = widget
        while current is not None:
            if current is self.canvas or current is self.table_body:
                return True
            current = getattr(current, "master", None)
        return False

    def _replace_rows(self, entries: list[Answer]):
        for row in self.rows:
            row.outer.destroy()
        self.rows = []
        for index, answer in enumerate(entries, 1):
            row = SubnetRow(self.rows_frame, index, self.invalidate_result)
            self.rows.append(row)
            for key in FIELD_NAMES:
                row.put(key, getattr(answer, key))
        self.count_var.set(str(len(entries)))
        self.invalidate_result()
        self.after_idle(self._update_scroll)

    def _create_rows(self, count: int, hosts: list[int] | None = None):
        self._replace_rows([Answer(str(hosts[i]) if hosts and i < len(hosts) else "")
                            for i in range(count)])

    def resize_rows(self):
        try:
            count = int(self.count_var.get())
            if not 1 <= count <= 50:
                raise ValueError
        except ValueError:
            messagebox.showerror("Liczba podsieci", "Podaj liczbę podsieci od 1 do 50.", parent=self)
            return
        previous = [row.answer() for row in self.rows]
        entries = previous[:count] + [Answer("") for _ in range(max(0, count - len(previous)))]
        self._replace_rows(entries)

    def random_exercise(self):
        base_address, prefix, hosts = random.choice(EXERCISES)
        self.base_ip_var.set(base_address)
        self.base_mask_var.set(format_prefix(prefix))
        self._create_rows(len(hosts), hosts)
        self.update_parent_note()
        self.summary_var.set("Wylosowano ćwiczenie. Uzupełnij adresy i sprawdź odpowiedź.")
        self.canvas.yview_moveto(0)
        self.canvas.xview_moveto(0)

    def invalidate_result(self):
        for row in self.rows:
            row.clear_result()
        self.summary_var.set("Odpowiedzi zmienione — kliknij „Sprawdź”.")

    def _base_inputs(self):
        return self.base_ip_pair.get(), self.base_mask_pair.get()

    def update_parent_note(self):
        try:
            base = parse_base_network(*self._base_inputs())
            self.parent_note_var.set(
                f"Sieć: {base}   |   pula: {base.num_addresses:,} adresów   |   "
                f"zakres: {base.network_address} – {base.broadcast_address}")
            self.parent_note.configure(fg=MUTED)
        except VLSMError as exc:
            self.parent_note_var.set("Sieć bazowa: " + str(exc))
            self.parent_note.configure(fg="#b42332")

    def _expected_for_octets(self, answer: Answer, result, key: str) -> str | None:
        try:
            if key == "mask":
                if self.strict_var.get():
                    return format_prefix(min_prefix_for_hosts(parse_host_count(answer.hosts)), True)
                return format_prefix(parse_prefix(answer.mask), True)
            if key == "inverse_mask":
                mask = ipaddress.IPv4Network((0, parse_prefix(answer.mask))).hostmask
                return format_ipv4(mask, True)
            prefix = parse_prefix(answer.mask)
            addr = parse_ipv4(answer.network)
            net = ipaddress.IPv4Network((int(addr), prefix), strict=False)
            expected = {
                "network": net.network_address,
                "broadcast": net.broadcast_address,
                "first": int(net.network_address) + 1,
                "last": int(net.broadcast_address) - 1,
            }
            return format_ipv4(expected[key], True) if key in expected else None
        except (VLSMError, ValueError):
            return None

    def check(self):
        self.update_parent_note()
        answers = [row.answer() for row in self.rows]
        report = check_answers(*self._base_inputs(), answers,
                               strict_vlsm=self.strict_var.get(),
                               require_counts=True, require_inverse_mask=True)
        for row, answer, result in zip(self.rows, answers, report.rows):
            for key in FIELD_NAMES:
                row.set_color(key, result.status[key],
                              self._expected_for_octets(answer, result, key))
            if result.valid:
                row.status.configure(text="POPRAWNIE", fg="#176a37")
                row.info.configure(text="Podsieć jest poprawna: adresy, maska i wielkość bloku są zgodne.",
                                   fg="#176a37")
            else:
                row.status.configure(text="DO POPRAWY", fg="#bb243a")
                row.info.configure(text=("  •  ".join(result.messages) if result.messages else
                                         "Najpierw podaj poprawny adres sieci i maskę, aby ocenić resztę."),
                                   fg="#a41d30")
        summary = f"Poprawnych podsieci: {report.correct_rows}/{len(self.rows)}. "
        if report.success:
            summary += "Wszystko poprawnie — zadanie zaliczone. "
        else:
            summary += "Czerwone pola wymagają poprawy; zielone oktety są poprawne. "
        if report.base and report.success:
            total = sum(row.subnet.num_addresses for row in report.rows if row.subnet is not None)
            summary += f"Przydzielono {total} z {report.base.num_addresses} adresów sieci bazowej."
        failures = report.parent_errors + report.global_errors
        if failures:
            summary += "  |  " + "  |  ".join(failures)
        self.summary_var.set(summary)
        self.after_idle(self._update_scroll)
        return report

    def clear_answers(self):
        for row in self.rows:
            for key in FIELD_NAMES:
                if key != "hosts":
                    row.put(key, "")
            row.clear_result()
        self.invalidate_result()
        self.canvas.yview_moveto(0)

    def show_solution(self):
        try:
            base = parse_base_network(*self._base_inputs())
            counts = [parse_host_count(row.get("hosts")) for row in self.rows]
            solution = generate_solution(base, counts)
        except VLSMError as exc:
            messagebox.showerror("Nie można wyznaczyć rozwiązania", str(exc), parent=self)
            return
        if any(row.get(key) for row in self.rows for key in FIELD_NAMES if key != "hosts"):
            if not messagebox.askyesno("Rozwiązanie wzorcowe",
                                      "Wypełnić pola rozwiązaniem wzorcowym? "
                                      "Zastąpi to dotychczasowe odpowiedzi.", parent=self):
                return
        for row, answer in zip(self.rows, solution):
            for key in FIELD_NAMES:
                if key != "hosts":
                    row.put(key, getattr(answer, key))
        self.check()
        self.summary_var.set("Pokazano przykładowy poprawny przydział VLSM. "
                             "Inny prawidłowy, bezkolizyjny podział również jest akceptowany.")
        self.canvas.yview_moveto(0)


def main():
    VLSMTrainer().mainloop()


if __name__ == "__main__":
    main()
