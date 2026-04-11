import csv
import io

# Map common column names (PT-BR and EN) to Lead model fields
COLUMN_MAP = {
    # PT-BR (matching model fields)
    "nome": "nome",
    "telefone": "telefone",
    "website": "website",
    "endereco": "endereco",
    "cidade": "cidade",
    "nicho": "nicho",
    "categoria": "categoria",
    "rating": "rating",
    "email": "email",
    # English aliases
    "name": "nome",
    "phone": "telefone",
    "address": "endereco",
    "city": "cidade",
    "niche": "nicho",
    "category": "categoria",
}


def parse_csv(file_content: str, encoding: str = "utf-8") -> tuple[list[dict], list[str]]:
    """Parse CSV content into lead dicts.

    Returns (leads, errors) where leads is a list of dicts with Lead model field names,
    and errors is a list of per-row error messages.
    """
    leads = []
    errors = []

    reader = csv.DictReader(io.StringIO(file_content))

    if not reader.fieldnames:
        return [], ["CSV vazio ou sem cabeçalho"]

    # Map CSV headers to model fields
    header_map = {}
    for header in reader.fieldnames:
        normalized = header.strip().lower()
        if normalized in COLUMN_MAP:
            header_map[header] = COLUMN_MAP[normalized]

    if "nome" not in header_map.values() and "name" not in [h.strip().lower() for h in reader.fieldnames]:
        return [], ["Coluna obrigatória 'nome' (ou 'name') não encontrada no CSV"]

    for row_num, row in enumerate(reader, start=2):  # start=2 because row 1 is header
        try:
            lead = {}
            for csv_col, model_field in header_map.items():
                value = row.get(csv_col, "").strip()
                if value:
                    lead[model_field] = value

            if not lead.get("nome"):
                errors.append(f"Linha {row_num}: campo 'nome' vazio, pulando")
                continue

            # Parse rating as float if present
            if "rating" in lead:
                try:
                    lead["rating"] = float(lead["rating"])
                except ValueError:
                    lead.pop("rating")

            leads.append(lead)
        except Exception as exc:
            errors.append(f"Linha {row_num}: {str(exc)[:120]}")

    return leads, errors
