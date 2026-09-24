"""The stats on every card, and which direction wins."""

from dataclasses import dataclass

# Electric cars get a petrol-equivalent consumption, the way European comparisons do it:
# one litre of petrol holds about 8.9 kWh of energy.
PETROL_KWH_PER_LITRE = 8.9


@dataclass(frozen=True)
class Stat:
    key: str
    label: str
    unit: str
    higher_wins: bool
    icon: str

    def value(self, car: dict) -> float:
        if self.key == "jare":
            return car["jaar_einde"] - car["jaar_begin"] + 1
        if self.key == "verbruik_l100" and car.get("kwh_100km"):
            return round(car["kwh_100km"] / PETROL_KWH_PER_LITRE, 1)
        return car[self.key]

    def display(self, car: dict) -> str:
        if self.key == "jare":
            years = self.value(car)
            span = str(car["jaar_begin"]) if years == 1 else f"{car['jaar_begin']}–{car['jaar_einde']}"
            return f"{span} · {years} jaar"
        if self.key == "enjin_cc" and not car["enjin_cc"]:
            return "⚡ Elektries"
        v = self.value(car)
        if self.key == "verbruik_l100" and car.get("kwh_100km"):
            return f"⚡ {v:.1f} {self.unit}".replace(".", ",")
        text = f"{v:.1f}".replace(".", ",") if isinstance(v, float) else f"{v:,}".replace(",", " ")
        return f"{text} {self.unit}"

    @property
    def hint(self) -> str:
        return "hoër wen ⬆️" if self.higher_wins else "laer wen ⬇️"


STATS = [
    Stat("topspoed_kmh", "Topspoed", "km/h", True, "🏁"),
    Stat("nul_tot_100_s", "0–100 km/h", "s", False, "🚀"),
    Stat("kwartmyl_s", "Kwartmyl", "s", False, "🛣️"),
    Stat("krag_kw", "Krag", "kW", True, "💪"),
    Stat("wringkrag_nm", "Wringkrag", "Nm", True, "🌀"),
    Stat("massa_kg", "Massa", "kg", False, "⚖️"),
    Stat("jare", "Produksiejare", "", True, "📅"),
    Stat("enjin_cc", "Enjingrootte", "cc", True, "🔧"),
    Stat("verbruik_l100", "Brandstof", "l/100 km", False, "⛽"),
]
BY_KEY = {s.key: s for s in STATS}
