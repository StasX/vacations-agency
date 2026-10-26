from decimal import Decimal, InvalidOperation

from utils.date_handler import DateHandler


class VacationModel:
    def __init__(self, id, country, description, start_date, end_date, price, image):
        self.id = id
        self.country = country
        self.description = description
        self.start_date = start_date
        self.end_date = end_date
        self.price = price
        self.image = image

    def validate_insert(self):
        if not self.country:
            return "Country not set."
        if not self.description:
            return "Missing description."
        if not self.start_date:
            return "Missing start date."
        if not self.end_date:
            return "Missing end date."
        if self.price is None or self.price == "":
            return "Missing price."
        if not self.image:
            return "Missing image."

        return self._validate_values(require_future_start=True)

    def validate_update(self):
        if not self.country:
            return "Country not set."
        if not self.description:
            return "Missing description."
        if not self.start_date:
            return "Missing start date."
        if not self.end_date:
            return "Missing end date."
        if self.price is None or self.price == "":
            return "Missing price."
        
        return self._validate_values(require_future_start=False)

    def _validate_values(self, require_future_start):
        if not (isinstance(self.country, str) and self.country.isnumeric()):
            return "Country is invalid"
        if not isinstance(self.description, str) or not self.description.strip():
            return "Description can't be empty"
        try:
            start = DateHandler.to_date(self.start_date)
        except (ValueError, TypeError):
            return "Start date is invalid."
        try:
            end = DateHandler.to_date(self.end_date)
        except (ValueError, TypeError):
            return "End date is invalid."
        if require_future_start and start <= DateHandler.now():
            return "Start of vacation should be in future"
        if start > end:
            return "Start of vacation can't be before vacation end"
        try:
            price = Decimal(str(self.price))
        except (InvalidOperation, ValueError, TypeError):
            return "Price is invalid."
        if not price.is_finite() or not 0 <= price <= 10000:
            return "Price is invalid."
        return None
