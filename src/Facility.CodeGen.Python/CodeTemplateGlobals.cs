using System.Collections;
using System.Net;
using System.Text.RegularExpressions;
using Facility.Definition;
using Facility.Definition.CodeGen;
using Facility.Definition.Http;

namespace Facility.CodeGen.Python
{
	internal sealed class CodeTemplateGlobals
	{
		public CodeTemplateGlobals(PythonGenerator generator, ServiceInfo serviceInfo, HttpServiceInfo? httpServiceInfo)
		{
			Service = serviceInfo;
			HttpService = httpServiceInfo;
			CodeGenCommentText = CodeGenUtility.GetCodeGenComment(generator.GeneratorName ?? "");
		}

		public ServiceInfo Service { get; }

		public HttpServiceInfo? HttpService { get; }

		public string CodeGenCommentText { get; }

		public string KindName(ServiceTypeKind kind) => kind.ToString();

		public HttpElementInfo? GetHttp(ServiceMethodInfo methodInfo) =>
			HttpService?.Methods.FirstOrDefault(x => x.ServiceMethod == methodInfo);

		public ServiceTypeInfo? GetFieldType(ServiceFieldInfo field) => Service.GetFieldType(field);

		public bool IsRequired(HttpFieldInfo field) => field is HttpBodyFieldInfo || field is HttpPathFieldInfo || field.ServiceField.IsRequired;

		public IEnumerable<HttpFieldInfo> Fields(HttpMethodInfo methodInfo)
		{
			var foo = methodInfo.RequestHeaderFields.Cast<HttpFieldInfo>().Concat(methodInfo.PathFields.Cast<HttpFieldInfo>());
			if (methodInfo.RequestBodyField != null)
				foo = foo.Append(methodInfo.RequestBodyField);
			foo = foo.Concat(methodInfo.QueryFields.Cast<HttpFieldInfo>()).Concat(methodInfo.RequestNormalFields.Cast<HttpFieldInfo>());
			return foo;
		}

		public static string RenderFieldTypeClass(ServiceTypeInfo typeInfo) =>
			typeInfo.Kind switch
			{
				ServiceTypeKind.String => "str",
				ServiceTypeKind.DateTime => "str",
				ServiceTypeKind.Boolean => "bool",
				ServiceTypeKind.Float => "float",
				ServiceTypeKind.Double => "float",
				ServiceTypeKind.Int32 => "int",
				ServiceTypeKind.Int64 => "int",
				ServiceTypeKind.Decimal => "decimal.Decimal",
				ServiceTypeKind.Bytes => "bytes",
				ServiceTypeKind.Object => "object",
				ServiceTypeKind.Error => "facility.Error",
				ServiceTypeKind.Dto => typeInfo.Dto!.Name,
				ServiceTypeKind.Enum => typeInfo.Enum!.Name,
				ServiceTypeKind.Result => "facility.Result",
				ServiceTypeKind.Array => "list",
				ServiceTypeKind.Map => "dict",
				ServiceTypeKind.Nullable => "TODO",
				_ => throw new ArgumentException("Type kind out of range.", nameof(typeInfo)),
			};

		public static string RenderFieldTypeDeclaration(ServiceTypeInfo typeInfo) =>
			typeInfo.Kind switch
			{
				ServiceTypeKind.String => "str",
				ServiceTypeKind.DateTime => "str",
				ServiceTypeKind.Boolean => "bool",
				ServiceTypeKind.Float => "float",
				ServiceTypeKind.Double => "float",
				ServiceTypeKind.Int32 => "int",
				ServiceTypeKind.Int64 => "int",
				ServiceTypeKind.Decimal => "decimal.Decimal",
				ServiceTypeKind.Bytes => "bytes",
				ServiceTypeKind.Object => "object",
				ServiceTypeKind.Error => "facility.Error",
				ServiceTypeKind.Dto => $"\"{typeInfo.Dto!.Name}\"",
				ServiceTypeKind.Enum => $"\"{typeInfo.Enum!.Name}\"",
				ServiceTypeKind.Result => $"facility.Result[{RenderFieldTypeDeclaration(typeInfo.ValueType!)}]",
				ServiceTypeKind.Array => $"typing.List[{RenderFieldTypeDeclaration(typeInfo.ValueType!)}]",
				ServiceTypeKind.Map => $"typing.Dict[str, {RenderFieldTypeDeclaration(typeInfo.ValueType!)}]",
				ServiceTypeKind.Nullable => "TODO",
				_ => throw new ArgumentException("Type kind out of range.", nameof(typeInfo)),
			};

