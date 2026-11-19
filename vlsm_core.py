"""Logika ćwiczeń VLSM dla IPv4 (niezależna od GUI, tylko biblioteka standardowa)."""
from __future__ import annotations

from dataclasses import dataclass, field
import ipaddress
import re
from typing import Iterable

IPv4Address = ipaddress.IPv4Address
IPv4Network = ipaddress.IPv4Network


class VLSMError(ValueError):
    """Czytelny błąd danych zadania lub adresu IPv4."""


def parse_ipv4(value: str) -> IPv4Address:
    """IPv4: np. 192.168.1.2, 11000000.10101000.00000001.00000010, 32 bity."""
    s = str(value).strip()
    if not s:
        raise VLSMError("Nie podano adresu IPv4.")
    compact = re.sub(r"[\s_]", "", s)
    if re.fullmatch(r"[01]{32}", compact):
        return IPv4Address(int(compact, 2))
    if re.fullmatch(r"[01]{8}(?:\.[01]{8}){3}", compact):
        return IPv4Address(int(compact.replace(".", ""), 2))
    try:
        return IPv4Address(s)
    except ipaddress.AddressValueError as exc:
        raise VLSMError(
            "Niepoprawny IPv4. Użyj np. 192.168.1.0 lub "
            "11000000.10101000.00000001.00000000."
        ) from exc


def parse_prefix(value: str) -> int:
    """Prefiks /24, 24 lub maska dziesiętna/binarna (tylko maski ciągłe)."""
    s = str(value).strip()
    if not s:
        raise VLSMError("Nie podano maski.")
    if re.fullmatch(r"/?\d+", s) and not re.fullmatch(r"[01]{32}", s):
        prefix = int(s.lstrip("/"))
        if 0 <= prefix <= 32:
            return prefix
        raise VLSMError("Długość prefiksu musi mieścić się w zakresie 0–32.")
    mask = parse_ipv4(s)
    try:
        return IPv4Network(f"0.0.0.0/{mask}").prefixlen
    except ipaddress.NetmaskValueError as exc:
        raise VLSMError("Maska musi mieć nieprzerwany ciąg bitów 1, a potem 0.") from exc


def format_ipv4(address: IPv4Address | int, binary: bool = False) -> str:
    addr = IPv4Address(address)
    if binary:
        return ".".join(f"{b:08b}" for b in addr.packed)
    return str(addr)


def format_prefix(prefix: int, binary: bool = False) -> str:
    mask = IPv4Network(f"0.0.0.0/{prefix}").netmask
    return format_ipv4(mask, binary)


def parse_base_network(address: str, mask: str) -> IPv4Network:
    """Adres i maska w osobnych polach lub CIDR w polu adresu."""
    raw = str(address).strip()
    supplied_mask = str(mask).strip()
    if not raw:
        raise VLSMError("Podaj adres sieci bazowej.")
    if "/" in raw:
        parts = raw.split("/")
        if len(parts) != 2 or not parts[1]:
            raise VLSMError("Niepoprawny zapis CIDR sieci bazowej.")
        raw, inline_mask = parts
        inline_prefix = parse_prefix(inline_mask)
        if supplied_mask and parse_prefix(supplied_mask) != inline_prefix:
            raise VLSMError("Maska w adresie CIDR i osobnym polu jest różna.")
        prefix = inline_prefix
    else:
        prefix = parse_prefix(supplied_mask)
    ip = parse_ipv4(raw)
    try:
        return IPv4Network((int(ip), prefix), strict=True)
    except ValueError as exc:
        normalized = IPv4Network((int(ip), prefix), strict=False)
        raise VLSMError(
            f"Adres bazowy nie jest adresem sieci dla /{prefix}. "
            f"Początek tego bloku to {normalized.network_address}."
        ) from exc


def min_prefix_for_hosts(host_count: int) -> int:
    """Klasyczny IPv4: 2 adresy zarezerwowane, min. /30, bez /31 i /32."""
    if not isinstance(host_count, int) or isinstance(host_count, bool) or host_count < 1:
        raise VLSMError("Liczba urządzeń musi być dodatnią liczbą całkowitą.")
    required = max(4, host_count + 2)
    bits = (required - 1).bit_length()
    if bits > 32:
        raise VLSMError("Zbyt duża liczba urządzeń dla IPv4.")
    return 32 - bits


def host_capacity(prefix: int) -> int:
    return max(0, (1 << (32 - prefix)) - 2) if prefix <= 30 else 0


@dataclass(frozen=True)
class Answer:
    hosts: str
    network: str = ""
    mask: str = ""
    broadcast: str = ""
    first: str = ""
    last: str = ""
    allocated: str = ""       # Rozmiar bloku, wliczając sieć i broadcast.
    capacity: str = ""        # Liczba dostępnych adresów hostów.
    inverse_mask: str = ""    # Maska odwrócona (NOT); ćwiczona w widoku binarnym.


