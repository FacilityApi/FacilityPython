using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using Faithlife.Build;
using static Faithlife.Build.AppRunner;
using static Faithlife.Build.BuildUtility;
using static Faithlife.Build.DotNetRunner;

internal static class Build
{
	public static int Main(string[] args) => BuildRunner.Execute(args, build =>
	{
		var codegen = "fsdgenpython";

		var dotNetBuildSettings = new DotNetBuildSettings
		{
			NuGetApiKey = Environment.GetEnvironmentVariable("NUGET_API_KEY"),
			DocsSettings = new DotNetDocsSettings
			{
				GitLogin = new GitLoginInfo("FacilityApiBot", Environment.GetEnvironmentVariable("BUILD_BOT_PASSWORD") ?? ""),
				GitAuthor = new GitAuthorInfo("FacilityApiBot", "facilityapi@gmail.com"),
				SourceCodeUrl = "https://github.com/FacilityApi/FacilityPython/tree/master/src",
				ProjectHasDocs = name => !name.StartsWith("fsdgen", StringComparison.Ordinal),
			},
			Verbosity = DotNetBuildVerbosity.Minimal,
			CleanSettings = new DotNetCleanSettings
			{
				FindDirectoriesToDelete = () => s_directoriesToDelete,
			},
		};

		build.AddDotNetTargets(dotNetBuildSettings);

		build.Target("codegen")
			.DependsOn("build")
			.Describe("Generates code from the FSD")
			.Does(() => CodeGen(verify: false));

		build.Target("verify-codegen")
			.DependsOn("build")
			.Describe("Ensures the generated code is up-to-date")
			.Does(() => CodeGen(verify: true));

		build.Target("test")
			.DependsOn("verify-codegen");

		build.Target("pip")
			.DependsOn("clean")
			.DependsOn("verify-codegen")
			.Describe("Creates a pip package")
			.Does(() => CreatePipPackage());

		build.Target("pip-publish")
			.DependsOn("pip")
			.Describe("Publishes a pip package")
			.Does(() => PublishPipPackage());

		build.Target("try-pip-publish")
			.DependsOn("pip")
			.Describe("Publishes a pip package. Ignores failure.")
			.Does(() => PublishPipPackage(ignoreFailure: true));

		void CodeGen(bool verify)
		{
			var configuration = dotNetBuildSettings!.BuildOptions!.ConfigurationOption!.Value;
			var toolPath = FindFiles($"src/{codegen}/bin/{configuration}/netcoreapp3.1/{codegen}.dll").FirstOrDefault();

			var verifyOption = verify ? "--verify" : null;

			RunDotNet("tool", "restore");
			RunDotNet("tool", "run", "FacilityConformance", "fsd", "--output", "conformance/ConformanceApi.fsd", verifyOption);

			RunDotNet(toolPath, "conformance/ConformanceApi.fsd", "conformance/", "--newline", "lf", verifyOption);
		}

		void CreatePipPackage()
		{
			CopyFiles("src", "pip/facilitypython", "*.py");
			RunApp("python", "-m pip install --user --upgrade setuptools wheel twine".Split());
			RunApp("python", new AppRunnerSettings
				{
					Arguments = "setup.py sdist bdist_wheel".Split(),
					WorkingDirectory = "pip",
				});
			RunApp("python", new AppRunnerSettings
				{
					Arguments = "-m twine check dist/*".Split(),
					WorkingDirectory = "pip",
				});
		}

		void PublishPipPackage(bool ignoreFailure = false)
		{
			var settings = new AppRunnerSettings
			{
				Arguments = "-m twine upload dist/* --verbose".Split(),
				WorkingDirectory = "pip",
			};
			if (ignoreFailure)
				settings.IsExitCodeSuccess = _ => true;
			RunApp("python", settings);
		}
	});

	private static readonly string[] s_directoriesToDelete = new string[]
	{
		"pip/facilitypython",
		"pip/facilitypython.egg-info",
		"pip/dist",
		"pip/build",
	};
}
