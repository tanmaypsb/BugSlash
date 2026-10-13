const CAPABILITIES = {
  python: { extensions: [".py"], analyzers: ["ruff"], findingRules: null },
  javascript: { extensions: [".js", ".jsx"], analyzers: ["eslint"], findingRules: ["quotes"] },
  typescript: { extensions: [".ts", ".tsx"], analyzers: ["eslint"], findingRules: ["quotes"] },
  c: { extensions: [".c", ".h"], analyzers: ["clang-tidy"], findingRules: ["readability-braces-around-statements"] },
  cpp: { extensions: [".cpp", ".cc", ".cxx", ".hpp"], analyzers: ["clang-tidy"], findingRules: ["readability-braces-around-statements"] },
  java: { extensions: [".java"], analyzers: ["spotbugs"], findingRules: [] },
  go: { extensions: [".go"], analyzers: ["staticcheck"], findingRules: [] },
  rust: { extensions: [".rs"], analyzers: ["clippy"], findingRules: ["clippy::let_and_return"] },
};

export function supportsAutofixSource(fileName, language) {
  const capability = CAPABILITIES[String(language || "").toLowerCase()];
  const extension = String(fileName || "").toLowerCase().match(/\.[^.\\/]+$/)?.[0];
  return Boolean(capability && extension && capability.extensions.includes(extension));
}

export function supportsFindingAutofix(fileName, language, analyzer, category) {
  const capability = CAPABILITIES[String(language || "").toLowerCase()];
  return Boolean(
    supportsAutofixSource(fileName, language) &&
    capability.analyzers.includes(String(analyzer || "").toLowerCase()) &&
    (capability.findingRules === null ||
      capability.findingRules.includes(String(category || "").toLowerCase()))
  );
}
