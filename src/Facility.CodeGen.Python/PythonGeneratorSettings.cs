using Facility.Definition.CodeGen;

namespace Facility.CodeGen.Python
{
	/// <summary>
	/// Settings for generating Python.
	/// </summary>
	public sealed class PythonGeneratorSettings : FileGeneratorSettings
	{
		/// <summary>
		/// True if the HTTP documentation should be omitted.
		/// </summary>
		public bool NoHttp { get; set; }
	}
}
