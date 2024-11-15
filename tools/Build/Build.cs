return BuildRunner.Execute(args, build =>
{
	var codegen = "fsdgenpython";

	var gitLogin = new GitLoginInfo("FacilityApiBot", Environment.GetEnvironmentVariable("BUILD_BOT_PASSWORD") ?? "");

	var dotNetBuildSettings = new DotNetBuildSettings
	{
		NuGetApiKey = Environment.GetEnvironmentVariable("NUGET_API_KEY"),
		DocsSettings = new DotNetDocsSettings
		{
			GitLogin = gitLogin,
			GitAuthor = new GitAuthorInfo("FacilityApiBot", "facilityapi@gmail.com"),
			SourceCodeUrl = "https://github.com/FacilityApi/FacilityPython/tree/master/src",
			ProjectHasDocs = name => !name.StartsWith("fsdgen", StringComparison.Ordinal),
		},
		Verbosity = DotNetBuildVerbosity.Minimal,
		CleanSettings = new DotNetCleanSettings
		{
			FindDirectoriesToDelete = () =>
			[
				"pip/facilitypython",
				"pip/facilitypython.egg-info",
				"pip/dist",
				"pip/build",
			],
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
		var configuration = dotNetBuildSettings.GetConfiguration();
		var verifyOption = verify ? "--verify" : null;

		RunDotNet("FacilityConformance", "fsd", "--output", "conformance/ConformanceApi.fsd", verifyOption);
		RunCodeGen("conformance/ConformanceApi.fsd", "conformance/");

		void RunCodeGen(params string?[] args) =>
			RunDotNet(new[] { "run", "--no-build", "--project", $"src/{codegen}", "-c", configuration, "--", "--newline", "lf", verifyOption }.Concat(args));
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
