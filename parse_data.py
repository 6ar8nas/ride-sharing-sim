import json


def parse_city_data(
    file_path: str, city_name: str
) -> tuple[
    list[tuple[tuple[float, float], float]], list[tuple[tuple[float, float], float]]
]:
    try:
        with open(file_path, "r") as f:
            data_json = json.load(f)

        center_areas: list[tuple[tuple[float, float], float]] = []
        residential_areas: list[tuple[tuple[float, float], float]] = []

        for city_data in data_json:
            if city_data["city"] != city_name:
                continue

            for area in city_data["central_areas"]:
                center = (area["center"]["x"], area["center"]["y"])
                radius = area["radius"]
                center_areas.append((center, radius))

            for area in city_data["residential_areas"]:
                center = (area["center"]["x"], area["center"]["y"])
                radius = area["radius"]
                residential_areas.append((center, radius))

        return center_areas, residential_areas

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
