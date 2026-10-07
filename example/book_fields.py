"""Book form fields, shared by the Form View tab and the edit modal.

Runs in the browser. The store keeps publication dates as the seed has them,
M/D/YYYY with no leading zeros ("9/16/2006"), but wapyt's `date` field is the
browser's native picker, which reads and writes ISO dates ("2006-09-16"). The
two helpers below convert at the form boundary so a save never rewrites the
stored format.
"""
from wapyt import FieldConfig


def book_fields(languages=()):
    """The editable book fields, in display order."""
    return [
        FieldConfig(id="title", label="Title", span=2),
        FieldConfig(id="authors", label="Authors", span=2),
        # A rating is a bounded number, so a slider reads better than a text
        # box. Ratings carry two decimals, hence the 0.01 step.
        FieldConfig(id="average_rating", label="Rating", type="range",
                    min=0, max=5, step=0.01),
        FieldConfig(id="publication_date", label="Publication date", type="date"),
        FieldConfig(id="isbn13", label="ISBN"),
        # Language is a closed set drawn from the catalog; the options are
        # replaced once the dataset arrives (Form.set_field_options).
        FieldConfig(id="language_code", label="Language", type="combo",
                    options=list(languages), placeholder="Select..."),
        FieldConfig(id="num_pages", label="Pages", type="number", min=0),
        FieldConfig(id="ratings_count", label="Rating count", type="number", min=0),
        FieldConfig(id="text_reviews_count", label="Text reviews", type="number", min=0),
        FieldConfig(id="publisher", label="Publisher"),
    ]


def to_iso_date(value):
    """'9/16/2006' -> '2006-09-16'. Anything unparseable passes through."""
    try:
        month, day, year = (int(part) for part in str(value).split("/"))
    except (TypeError, ValueError):
        return value
    return f"{year:04d}-{month:02d}-{day:02d}"


def from_iso_date(value):
    """'2006-09-16' -> '9/16/2006', the store's format."""
    try:
        year, month, day = (int(part) for part in str(value).split("-"))
    except (TypeError, ValueError):
        return value
    return f"{month}/{day}/{year}"


def record_to_form(record):
    """A store record as form values: no id, ISO date."""
    values = {key: value for key, value in dict(record or {}).items() if key != "id"}
    if values.get("publication_date"):
        values["publication_date"] = to_iso_date(values["publication_date"])
    return values


def form_to_record(values):
    """Form values as store fields: the date back in M/D/YYYY."""
    fields = dict(values or {})
    if fields.get("publication_date"):
        fields["publication_date"] = from_iso_date(fields["publication_date"])
    return fields
