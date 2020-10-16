
import inspect
import json
import logging
import re
from typing import Callable

import facility

from conformance import conformance_api as api


class ConformanceTester:

    def __init__(self, client: facility.ClientBase):
        self.client = client
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self, json_path: str) -> int:
        with open(json_path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        successes = errors = 0
        for item in data.get("tests", []):
            ok = self.test(item)
            if ok:
                successes += 1
            else:
                errors += 1
        self.logger.info(f"passed: {successes}")
        self.logger.info(f"failed: {errors}")
        if errors == 0 != successes:
            self.logger.info(f"SUCCESS")
        return errors

    def camel_to_pascal_case(self, name: str) -> str:
        return name[0].upper() + name[1:]

    def snake_case(self, name: str) -> str:
        return re.sub(r'([a-z])([A-Z])', r'\1_\2', name).lower()

    def test(self, item: dict) -> bool:
        test_name = item['test']
        self.logger.info(f"testing {test_name}")
        method_name = self.snake_case(item["method"])
        if not hasattr(self.client, method_name) and hasattr(self.client, f"{method_name}_"):
            method_name = f"{method_name}_"
        method = getattr(self.client, method_name, None)
        if not callable(method):
            self.logger.error(f"{test_name}: method not found: \"{method_name}\"")
            return False
        spec = inspect.getfullargspec(method)
        kwargs = dict()
        for key, value in item["request"].items():
            keys = [key, self.snake_case(key)]
            keys.append(f"{keys[1]}_")
            key = None
            for key_ in keys:
                if key_ in spec.kwonlyargs:
                    key = key_
                    break
            if key is None:
                self.logger.error(f"{test_name}: method \"{method_name}\" does not expect parameter: \"{key}\"")
                return False
            annotation = spec.annotations[key]
            if inspect.isclass(annotation) and issubclass(annotation, facility.DTO):
                try:
                    value = annotation.from_data(value)
                except:
                    self.logger.exception(f"{test_name}: method \"{method_name}\" parameter \"{key}\" invalid value: {value}")
                    return False
            kwargs[key] = value
        for key in spec.kwonlyargs or []:
            if key not in (spec.kwonlydefaults or []):
                kwargs[key] = None
        try:
            response = method(**kwargs)
        except:
            self.logger.exception(f"{test_name}: method \"{method_name}\" call failed")
            return False
        # TODO: check response
        return True

    def map_method_field(self, method: Callable, field: str) -> str:
        return field


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = api.Client("http://localhost:4117/")
    tester = ConformanceTester(client)
    tester.run("tests.json")
