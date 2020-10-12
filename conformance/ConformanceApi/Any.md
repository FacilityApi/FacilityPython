# Any

```
{
  "string": "(string)",
  "boolean": (true|false),
  "double": (number),
  "int32": (integer),
  "int64": (integer),
  "decimal": (number),
  "bytes": "(base64)",
  "object": { ... },
  "error": { "code": ... },
  "data": { "string": ... },
  "enum": "(yes|no|maybe)",
  "array": { "string": ... },
  "map": { "string": ... },
  "result": { "string": ... }
}
```

| field | type | description |
| --- | --- | --- |
| string | string |  |
| boolean | boolean |  |
| double | double |  |
| int32 | int32 |  |
| int64 | int64 |  |
| decimal | decimal |  |
| bytes | bytes |  |
| object | object |  |
| error | error |  |
| data | [Any](Any.md) |  |
| enum | [Answer](Answer.md) |  |
| array | [AnyArray](AnyArray.md) |  |
| map | [AnyMap](AnyMap.md) |  |
| result | [AnyResult](AnyResult.md) |  |

<!-- DO NOT EDIT: generated by fsdgenpython -->