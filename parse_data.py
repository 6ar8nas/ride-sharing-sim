import json

from utils import Area


def parse_city_data(
    file_path: str, city_name: str
) -> tuple[list[Area], list[Area], str]:
    try:
        with open(file_path, "r") as f:
            data_json = json.load(f)

        center_areas: list[Area] = []
        residential_areas: list[Area] = []
        filters: str = ""

        for city_data in data_json:
            if city_data["city"] != city_name:
                continue

            for area in city_data["central_areas"]:
                center_areas.append(
                    Area((area["center"]["x"], area["center"]["y"]), area["radius"])
                )

            for area in city_data["residential_areas"]:
                residential_areas.append(
                    Area((area["center"]["x"], area["center"]["y"]), area["radius"])
                )

            filters = city_data["osm_filters"]

            return (center_areas, residential_areas, filters)

        print(f"Error: City {city_name} data not defined at {file_path}")
        return [], [], []

    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return [], []
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {file_path}")
        return [], []
    except KeyError as e:
        print(f"Error: Missing key in JSON: {e}")
        return [], []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return [], []
