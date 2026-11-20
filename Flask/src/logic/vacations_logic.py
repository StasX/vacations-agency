import logging

from utils.dal import DAL
from utils.image_handler import ImageHandler
from utils.image_cleanup import enqueue_image_cleanup
from models.client_errors import ResourceNotFoundError


logger = logging.getLogger(__name__)


def discard_failed_upload(image_name, commit_started):
    if not image_name:
        return
    if commit_started:
        logger.warning("Keeping vacation image %r because the database commit outcome is unknown", image_name)
        return
    try:
        ImageHandler.delete_image(image_name)
    except Exception:
        logger.exception("Failed to discard vacation image %r after a database error", image_name)


class VacationsLogic:
    def __init__(self):
        self.dal = DAL()

    def get_all_vacations(self, user_id):
        sql = """SELECT 
                    vacations.id AS id,
                    countries.name AS country,
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
        if result is None:
            raise ResourceNotFoundError(id)
        return result

    def add_vacation(self, vacation):
        # Add image
        image_name = ImageHandler.save_image(vacation.image)
        # Add vacation
        sql = "INSERT INTO vacations(country_id, description, start_date, end_date, price, image) VALUES (%s, %s, %s, %s, %s, %s)"
        params = (vacation.country, vacation.description, vacation.start_date,
                  vacation.end_date, vacation.price, image_name)
        commit_started = False
        try:
            with self.dal.transaction():
                self.dal.insert(sql, params)
                commit_started = True
        except Exception:
            discard_failed_upload(image_name, commit_started)
            raise

    def update_vacation(self, vacation):
        uploaded_image = None
        commit_started = False
        try:
            with self.dal.transaction():
                old_image = self.get_old_image_name(vacation.id, for_update=True)
                uploaded_image = ImageHandler.save_image(vacation.image)
                image_name = uploaded_image or old_image
                sql = "UPDATE vacations SET country_id = %s, description = %s, start_date = %s, end_date = %s, price = %s, image = %s WHERE id = %s"
                params = (vacation.country, vacation.description, vacation.start_date,
                          vacation.end_date, vacation.price, image_name, vacation.id)
                if self.dal.update(sql, params) == 0:
                    self.get_one_vacation(vacation.id)
                if image_name != old_image:
                    enqueue_image_cleanup(self.dal, old_image)
                commit_started = True
        except Exception:
            discard_failed_upload(uploaded_image, commit_started)
            raise

    def delete_vacation(self, id):
        with self.dal.transaction():
            old_image = self.get_old_image_name(id, for_update=True)
            row_count = self.dal.delete("DELETE FROM vacations WHERE id = %s", (id,))
            if row_count == 0:
                raise ResourceNotFoundError(id)
            enqueue_image_cleanup(self.dal, old_image)
        return row_count

    def get_old_image_name(self, id, for_update=False):
        sql = "SELECT image FROM vacations WHERE id=%s"
        if for_update:
            sql += " FOR UPDATE"
        params = (id,)
        old_image_name = self.dal.get_scalar(sql, params)
        if old_image_name is None:
            raise ResourceNotFoundError(id)
        return old_image_name["image"]

    def close(self):
        self.dal.close()
