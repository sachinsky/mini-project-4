"""City name to IATA airport code mapping for cities in the flights dataset."""

CITY_TO_CODE: dict[str, str] = {
    # Major metros
    "delhi": "DEL",
    "new delhi": "DEL",
    "mumbai": "BOM",
    "bombay": "BOM",
    "bengaluru": "BLR",
    "bangalore": "BLR",
    "chennai": "MAA",
    "madras": "MAA",
    "hyderabad": "HYD",
    "kolkata": "CCU",
    "calcutta": "CCU",
    "pune": "PNQ",
    "goa": "GOI",
    "nagpur": "NAG",
    # Other airports in dataset
    "ahmedabad": "AMD",
    "kochi": "COK",
    "cochin": "COK",
    "jaipur": "JAI",
    "varanasi": "VNS",
    "banaras": "VNS",
    "patna": "PAT",
    "chandigarh": "IXC",
}

# Allow querying by IATA code directly (lowercase key -> uppercase code)
for code in {"amd", "blr", "bom", "ccu", "cok", "del", "goi", "hyd", "ixc", "jai", "maa", "nag", "pat", "pnq", "vns"}:
    CITY_TO_CODE[code] = code.upper()

_ROUTE_SKIP_WORDS = frozenset({
    "a", "an", "any", "date", "earliest", "flight", "flights", "is", "me",
    "next", "route", "show", "status", "the", "upcoming", "what",
})


def resolve_city(name: str) -> str | None:
    normalized = name.strip().lower()
    if not normalized:
        return None
    if len(normalized) == 3 and normalized.isalpha():
        return normalized.upper()
    return CITY_TO_CODE.get(normalized)


def is_route_skip_word(word: str) -> bool:
    return word.lower() in _ROUTE_SKIP_WORDS
