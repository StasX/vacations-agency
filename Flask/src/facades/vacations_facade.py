from flask import session, request
from models.user_model import UserModel
from models.client_errors import ValidationError
from models.vacation_model import VacationModel
from logic.vacations_logic import VacationsLogic
from utils.date_handler import DateHandler



class VacationsFacade:
    def __init__(self):
        self.logic = VacationsLogic()

    # Get all vacations
    def get_all_vacations(self):
        # Get id of current user
        current_user = session.get("current_user")
        user_id = current_user["id"]
        all_vacations = self.logic.get_all_vacations(user_id)
        all_vacations=list(map(DateHandler.format_vacation_dates,all_vacations))

        return all_vacations

    # Get one vacation
    def get_one_vacation(self, id):
        one_vacation = self.logic.get_one_vacation(id)

        return one_vacation

    # Add vacation
    def add_vacation(self):
        country = request.form.get("country")
        description = request.form.get("description")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        price = request.form.get("price")
        image = None
        if "image" in request.files: 
            image = request.files["image"]
        vacation = VacationModel(
            None, country, description, start_date, end_date, price, image)
        error = vacation.validate_insert()
        if error:
            raise ValidationError(error, vacation)
        self.logic.add_vacation(vacation)

    # Update vacation
    def update_vacation(self, id):
        country = request.form.get("country")
        description = request.form.get("description")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        price = request.form.get("price")
        image = request.files.get("image")
        vacation = VacationModel(
            id, country, description, start_date, end_date, price, image)
        error = vacation.validate_update()
        print(error)
        if error:
            raise ValidationError(error, vacation)
        last_row_id = self.logic.update_vacation(vacation)

    # Delete vacation
    def delete_vacation(self, id):
        row_count = self.logic.delete_vacation(id)
        return row_count
    # Get current vacation image
    def get_old_image(self,id):
        return self.logic.get_old_image_name(id)

    # Free resources
    def close(self):
        self.logic.close()

    def __enter__(self):
        return self

    def __exit__(self, ex_type, ex_value, ex_trace):
        self.close()
