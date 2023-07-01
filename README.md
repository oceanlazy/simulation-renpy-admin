# Simulation admin
This project provides an easy way to create characters, places and other objects for `simulation-renpy` project.

## Prerequisites
- Python 3.6+
- installed packages from `requirements.txt` using `pip`

## Using
- set the `EXPORT_DIR` in `base/settings.py` to your `renpy` project.
- run project locally `python manage.py runserver`
- go to http://127.0.0.1:8000/ and make changes
- if you have added new characters, run `python manage.py build_homes` and `build_relationships` commands
- export modified data to your game by running `python manage.py db_to_json`