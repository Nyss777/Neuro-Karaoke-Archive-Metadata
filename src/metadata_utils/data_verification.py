import re
from datetime import date, datetime

V1_VERSION_START = date(2023, 1, 3)
V1_VERSION_END = date(2023, 5, 17)

V2_VERSION_START = date(2023, 5, 27)
V2_VERSION_END = date(2023, 6, 8)

V3_VERSION_START = date(2023, 6, 21)

OLDEST_DATE_ALLOWED = V1_VERSION_START

class ValidationError(Exception):
    pass

def _validate_disc_number(payload: dict[str, str]) -> None:
    d_n = payload['disc_number']
    if not d_n:
        raise ValidationError("No disc number!")
    elif d_n not in ('1', '2', '3', '4', '5', '6', '7', '8', '9', '66'):
        raise ValidationError("Invalid disc number!")

def _validate_track(payload: dict[str, str]) -> None:
    track = payload['track']
    track_number = total_track = None

    if not track:
        raise ValidationError("Missing track number!")
    
    if '/' in track:
        track_number, total_track = track.split('/')
        if not (track_number.isdigit() and total_track.isdigit()):
            raise ValidationError("Invalid track number!")
        elif int(track_number) > int(total_track):
            raise ValidationError("Invalid track number!")
        elif int(track_number) == 0 or int(total_track) == 0:
            raise ValidationError("Invalid track number!")

    elif (not track.isdigit()) or (int(track) == 0):
        raise ValidationError("Invalid track number!") 
        
def _validate_date(payload: dict[str, str]) -> date:
    #   validate dates too old
    #   validate future dates
    #   validate specific format
    today = date.today()
    input_date = payload['date']

    if not re.match(r'^\d{4}-\d{2}-\d{2}$', input_date):
        raise ValidationError("Invalid date format! Use YYYY-MM-DD (e.g., 2025-06-17)")

    try:
        input_date = datetime.strptime(input_date, "%Y-%m-%d").date()
        if input_date > today:
            raise ValidationError("Future dates are not allowed!")
        elif input_date < OLDEST_DATE_ALLOWED:
            raise ValidationError("Input date is too old!")

    except ValueError:
        raise ValidationError("Invalid date!")       
    
    else:
        return input_date

def _validate_version(payload: dict[str, str]) -> tuple[str, str | None]:
    major_version = minor_version = None
    version = payload['version']
    if not version:
        raise ValidationError("No version!")

    if '.' in version:
        major_version, minor_version = version.split('.')
    else:
        major_version = version

    if major_version not in ('1', '2', '3') or minor_version not in (None, '2', '3', '4'):
        raise ValidationError("Invalid version!")
    
    return major_version, minor_version

def _validate_version_in_timeframe(payload: dict[str, str], major_version: str, date_input: date) -> None:
    # Since both the date and the version validation were already passed,
    # it is assumed they have valid values
    cover_singer = payload["cover_artist"]

    if cover_singer != "Neuro":
        return

    if major_version == '1' and (date_input < V1_VERSION_START or date_input > V1_VERSION_END):
        raise ValidationError("Neuro V1 ended 2023-05-17!")
    elif major_version == '2' and (date_input < V2_VERSION_START or date_input > V2_VERSION_END):
        raise ValidationError("Neuro V2 ended 2023-06-08!")
    elif major_version == '3' and (date_input < V3_VERSION_START):
        raise ValidationError("Neuro V3 started 2023-06-21!")

def validate_payload(payload: dict[str, str]) -> bool:

    _validate_disc_number(payload)

    _validate_track(payload)

    input_date = _validate_date(payload)

    version_info = _validate_version(payload)

    _validate_version_in_timeframe(payload, version_info[0], input_date)

    if payload['cover_artist'] == "Evil & Neuro":
        raise ValidationError("Wrong twin order!")

    if payload['special'] not in ('0', '1'):
        raise ValidationError("Invalid Special! It must be either a '0' or an '1'!")

    return True