FIELD_NAMES = ("hosts", "network", "mask", "broadcast", "first", "last",
               "allocated", "capacity", "inverse_mask")
FIELD_LABELS = {
    "hosts": "Urządzenia", "network": "Adres sieci", "mask": "Maska",
    "broadcast": "Broadcast", "first": "Pierwszy host", "last": "Ostatni host",
    "allocated": "Przydzielone adresy", "capacity": "Dostępne hosty",
    "inverse_mask": "Negacja maski",
}


@dataclass
class RowResult:
    status: dict[str, str] = field(default_factory=lambda: {k: "unchecked" for k in FIELD_NAMES})
    messages: list[str] = field(default_factory=list)
    subnet: IPv4Network | None = None

    def good(self, name: str) -> None:
        if self.status[name] != "error":
            self.status[name] = "good"

    def error(self, name: str, msg: str) -> None:
        self.status[name] = "error"
        if msg and msg not in self.messages:
            self.messages.append(msg)

    @property
    def valid(self) -> bool:
        return all(self.status[k] == "good" for k in FIELD_NAMES)


@dataclass
class ValidationReport:
    rows: list[RowResult]
    parent_errors: list[str]
    global_errors: list[str]
    base: IPv4Network | None

    @property
    def correct_rows(self) -> int:
        return sum(row.valid for row in self.rows)

    @property
    def success(self) -> bool:
        return (bool(self.rows) and self.correct_rows == len(self.rows)
                and not self.parent_errors and not self.global_errors)


def parse_host_count(raw: str) -> int:
    s = str(raw).strip()
    if not re.fullmatch(r"\d+", s):
        raise VLSMError("Liczba urządzeń musi być dodatnią liczbą całkowitą.")
    count = int(s)
    min_prefix_for_hosts(count)
    return count


def required_size(hosts: int) -> int:
    return 1 << (32 - min_prefix_for_hosts(hosts))


