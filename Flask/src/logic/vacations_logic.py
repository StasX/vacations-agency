from utils.dal import DAL
from utils.image_handler import ImageHandler
from models.vacation_model import VacationModel


class VacationsLogic:
    def __init__(self):
        self.dal = DAL()

    def get_all_vacations(self, user_id):
        sql = """SELECT 
                    vacations.id AS id,
                    countries.name,
                    vacations.description,
                    vacations.start_date,
                    vacations.end_date,
                    vacations.price,
                    vacations.image,
                    COUNT(likes.vacation_id) AS likes_count,
                    CASE WHEN EXISTS(SELECT 1 FROM likes WHERE likes.vacation_id=vacations.id AND likes.user_id=%s) THEN 1 ELSE 0 END AS liked
                FROM vacations 
                CROSS JOIN countries ON vacations.country_id = countries.id 
                LEFT JOIN likes ON vacations.id = likes.vacation_id
                GROUP BY
                    vacations.id,
                    countries.name,
                    vacations.description,
                    vacations.start_date,
                    vacations.end_date,
                    vacations.price,
                    vacations.image
                ORDER BY vacations.start_date"""
        params = (user_id,)
        return self.dal.get_table(sql, params)
    
    def get_one_vacation(self, id):
        sql = """SELECT V.id AS id, C.name as country, C.id AS country_id, V.description, V.start_date, V.end_date,V.price, V.image FROM vacations AS V JOIN countries AS C ON V.country_id = C.id WHERE V.id = %s ORDER BY start_date"""
        result = self.dal.get_scalar(sql, (id,))
        return result

    def add_vacation(self, vacation):
        # Add image
        image_name = ImageHandler.save_image(vacation.image)
        # Add vacation
        sql = "INSERT INTO vacations(country_id, description, start_date, end_date, price, image) VALUES (%s, %s, %s, %s, %s, %s)"
        params = (vacation.country, vacation.description, vacation.start_date,
                  vacation.end_date, vacation.price, image_name)
        try:
            self.dal.insert(sql, params)
        except Exception:
            ImageHandler.delete_image(image_name)
            raise

    def update_vacation(self, vacation):
        # Update image
        old_image = self.get_old_image_name(vacation.id)
        image_name = ImageHandler.save_image(vacation.image) or old_image
        # Update vacation
        sql = "UPDATE vacations SET country_id = %s, description = %s, start_date = %s, end_date = %s, price = %s, image = %s WHERE id = %s"
        params = (vacation.country, vacation.description,
                  vacation.start_date, vacation.end_date, vacation.price, image_name, vacation.id)
        try:
            self.dal.update(sql, params)
        except Exception:
            if image_name != old_image:
                ImageHandler.delete_image(image_name)
            raise
        if image_name != old_image:
            ImageHandler.delete_image(old_image)

    def delete_vacation(self, id):
        # Delete image
        old_image = self.get_old_image_name(id)
        # Delete vacation
        sql = "DELETE FROM vacations WHERE id = %s"
        params = (id,)
        row_count = self.dal.delete(sql, params)
        ImageHandler.delete_image(old_image)

    def get_old_image_name(self, id):
        sql = "SELECT image FROM vacations WHERE id=%s"
        params = (id,)
        old_image_name = self.dal.get_scalar(sql, params)
        return old_image_name["image"]

    def close(self):
        self.dal.close()
