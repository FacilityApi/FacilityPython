using System.Globalization;
using System.Linq.Expressions;
using System.Text.RegularExpressions;
using Scriban;
using Scriban.Runtime;

namespace Facility.CodeGen.Python
{
	internal static class CodeTemplateUtility
	{
		public static string Render(string templateText, CodeTemplateGlobals globals)
		{
			var templateContext = new TemplateContext { StrictVariables = true, MemberRenamer = x => x.Name };
			templateContext.PushCulture(new CultureInfo("en-US"));
			templateContext.PushGlobal(CreateScriptObject(globals));

			var template = Template.Parse(templateText);
			var text = template.Render(templateContext);

			text = Regex.Replace(text, @"[ \t]+\n", "\n");
			text = Regex.Replace(text, @"\n\n\n\n+", "\n\n\n");
			text = Regex.Replace(text, @"\n+$", "\n");

			return text;
		}

#if !NETSTANDARD2_0
		internal static string ReplaceOrdinal(this string text, string oldValue, string newValue) => text.Replace(oldValue, newValue, StringComparison.Ordinal);
#else
		internal static string ReplaceOrdinal(this string text, string oldValue, string newValue) => text.Replace(oldValue, newValue);
#endif

		private static ScriptObject CreateScriptObject(object globals)
		{
			var scriptObject = new ScriptObject();

			foreach (var (name, methodInfo) in globals.GetType().GetProperties().Select(x => (x.Name, x.GetMethod!))
				.Concat(globals.GetType().GetMethods().Select(x => (x.Name, x))))
			{
				scriptObject.Import(name,
					methodInfo.CreateDelegate(Expression.GetDelegateType(
						methodInfo.GetParameters().Select(parameter => parameter.ParameterType)
							.Concat([methodInfo.ReturnType])
							.ToArray()), methodInfo.IsStatic ? null : globals));
			}

			return scriptObject;
		}
	}
}
