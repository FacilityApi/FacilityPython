
import inspect
import json
import logging
import re
import typing

from facilitypython import facility

from conformance import conformance_api as api


class ConformanceTester:

    def __init__(self, client: facility.ClientBase, *, verbose: bool = True):
        self.client = client
        self.logger = logging.getLogger(self.__class__.__name__)
        if verbose:
            self.logger.setLevel(logging.DEBUG)
        self.dtos = {
            cls.__name__: cls for cls in
            facility.DTO.__subclasses__()
        }
        self.enums = {
            cls.__name__: cls for cls in
            facility.Enum.__subclasses__()
        }

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

    def get_from_data(self, data: typing.Optional[dict], annotation):
        if data is None or annotation is None:
            return data
        if isinstance(annotation, str):
            annotation_ = self.dtos.get(annotation) or self.enums.get(annotation)
            if annotation_ is None:
                raise ValueError(f"Unknown type annotation: {annotation}")
            annotation = annotation_
        if inspect.isclass(annotation):
            if issubclass(annotation, facility.DTO):
                return annotation.from_data(data)
            if issubclass(annotation, facility.Enum) and isinstance(data, str):
                return annotation.get(data)
        if isinstance(annotation, typing.ForwardRef):
            origin = getattr(annotation, "__forward_arg__", None)
            if origin:
                return self.get_from_data(data, origin)
        if isinstance(annotation, typing._GenericAlias):
            origin = getattr(annotation, "__origin__", None)
            if inspect.isclass(origin):
                if issubclass(origin, facility.DTO):
                    return origin.from_data(data)
                if issubclass(origin, facility.Enum) and isinstance(data, str):
                    return origin.get(data)
            args = getattr(annotation, "__args__", [])
            if origin is list:
                if len(args) != 1:
                    raise ValueError(f"Invalid generic data type: {annotation}")
                if not isinstance(data, list):
                    raise ValueError(f"Expected {annotation} not {data}")
                sub_type = args[0]
                return [self.get_from_data(x, sub_type) for x in data]
            if origin is dict:
                if len(args) != 2:
                    raise ValueError(f"Invalid generic data type: {annotation}")
                sub_type = args[1]
                if not isinstance(data, dict):
                    raise ValueError(f"Expected {annotation} not {data}")
                return {k: self.get_from_data(v, sub_type) for k, v in data.items()}
            if origin is typing.Union:
                for arg in args:
                    if inspect.isclass(arg):
                       if issubclass(arg, facility.DTO):
                          return arg.from_data(data)
                       if issubclass(arg, facility.Enum) and isinstance(data, str):
                          return arg.get(data)
            raise ValueError(f"Data mismatches generic data type: {annotation} <= {data}")
        if annotation in (bytes, bytearray):
            return bytes(data)
        return data

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
        kwargs = {
            key: None
            for key in spec.kwonlyargs or []
            if key not in (spec.kwonlydefaults or [])
        }
        for key, actual in item["request"].items():
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
            try:
                kwargs[key] = self.get_from_data(actual, annotation)
            except:
                self.logger.exception(f"{test_name}: method \"{method_name}\" parameter \"{key}\" invalid value: {actual}")
                return False
        try:
            result = method(**kwargs)
        except:
            self.logger.exception(f"{test_name}: method \"{method_name}\" call failed")
            return False
        if result.error and item.get("error") is None:
            self.logger.warning(f"{test_name} got unexpected error: {result.error}")
            return False
        if item.get("error") is not None:
            expected = facility.Result(error=facility.Error.from_data(item["error"]))
        elif item.get("response") is not None:
            if not result.value:
                self.logger.warning(f"{test_name} missing expected response: {item['response']}")
                return False
            expected = facility.Result(value=result.value.__class__.from_data(item["response"]))
        elif all(x is None for x in result.value.to_data().values()):
            return True
        else:
            self.logger.warning(f"{test_name} invalid, no expectation indicated")
            return False
        if result.to_data() == expected.to_data():
            return True
        self.logger.warning(f"{test_name} had incorrect result")
        self.compare_dtos(test_name, "result", expected, result)
        return False

    def compare_dtos(self, test_name: str, prefix: str, expected: facility.DTO, actual: facility.DTO):
        for key, expected_value in expected.__dict__.items():
            actual_value = getattr(actual, key, None)
            if expected_value == actual_value:
                continue
            if isinstance(expected_value, facility.DTO) and isinstance(actual_value, facility.DTO):
                self.compare_dtos(test_name, f"{prefix}.{key}", expected_value, actual_value)
            else:
                self.logger.debug(f"{test_name} {prefix}.{key} expected: {repr(expected_value)} actual: {repr(actual_value)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = api.Client("http://localhost:4117/")
    tester = ConformanceTester(client)
    tester.run("tests.json")
