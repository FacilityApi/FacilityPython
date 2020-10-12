using System;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;
using Facility.Definition;
using Facility.Definition.CodeGen;
using Facility.Definition.Http;

namespace Facility.CodeGen.Python
{
	/// <summary>
	/// Generates Python.
	/// </summary>
	public sealed class PythonGenerator : CodeGenerator
	{
		/// <summary>
		/// Generates Python.
		/// </summary>
		/// <param name="settings">The settings.</param>
		/// <returns>The number of updated files.</returns>
		public static int GeneratePython(PythonGeneratorSettings settings) =>
			FileGenerator.GenerateFiles(new PythonGenerator { GeneratorName = nameof(PythonGenerator) }, settings);

		/// <summary>
		/// True if the HTTP documentation should be omitted.
		/// </summary>
		public bool NoHttp { get; set; }

		/// <summary>
		/// Generates the Python.
		/// </summary>
		public override CodeGenOutput GenerateOutput(ServiceInfo serviceInfo)
		{
			var outputFiles = new List<CodeGenFile>();

			var httpServiceInfo = NoHttp ? null : HttpServiceInfo.Create(serviceInfo);

			var templateText = GetEmbeddedResourceText("Facility.CodeGen.Python.template.scriban-txt");
			var outputText = CodeTemplateUtility.Render(templateText, new CodeTemplateGlobals(this, serviceInfo, httpServiceInfo));
			using var stringReader = new StringReader(outputText);

			var fileStart = "";

			string? line;
			while ((line = stringReader.ReadLine()) != null)
			{
				var match = Regex.Match(line, @"^==+>");
				if (match.Success)
				{
					fileStart = match.Value;
					break;
				}
			}

			while (line != null)
			{
				var fileName = line.Substring(fileStart.Length);

				var fileLines = new List<string>();
				while ((line = stringReader.ReadLine()) != null && !line.StartsWith(fileStart, StringComparison.Ordinal))
					fileLines.Add(line);

				// skip exactly one blank line to allow file start to stand out
				if (fileLines.Count != 0 && string.IsNullOrWhiteSpace(fileLines[0]))
					fileLines.RemoveAt(0);

				// remove all blank lines at the end
				while (fileLines.Count != 0 && string.IsNullOrWhiteSpace(fileLines[fileLines.Count - 1]))
					fileLines.RemoveAt(fileLines.Count - 1);

				outputFiles.Add(CreateFile(fileName.Trim(), code =>
				{
					foreach (var fileLine in fileLines)
						code.WriteLine(fileLine);
				}));
			}

			var codeGenComment = CodeGenUtility.GetCodeGenComment(GeneratorName ?? "");
			var patternsToClean = new[]
			{
				new CodeGenPattern("*.md", codeGenComment),
				new CodeGenPattern("*.py", codeGenComment),
			};
			return new CodeGenOutput(outputFiles, patternsToClean);
		}

		/// <summary>
		/// Applies generator-specific settings.
		/// </summary>
		public override void ApplySettings(FileGeneratorSettings settings)
		{
		}

		/// <summary>
		/// Patterns to clean are returned with the output.
		/// </summary>
		public override bool HasPatternsToClean => true;

		private static string GetEmbeddedResourceText(string name)
		{
			using var reader = new StreamReader(typeof(PythonGenerator).Assembly.GetManifestResourceStream(name) ?? throw new InvalidOperationException());
			return reader.ReadToEnd();
		}
	}
}
