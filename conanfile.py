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

    _scratch_dir = "srcbuild-%s" % version
    _source_dir = os.path.join(_scratch_dir, "crashpad")
    _build_name = "out/Conan"
    _build_dir = os.path.join(_source_dir, _build_name)

    def _depot_tools(self):
        return os.path.join(self.source_folder, "depot_tools")

    def _crashpad_source_base(self):
        return os.path.join(self.source_folder, "crashpad_source")

    def _crashpad_source(self):
        return os.path.join(self._crashpad_source_base(), "crashpad")

    def build_requirements(self):
        self.build_requires("depot_tools_installer/master@nexenio/testing")
        self.build_requires("ninja_installer/1.9.0@bincrafters/stable")

    def source(self):
        tools.mkdir(self._scratch_dir)
        with tools.chdir(self._scratch_dir):
            self.run("fetch crashpad")

    def build(self):
        with tools.chdir(self._source_dir):
            self.run("gn gen %s" % self._build_name)
            self.run("ninja -j%d -C %s" % (tools.cpu_count(), self._build_name))

    def _copy_lib(self, src_dir):
        self.copy("*.a", dst="lib", 
                  src=os.path.join(self._build_dir, src_dir), keep_path=False)
        self.copy("*.lib", dst="lib", 
                  src=os.path.join(self._build_dir, src_dir), keep_path=False)
        
    def _copy_headers(self, dst_dir, src_dir):
        self.copy("*.h", dst=os.path.join("include", dst_dir), 
                         src=os.path.join(self._source_dir, src_dir))

    def package(self):
        self.copy("LICENSE", dst="licenses", src=self._source_dir, 
                             ignore_case=True, keep_path=False)

        self._copy_headers("crashpad/client", "client")
        self._copy_headers("crashpad/util",   "util")
        self._copy_headers("mini_chromium",   "third_party/mini_chromium/mini_chromium")
        self._copy_lib("obj/client")
        self._copy_lib("obj/util")
        self._copy_lib("obj/third_party/mini_chromium")

    def package_info(self):
        self.cpp_info.includedirs = [ "include/crashpad", "include/mini_chromium" ]
        self.cpp_info.libdirs = [ "lib" ]
        self.cpp_info.libs = tools.collect_libs(self)
