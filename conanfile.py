from conans import ConanFile, CMake, tools
import os

class CrashpadConan(ConanFile):
    name = "crashpad"

    # crashpad does not have tagged releases, instead we track commit ids that
    # show up in official builds of Chromium every now and then...
    commit_id = "ee1d5124a2bfec578a1474b048cf934d92dcf7ba"
    version = commit_id[:7]

    license = "Apache License 2.0"
    url = "https://chromium.googlesource.com/crashpad/crashpad"
    description = "Crashpad is a crash-reporting system."
    settings = "os", "compiler", "build_type", "arch"
    generators = "cmake"

    def _depot_tools(self):
        return os.path.join(self.source_folder, "depot_tools")

    def _crashpad_source_base(self):
        return os.path.join(self.source_folder, "crashpad_source")

    def _crashpad_source(self):
        return os.path.join(self._crashpad_source_base(), "crashpad")

    def build_requirements(self):
        self.build_requires("depot_tools_installer/master@bincrafters/stable")

    def source(self):
        self.run("fetch crashpad", run_environment=True)

    def build(self):
        with tools.environment_append({"PATH": [ self._depot_tools() ]}), tools.chdir(self._crashpad_source()):
            self.run("gn gen out/%s" % self.settings.build_type)
            self.run("ninja -C out/%s -j %s" % (self.settings.build_type, tools.cpu_count()))

    def package(self):
        pass

    def package_info(self):
        self.cpp_info.libs = ["hello"]

