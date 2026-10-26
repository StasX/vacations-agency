from flask import Blueprint, render_template, request, redirect, url_for, request, session, send_file
from models.client_errors import ValidationError, AuthError
from facades.auth_facade import AuthFacade
from facades.vacations_facade import VacationsFacade
from facades.countries_facade import CountriesFacade
from models.role_model import RoleModel
from utils.image_handler import ImageHandler


vacations_blueprint = Blueprint("vacations_view", __name__)

vacations_facade = VacationsFacade()


# Get list of all vacations
@vacations_blueprint.route("/vacations")
def list():
    try:
        # Block anonymous
        auth_facade = AuthFacade()
        auth_facade.block_anonymous()

        #  Get all vacations
        vacations_facade = VacationsFacade()
        all_vacations = vacations_facade.get_all_vacations()
        # If user is Admin display admin's template
        current_user = session.get("current_user")
        if current_user.get("role") == RoleModel.Admin.value:
            return render_template("admin_vacations.html", vacations=all_vacations)
        # Other way display User's template
        return render_template("user_vacations.html", vacations=all_vacations)
    except AuthError:
        return redirect(url_for("auth_view.login"))


# Get image file
@vacations_blueprint.route("/vacations/images/<string:image_name>")
def get_image(image_name):
    try:
        # Block anonymous. (I assume that just logged-in users can see images)
        auth_facade = AuthFacade()
        auth_facade.block_anonymous()
        # Get image path
        image_path = ImageHandler.get_image_path(image_name)
        # Send file to front-end
        return send_file(image_path)
    except AuthError:
        return redirect(url_for('auth_view.login'))


# Add vacation
@vacations_blueprint.route("/vacations/add", methods=["GET", "POST"])
def insert():
    try:
        # block non Admins
        auth_facade = AuthFacade()
        auth_facade.block_non_admin()

        # If method GET render template
        if request.method == "GET":
            countries_facade = CountriesFacade()
            countries = countries_facade.get_all_countries()
            return render_template("add_vacation.html", countries=countries, error={})

        # Other way add  vacation
        vacations_facade = VacationsFacade()
        vacations_facade.add_vacation()

        # Redirect to vacations page
        return redirect(url_for("vacations_view.list"))
    except AuthError:
        return redirect(url_for('auth_view.login'))
    except ValidationError as err:
        countries_facade = CountriesFacade()
        countries = countries_facade.get_all_countries()
        return render_template("add_vacation.html", countries=countries, error=err)


@vacations_blueprint.route("/vacations/<int:id>/edit", methods=["GET", "POST"])
def edit(id):

    try:
        # Block non Admins
        auth_facade = AuthFacade()
        auth_facade.block_non_admin()
        vacations_facade = VacationsFacade()
        if request.method == "GET":
            # Get vacation by id
            one_vacation = vacations_facade.get_one_vacation(id)
            # Get list of countries
            countries_facade = CountriesFacade()
            countries = countries_facade.get_all_countries()
            return render_template("edit_vacations.html", vacation=one_vacation, countries=countries)
        vacations_facade.update_vacation(id)
        return redirect(url_for("vacations_view.list"))
    except AuthError:
        return redirect(url_for('auth_view.login'))
    except ValidationError as err:
        # Get list of countries
        countries_facade = CountriesFacade()
        countries = countries_facade.get_all_countries()
        country_id = err.model.country
        filtered_countries = [
            country for country in countries if str(country["id"]) == str(country_id)]
        if not len(filtered_countries):
            # If country not exists  reset country
            selected_country = "Select country"
            err.model.country = None
        else:
            selected_country = filtered_countries[0]["name"]
        # Fix country id and country name
        err.model.country_id, err.model.country = err.model.country, selected_country
        # Get current vacation image
        vacations_facade = VacationsFacade()
        err.model.image = vacations_facade.get_old_image(id)
        return render_template("edit_vacations.html", error=err.message, vacation=err.model, countries=countries)


@vacations_blueprint.route("/vacations/<int:id>/delete", methods=["POST"])
def delete(id):
    try:
        # Block non Admins
        auth_facade = AuthFacade()
        auth_facade.block_non_admin()
        # Delete vacation
        vacations_facade = VacationsFacade()
        vacations_facade.delete_vacation(id)
        # Redirect to vacations page
        return redirect(url_for("vacations_view.list"))
    except AuthError:
        return redirect(url_for('auth_view.login'))
