using System.Reflection;
using Facility.Definition;
using Facility.Definition.Fsd;
using NUnit.Framework;

namespace Facility.CodeGen.Python.UnitTests
{
	public sealed class PythonGeneratorTests
	{
		[Test]
		public void GenerateExampleApiSuccess()
		{
			ServiceInfo service;
			const string fileName = "Facility.CodeGen.Python.UnitTests.ConformanceApi.fsd";
			var parser = new FsdParser(new FsdParserSettings { SupportsEvents = true });
			var stream = GetType().GetTypeInfo().Assembly.GetManifestResourceStream(fileName);
			Assert.That(stream, Is.Not.Null);
			using (var reader = new StreamReader(stream!))
				service = parser.ParseDefinition(new ServiceDefinitionText(Path.GetFileName(fileName), reader.ReadToEnd()));

			var generator = new PythonGenerator
			{
				GeneratorName = "PythonGeneratorTests",
			};
			generator.GenerateOutput(service);
		}
	}
}
