using System.Reflection;
using Facility.Definition;
using Facility.Definition.Fsd;
using NUnit.Framework;

namespace Facility.CodeGen.Python.UnitTests
{
	internal sealed class PythonGeneratorTests
	{
		[Test]
		public void GenerateExampleApiSuccess()
		{
			var generator = CreateGenerator();
			generator.GenerateOutput(ParseEmbeddedFsd("Facility.CodeGen.Python.UnitTests.ConformanceApi.fsd"));
		}

		[Test]
		public void GenerateLargeDataSuccess()
		{
			var fieldLines = string.Join(Environment.NewLine, Enumerable.Range(1, 1001).Select(index => $"\t\tfield{index}: string;"));
			var fsdText =
				$$"""
				service LargeApi
				{
					data LargeData
					{
				{{fieldLines}}
					}
				}
				""";

			var generator = CreateGenerator();
			generator.GenerateOutput(ParseFsd("LargeApi.fsd", fsdText));
		}

		private static PythonGenerator CreateGenerator() =>
			new()
			{
				GeneratorName = "PythonGeneratorTests",
			};

		private static ServiceInfo ParseEmbeddedFsd(string fileName)
		{
			var stream = typeof(PythonGeneratorTests).GetTypeInfo().Assembly.GetManifestResourceStream(fileName);
			Assert.That(stream, Is.Not.Null);
			using var reader = new StreamReader(stream!);
			return ParseFsd(Path.GetFileName(fileName), reader.ReadToEnd());
		}

		private static ServiceInfo ParseFsd(string fileName, string text)
		{
			var parser = new FsdParser(new FsdParserSettings { SupportsEvents = true });
			return parser.ParseDefinition(new ServiceDefinitionText(fileName, text));
		}
	}
}