		public IEnumerable WhereNotObsolete(IEnumerable items)
		{
			foreach (var item in items)
			{
				if (item is ServiceElementWithAttributesInfo withAttributes)
				{
					if (!withAttributes.IsObsolete)
						yield return item;
				}
				else if (item is HttpMethodInfo httpMethod)
				{
					if (!httpMethod.ServiceMethod.IsObsolete)
						yield return item;
				}
				else if (item is HttpFieldInfo httpField)
				{
					if (!httpField.ServiceField.IsObsolete)
						yield return item;
				}
				else
				{
					throw new InvalidOperationException("WhereNotObsolete: Unsupported type " + item.GetType().Name);
				}
			}
		}

		public static string? StatusCodePhrase(HttpStatusCode statusCode)
		{
			s_reasonPhrases.TryGetValue((int) statusCode, out var reasonPhrase);
			return reasonPhrase;
		}

		public static string SnakeCase(string text)
		{
			text = Regex.Replace(text, @"(\p{Ll})(\p{Lu})", "$1_$2").ToLowerInvariant() +
				(s_pythonReserved.Contains(text) ? "_" : "");
			return text;
		}

		public static string PascalCase(string text)
		{
			text = Regex.Replace(text, @"_(\p{L})", x => x.Value.ToUpperInvariant());
			if (char.IsLower(text[0]))
			{
				text = text.Substring(0, 1).ToUpperInvariant() + text.Substring(1);
			}
			return text;
		}

		public static string ToUpper(string text)
		{
			return text.ToUpperInvariant();
		}

		public static string RenderPathAsPythonFString(HttpMethodInfo http)
		{
			string text = http.Path;
			string prefix = "";
			foreach (var field in http.PathFields)
			{
				string key = "{" + field.Name + "}";
				string value = SnakeCase(field.ServiceField.Name);
				text = text.ReplaceOrdinal(key, "{facility.encode(" + value + ")}");
				prefix = "f";
			}
			text = $"{prefix}\"{text}\"";
			return text;
		}

		private static readonly Dictionary<int, string> s_reasonPhrases = new Dictionary<int, string>
		{
			{ 100, "Continue" },
			{ 101, "Switching Protocols" },
			{ 200, "OK" },
			{ 201, "Created" },
			{ 202, "Accepted" },
			{ 203, "Non-Authoritative Information" },
			{ 204, "No Content" },
			{ 205, "Reset Content" },
			{ 206, "Partial Content" },
			{ 300, "Multiple Choices" },
			{ 301, "Moved Permanently" },
			{ 302, "Found" },
			{ 303, "See Other" },
			{ 304, "Not Modified" },
			{ 305, "Use Proxy" },
			{ 307, "Temporary Redirect" },
			{ 400, "Bad Request" },
			{ 401, "Unauthorized" },
			{ 402, "Payment Required" },
			{ 403, "Forbidden" },
			{ 404, "Not Found" },
			{ 405, "Method Not Allowed" },
			{ 406, "Not Acceptable" },
			{ 407, "Proxy Authentication Required" },
			{ 408, "Request Timeout" },
			{ 409, "Conflict" },
			{ 410, "Gone" },
			{ 411, "Length Required" },
			{ 412, "Precondition Failed" },
			{ 413, "Request Entity Too Large" },
			{ 414, "Request-Uri Too Long" },
			{ 415, "Unsupported Media Type" },
			{ 416, "Requested Range Not Satisfiable" },
			{ 417, "Expectation Failed" },
			{ 426, "Upgrade Required" },
			{ 500, "Internal Server Error" },
			{ 501, "Not Implemented" },
			{ 502, "Bad Gateway" },
			{ 503, "Service Unavailable" },
			{ 504, "Gateway Timeout" },
			{ 505, "Http Version Not Supported" },
		};

		private static readonly HashSet<string> s_pythonReserved = new HashSet<string>
		{
			"and",
			"as",
			"assert",
			"bool",
			"break",
			"bytes",
			"class",
			"continue",
			"decimal",
			"def",
			"del",
			"dict",
			"elif",
			"else",
			"enum",
			"except",
			"exec",
			"facility",
			"finally",
			"float",
			"for",
			"from",
			"global",
			"id",
			"if",
			"import",
			"in",
			"int",
			"is",
			"lambda",
			"list",
			"map",
			"next",
			"not",
			"object",
			"or",
			"pass",
			"print",
			"raise",
			"return",
			"self",
			"set",
			"str",
			"try",
			"tuple",
			"type",
			"typing",
			"while",
			"with",
			"yield",
		};
	}
}