def generate_solution(base: IPv4Network, host_counts: Iterable[int]) -> list[Answer]:
    """Wzorcowy przydział: malejąco według rozmiaru bloku, bez nakładania."""
    counts = list(host_counts)
    if not counts:
        raise VLSMError("Brak podsieci.")
    sizes = [required_size(count) for count in counts]
    if sum(sizes) > base.num_addresses:
        raise VLSMError(
            f"Za mała sieć bazowa: potrzeba {sum(sizes)} adresów, "
            f"a sieć {base} ma tylko {base.num_addresses}."
        )
    cursor = int(base.network_address)
    result: list[Answer | None] = [None] * len(counts)
    for idx in sorted(range(len(counts)), key=lambda i: (-sizes[i], i)):
        size = sizes[idx]
        cursor = ((cursor + size - 1) // size) * size
        prefix = min_prefix_for_hosts(counts[idx])
        net = IPv4Network((cursor, prefix), strict=True)
        if not net.subnet_of(base):
            raise VLSMError("Nie udało się zmieścić podsieci w sieci bazowej.")
        result[idx] = Answer(
            hosts=str(counts[idx]), network=str(net.network_address),
            mask=format_prefix(prefix), broadcast=str(net.broadcast_address),
            first=str(IPv4Address(cursor + 1)),
            last=str(IPv4Address(int(net.broadcast_address) - 1)),
            allocated=str(net.num_addresses), capacity=str(host_capacity(prefix)),
            inverse_mask=str(net.hostmask),
        )
        cursor += size
    return [item for item in result if item is not None]


def check_answers(base_address: str, base_mask: str, answers: Iterable[Answer],
                  strict_vlsm: bool = True, require_counts: bool = False,
                  require_inverse_mask: bool = False) -> ValidationReport:
    entries = list(answers)
    parent_errors: list[str] = []
    global_errors: list[str] = []
    base: IPv4Network | None = None
    try:
        base = parse_base_network(base_address, base_mask)
    except VLSMError as exc:
        parent_errors.append(str(exc))

    rows: list[RowResult] = []
    counts: list[int | None] = []
    for index, entry in enumerate(entries, start=1):
        result = RowResult()
        rows.append(result)
        hosts: int | None = None
        try:
            hosts = parse_host_count(entry.hosts)
            result.good("hosts")
        except VLSMError as exc:
            result.error("hosts", f"Liczba urządzeń: {exc}")
        counts.append(hosts)

        prefix: int | None = None
        try:
            prefix = parse_prefix(entry.mask)
            if prefix > 30:
                result.error("mask", "W ćwiczeniu używamy podsieci /0–/30 (z broadcastem i hostami).")
            else:
                result.good("mask")
        except VLSMError as exc:
            result.error("mask", f"Maska: {exc}")

        addr: IPv4Address | None = None
        try:
            addr = parse_ipv4(entry.network)
            result.good("network")
        except VLSMError as exc:
            result.error("network", f"Adres sieci: {exc}")

        other_addresses: dict[str, IPv4Address | None] = {}
        for field_name in ("broadcast", "first", "last"):
            try:
                other_addresses[field_name] = parse_ipv4(getattr(entry, field_name))
            except VLSMError as exc:
                other_addresses[field_name] = None
                result.error(field_name, f"{FIELD_LABELS[field_name]}: {exc}")

        if prefix is not None and hosts is not None and prefix <= 30:
            capacity = host_capacity(prefix)
            min_prefix = min_prefix_for_hosts(hosts)
            if hosts > capacity:
                result.error("mask", f"Maska /{prefix} mieści {capacity} hostów; potrzebujesz {hosts} (co najmniej /{min_prefix}).")
            elif strict_vlsm and prefix != min_prefix:
                result.error("mask", f"Nieoptymalna maska /{prefix}: dla {hosts} urządzeń najmniejszy wystarczający blok to /{min_prefix}.")

        # Pola liczbowe: wielkość zarezerwowanego bloku (np. /26 -> 64)
        # i liczba adresów możliwych do przypisania hostom (/26 -> 62).
        for name in ("allocated", "capacity"):
            value = getattr(entry, name).strip()
            if not value and not require_counts:
                result.good(name)  # Kompatybilność z wcześniejszymi zadaniami.
                continue
            if not value:
                result.error(name, f"{FIELD_LABELS[name]}: uzupełnij liczbę.")
                continue
            if not re.fullmatch(r"\d+", value):
                result.error(name, f"{FIELD_LABELS[name]}: wpisz nieujemną liczbę całkowitą.")
                continue
            if prefix is not None and prefix <= 30:
                expected_number = (1 << (32 - prefix)) if name == "allocated" else host_capacity(prefix)
                if int(value) == expected_number:
                    result.good(name)
                else:
                    result.error(name, f"{FIELD_LABELS[name]}: wpisano {value}, prawidłowo {expected_number}.")

        # Dokument: NOT(maski), następnie adres sieci OR negacja maski.
        raw_inverse = entry.inverse_mask.strip()
        if not require_inverse_mask:
            # W trybie dziesiętnym to pole jest ukryte; jego poprzednia
            # (również błędna) wartość nie może blokować zaliczenia.
            result.good("inverse_mask")
        else:
            try:
                inverse_address = parse_ipv4(raw_inverse)
            except VLSMError as exc:
                result.error("inverse_mask", f"Negacja maski: {exc}")
            else:
                if prefix is not None:
                    inverse_expected = IPv4Network((0, prefix)).hostmask
                    if inverse_address == inverse_expected:
                        result.good("inverse_mask")
                    else:
                        result.error("inverse_mask", "Negacja maski: wpisano "
                                     f"{inverse_address}, prawidłowo {inverse_expected}.")

        if addr is not None and prefix is not None:
            net = IPv4Network((int(addr), prefix), strict=False)
            if net.network_address != addr:
                result.error("network", f"Adres {addr} nie jest początkiem podsieci /{prefix}. Początek: {net.network_address}.")
            elif prefix <= 30:
                result.subnet = net
                if base is not None and not net.subnet_of(base):
                    result.error("network", f"Podsieć {net} wychodzi poza sieć bazową {base}.")
                    result.error("mask", "Maska/adres nie mieszczą się w sieci bazowej.")

            if prefix <= 30 and net.network_address == addr:
                expected = {
                    "broadcast": net.broadcast_address,
                    "first": IPv4Address(int(net.network_address) + 1),
                    "last": IPv4Address(int(net.broadcast_address) - 1),
                }
                for key, correct in expected.items():
                    if other_addresses[key] is not None:
                        if other_addresses[key] == correct:
                            result.good(key)
                        else:
                            result.error(key, f"{FIELD_LABELS[key]}: wpisano {other_addresses[key]}, prawidłowo {correct}.")
        # Gdy nie można ustalić sieci i maski, pozostałe poprawne składniowo
        # adresy są nierozstrzygnięte, a nie błędnie uznane za prawidłowe.

    if base is not None and all(count is not None for count in counts):
        total_required = sum(required_size(count) for count in counts if count is not None)
        if total_required > base.num_addresses:
            global_errors.append(
                f"Zadanie niemożliwe do wykonania: minimalne podsieci potrzebują "
                f"{total_required} adresów, a {base} udostępnia {base.num_addresses}."
            )

    # Sprawdzanie par i konfliktów adresacji; nie narzucamy kolejności przydziału.
    for i in range(len(rows)):
        a = rows[i].subnet
        if a is None:
            continue
        for j in range(i + 1, len(rows)):
            b = rows[j].subnet
            if b is not None and a.overlaps(b):
                msg = f"Nakładanie podsieci: #{i + 1} ({a}) oraz #{j + 1} ({b})."
                rows[i].error("network", msg)
                rows[j].error("network", msg)
                rows[i].error("mask", "Sprawdź zakresy i wielkość podsieci.")
                rows[j].error("mask", "Sprawdź zakresy i wielkość podsieci.")

    return ValidationReport(rows, parent_errors, global_errors, base)
